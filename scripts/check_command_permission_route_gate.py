#!/usr/bin/env python3
"""Run the offline command/permission route gate as one planning-only check."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import protected_paths


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_QUERY_CONTRACT = REPO_ROOT / "docs" / "permissions_admin_query_failclosed_contract.json"
DEFAULT_PLAYER_IDENTITY_DECISIONS = REPO_ROOT / "docs" / "player_identity_public_contract_decisions.json"
DEFAULT_PUBLIC_SDK_SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
DEFAULT_PLAYER_IDENTITY_PRIVATE_CANDIDATE = (
    REPO_ROOT / "docs" / "research" / "2026-06-01-player-identity-private-candidate-contract.json"
)
DEFAULT_PLAYER_IDENTITY_LIFECYCLE_ANCHOR_CANDIDATES = (
    REPO_ROOT
    / "docs"
    / "research"
    / "player-identity-planning-sources"
    / "players-identity-lifecycle-anchor-candidates.json"
)
DEFAULT_PLAYER_IDENTITY_PRINCIPAL_INVALIDATION_POLICY = (
    REPO_ROOT
    / "docs"
    / "research"
    / "player-identity-planning-sources"
    / "players-identity-principal-invalidation-policy.json"
)
DEFAULT_PUBLIC_HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"
COMMAND_RESPONSE_DEFAULT_READINESS_NAME = "command-chat-response-route-planning-readiness.json"
COMMAND_RESPONSE_DEFAULT_REPORT_NAME = "command-chat-response-public-readiness.json"
COMMAND_RESPONSE_REPORT_SOURCE_ARTIFACT_KEYS = (
    "readiness_path",
    "decisions_path",
    "surfaces_path",
    "public_header_path",
)

REPORT_SCHEMA = "obelisk.command-permission-route-gate-check.v1"
PLAYER_IDENTITY_FIRST_EVIDENCE_SCHEMA = "obelisk.player-identity-first-evidence-readiness.v1"
PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA = "obelisk.player-identity-promotion-certificate.v1"
APPROVED_RUNTIME_EVIDENCE_REPORT_SCHEMA = (
    "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1"
)
APPROVED_RUNTIME_EVIDENCE_INPUT_SCHEMA = (
    "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1"
)
EXPECTED_ROUTE_CHECK_SCHEMAS = {
    "player_identity_public_contract_gap": "obelisk.player-identity-public-contract-gap-report.v1",
    "permissions_query_failclosed": "obelisk.permissions-admin-query-failclosed-contract-check.v1",
    "permissions_admin_public_readiness": "obelisk.permissions-admin-public-readiness-check.v1",
    "command_copied_response_intent_planning": "obelisk.command-copied-response-intent-planning-check.v1",
    "command_copied_response_intent_lifecycle_planning": (
        "obelisk.command-copied-response-intent-lifecycle-planning-check.v1"
    ),
    "command_principal_authz_response_bridge": "obelisk.command-principal-authz-response-bridge-check.v1",
    "command_chat_response_public_readiness": "obelisk.command-chat-response-public-readiness-check.v1",
    "commands_replies_public_readiness": "obelisk.commands-replies-public-readiness-check.v1",
}
REQUIRED_PLANNING_ONLY_CHECKS = {
    "permissions_admin_public_readiness",
    "command_copied_response_intent_planning",
    "command_copied_response_intent_lifecycle_planning",
    "command_principal_authz_response_bridge",
    "command_chat_response_public_readiness",
    "commands_replies_public_readiness",
}
REQUIRED_LOCKED_CHILD_CHECKS = {
    "permissions_admin_public_readiness",
    "command_chat_response_public_readiness",
    "commands_replies_public_readiness",
}
CANONICAL_V1_DEPENDENCY_SEQUENCE = [
    "obelisk.player_identity.v1",
    "obelisk.permissions_admin.v1",
    "obelisk.command_chat_response_path.v1",
    "obelisk.commands_replies.v1",
]
SHA256_RE = re.compile(r"[0-9a-fA-F]{64}")
POST_RUNTIME_IDENTITY_CONTRACT_CHILD_LOCK_BLOCKERS = {
    "accounting_lock_route_blocker_stale_after_approved_runtime_evidence",
    "accounting_lock_remaining_route_blocker_stale_after_approved_runtime_evidence",
}
POST_RUNTIME_IDENTITY_CONTRACT_CHILD_LOCK_CLAIMS = {
    "identity_input_diagnostics.accepted_runtime_evidence_observed",
    "next_steps.identity_input_diagnostics.accepted_runtime_evidence_observed",
}
POST_RUNTIME_IDENTITY_CONTRACT_RESPONSE_REPORT_DERIVED_BLOCKERS = {
    "response_path_report_not_accepted_for_planning",
    "response_path_report_not_planning_only",
    "response_path_report_blockers_not_empty",
    "response_path_report_source_artifact_revalidation_failed",
}
POST_RUNTIME_IDENTITY_CONTRACT_GAP_CHECK_BLOCKERS = {
    "public_text_or_source_overclaim",
    "readiness_flag_not_false",
}
POST_RUNTIME_IDENTITY_CONTRACT_GAP_CHECK_CLAIMS = {
    "blocker_details[0].claims[0].value",
    "blocker_details[1].value",
    "blocker_details[1].claims[1].value",
    "blocker_details[1].claims[3].value",
    "blocker_details[2].expected.p0_dependency_chain",
    "blocker_details[2].observed.p0_dependency_chain",
    "blocker_details[2].value",
    "blocker_details[4].claims[0].value",
    "blocker_details[5].value",
    "identity_public_contract_gate_missing",
    "identity_public_contract_gate_missing.next_auditable_blocker.next_required_artifact.p0_dependency_chain",
    "identity_public_contract_gate_missing.post_runtime_contract_gap_diagnostic.approved_runtime_bundle_consumed",
    "identity_public_contract_gate_missing.post_runtime_contract_gap_diagnostic.next_required_artifact.p0_dependency_chain",
    "next_offline_actions[0].next_required_artifact.p0_dependency_chain",
    "post_runtime_public_identity_gap_summary",
    "post_runtime_public_identity_gap_summary.approved_runtime_bundle_consumed",
    "post_approved_runtime_evidence_gate.next_required_artifact.p0_dependency_chain",
    "post_runtime_contract_gap_diagnostic.approved_runtime_bundle_consumed",
    "post_runtime_contract_gap_diagnostic.next_required_artifact.p0_dependency_chain",
    "public_abi_promotion_preflight.principal_invalidation_policy.ready",
    "runtime_evidence_contract_review_currentness.runtime_evidence_accepted",
}
UPSTREAM_IDENTITY_LOCK_BLOCKERS = {
    "lifecycle_anchor_first_evidence_provenance_unbound",
}
UPSTREAM_SKIPPED_ROUTE_CHECKS = REQUIRED_LOCKED_CHILD_CHECKS | {
    "player_identity_public_contract_gap",
}
REQUIRED_CHILD_ACCOUNTING_FALSE_KEYS = (
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "public_or_runtime_accounting_allowed",
)
NOTICE_OR_BUNDLE_NON_PROGRESS_FALSE_ALIAS_KEYS = {
    "accepted_bundle",
    "accepted_notice_action",
    "accepted_player_notice_action",
    "accepted_runtime_evidence",
    "approved_bundle_accepted",
    "approved_bundle_request_accepted",
    "approved_notice_action",
    "approved_player_notice_action",
    "approved_runtime_bundle_request_accepted",
    "approved_runtime_evidence_accepted",
    "beta_notice_send_attested",
    "beta_notice_sent",
    "beta_notice_sent_attested",
    "bundle_accepted",
    "confirmed_beta_notice_sent",
    "confirmed_notice_sent",
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
    "player_notice_action_accepted",
    "player_notice_action_bundle_accepted",
    "player_notice_action_dry_run_accepted",
    "player_notice_action_sent",
    "player_notice_bundle_accepted",
    "player_notice_delivery_accepted",
    "player_notice_dry_run_accepted",
    "player_notice_dry_run_sent",
    "player_notice_sent",
}
NOTICE_OR_BUNDLE_STATUS_CONTAINER_KEYS = {
    "accepted_notice_action",
    "approved_bundle",
    "approved_bundle_request",
    "approved_notice_action",
    "approved_runtime_bundle_request",
    "beta_notice",
    "beta_notice_attestation",
    "beta_notice_send",
    "beta_notice_send_attestation",
    "bundle_acceptance",
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
NOTICE_OR_BUNDLE_POSITIVE_STATUS_VALUES = {
    "accepted",
    "accepted_bundle",
    "approved",
    "bundle_accepted",
    "confirmed_send",
    "delivered",
    "delivery_accepted",
    "dry_run_accepted",
    "dry_run_passed",
    "dry_run_sent",
    "notice_sent",
    "passed",
    "sent",
    "sent_ok",
}
MULTI_SURFACE_BETA_CAPTURE_SOURCE_VALUES = {
    "beta_capture_pack",
    "beta_capture_plan",
    "beta_capture_queue",
    "candidate_multi_surface_beta_capture_pack",
    "future_multi_surface_beta_capture_pack",
    "multi_surface",
    "multi_surface_beta_capture",
    "multi_surface_beta_capture_candidate_queue",
    "multi_surface_beta_capture_checker_matrix",
    "multi_surface_beta_capture_non_claim_manifest",
    "multi_surface_beta_capture_pack",
    "multi_surface_beta_capture_plan",
    "multi_surface_beta_capture_plan_queue",
    "multi_surface_beta_capture_queue",
    "multi_surface_candidate_queue",
    "multi_surface_capture_pack",
    "multi_surface_capture_plan",
}
MULTI_SURFACE_BETA_CAPTURE_CONTEXT_RE = (
    r"(?:"
    r"(?:candidate_|future_)?multi_?surface(?:_?beta_?capture)?"
    r"(?:_?(?:candidate_?queue|checker_?matrix|capture_?pack|capture_?plan|"
    r"non_?claim_?manifest|pack|plan|plan_?queue|queue|runbook|artifacts?|manifest))?|"
    r"beta_?capture(?:_?(?:candidate_?pack|candidate_?queue|pack|plan|plan_?queue|queue))?"
    r")"
)
MULTI_SURFACE_BETA_CAPTURE_CLEARANCE_KEYS = {
    "approved_runtime_evidence_missing_cleared",
    "approved_runtime_evidence_missing_resolved",
    "approved_runtime_evidence_missing_satisfied",
    "approved_runtime_evidence_missing_unblocked",
    "clears_approved_runtime_evidence_missing",
    "current_blocker_cleared",
    "current_route_blocker_cleared",
    "route_blocker_cleared",
}
MULTI_SURFACE_BETA_CAPTURE_BLOCKER_KEYS = {
    "approved_runtime_evidence_missing",
    "current_blocker",
    "current_route_blocker",
    "next_blocker",
    "next_route_blocker",
    "remaining_blockers",
    "remaining_route_blockers",
    "route_blocker",
}
POST_EVIDENCE_P0_LOCK_FALSE_KEYS = (
    "authorizes_runtime_work",
    "authorizes_server_operations",
    "authorizes_server_work",
    "authorizes_workspace_work",
    "authorizes_workspace_writes",
    "accepted_runtime_identity_evidence_only_unlock_allowed",
    "identity_evidence_shortcut_allowed",
    "identity_evidence_only_unblocks_p0",
    "identity_evidence_only_unlocks_permissions_admin",
    "identity_evidence_only_unlocks_command_response",
    "identity_evidence_only_unlocks_commands_replies",
    "permissions_admin_unlocked",
    "command_response_unlocked",
    "commands_replies_unlocked",
    "promotion_ready",
    "public_sdk_ready",
    "public_abi_ready",
    "runtime_ready",
    "public_header_allowed",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "counts_toward_complete_sdk_claim",
    "counts_toward_complete_sdk_claim_now",
    "counts_toward_p0_dependency_chain_claim",
    "counts_toward_p0_dependency_chain_claim_now",
    "identity_public_contract_decision_record_reviewed",
    "identity_public_contract_decision_record_hash_current",
    "identity_public_contract_decision_record_contract_review_only",
    "reviewed_hash_current_contract_review_only",
    "player_identity_promotion_certificate_accepted",
    "player_identity_promotion_certificate_hash_bound",
    "player_identity_promotion_certificate_promoted",
    "permissions_admin_unlock_has_hash_bound_player_identity_promotion_certificate",
    "live_ops_authorized",
    "public_or_runtime_accounting_allowed",
    "read_live_logs",
    "reads_live_logs",
    "runtime_capture_authorized",
    "server_operations_authorized",
    "stable_claim_allowed",
    "workspace_writes_authorized",
)
POST_EVIDENCE_P0_LOCK_ZERO_KEYS = (
    "claim_progress_contribution",
    "complete_sdk_claim_progress_contribution",
    "complete_sdk_progress_contribution",
    "p0_dependency_chain_claim_progress_contribution",
    "p0_dependency_chain_progress_contribution",
    "progress",
)
APPROVED_RUNTIME_EVIDENCE_FALSE_KEYS = (
    "counts_toward_complete_sdk",
    "counts_toward_complete_sdk_claim",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_sdk",
    "counts_toward_v1_completion",
    "promotion_ready",
    "public_or_runtime_accounting_allowed",
    "public_header_allowed",
    "public_sdk_ready",
    "public_abi_ready",
    "runtime_ready",
    "v1_completion_ready",
)
APPROVED_RUNTIME_EVIDENCE_EMPTY_KEYS = (
    "public_capability_bits_now",
    "public_callback_abi_now",
)
APPROVED_RUNTIME_EVIDENCE_OPTIONAL_FALSE_KEYS = (
    "p0_progress_ready",
    "public_api_ready",
    "public_readiness",
    "runtime_readiness",
    "sdk_p0_progress_ready",
    "v1_completion_evidence",
    "v1_completion_ready",
)
APPROVED_RUNTIME_EVIDENCE_OPTIONAL_ZERO_KEYS = (
    "claim_progress",
    "claim_progress_contribution",
    "complete_sdk_claim_progress_contribution",
    "complete_sdk_progress_contribution",
    "p0_dependency_chain_claim_progress_contribution",
    "p0_dependency_chain_progress_contribution",
    "p0_progress",
    "progress",
    "progress_contribution",
    "progress_percent",
    "progress_ratio",
    "public_sdk_progress_contribution",
    "runtime_progress_contribution",
    "sdk_p0_progress",
)
APPROVED_RUNTIME_EVIDENCE_OBSERVED_RUNTIME_CASES = [
    "observer_enable",
    "session_start_anchor",
    "session_start_rejected_anchor",
    "session_end_anchor",
]
APPROVED_RUNTIME_EVIDENCE_CONSUMER_CASES = [
    "malformed_or_unsupported_evidence",
    "stale_after_logout",
]
ALLOWED_IDENTITY_LOCK_BLOCKERS = {
    "lifecycle_anchor_first_evidence_provenance_unbound": {
        "next_action": "bind_lifecycle_anchor_and_principal_policy_sources",
        "blocked_until": "bound_lifecycle_anchor_and_principal_policy_sources",
    },
    "approved_runtime_evidence_missing": {
        "next_action": "produce_approved_runtime_principal_lifecycle_evidence",
        "blocked_until": "approved_runtime_principal_lifecycle_evidence",
    },
    "identity_public_contract_gate_missing": {
        "next_action": "review_identity_public_contract_gate",
        "blocked_until": "reviewed_identity_public_contract",
    },
}
APPROVED_RUNTIME_EVIDENCE_BINDING_SCHEMA = (
    "obelisk.player-identity-public-contract-approved-runtime-evidence-binding.v1"
)
APPROVED_RUNTIME_EVIDENCE_BINDING_SCOPE = "reviewed_identity_public_contract_review"
APPROVED_RUNTIME_EVIDENCE_BINDING_RESOLVED_INPUT = "runtime.lifecycle_evidence"
APPROVED_RUNTIME_EVIDENCE_BINDING_FALSE_FLAGS = (
    "public_header_api_abi_sdk_runtime_shortcut_allowed",
    "counts_toward_public_sdk",
    "counts_toward_p0_dependency_chain_claim",
    "promotion_ready",
    "public_sdk_ready",
    "runtime_ready",
    "public_header_allowed",
    "public_abi_ready",
    "public_api_ready",
    "v1_completion_evidence",
)
APPROVED_RUNTIME_EVIDENCE_BINDING_NON_CLAIM = (
    "This binding identifies the accepted runtime lifecycle evidence for the next "
    "offline identity contract review step only; it does not open public header, "
    "public API/ABI/SDK, downstream P0, permissions, commands, lookup, mutation, "
    "return override, runtime readiness, or v1 completion."
)
ACCEPTED_RUNTIME_EVIDENCE_SURFACE_RECORD = {
    "schema": APPROVED_RUNTIME_EVIDENCE_INPUT_SCHEMA,
    "result": "approved runtime principal lifecycle evidence",
    "next_blocker": "identity_public_contract_gate_missing",
    "approved_runtime_evidence_binding_required": True,
    "approved_runtime_evidence_binding": {
        "schema": APPROVED_RUNTIME_EVIDENCE_BINDING_SCHEMA,
        "accepted_for_contract_review": True,
        "resolved_input": APPROVED_RUNTIME_EVIDENCE_BINDING_RESOLVED_INPUT,
        "next_blocker": "identity_public_contract_gate_missing",
        "binding_scope": APPROVED_RUNTIME_EVIDENCE_BINDING_SCOPE,
        "non_claim": APPROVED_RUNTIME_EVIDENCE_BINDING_NON_CLAIM,
        **{key: False for key in APPROVED_RUNTIME_EVIDENCE_BINDING_FALSE_FLAGS},
    },
}
IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_REQUIREMENTS = {
    "id": "reviewed_identity_public_contract_decision_record",
    "checker": "scripts/check_player_identity_public_contract_decision_record.py",
    "review_status": "reviewed",
    "hash_bound_to_current_source_artifacts": True,
    "decision_scope": "contract_review_only",
    "required_before_unlocking": [
        "permissions_admin_unlocked",
        "command_response_unlocked",
        "commands_replies_unlocked",
        "public_sdk_ready",
        "runtime_ready",
        "v1_completion_ready",
    ],
    "non_claim": (
        "Only a reviewed, hash-current, contract-review-only identity public contract decision "
        "record can satisfy the identity public contract review blocker; it still does not "
        "unlock downstream P0 surfaces by itself."
    ),
}
PLAYER_IDENTITY_PROMOTION_CERTIFICATE_REQUIREMENTS = {
    "id": "hash_bound_player_identity_promotion_certificate",
    "schema": PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
    "surface_id": "obelisk.player_identity.v1",
    "v1_dependency_chain": CANONICAL_V1_DEPENDENCY_SEQUENCE,
    "v1_dependency_chain_position": 1,
    "required_by_surface": "obelisk.permissions_admin.v1",
    "required_by_v1_dependency_chain_position": 2,
    "required_certificate_fields": [
        "promotion_status",
        "evidence.reviewed_surface_record_sha256",
        "evidence.reviewed_artifact_hash",
    ],
    "required_reviewed_artifact_hash": "evidence.reviewed_surface_record_sha256",
    "reviewed_artifact_hash_policy": (
        "must match the reviewed identity surface record hash carried by the certificate"
    ),
    "missing_mismatched_or_stale_certificate_counts": False,
    "non_claim": (
        "Only a path-and-sha-bound player identity promotion certificate with a current "
        "reviewed surface record hash can satisfy the permissions/admin dependency; "
        "plain identity, public-contract, status, diagnostic, or placeholder artifacts "
        "remain non-counting."
    ),
}
POST_EVIDENCE_P0_CHILD_GATE_REQUIREMENTS = {
    "permissions_admin_public_readiness": {
        "surface": "obelisk.permissions_admin.v1",
        "required_before_unlocking": [
            "reviewed_identity_public_contract_decision_record",
            "hash_bound_player_identity_promotion_certificate",
            "permissions_admin_promotion_certificate",
        ],
    },
    "command_chat_response_public_readiness": {
        "surface": "obelisk.command_chat_response_path.v1",
        "required_before_unlocking": [
            "reviewed_identity_public_contract_decision_record",
            "hash_bound_player_identity_promotion_certificate",
            "permissions_admin_promotion_certificate",
            "command_chat_response_path_promotion_certificate",
        ],
    },
    "commands_replies_public_readiness": {
        "surface": "obelisk.commands_replies.v1",
        "required_before_unlocking": [
            "reviewed_identity_public_contract_decision_record",
            "hash_bound_player_identity_promotion_certificate",
            "permissions_admin_promotion_certificate",
            "command_chat_response_path_promotion_certificate",
            "commands_replies_promotion_certificate",
        ],
    },
}
STALE_RUNTIME_EVIDENCE_SURFACE_BLOCKERS = {
    "No approved runtime principal lifecycle evidence.",
    "approved_runtime_evidence_missing",
}
FORBIDDEN_PUBLIC_OR_RUNTIME_CLAIM_KEYS = {
    "accepted_runtime_evidence_ready",
    "accepted_runtime_simulation_accepted",
    "accepted_runtime_simulation_ready",
    "admin_authority_ready",
    "admin_route_snapshot_ready",
    "admin_snapshot_ready",
    "admin_status_snapshot_ready",
    "approved_runtime_evidence_ready",
    "approved_runtime_principal_lifecycle_evidence_ready",
    "authz_bridge_ready",
    "authz_ready",
    "authz_response_ready",
    "authorization_ready",
    "blocker_resolved",
    "compact_context_accepted",
    "compact_context_ready",
    "contract_reviewed",
    "active_player_presence_ready",
    "active_players_ready",
    "diagnostic_drift_ready",
    "diagnostic_only",
    "diagnostic_only_non_evidence",
    "drift_ready",
    "header_shape_valid",
    "identity_contract_hash_current",
    "identity_contract_ready",
    "identity_contract_decision_record_contract_review_only",
    "identity_contract_decision_record_hash_current",
    "identity_contract_decision_record_reviewed",
    "identity_contract_reviewed",
    "identity_public_contract_gate_missing",
    "identity_public_contract_allowed",
    "identity_public_contract_gate_ready",
    "identity_public_contract_gate_reviewed",
    "identity_public_contract_gate_unlocked",
    "identity_public_contract_ready",
    "identity_public_contract_reviewed",
    "identity_public_contract_decision_record_reviewed",
    "identity_public_contract_decision_record_hash_current",
    "identity_public_contract_decision_record_contract_review_only",
    "reviewed_hash_current_contract_review_only",
    "hash_current_identity_contract_decision_record",
    "hash_current_identity_public_contract_decision_record",
    "identity_public_contract_record_contract_review_only",
    "identity_public_contract_record_hash_current",
    "identity_public_contract_record_reviewed",
    "reviewed_identity_contract_decision_record",
    "reviewed_identity_public_contract",
    "reviewed_identity_public_contract_decision_record",
    "identity_ready",
    "identity_promoted",
    "identity_promotion_ready",
    "player_identity_public_contract_ready",
    "player_identity_promoted",
    "player_identity_ready",
    "principal_ready",
    "public_identity_allowed",
    "public_identity_promoted",
    "public_identity_ready",
    "public_player_identity_promoted",
    "public_player_identity_ready",
    "public_contract_allowed",
    "public_contract_gate_ready",
    "public_contract_gate_reviewed",
    "public_contract_gate_unlocked",
    "public_contract_ready",
    "public_contract_record_package_ready",
    "public_contract_reviewed",
    "public_reachability",
    "public_reachability_status",
    "public_readiness_ready",
    "p0_unlocked",
    "release_readiness_ready",
    "request_pack_public_contract_record_ready",
    "sdk_ready",
    "stable_sdk_claim_allowed",
    "stable_sdk_ready",
    "v1_0_stable_ready",
    "v1_ready",
    "v1_release_ready",
    "v1_sdk_ready",
    "v1_sdk_support_ready",
    "v1_stable_ready",
    "v1_support_ready",
    "v1_supported",
    "promotion_ready",
    "public_sdk_ready",
    "public_sdk",
    "public_abi_ready",
    "public_abi_allowed",
    "public_reply_abi_ready",
    "public_response_path_ready",
    "runtime_ready",
    "send_chat_ready",
    "route_cleared",
    "route_cleared_for_public_abi",
    "route_cleared_for_public_reply_or_send_chat_abi",
    "route_cleared_for_public_send_chat_abi",
    "scoped_release_statement_ready",
    "scoped_release_statement_counts_toward_completion",
    "scoped_release_statement_counts_toward_complete_sdk_claim",
    "scoped_release_statement_outcomes_satisfy_completion",
    "scoped_statement_ready",
    "scoped_statement_counts_toward_completion",
    "scoped_statement_counts_toward_complete_sdk_claim",
    "scoped_statement_outcomes_satisfy_completion",
    "support_tier_package_ready",
    "support_tier_package_shape_ready",
    "terminal_certificate",
    "terminal_certificate_accepted",
    "terminal_certificate_metadata",
    "terminal_certificate_metadata_accepted",
    "terminal_certificate_metadata_ready",
    "terminal_certificate_ready",
    "terminal_certificate_status",
    "terminal_certificate_status_ready",
    "final_artifact_accepted",
    "final_artifact_ready",
    "final_certificate_accepted",
    "final_certificate_metadata_ready",
    "final_certificate_ready",
    "final_certificate_status_ready",
    "final_gate_accepted",
    "final_gate_ready",
    "final_gate_unlocked",
    "package_shape_accepted",
    "package_shape_evidence",
    "package_shape_evidence_accepted",
    "package_shape_evidence_ready",
    "package_shape_ready",
    "child_checker_placeholder",
    "child_checker_placeholder_accepted",
    "child_checker_placeholder_ready",
    "command_response_planning_package_ready",
    "copied_intent_package_shape_ready",
    "response_planning_report",
    "response_planning_report_accepted",
    "response_planning_report_ready",
    "response_status_report",
    "response_status_report_accepted",
    "response_status_report_ready",
    "status_report",
    "status_report_accepted",
    "status_report_ready",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "public_or_runtime_accounting_allowed",
    "counts_as_public_sdk",
    "counts_as_runtime",
    "counts_as_v1_completion",
    "counts_toward_complete_sdk",
    "counts_toward_complete_sdk_claim",
    "counts_toward_complete_sdk_claim_now",
    "counts_toward_p0_dependency_chain_claim",
    "counts_toward_p0_dependency_chain_claim_now",
    "counts_toward_sdk",
    *NOTICE_OR_BUNDLE_NON_PROGRESS_FALSE_ALIAS_KEYS,
    "route_gate_counts_toward_public_sdk",
    "route_gate_counts_toward_runtime",
    "route_gate_counts_toward_v1_completion",
    "route_gate_public_or_runtime_accounting_allowed",
    "route_gate_non_counting_counts_toward_public_sdk",
    "route_gate_non_counting_counts_toward_runtime",
    "route_gate_non_counting_counts_toward_v1_completion",
    "route_gate_non_counting_override",
    "public_header_allowed",
    "public_header_ready",
    "public_route_ready",
    "public_bridge_abi_allowed",
    "public_command_router_allowed",
    "public_response_abi_allowed",
    "public_reply_or_send_chat_abi_allowed",
    "public_reply_abi_allowed",
    "public_send_chat_abi_allowed",
    "reply_send_chat_router_claims_allowed",
    "public_reply_api",
    "public_send_chat_api",
    "reply_allowed",
    "reply_api_allowed",
    "reply_abi_allowed",
    "send_chat_allowed",
    "send_chat_api_allowed",
    "permissions_admin_ready",
    "permissions_admin_route_ready",
    "permissions_query_ready",
    "permissions_unlocked",
    "permissions_ready",
    "permission_ready",
    "permission_header_allowed",
    "permissions_admin_unlocked",
    "list_player_ready",
    "list_players_ready",
    "kick_player_ready",
    "server_list_players_ready",
    "server_kick_player_ready",
    "command_response_ready",
    "command_response_unlocked",
    "command_chat_response_path_complete",
    "command_chat_response_path_completed",
    "command_chat_response_path_ready",
    "command_response_path_ready",
    "command_response_path_complete",
    "command_response_path_completed",
    "command_planning_ready",
    "commands_replies_final_gate_ready",
    "commands_replies_final_ready",
    "commands_replies_ready",
    "commands_replies_unlocked",
    "counts_as_approved_runtime_evidence",
    "counts_as_runtime_evidence",
    "counts_as_sdk_evidence",
    "response_ready",
    "response_path_ready",
    "response_path_complete",
    "response_path_completed",
    "response_complete",
    "response_completed",
    "reply_ready",
    "reply_unlocked",
    "command_router_allowed",
    "command_router_ready",
    "runtime_delivery_allowed",
    "runtime_delivery_ready",
    "runtime_readiness_allowed",
    "runtime_wiring_allowed",
    "server_validation_allowed",
    "bridge_claims_allowed",
    "route_ready",
    "route_readiness_ready",
    "route_snapshot_accepted",
    "route_snapshot_ready",
    "route_gate_unlocked",
    "public_response_path_allowed",
    "broadcast_ready",
    "broadcast_status",
    "rcon_command_ready",
    "rcon_command_status",
    "rcon_ready",
    "rcon_route_ready",
    "rcon_route_status",
    "rcon_status",
    "v1_completion_evidence",
    "v1_completion_ready",
    "complete",
    "runtime_evidence_present",
    "runtime_evidence_ready",
    "runtime_principal_lifecycle_start_end_evidence_ready",
    "runtime_principal_start_end_evidence_ready",
    "sdk_evidence_ready",
    "stable_claim_allowed",
    "start_end_evidence_ready",
    "start_end_only_evidence_ready",
    "start_end_only_ready",
    "publication_allowed",
    "publication_authorized",
    "package_publication_allowed",
    "plugin_hub_ready",
    "plugin_hub_publication_allowed",
    "plugin_hub_readiness_claim_allowed",
    "plugin_hub_package_published",
    "plugin_hub_counts_toward_completion",
    "plugin_hub_counts_toward_public_sdk",
    "plugin_hub_counts_toward_v1_completion",
    "plugin_hub_planning_accepted",
    "plugin_hub_planning_ready",
    "plugin_hub_planning_supported",
    "plugin_hub_seed_ready",
    "plugin_hub_support_tier_ready",
    "operator_approval_granted",
    "observer_enabled",
    "observer_enabled_ready",
    "observer_enablement_ready",
    "player_presence_ready",
    "live_posture_ready",
    "live_server_posture_ready",
    "server_posture_ready",
    "runtime_posture_ready",
    "runtime_approval",
    "runtime_approval_granted",
    "runtime_work_authorized",
    "server_operations_authorized",
    "dependency_chain_unlocked",
    "public_dependency_chain_unlocked",
    "v1_dependency_chain_unlocked",
}
BROAD_PUBLIC_OR_RUNTIME_CLAIM_KEY_RE = re.compile(
    r"^(?:"
    r"(?:.*_)?counts_(?:towards?|as)_(?:public_)?sdk(?:_claim)?|"
    r"(?:.*_)?counts_(?:towards?|as)_(?:runtime|v1_completion|complete_sdk(?:_claim)?)|"
    r"(?:complete|full|stable|production(?:_ready|_grade)?)_(?:sdk|api|support)"
    r"(?:_(?:ready|allowed|supported|enabled|public))?|"
    r"(?:sdk|api|support)_(?:complete|full|stable|production(?:_ready|_grade)?)"
    r"(?:_(?:ready|allowed|supported|enabled|public))?|"
    r"public_api(?:_(?:ready|allowed|supported|enabled|public))?|"
    r"(?:identity_)?public_contract(?:_gate)?_(?:ready|reviewed|allowed|supported|enabled|public|unlocked)|"
    r"(?:identity_)?contract_(?:ready|reviewed)|"
    r"(?:accepted|approved)_runtime(?:_principal_lifecycle)?_evidence_(?:ready|accepted|approved|available|supported)|"
    r"v1(?:_0)?(?:_(?:sdk|api|public|release|stable|completion|support))*_"
    r"(?:ready|supported|allowed|enabled|public|complete|stable)"
    r")$"
)
BROAD_P0_ROUTE_ALIAS_SCOPE_RE = re.compile(
    r"(?:^|_)(?:"
    + MULTI_SURFACE_BETA_CAPTURE_CONTEXT_RE
    + r"|"
    r"accepted_runtime_simulation|"
    r"admin_authority|"
    r"admin_(?:route_)?snapshot|admin_status_snapshot|"
    r"authz(?:_?(?:bridge|response|ready))?|authorization|"
    r"child_?checker_?placeholders?|"
    r"(?:command_principal_authz_response_)?bridge(?:_report)?|"
    r"(?:authz_response|response)_bridge(?:_report)?|"
    r"command_principal_authz_bridge(?:_report)?|"
    r"command(?:_chat)?_response(?:_path)?|command_planning|command_router|command_routing|"
    r"command_response_planning|"
    r"compact_context|"
    r"copied_intent(?:_planning)?|"
    r"commands?_repl(?:y|ies)|dependency_chain|"
    r"final_?(?:gate|certificate|artifact)(?:_?(?:metadata|reports?|status))?|"
    r"broadcast(?:_notice)?|"
    r"package_shape(?:_evidence)?|public_contract_record(?:_package)?|"
    r"plugin_hub(?:_planning|_seed|_support|_package|_package_shape)?|publication|"
    r"permissions?_admin|permissions?_quer(?:y|ies)|permission(?:_header|_query)?|"
    r"public_(?:abi|api|header|readiness|reachability|route|runtime|sdk)|"
    r"list_players?|list_player(?:_capture|_candidate)?|kick(?:_player)?|kickplayer|"
    r"server_(?:list_players|kick_player)|"
    r"rcon(?:_command)?(?:_candidate|_route|_status)?|"
    r"reply(?:_(?:abi|api|endpoint|path))?|replies(?:_(?:abi|api|endpoint|path))?|"
    r"response(?:_path)?|"
    r"response_planning(?:_reports?|_packages?)?|response_status(?:_reports?)?|"
    r"route(?:_(?:accepted|acceptance|cleared|gate|readiness|snapshot))?|"
    r"request_pack(?:_public_contract_record)?|"
    r"runtime(?:_(?:capture|delivery|readiness|wiring|work))?|"
    r"send_chat|server_operations|stable_(?:claim|sdk)|"
    r"scoped(?:_non_complete)?(?:_v1)?_release_statement(?:_outcomes)?|"
    r"scoped(?:_non_complete)?(?:_v1)?_statement(?:_outcomes)?|"
    r"support(?:_tier)?(?:_readiness|_report|_package|_package_shape)|"
    r"terminal_certificates?(?:_metadata|_status|_reports?)?|"
    r"(?:complete|full|production)_sdk|"
    r"p0(?:_(?:completion|dependency|progress|release|surface|chain))*|"
    r"v1(?:_0)?(?:_(?:api|completion|release|sdk|stable|support))*"
    r")(?:_|$)"
)
BROAD_P0_ROUTE_ALIAS_STATE_RE = re.compile(
    r"(?:^|_)(?:"
    r"accepted|approved|allowed|available|authorized|complete|completed|enabled|"
    r"granted|implemented|live|opened|promoted|public|ready|reviewed|stable|"
    r"supported|unlocked|validated|verified"
    r")(?:_|$)"
)
BROAD_P0_PROGRESS_OR_CREDIT_ALIAS_RE = re.compile(
    r"(?:^|_)(?:"
    r"claim_progress|credit|credited|progress|progress_contribution|progress_percent|"
    r"progress_ratio|readiness_credit|sdk_credit|sdk_completion_credit|"
    r"v1_completion_credit|public_sdk_credit|counts?(?:_towards?|_toward|_as)?"
    r")(?:_|$)"
)
APPROVED_RUNTIME_EVIDENCE_BLOCKER_ALIAS_RE = re.compile(
    r"(?:^|_)approved_runtime(?:_principal_lifecycle)?_evidence_"
    r"(?:missing|required(?:_before_[a-z0-9_]+)?)$"
)
PROMOTED_SURFACE_COUNT_ALIAS_KEYS = {
    "promoted_count",
    "promoted_surface_count",
    "promoted_surface_total",
    "promoted_surfaces_count",
    "promoted_surfaces_total",
    "surface_promoted_count",
    "surface_promoted_total",
    "surfaces_promoted_count",
    "surfaces_promoted_total",
    "surface_promotion_count",
    "surface_promotion_total",
    "surfaces_promotion_count",
    "surfaces_promotion_total",
}
NON_FALSE_PUBLIC_OR_RUNTIME_CLAIM_KEYS = {
    "blocker_resolved",
    "p0_unlocked",
}
PUBLIC_SURFACE_STATUS_ALIAS_SUFFIXES = {
    "identity_public_surface_status",
    "public_identity_surface_status",
    "public_surface_status",
}
BROAD_P0_ROUTE_ALIAS_EXEMPT_KEYS = frozenset(
    (
        "accepted_runtime_evidence_context",
        "approved_runtime_evidence_binding_required",
        "approved_runtime_evidence",
        "approved_runtime_evidence_binding",
        "approved_runtime_principal_lifecycle_evidence_manifest",
        "approved_runtime_evidence_present",
        "owner_token_sdk_consumer_contract",
        "post_approved_runtime_evidence_gate",
        "post_approved_runtime_evidence_route_check",
        "public_abi_preflight_candidate",
        "public_abi_promotion_preflight",
        "public_header_contract_scan",
        "public_header_scan",
        "route_context_public_sdk_surfaces",
        "runtime_evidence_ready",
        "source_checker_approved_runtime_evidence_manifest",
    )
)
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
    "accepted",
    "allowed",
    "approved",
    "authorized",
    "available",
    "claim_state",
    "claim_value",
    "enabled",
    "is_ready",
    "outcome",
    "promoted",
    "public",
    "ready",
    "result",
    "source_accepted",
    "source_outcome",
    "source_ready",
    "source_result",
    "source_state",
    "source_status",
    "source_supported",
    "state",
    "status",
    "unlocked",
    "value",
    "verdict",
}
SOURCE_MARKER_KEYS = {"source_marker", "source_markers"}
SOURCE_PROVENANCE_CONTEXT_KEYS = {
    "artifact_provenance",
    "evidence_provenance",
    "metadata_provenance",
    "provenance",
    "provenance_marker",
    "provenance_markers",
    "review_provenance",
    "route_provenance",
    "snapshot_provenance",
    "source_provenance",
    "source_provenances",
}
SOURCE_STATUS_KEYS = {
    "source_accepted",
    "source_outcome",
    "source_ready",
    "source_result",
    "source_state",
    "source_status",
    "source_supported",
}
PLAYER_IDENTITY_PROMOTION_CERTIFICATE_CONTEXT_KEYS = frozenset(
    {
        "certificate_build_report",
        "certificate_builder_report",
        "certificate_generation_report",
        "generated_certificate",
        "generated_certificate_reference",
        "generated_promotion_certificate",
        "generated_promotion_certificate_reference",
        "identity_certificate_reference",
        "identity_promotion_certificate_reference",
        "player_identity_certificate_reference",
        "player_identity_promotion_certificate",
        "player_identity_promotion_certificate_reference",
        "promotion_certificate_builder_report",
    }
)
PLAYER_IDENTITY_PROMOTION_CERTIFICATE_REFERENCE_KEYS = frozenset(
    {
        "certificate_binding",
        "certificate_reference",
        "generated_certificate",
        "generated_certificate_binding",
        "generated_certificate_reference",
        "generated_promotion_certificate",
        "generated_promotion_certificate_binding",
        "generated_promotion_certificate_reference",
        "identity_certificate_reference",
        "identity_promotion_certificate_reference",
        "player_identity_certificate_reference",
        "player_identity_promotion_certificate",
        "player_identity_promotion_certificate_binding",
        "player_identity_promotion_certificate_reference",
        "promotion_certificate_binding",
        "promotion_certificate_reference",
    }
)
PLAYER_IDENTITY_PROMOTION_CERTIFICATE_CANONICAL_REFERENCE_KEYS = frozenset(
    {
        "hash_bound_player_identity_promotion_certificate",
        "player_identity_promotion_certificate",
        "player_identity_promotion_certificate_binding",
        "player_identity_promotion_certificate_reference",
    }
)
PLAYER_IDENTITY_PROMOTION_CERTIFICATE_POSITIVE_KEYS = frozenset(
    {
        "accepted",
        "approved",
        "binding_valid",
        "certificate_binding_valid",
        "generated_certificate_valid",
        "hash_bound_to_current_source_artifacts",
        "identity_surface_certificate_binding_valid",
        "promotion_status",
        "promoted",
        "ready",
        "state",
        "status",
    }
)
PLAYER_IDENTITY_PROMOTION_CERTIFICATE_STALE_OR_MISMATCH_KEYS = frozenset(
    {
        "certificate_hash_mismatch",
        "certificate_mismatched",
        "certificate_stale",
        "current_certificate_mismatch",
        "current_hash_mismatch",
        "hash_mismatch",
        "mismatch",
        "mismatched",
        "missing_mismatched_or_stale_certificate_counts",
        "reviewed_artifact_hash_mismatch",
        "reviewed_surface_record_hash_mismatch",
        "stale",
        "stale_certificate",
    }
)
PLAYER_IDENTITY_PROMOTION_CERTIFICATE_CURRENT_HASH_KEYS = frozenset(
    {
        "current_reviewed_artifact_hash",
        "current_reviewed_surface_record_sha256",
        "current_source_artifact_hash",
        "expected_reviewed_artifact_hash",
        "expected_reviewed_surface_record_sha256",
        "expected_source_artifact_hash",
    }
)
PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_SCHEMA = (
    "obelisk.player-identity-public-contract-decision-record.v1"
)
PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_ID = "reviewed_identity_public_contract_decision_record"
PLAYER_IDENTITY_PUBLIC_CONTRACT_REVIEW_INPUT = "runtime.lifecycle_evidence"
PLAYER_IDENTITY_PROMOTION_CERTIFICATE_PROMOTION_EVIDENCE_KIND = "player_identity_promotion_certificate"
PLAYER_IDENTITY_PROMOTION_CERTIFICATE_FALSE_KEYS = frozenset(
    {
        "approved_runtime_evidence_only",
        "candidate_only",
        "contract_review_only",
        "diagnostic_only",
        "passive_evidence_only",
        "readiness_report_only",
        "review_artifact_only",
    }
)
PLAYER_IDENTITY_PROMOTION_CERTIFICATE_REQUIRED_SEMANTIC_PROOFS = frozenset(
    {
        "approved_runtime_principal_lifecycle_evidence",
        "copied_principal_handle_generation_scope_flags",
        "principal_invalidation_semantics",
        "owner_token_lifecycle_cleanup",
        "reviewed_identity_public_contract_decision_record",
        "public_contract_capability_abi_lifecycle",
        "sdk_consumer_coverage",
    }
)
PLAYER_IDENTITY_PUBLIC_CONTRACT_REVIEW_DECISION_KEYS = (
    "identity_public_contract.reviewed_copied_opaque_principal_pod_abi",
    "identity_public_contract.reviewed_owner_token_lifecycle",
    "identity_public_contract.reviewed_process_local_non_persistent_handles",
    "identity_public_contract.reviewed_no_lookup_persistence_permissions_commands_mutation_return_override",
)
PLAYER_IDENTITY_CONTRACT_REVIEW_FALSE_KEYS = frozenset(
    {
        "commands_ready",
        "live_ops_authorized",
        "lookup_ready",
        "permissions_ready",
        "promotion_ready",
        "public_abi_ready",
        "public_api_ready",
        "public_contract_allowed",
        "public_header_allowed",
        "public_sdk_ready",
        "reads_live_logs",
        "runtime_capture_authorized",
        "runtime_ready",
        "server_operations_authorized",
        "v1_completion_evidence",
        "workspace_writes_authorized",
    }
)
PLAYER_IDENTITY_CONTRACT_REVIEW_EXACT_FIELDS = {
    "complete_identity_public_contract_reviewed": True,
    "partial_identity_contract": False,
    "hash_current_identity_public_contract_decision_record": True,
    "permissions_admin_unlock_allowed": False,
    "permissions_admin_counting_allowed": False,
    "sdk_or_p0_counting_allowed": False,
}
DOWNSTREAM_PROMOTION_CERTIFICATE_ALIAS_KEYS = frozenset(
    {
        "hash_bound_permissions_admin_promotion_certificate",
        "hash_bound_command_chat_response_path_promotion_certificate",
        "hash_bound_command_response_promotion_certificate",
        "hash_bound_commands_replies_promotion_certificate",
        "permissions_admin_promotion_certificate",
        "command_chat_response_path_promotion_certificate",
        "command_response_promotion_certificate",
        "commands_replies_promotion_certificate",
        "promotion_certificate_ready",
    }
)
DOWNSTREAM_PROMOTION_CERTIFICATE_SURFACE_TOKENS = (
    "permissions_admin",
    "permission_admin",
    "command_chat_response_path",
    "command_response",
    "commands_replies",
)
DOWNSTREAM_PROMOTION_CERTIFICATE_DECLARATIVE_VALUE_KEYS = frozenset(
    {
        "blocked_until",
        "blocker",
        "blockers",
        "cannot_unlock_without",
        "current_blocker",
        "current_route_blocker",
        "missing_mismatched_or_stale_certificate_counts",
        "next_blocker",
        "next_route_blocker",
        "non_claim",
        "non_claims",
        "remaining_blockers",
        "remaining_route_blockers",
        "required",
        "required_before_unlocking",
        "required_certificate_fields",
        "required_fields",
        "required_policy",
        "requirements",
        "why_blocked",
    }
)
NON_AUTHORIZING_CONTEXT_RE = re.compile(
    r"(?:"
    + MULTI_SURFACE_BETA_CAPTURE_CONTEXT_RE
    + r"|"
    r"(?:player_?)?notice(?:_?(?:action|bundle|dry_run|sent|accepted))?|"
    r"(?:player_?)?notice_?actions?(?:_?reports?)?|"
    r"beta_?notice(?:_?(?:prep|send|sent|attestation|confirmed))?|"
    r"beta_?notice_?actions?(?:_?reports?)?|"
    r"compact_?contexts?|compact_?summar(?:y|ies)|"
    r"discord_?notice|"
    r"(?:agent_?)?handoff(?:_?(?:notes?|reports?|summar(?:y|ies)))?|"
    r"(?:command_?principal_?authz_?response_?|authz_?response_?|response_?)?bridge_?reports?|"
    r"passive(?:_?(?:snapshot|observation|activity|latest|capture|triplet|monitor|report|status|summary))?|"
    r"diagnostic(?:_?(?:only|summary|triage|observer))?|"
    r"(?:diagnostic_?)?drift(?:_?(?:checks?|diagnostics?|reports?|status|summar(?:y|ies)))?|"
    r"observer_?event_?triage|"
    r"(?:active_?)?players?_?presence(?:_?(?:reports?|status|summar(?:y|ies)|snapshots?))?|"
    r"active_?players?(?:_?(?:detected|present|presence|reports?|status|summar(?:y|ies)))?|"
    r"(?:player_?)?presence(?:_?(?:active|detected|reports?|status|summar(?:y|ies)))?|"
    r"(?:lifecycle_?|principal_?|player_?principal_?|runtime_?)?observers?(?:_?(?:enable|enabled|enablement|reports?|status))?|"
    r"(?:live_?|server_?|runtime_?)?posture(?:_?(?:checks?|reports?|status|snapshots?))?|"
    r"player_?principal_?passive_?snapshot|"
    r"activation_?preconditions?(?:_?(?:artifacts?|reports?))?|"
    r"precondition_?(?:artifacts?|reports?)|"
    r"(?:accepted_?)?runtime_?simulations?|"
    r"pre_?activation_?consistency|"
    r"request_?(?:pack|check|artifact|preflight|readiness)|"
    r"public_?contract_?(?:records?(?:_?packages?)?|status)|"
    r"(?:reviewed_?)?identity_?(?:public_?)?contract_?decision_?record_?templates?|"
    r"(?:approved_?)?(?:runtime_?)?bundle_?requests?|"
    r"broadcast_?(?:notices?|status|reports?)|"
    r"support_?tiers?(?:_?(?:readiness|reports?))?|"
    r"support_?tier_?(?:packages?|package_?shapes?)|"
    r"(?:support_?)?package_?shapes?(?:_?evidence)?|"
    r"terminal_?certificates?(?:_?(?:metadata|status|reports?))?|"
    r"child_?checker_?placeholders?|checker_?placeholders?|"
    r"command_?planning(?:_?packages?|_?package_?shapes?)?|"
    r"command_?(?:chat_?)?response_?planning(?:_?packages?)?|"
    r"response_?planning(?:_?(?:reports?|packages?))?|response_?status(?:_?reports?)?|"
    r"copied_?(?:response_?)?intent(?:_?planning)?(?:_?packages?|_?package_?shapes?)?|"
    r"public_?reachability(?:_?(?:check|ready|report|status))?|"
    r"public_?readiness(?:_?(?:artifact|check|ready|report|status))?|"
    r"public_?header(?:_?(?:artifact|gate|preflight|readiness|report|review|scan|status))?|"
    r"admin_?(?:route_?|status_?)?snapshots?(?:_?(?:status|reports?|candidates?))?|"
    r"(?:server_?)?list_?players?(?:_?(?:status|reports?|candidates?|capture))?|"
    r"(?:server_?)?kick(?:_?players?)?(?:_?(?:status|reports?|candidates?|capture|path))?|"
    r"kick_?path(?:_?(?:status|reports?|candidates?|capture))?|"
    r"rcon_?(?:command_?)?(?:routes?|status|reports?)|rcon_?command_?candidates?|rcon_?route_?candidates?|"
    r"next_?action_?sequence|"
    r"route_?snapshots?(?:_?packages?)?|"
    r"(?:route_?bound_?)?identity_?source(?:_?(?:forward|forwarded|forwarding|readiness|report))?|"
    r"plugin_?hub(?:_?(?:planning|readiness|reports?|support|package|package_?shape))?|"
    r"(?:runtime_?)?window_?(?:manifest|request|execution|executor|executor_?artifact|executor_?closure|closure|status|report)|"
    r"(?:runtime_?principal_?lifecycle_?)?start_?end(?:_?only)?(?:_?evidence)?|"
    r"(?:evidence_?)?closure(?:_?(?:report|request|output|status))?|"
    r"(?:executor|execution)(?:_?(?:artifact|report|closure|output|status))?|"
    r"(?:copied?|copy)_?(?:artifacts?|reports?|status|metadata)|"
    r"copied_?(?:obelisk_?)?logs?(?:_?(?:only|artifact|copy|ready|status|report))?|"
    r"copied_?log_?only(?:_?artifact)?|"
    r"status_?(?:artifacts?|json|reports?|snapshots?|updates?)|"
    r"window_?request_?check|"
    r"player_?principal_?lifecycle_?window_?request|"
    r"route_?(?:simulation|lock_?simulation|check_?readiness|readiness)|"
    r"post_?evidence_?identity_?lock|"
    r"identity_?lock(?:_?(?:simulation|readiness|report))?|"
    r"transfer_?(?:script_?struct|baccept)_?readiness|"
    r"buff_?status_?readiness|"
    r"dino_?scalar_?readiness|"
    r"tribe_?scalar_?boundary_?readiness|"
    r"scalar_?boundary_?readiness|"
    r"mission_?transfer_?dino_?tribe(?:_?buff)?_?accounting|"
    r"side_?lane(?:_?(?:artifacts?|reports?|candidate|candidates))?|"
    r"(?:route_?gate_?)?post_?evidence_?p0_?lock_?simulation|"
    r"simulation_?only"
    r")",
    re.IGNORECASE,
)
NON_AUTHORIZING_ROUTE_ALIAS_KEY_RE = re.compile(
    r"(?:"
    + MULTI_SURFACE_BETA_CAPTURE_CONTEXT_RE
    + r"|"
    r"(?:accepted_?)?runtime_?simulations?|"
    r"(?:command_?principal_?authz_?response_?|authz_?response_?|response_?)?bridge_?reports?|"
    r"(?:player_?)?notice_?actions?(?:_?reports?)?|"
    r"beta_?notice_?actions?(?:_?reports?)?|"
    r"(?:agent_?)?handoff(?:_?(?:notes?|reports?|summar(?:y|ies)))?|"
    r"compact_?contexts?|compact_?summar(?:y|ies)|"
    r"activation_?preconditions?(?:_?(?:artifacts?|reports?))?|"
    r"precondition_?(?:artifacts?|reports?)|"
    r"public_?contract_?records?(?:_?packages?)?|"
    r"(?:reviewed_?)?identity_?(?:public_?)?contract_?decision_?record_?templates?|"
    r"public_?reachability(?:_?(?:check|ready|report|status))?|"
    r"public_?readiness(?:_?(?:artifact|check|ready|report|status))?|"
    r"public_?header(?:_?(?:artifact|gate|preflight|readiness|report|review|scan|status))?|"
    r"admin_?(?:route_?|status_?)?snapshots?(?:_?(?:status|reports?|candidates?))?|"
    r"(?:server_?)?list_?players?(?:_?(?:status|reports?|candidates?|capture))?|"
    r"(?:server_?)?kick(?:_?players?)?(?:_?(?:status|reports?|candidates?|capture|path))?|"
    r"kick_?path(?:_?(?:status|reports?|candidates?|capture))?|"
    r"request_?pack(?:_?public_?contract_?record)?|"
    r"broadcast_?(?:notices?|status|reports?)|"
    r"support_?tiers?(?:_?(?:readiness|reports?))?|"
    r"support_?tier_?(?:packages?|package_?shapes?)|"
    r"(?:support_?)?package_?shapes?(?:_?evidence)?|"
    r"terminal_?certificates?(?:_?(?:metadata|status|reports?))?|"
    r"child_?checker_?placeholders?|checker_?placeholders?|"
    r"rcon_?(?:command_?)?(?:routes?|status|reports?)|rcon_?command_?candidates?|rcon_?route_?candidates?|"
    r"command_?planning(?:_?packages?|_?package_?shapes?)?|"
    r"command_?(?:chat_?)?response_?planning(?:_?packages?)?|"
    r"response_?planning(?:_?(?:reports?|packages?))?|response_?status(?:_?reports?)?|"
    r"copied_?(?:response_?)?intent(?:_?planning)?(?:_?packages?|_?package_?shapes?)?"
    r"|(?:runtime_?)?window_?(?:manifest|request|execution|executor|executor_?artifact|executor_?closure|closure|status|report)"
    r"|(?:runtime_?principal_?lifecycle_?)?start_?end(?:_?only)?(?:_?evidence)?"
    r"|(?:evidence_?)?closure(?:_?(?:report|request|output|status))?"
    r"|(?:executor|execution)(?:_?(?:artifact|report|closure|output|status))?"
    r"|(?:copied?|copy)_?(?:artifacts?|reports?|status|metadata)"
    r"|copied_?(?:obelisk_?)?logs?(?:_?(?:only|artifact|copy|ready|status|report))?"
    r"|copied_?log_?only(?:_?artifact)?"
    r"|status_?(?:artifacts?|json|reports?|snapshots?|updates?)"
    r"|route_?snapshots?(?:_?packages?)?"
    r"|plugin_?hub(?:_?(?:planning|readiness|reports?|support|package|package_?shape))?"
    r"|side_?lane(?:_?(?:artifacts?|reports?|candidate|candidates))?"
    r")",
    re.IGNORECASE,
)
NON_AUTHORIZING_CONTEXT_READY_ALIAS_KEYS = {
    "activation_preconditions_met",
    "activation_ready",
    "approved_bundle_request_ready",
    "approved_runtime_bundle_request_ready",
    "candidate_ready",
    "capture_ready",
    "clears_approved_runtime_evidence_missing",
    "complete_triplet_ready",
    "current_blocker_cleared",
    "current_route_blocker_cleared",
    "debug_capture_ready",
    "identity_lock_ready",
    "identity_source_forwarding_ready",
    "mutation_authority_ready",
    "mode",
    "outcome",
    "passive_triplet_ready",
    "handoff_ready",
    "side_lane_ready",
    "precondition_ready",
    "preconditions_met",
    "public_reachability_ready",
    "queue_status",
    "readiness_ready",
    "ready",
    "request_check_ready",
    "request_pack_ready",
    "result",
    "route_bound_identity_source_forwarding_ready",
    "route_ready",
    "route_blocker_cleared",
    "public_readiness_ready",
    "source_binding_ready",
    "start_end_evidence_ready",
    "start_end_only_evidence_ready",
    "start_end_only_ready",
    "source_accepted",
    "source_outcome",
    "source_ready",
    "source_result",
    "source_state",
    "source_status",
    "source_supported",
    "state",
    "status",
}
NON_AUTHORIZING_CONTEXT_POSITIVE_STATUS_VALUES = NOTICE_OR_BUNDLE_POSITIVE_STATUS_VALUES | {
    "candidate_only_accepted",
    "candidate_ready",
    "certified",
    "complete",
    "complete_triplet",
    "complete_triplet_present",
    "issued",
    "met",
    "passive_triplet_complete",
    "placeholder",
    "reachable",
    "ready",
    "reviewed",
    "signed",
    "satisfied",
    "supported",
    "terminal",
    "true",
    "unlocked",
    "yes",
}
NON_AUTHORIZING_CONTEXT_ZERO_ALIAS_KEYS = {
    "claim_progress_contribution",
    "complete_sdk_claim_progress_contribution",
    "complete_sdk_claim_progress_percent",
    "complete_sdk_claim_progress_ratio",
    "complete_sdk_progress_contribution",
    "complete_sdk_progress_percent",
    "complete_sdk_progress_ratio",
    "p0_dependency_chain_claim_progress_contribution",
    "p0_dependency_chain_claim_progress_percent",
    "p0_dependency_chain_claim_progress_ratio",
    "p0_dependency_chain_progress_contribution",
    "p0_dependency_chain_progress_percent",
    "p0_dependency_chain_progress_ratio",
    "p0_dependency_progress_contribution",
    "p0_progress",
    "p0_progress_contribution",
    "p0_progress_percent",
    "p0_progress_ratio",
    "progress",
    "public_sdk_progress_contribution",
    "runtime_progress_contribution",
    "sdk_progress",
    "sdk_progress_contribution",
    "sdk_progress_percent",
    "sdk_progress_ratio",
    "v1_completion_contribution",
}
IDENTITY_DECISION_RECORD_METADATA_CONTEXT_KEYS = frozenset(
    {
        "hash_current_identity_contract_decision_record",
        "hash_current_identity_public_contract_decision_record",
        "identity_contract_decision_record",
        "identity_public_contract_decision_record",
        "identity_public_contract_record",
        "public_contract_decision_record",
        "reviewed_hash_current_contract_review_only",
        "reviewed_identity_contract_decision_record",
        "reviewed_identity_public_contract",
        "reviewed_identity_public_contract_decision_record",
        "reviewed_identity_public_contract_decision_record_template",
    }
)
IDENTITY_DECISION_RECORD_TEMPLATE_CONTEXT_KEYS = frozenset(
    {
        "identity_contract_decision_record_template",
        "identity_public_contract_decision_record_template",
        "identity_public_contract_record_template",
        "reviewed_identity_contract_decision_record_template",
        "reviewed_identity_public_contract_decision_record_template",
    }
)
IDENTITY_DECISION_RECORD_METADATA_STATUS_KEYS = frozenset(
    {
        "decision_scope",
        "hash_bound_to_current_source_artifacts",
        "hash_current",
        "record_valid_scope",
        "review_status",
        "reviewed_hash_current_contract_review_only",
        "scope",
        "source_artifact_hash_state",
        "state",
        "status",
    }
)
IDENTITY_DECISION_RECORD_DOWNSTREAM_CONTEXT_KEYS = frozenset(
    {
        "command_chat_response",
        "command_response",
        "commands",
        "commands_replies",
        "complete_sdk",
        "permissions",
        "permissions_admin",
        "public_abi",
        "public_api",
        "public_header",
        "public_sdk",
        "runtime",
        "sdk",
        "sdk_completion",
        "send_chat",
        "stable_claim",
        "v1_completion",
    }
)
IDENTITY_DECISION_RECORD_DOWNSTREAM_STATUS_KEYS = frozenset(
    {
        "allowed",
        "available",
        "enabled",
        "readiness",
        "ready",
        "result",
        "state",
        "status",
        "supported",
        "unlocked",
        "value",
    }
)
IDENTITY_DECISION_RECORD_METADATA_REVIEWED_VALUES = frozenset(
    {
        "reviewed",
        "reviewed_hash_current_contract_review_only",
    }
)
IDENTITY_DECISION_RECORD_METADATA_HASH_CURRENT_VALUES = frozenset(
    {
        "current",
        "hash_bound_to_current_source_artifacts",
        "hash_current",
        "reviewed_hash_current_contract_review_only",
    }
)
IDENTITY_DECISION_RECORD_METADATA_SCOPE_VALUES = frozenset(
    {
        "contract_review_only",
        "reviewed_hash_current_contract_review_only",
        "reviewed_identity_public_contract_record_only",
    }
)
IDENTITY_DECISION_RECORD_PROGRESS_ALIAS_KEYS = frozenset(
    {
        "completion_credit",
        "contribution",
        "credit",
        "credits",
        "p0",
        "p0_credit",
        "p0_progress_credit",
        "p0_sdk",
        "percent",
        "percentage",
        "phase0",
        "phase_0",
        "progress_credit",
        "public_sdk_credit",
        "ratio",
        "readiness_credit",
        "sdk_completion_credit",
        "sdk_p0",
        "sdk_p0_credit",
        "v1_completion_credit",
    }
)
IDENTITY_DECISION_RECORD_PROGRESS_ALIAS_RE = re.compile(
    r"(?:^|_)(?:"
    r"credits?|readiness_credit|progress|progress_contribution|progress_percent|progress_ratio|"
    r"percent|percentage|ratio|contribution|"
    r"p0|phase_?0|sdk_p0|p0_sdk|"
    r"counts?(?:_towards?|_toward|_as)?"
    r")(?:_|$)"
)
IDENTITY_DECISION_RECORD_PROGRESS_VALUE_RE = re.compile(
    r"(?:^|_)(?:"
    r"credits?|progress|percent|percentage|ratio|contribution|"
    r"p0|phase_?0|sdk_p0|p0_sdk|"
    r"counts?(?:_towards?|_toward|_as)?"
    r")(?:_|$)"
)


def normalized_claim_key(value: object) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value))
    return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")


def normalized_claim_path_parts(path: str) -> list[str]:
    return [
        part
        for part in (
            normalized_claim_key(raw_part)
            for raw_part in re.split(r"(?:\.|\[\d+\])", path)
        )
        if part
    ]


def identity_decision_record_metadata_context_key(key_name: str) -> bool:
    return (
        key_name in IDENTITY_DECISION_RECORD_METADATA_CONTEXT_KEYS
        or key_name in IDENTITY_DECISION_RECORD_TEMPLATE_CONTEXT_KEYS
        or (
            "decision_record" in key_name
            and ("identity" in key_name or "contract" in key_name or "public" in key_name)
        )
        or ("reviewed_hash_current" in key_name and "contract_review_only" in key_name)
    )


def identity_decision_record_metadata_progress_alias_key(key_name: str) -> bool:
    return (
        key_name in IDENTITY_DECISION_RECORD_PROGRESS_ALIAS_KEYS
        or public_or_runtime_progress_alias_key(key_name)
        or IDENTITY_DECISION_RECORD_PROGRESS_ALIAS_RE.search(key_name) is not None
    )


def identity_decision_record_template_context_key(key_name: str) -> bool:
    return (
        key_name in IDENTITY_DECISION_RECORD_TEMPLATE_CONTEXT_KEYS
        or (
            "template" in key_name
            and "decision_record" in key_name
            and ("identity" in key_name or "contract" in key_name or "public" in key_name)
        )
    )


def normalized_metadata_values(value: Any) -> set[str]:
    if isinstance(value, str):
        return {normalized_claim_key(value)}
    if isinstance(value, bool) or value is None:
        return set()
    if isinstance(value, (int, float)):
        return {str(value)}
    if isinstance(value, list):
        values: set[str] = set()
        for item in value:
            values.update(normalized_metadata_values(item))
        return values
    if isinstance(value, dict):
        values: set[str] = set()
        for item in value.values():
            values.update(normalized_metadata_values(item))
        return values
    return set()


def value_marks_identity_decision_record_metadata(value: Any) -> bool:
    if isinstance(value, str):
        return normalized_claim_key(value) == "reviewed_hash_current_contract_review_only"
    if isinstance(value, list):
        return any(value_marks_identity_decision_record_metadata(item) for item in value)
    if not isinstance(value, dict):
        return False

    reviewed = False
    hash_current = False
    contract_review_only = False
    for key, item in value.items():
        key_name = normalized_claim_key(key)
        item_values = normalized_metadata_values(item)
        if "reviewed_hash_current_contract_review_only" in item_values:
            return True
        if key_name not in IDENTITY_DECISION_RECORD_METADATA_STATUS_KEYS:
            continue
        if item_values & IDENTITY_DECISION_RECORD_METADATA_REVIEWED_VALUES:
            reviewed = True
        if (
            item_values & IDENTITY_DECISION_RECORD_METADATA_HASH_CURRENT_VALUES
            and ("hash" in key_name or key_name in {"state", "status"})
        ):
            hash_current = True
        if item_values & IDENTITY_DECISION_RECORD_METADATA_SCOPE_VALUES:
            contract_review_only = True
    return reviewed and hash_current and contract_review_only


def identity_decision_record_metadata_progress_value_is_positive(item: Any) -> bool:
    if isinstance(item, bool):
        return item
    if isinstance(item, (int, float)):
        return item != 0
    if isinstance(item, str):
        normalized = normalized_claim_key(item)
        if normalized in {
            "",
            "0",
            "0_0",
            "blocked",
            "false",
            "missing",
            "no",
            "none",
            "not_ready",
            "pending",
            "reviewed",
            "current",
            "hash_current",
            "contract_review_only",
            "reviewed_hash_current_contract_review_only",
        }:
            return False
        if re.fullmatch(r"0+\s*/\s*[1-9]\d*", item.strip().casefold()):
            return False
        if re.fullmatch(r"0+(?:\.0+)?\s*(?:%|percent)", item.strip().casefold()):
            return False
        return (
            IDENTITY_DECISION_RECORD_PROGRESS_VALUE_RE.search(normalized) is not None
            or re.fullmatch(
                r"(?:[1-9]\d*(?:\.\d+)?|0\.\d*[1-9]\d*)\s*(?:/|%|percent|of\b)?.*",
                item.strip().casefold(),
            )
            is not None
        )
    if isinstance(item, list):
        return any(identity_decision_record_metadata_progress_value_is_positive(child) for child in item)
    if isinstance(item, dict):
        return any(identity_decision_record_metadata_progress_value_is_positive(child) for child in item.values())
    return False


def identity_decision_record_metadata_status_value_is_positive(item: Any) -> bool:
    if item is True:
        return True
    if isinstance(item, (int, float)) and not isinstance(item, bool):
        return item != 0
    if isinstance(item, str):
        normalized = normalized_claim_key(item)
        if normalized in {
            "",
            "0",
            "0_0",
            "blocked",
            "false",
            "missing",
            "no",
            "none",
            "not_ready",
            "pending",
            "unresolved",
        }:
            return False
        return (
            normalized in IDENTITY_DECISION_RECORD_METADATA_REVIEWED_VALUES
            or normalized in IDENTITY_DECISION_RECORD_METADATA_HASH_CURRENT_VALUES
            or normalized in IDENTITY_DECISION_RECORD_METADATA_SCOPE_VALUES
            or normalized
            in {
                "accepted",
                "allowed",
                "available",
                "complete",
                "enabled",
                "hash_bound",
                "passed",
                "passing",
                "ready",
                "satisfied",
                "supported",
                "true",
                "unlocked",
                "valid",
                "yes",
            }
        )
    if isinstance(item, list):
        return any(identity_decision_record_metadata_status_value_is_positive(child) for child in item)
    if isinstance(item, dict):
        return any(identity_decision_record_metadata_status_value_is_positive(child) for child in item.values())
    return False


def progress_claim_value_is_nonzero(item: Any) -> bool:
    if isinstance(item, bool):
        return item
    if isinstance(item, (int, float)):
        return item != 0
    if isinstance(item, str):
        normalized = item.strip().casefold()
        normalized_key = normalized_claim_key(item)
        if not normalized or normalized_key in {
            "0",
            "0_0",
            "0_percent",
            "blocked",
            "false",
            "missing",
            "no",
            "none",
            "not_ready",
            "pending",
        }:
            return False
        if re.fullmatch(r"0+\s*/\s*[1-9]\d*", normalized):
            return False
        if re.fullmatch(r"0+(?:\.0+)?\s*(?:%|percent)", normalized):
            return False
        return True
    if isinstance(item, list):
        return any(progress_claim_value_is_nonzero(child) for child in item)
    if isinstance(item, dict):
        return any(progress_claim_value_is_nonzero(child) for child in item.values())
    return False


def sha256_file(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def hash_bound_json_artifact(binding: Any) -> dict[str, Any] | None:
    if not isinstance(binding, dict):
        return None
    path_value = binding.get("path")
    sha256_value = binding.get("sha256")
    if not isinstance(path_value, str) or not path_value:
        return None
    if not isinstance(sha256_value, str) or SHA256_RE.fullmatch(sha256_value.strip()) is None:
        return None
    path = Path(path_value)
    if not path.is_absolute():
        path = REPO_ROOT / path
    try:
        protected_paths.reject_symlink_component(path, "player_identity_promotion_certificate")
        path = protected_paths.reject_protected_input_path(
            path,
            "player_identity_promotion_certificate",
        )
    except SystemExit:
        return None
    actual_sha256 = sha256_file(path)
    if actual_sha256 is None or actual_sha256 != sha256_value.strip().lower():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def canonical_json_sha256(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def string_set(value: Any) -> set[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return set()
    return set(value)


def strict_identity_public_contract_review_record(
    evidence: dict[str, Any],
    reviewed_surface_hash: str,
) -> bool:
    review = evidence.get("identity_public_contract_decision_record")
    if not isinstance(review, dict):
        return False
    expected_fields = {
        "schema": PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_SCHEMA,
        "artifact_id": PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_ID,
        "surface": "obelisk.player_identity.v1",
        "active_after_resolved_input": PLAYER_IDENTITY_PUBLIC_CONTRACT_REVIEW_INPUT,
        "review_status": "reviewed",
        "accepted_for_contract_review": True,
        "next_blocker": "public_header_gate_missing",
    }
    if any(review.get(key) != expected for key, expected in expected_fields.items()):
        return False
    record_surface_hash = review.get("reviewed_surface_record_sha256")
    if not isinstance(record_surface_hash, str) or record_surface_hash.lower() != reviewed_surface_hash.lower():
        return False
    if review.get("resolved_decision_keys") != list(PLAYER_IDENTITY_PUBLIC_CONTRACT_REVIEW_DECISION_KEYS):
        return False
    if any(review.get(key) is not False for key in PLAYER_IDENTITY_CONTRACT_REVIEW_FALSE_KEYS):
        return False
    if any(
        review.get(key) != expected
        for key, expected in PLAYER_IDENTITY_CONTRACT_REVIEW_EXACT_FIELDS.items()
    ):
        return False
    record_sha256 = evidence.get("identity_public_contract_decision_record_sha256")
    return (
        isinstance(record_sha256, str)
        and SHA256_RE.fullmatch(record_sha256) is not None
        and record_sha256.lower() != "0" * 64
        and record_sha256.lower() == canonical_json_sha256(review)
    )


def strict_player_identity_promotion_certificate_payload(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    evidence = value.get("evidence")
    reviewed_surface_hash = evidence.get("reviewed_surface_record_sha256") if isinstance(evidence, dict) else None
    reviewed_artifact_hash = evidence.get("reviewed_artifact_hash") if isinstance(evidence, dict) else None
    semantic_proofs = string_set(evidence.get("semantic_proofs")) if isinstance(evidence, dict) else set()
    return (
        value.get("schema") == PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA
        and value.get("surface_id") == "obelisk.player_identity.v1"
        and value.get("promotion_status") == "promoted"
        and value.get("v1_dependency_chain") == CANONICAL_V1_DEPENDENCY_SEQUENCE
        and value.get("v1_dependency_chain_position") == 1
        and value.get("required_by_surface") == "obelisk.permissions_admin.v1"
        and value.get("required_by_v1_dependency_chain_position") == 2
        and value.get("required_reviewed_artifact_hash") == "evidence.reviewed_surface_record_sha256"
        and value.get("reviewed_artifact_hash_policy")
        == "must match the reviewed identity surface record hash carried by the certificate"
        and value.get("missing_mismatched_or_stale_certificate_counts") is False
        and isinstance(reviewed_surface_hash, str)
        and SHA256_RE.fullmatch(reviewed_surface_hash) is not None
        and isinstance(reviewed_artifact_hash, str)
        and reviewed_artifact_hash.lower() == reviewed_surface_hash.lower()
        and evidence.get("promotion_evidence_kind")
        == PLAYER_IDENTITY_PROMOTION_CERTIFICATE_PROMOTION_EVIDENCE_KIND
        and all(evidence.get(key) is False for key in PLAYER_IDENTITY_PROMOTION_CERTIFICATE_FALSE_KEYS)
        and PLAYER_IDENTITY_PROMOTION_CERTIFICATE_REQUIRED_SEMANTIC_PROOFS.issubset(semantic_proofs)
        and strict_identity_public_contract_review_record(evidence, reviewed_surface_hash)
        and not player_identity_promotion_certificate_has_stale_or_mismatch_signal(value)
        and player_identity_promotion_certificate_current_hashes_match(value, reviewed_surface_hash)
    )


def strict_player_identity_promotion_certificate_reference(value: Any) -> bool:
    artifact = hash_bound_json_artifact(value)
    return strict_player_identity_promotion_certificate_payload(artifact)


def value_has_player_identity_promotion_certificate_signal(value: Any) -> bool:
    if isinstance(value, str):
        return normalized_claim_key(value) in {
            PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA.replace(".", "_").replace("-", "_"),
            "player_identity_promotion_certificate",
            "promoted",
        }
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, list):
        return any(value_has_player_identity_promotion_certificate_signal(item) for item in value)
    if isinstance(value, dict):
        return any(
            normalized_claim_key(key)
            in {
                "accepted",
                "approved",
                "certificate",
                "hash_bound_to_current_source_artifacts",
                "player_identity_promotion_certificate",
                "promotion_status",
                "promoted",
                "ready",
                "schema",
                "status",
                "state",
            }
            and value_has_player_identity_promotion_certificate_signal(item)
            for key, item in value.items()
        )
    return False


def player_identity_promotion_certificate_has_stale_or_mismatch_signal(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    for key, item in value.items():
        key_name = normalized_claim_key(key)
        if key_name in PLAYER_IDENTITY_PROMOTION_CERTIFICATE_STALE_OR_MISMATCH_KEYS and claim_value_is_nonfalse(
            item
        ):
            return True
        if isinstance(item, dict) and player_identity_promotion_certificate_has_stale_or_mismatch_signal(item):
            return True
    return False


def player_identity_promotion_certificate_current_hashes_match(
    value: dict[str, Any],
    reviewed_surface_hash: str,
) -> bool:
    expected = reviewed_surface_hash.lower()
    containers = [value]
    evidence = value.get("evidence")
    if isinstance(evidence, dict):
        containers.append(evidence)
    for container in containers:
        for key, item in container.items():
            key_name = normalized_claim_key(key)
            if key_name not in PLAYER_IDENTITY_PROMOTION_CERTIFICATE_CURRENT_HASH_KEYS:
                continue
            if not isinstance(item, str) or SHA256_RE.fullmatch(item) is None:
                return False
            if item.lower() != expected:
                return False
    return True


def player_identity_promotion_certificate_context_key(key_name: str) -> bool:
    return (
        key_name in PLAYER_IDENTITY_PROMOTION_CERTIFICATE_CONTEXT_KEYS
        or (
            "certificate" in key_name
            and "player_identity" in key_name
            and ("promotion" in key_name or "reference" in key_name or "binding" in key_name)
        )
        or (
            "promotion_certificate" in key_name
            and ("identity" in key_name or "generated" in key_name or "builder" in key_name)
        )
        or (
            "generated" in key_name
            and "certificate" in key_name
            and ("reference" in key_name or "binding" in key_name or "promotion" in key_name)
        )
    )


def player_identity_promotion_certificate_reference_key(key_name: str) -> bool:
    return (
        key_name in PLAYER_IDENTITY_PROMOTION_CERTIFICATE_REFERENCE_KEYS
        or (
            player_identity_promotion_certificate_context_key(key_name)
            and ("reference" in key_name or "binding" in key_name)
        )
    )


def canonical_player_identity_promotion_certificate_reference_key(key_name: str) -> bool:
    return key_name in PLAYER_IDENTITY_PROMOTION_CERTIFICATE_CANONICAL_REFERENCE_KEYS


def public_or_runtime_progress_alias_key(key_name: str) -> bool:
    return (
        key_name in NON_AUTHORIZING_CONTEXT_ZERO_ALIAS_KEYS
        or key_name in PROMOTED_SURFACE_COUNT_ALIAS_KEYS
        or BROAD_P0_PROGRESS_OR_CREDIT_ALIAS_RE.search(key_name) is not None
    )


def non_claiming_requirement_or_negative_key(key_name: str) -> bool:
    if key_name.startswith(
        (
            "cannot_",
            "does_not_",
            "do_not_",
            "must_not_",
            "no_",
            "not_",
        )
    ):
        return True
    if (
        key_name.startswith(("must_", "requires_", "required_"))
        or "_requires_" in key_name
        or "_required_" in key_name
        or key_name.endswith("_required")
        or key_name.endswith("_requirements")
    ):
        return re.search(
            r"(?:^|_)(?:allowed|authorized|complete|enabled|ready|stable|supported|unlocked)(?:_|$)",
            key_name,
        ) is None
    return False


def claim_value_is_nonfalse(item: Any) -> bool:
    if item in (False, None):
        return False
    if isinstance(item, (int, float)) and not isinstance(item, bool):
        return item != 0
    if isinstance(item, str):
        return normalized_claim_key(item) not in {
            "",
            "0",
            "0_0",
            "blocked",
            "false",
            "missing",
            "no",
            "none",
            "not_ready",
            "pending",
            "unresolved",
        }
    if isinstance(item, list):
        return any(claim_value_is_nonfalse(child) for child in item)
    if isinstance(item, dict):
        return any(claim_value_is_nonfalse(child) for child in item.values())
    return True


def downstream_promotion_certificate_alias_key_is_forbidden(key_name: str) -> bool:
    if non_claiming_requirement_or_negative_key(key_name):
        return False
    if key_name in DOWNSTREAM_PROMOTION_CERTIFICATE_ALIAS_KEYS:
        return True
    if (
        key_name.startswith("hash_bound_")
        and key_name.endswith("_promotion_certificate")
        and "player_identity" not in key_name
    ):
        return True
    if "promotion_certificate" not in key_name:
        return False
    return any(token in key_name for token in DOWNSTREAM_PROMOTION_CERTIFICATE_SURFACE_TOKENS)


def downstream_promotion_certificate_alias_value_is_positive(item: Any) -> bool:
    if item in (False, None):
        return False
    if isinstance(item, bool):
        return item
    if isinstance(item, (int, float)):
        return item != 0
    if isinstance(item, str):
        normalized = normalized_claim_key(item)
        if normalized in {
            "",
            "0",
            "0_0",
            "blocked",
            "false",
            "missing",
            "no",
            "none",
            "not_ready",
            "pending",
            "unresolved",
        }:
            return False
        if re.fullmatch(r"0+\s*/\s*[1-9]\d*", item.strip().casefold()):
            return False
        if re.fullmatch(r"0+(?:\.0+)?\s*(?:%|percent)", item.strip().casefold()):
            return False
        return True
    if isinstance(item, list):
        return any(downstream_promotion_certificate_alias_value_is_positive(child) for child in item)
    if isinstance(item, dict):
        normalized_keys = {normalized_claim_key(key) for key in item}
        if {"path", "sha256"}.issubset(normalized_keys):
            return True
        for key, child in item.items():
            key_name = normalized_claim_key(key)
            if (
                key_name in DOWNSTREAM_PROMOTION_CERTIFICATE_DECLARATIVE_VALUE_KEYS
                or non_claiming_requirement_or_negative_key(key_name)
            ):
                continue
            if downstream_promotion_certificate_alias_value_is_positive(child):
                return True
        return False
    return True


def non_authorizing_route_alias_key_is_forbidden(key_name: str) -> bool:
    if NON_AUTHORIZING_ROUTE_ALIAS_KEY_RE.search(key_name) is None:
        return False
    return re.search(
        r"(?:^|_)(?:evidence_only|planning_only|non_claim|non_authorizing|diagnostic_only)(?:_|$)",
        key_name,
    ) is None


def public_or_runtime_alias_key_is_forbidden(key_name: str) -> bool:
    if key_name in BROAD_P0_ROUTE_ALIAS_EXEMPT_KEYS:
        return False
    if non_claiming_requirement_or_negative_key(key_name):
        return False
    if re.search(r"(?:^|_)ready_to_plan(?:_|$)", key_name) is not None:
        return False
    if APPROVED_RUNTIME_EVIDENCE_BLOCKER_ALIAS_RE.search(key_name) is not None:
        return False
    return (
        key_name in FORBIDDEN_PUBLIC_OR_RUNTIME_CLAIM_KEYS
        or BROAD_PUBLIC_OR_RUNTIME_CLAIM_KEY_RE.fullmatch(key_name) is not None
        or downstream_promotion_certificate_alias_key_is_forbidden(key_name)
        or non_authorizing_route_alias_key_is_forbidden(key_name)
        or key_name in PROMOTED_SURFACE_COUNT_ALIAS_KEYS
        or (
            BROAD_P0_ROUTE_ALIAS_SCOPE_RE.search(key_name) is not None
            and (
                BROAD_P0_ROUTE_ALIAS_STATE_RE.search(key_name) is not None
                or public_or_runtime_progress_alias_key(key_name)
            )
        )
        or (
            key_name in {"progress", "claim_progress", "claim_progress_contribution"}
        )
    )


def contains_positive_public_or_runtime_claim_value(item: Any) -> bool:
    if is_positive_claim_value(item):
        return True
    if isinstance(item, list):
        return any(contains_positive_public_or_runtime_claim_value(child) for child in item)
    if isinstance(item, dict):
        return any(contains_positive_public_or_runtime_claim_value(child) for child in item.values())
    return False


def public_or_runtime_alias_value_is_positive(key_name: str, item: Any) -> bool:
    if key_name in MULTI_SURFACE_BETA_CAPTURE_SOURCE_VALUES and isinstance(item, dict):
        return False
    if key_name in NON_FALSE_PUBLIC_OR_RUNTIME_CLAIM_KEYS and claim_value_is_nonfalse(item):
        return True
    if public_or_runtime_progress_alias_key(key_name) and progress_claim_value_is_nonzero(item):
        return True
    return contains_positive_public_or_runtime_claim_value(item)


def route_lock_blocked_until(current_blocker: Any) -> list[str]:
    blocker_route = ALLOWED_IDENTITY_LOCK_BLOCKERS.get(str(current_blocker), {})
    required = blocker_route.get("blocked_until", "allowed_identity_lock_blocker")
    blocked_until = [required]
    if required != "reviewed_identity_public_contract":
        blocked_until.append("reviewed_identity_public_contract")
    return blocked_until


def downstream_child_route_blocker(current_route_blocker: Any) -> str | None:
    if current_route_blocker in UPSTREAM_IDENTITY_LOCK_BLOCKERS:
        return None
    if current_route_blocker == "identity_public_contract_gate_missing":
        return "identity_public_contract_gate_missing"
    return "approved_runtime_evidence_missing"


def materialize_route_context_surfaces(
    surfaces_path: Path,
    output_path: Path,
    *,
    approved_runtime_evidence_accepted: bool,
) -> tuple[Path, dict[str, Any], list[str]]:
    context = {
        "materialized": False,
        "source_path": str(surfaces_path),
        "path": str(surfaces_path),
        "accepted_runtime_evidence_context": False,
        "stale_identity_blockers_removed": [],
        "non_claim": (
            "route-context surfaces are a transient checker input only; they do not "
            "promote identity, permissions/admin, commands, public ABI, runtime readiness, "
            "or v1 completion"
        ),
    }
    if not approved_runtime_evidence_accepted:
        return surfaces_path, context, []

    blockers: list[str] = []
    try:
        payload = json.loads(surfaces_path.read_text(encoding="utf-8"))
    except OSError as exc:
        return surfaces_path, context, [f"route_context_surfaces_unreadable:{exc}"]
    except json.JSONDecodeError as exc:
        return surfaces_path, context, [f"route_context_surfaces_invalid_json:{exc}"]
    if not isinstance(payload, dict):
        return surfaces_path, context, ["route_context_surfaces_not_object"]

    route_payload = copy.deepcopy(payload)
    surfaces = route_payload.get("surfaces")
    if not isinstance(surfaces, list):
        return surfaces_path, context, ["route_context_surfaces_surfaces_not_list"]
    identity = next(
        (
            item
            for item in surfaces
            if isinstance(item, dict) and item.get("id") == "obelisk.player_identity.v1"
        ),
        None,
    )
    if not isinstance(identity, dict):
        return surfaces_path, context, ["route_context_surfaces_player_identity_missing"]

    evidence = identity.get("evidence")
    if not isinstance(evidence, dict):
        evidence = {}
        identity["evidence"] = evidence
    evidence["accepted_runtime_evidence"] = dict(ACCEPTED_RUNTIME_EVIDENCE_SURFACE_RECORD)

    removed: list[str] = []
    if isinstance(identity.get("blockers"), list):
        retained = []
        for item in identity["blockers"]:
            if isinstance(item, str) and item in STALE_RUNTIME_EVIDENCE_SURFACE_BLOCKERS:
                removed.append(item)
            else:
                retained.append(item)
        identity["blockers"] = retained

    output_path.write_text(json.dumps(route_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    context.update(
        {
            "materialized": True,
            "path": str(output_path),
            "accepted_runtime_evidence_context": True,
            "stale_identity_blockers_removed": removed,
        }
    )
    return output_path, context, blockers
FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_KEYS = {
    "approved_runtime_evidence_source",
    "approved_runtime_evidence_source_schema",
    "accepted_runtime_evidence_source",
    "accepted_runtime_evidence_source_schema",
    "authority_claim_source",
    "authz_principal_source",
    "authz_principal_source_schema",
    "artifact_status",
    "command_principal_source",
    "command_principal_source_schema",
    "classification",
    "drift_classification",
    "evidence_source",
    "evidence_classification",
    "evidence_source_schema",
    "identity_claim_source",
    "identity_claim_source_schema",
    "identity_evidence_schema",
    "identity_evidence_source",
    "identity_evidence_source_schema",
    "permission_principal_source",
    "permission_principal_source_schema",
    "post_identity_bridge",
    "principal_claim_source",
    "principal_claim_source_schema",
    "principal_evidence_schema",
    "principal_evidence_source",
    "principal_evidence_source_schema",
    "principal_source",
    "principal_source_schema",
    "public_identity_evidence_schema",
    "public_identity_evidence_source",
    "public_identity_evidence_source_schema",
    "readiness_classification",
    "public_identity_source",
    "public_identity_source_schema",
    "runtime_evidence_source",
    "runtime_evidence_source_schema",
    "runtime_identity_source",
    "runtime_identity_source_schema",
    "admin_kind",
    "admin_kinds",
    "admin_source",
    "admin_sources",
    "alias_source",
    "alias_sources",
    "source_alias",
    "source_aliases",
    "status_alias",
    "status_aliases",
    "status_source",
    "status_sources",
    "command",
    "command_candidate",
    "command_candidates",
    "route_candidate",
    "route_candidates",
    "artifact_kind",
    "artifact_source",
    "source_kind",
    "summary_classification",
}
FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_VALUES = {
    "command_text",
    "diagnostic_only",
    "diagnostic_only_non_evidence",
    "diagnostic_observer_triage",
    "diagnostic_triage",
    "admin_route_snapshot",
    "admin_snapshot",
    "admin_snapshots",
    "admin_status_snapshot",
    "copy_artifact",
    "copied_artifact",
    "copied_status_report",
    "generated_certificate",
    "generated_promotion_certificate",
    "hash_bound_player_identity_promotion_certificate",
    "identity_public_contract_decision_record_template",
    "kick",
    "kick_player",
    "kickplayer",
    "list_player",
    "list_players",
    "listplayers",
    "observer_diagnostic_triage",
    "observer_triage",
    "operator_config",
    "public_header_gate_report",
    "public_header_gate_status",
    "public_header_review_report",
    "public_readiness",
    "passive_snapshot",
    "passive_snapshot_diff",
    "passive_snapshot_non_evidence",
    "runtime_principal_lifecycle_start_end_evidence",
    "runtime_principal_start_end_evidence",
    "start_end_evidence",
    "start_end_only",
    "start_end_only_evidence",
    "status_artifact",
    "status_json",
    "status_report",
    "status_snapshot",
    *MULTI_SURFACE_BETA_CAPTURE_SOURCE_VALUES,
}
FORBIDDEN_PRE_PUBLIC_CONTRACT_CLAIM_SOURCE_VALUE_RE = re.compile(
    r"(?:"
    + MULTI_SURFACE_BETA_CAPTURE_CONTEXT_RE
    + r"|"
    r"(?:approved_?)?runtime(?:_local|_evidence|_lifecycle|_observation|_observed|_principal.*evidence)?|"
    r"approved_runtime_principal_lifecycle_evidence|"
    r"runtime_principal_lifecycle_evidence|"
    r"runtime_lifecycle_evidence|"
    r"players?_identity_runtime_principal_lifecycle_evidence|"
    r"reviewed_identity_public_contract|"
    r"identity_public_contract|"
    r"(?:players?_?)?identity_?lifecycle_?anchor_?candidates?|"
    r"lifecycle_?anchor_?(?:candidates?|report|evidence)|"
    r"request_?pack|"
    r"window_?request|"
    r"(?:runtime_?)?window_?(?:manifest|request|execution|executor|executor_?artifact|executor_?closure|closure|status|report)|"
    r"(?:evidence_?)?closure(?:_?(?:report|request|output|status))?|"
    r"(?:executor|execution)(?:_?(?:artifact|report|closure|output|status))?|"
    r"copied_?(?:obelisk_?)?logs?(?:_?(?:only|artifact|copy|ready|status|report))?|"
    r"copied_?log_?only(?:_?artifact)?|"
    r"preflight(?:_?sidecar)?|"
    r"operator_?(?:approval_?)?(?:requests?|receipts?)|"
    r"approval_?requests?|"
    r"(?:agent_?)?handoff(?:_?(?:notes?|reports?|summar(?:y|ies)))?|"
    r"compact_?contexts?|compact_?summar(?:y|ies)|"
    r"(?:live_?)?(?:validation|ops)_?sidecars?|"
    r"players?_?principal_?passive_?snapshots?(?:_?diff)?|"
    r"passive_?(?:principal_?)?snapshots?(?:_?diff)?|"
    r"passive_?monitors?(?:_?(?:ticks?|outputs?|reports?|status|summar(?:y|ies)))?|"
    r"passive_?snapshot_?(?:non_?)?evidence|"
    r"(?:diagnostic_?)?drift(?:_?(?:checks?|diagnostics?|reports?|status|summar(?:y|ies)))?|"
    r"diagnostic_?(?:observer_?)?triage|"
    r"observer_?diagnostic_?triage|"
    r"diagnostic_?(?:candidates?|only_?non_?evidence|observer_?triage)|"
    r"observer_?(?:window_?)?env|"
    r"(?:active_?)?players?_?presence(?:_?(?:reports?|status|summar(?:y|ies)|snapshots?))?|"
    r"active_?players?(?:_?(?:detected|present|presence|reports?|status|summar(?:y|ies)))?|"
    r"(?:player_?)?presence(?:_?(?:active|detected|reports?|status|summar(?:y|ies)))?|"
    r"(?:lifecycle_?|principal_?|player_?principal_?|runtime_?)?observers?(?:_?(?:enable|enabled|enablement|reports?|status))?|"
    r"(?:live_?|server_?|runtime_?)?posture(?:_?(?:checks?|reports?|status|snapshots?))?|"
    r"(?:source_?)?markers?|"
    r"window_?manifests?|"
    r"planning_?(?:artifacts?|manifests?|sources?)|"
    r"plugin_?hub(?:_?(?:planning|readiness|reports?|support|package|package_?shape))?|"
    r"rcon_?(?:command_?)?(?:routes?|status|reports?|candidates?)?|"
    r"admin_?(?:route_?|status_?)?snapshots?(?:_?(?:status|reports?|candidates?))?|"
    r"(?:server_?)?list_?players?(?:_?(?:status|reports?|candidates?|capture))?|"
    r"(?:server_?)?kick(?:_?players?)?(?:_?(?:status|reports?|candidates?|capture|path))?|"
    r"kick_?path(?:_?(?:status|reports?|candidates?|capture))?|"
    r"static_?(?:admin_?)?thunks?(?:_?(?:status|reports?|candidates?))?|"
    r"placeholder_?(?:runtime_?)?evidence|"
    r"child_?checker_?placeholders?|checker_?placeholders?|"
    r"public_?header(?:_?(?:artifact|gate|preflight|readiness|report|review|scan|status))?|"
    r"public_identity"
    r"|public_?readiness(?:_?(?:artifacts?|checks?|reports?|status))?"
    r"|(?:runtime_?principal_?lifecycle_?)?start_?end(?:_?only)?(?:_?evidence)?"
    r"|(?:copied?|copy)_?(?:artifacts?|reports?|status|metadata)"
    r"|status_?(?:artifacts?|json|reports?|snapshots?|updates?)"
    r"|side_?lane(?:_?(?:artifacts?|reports?|candidate|candidates))?"
    r")"
)
POSITIVE_PUBLIC_OR_RUNTIME_CLAIM_RE = re.compile(
    r"\b(?:"
    r"(?:accepted|approved)[_ -]?runtime(?:[_ -]?principal[_ -]?lifecycle)?[_ -]?evidence|"
    r"(?:accepted[_ -]?)?runtime[_ -]?simulations?|"
    r"activation[_ -]?preconditions?(?:[_ -]?(?:artifacts?|reports?))?|"
    r"(?:agent[_ -]?)?handoff(?:[_ -]?(?:notes?|reports?|summar(?:y|ies)))?|"
    r"admin[_ -]?(?:authority|(?:route[_ -]?)?snapshot|status[_ -]?snapshot)|"
    r"authz(?:[_ -]?(?:ready|bridge|response))?|authorization|"
    r"final[_ -]?(?:gate|certificate|artifact)(?:[_ -]?(?:metadata|status|reports?))?|"
    r"RCON(?:[_ -]?(?:command|route|status|candidates?))?|"
    r"(?:server[_ -]?)?list[_ -]?players?(?:[_ -]?(?:status|reports?|candidates?|capture))?|"
    r"(?:server[_ -]?)?kick(?:[_ -]?players?)?(?:[_ -]?(?:status|reports?|candidates?|capture|path))?|"
    r"kick[_ -]?path(?:[_ -]?(?:status|reports?|candidates?|capture))?|"
    r"(?:beta[_ -]?)?notice[_ -]?actions?(?:[_ -]?reports?)?|"
    r"compact[_ -]?contexts?|compact[_ -]?summar(?:y|ies)|"
    r"copied[_ -]?log[_ -]?only(?:[_ -]?(?:artifacts?|reports?|copies|metadata))?|"
    r"(?:copied?|copy)[_ -]?(?:artifacts?|reports?|status|metadata)|"
    r"status[_ -]?(?:artifacts?|json|reports?|snapshots?|updates?)|"
    r"(?:copied?|copy)[_ -]?(?:artifacts?|reports?|status|metadata)|"
    r"status[_ -]?(?:artifacts?|json|reports?|snapshots?|updates?)|"
    r"(?:copied?|copy)[_ -]?(?:artifacts?|reports?|status|metadata)|"
    r"status[_ -]?(?:artifacts?|json|reports?|snapshots?|updates?)|"
    r"(?:candidate[_ -]?|future[_ -]?)?multi[_ -]?surface(?:[_ -]?beta[_ -]?capture)?"
    r"(?:[_ -]?(?:candidate[_ -]?queue|checker[_ -]?matrix|capture[_ -]?pack|capture[_ -]?plan|"
    r"non[_ -]?claim[_ -]?manifest|pack|plan|plan[_ -]?queue|queue|runbook|artifacts?|manifest))?|"
    r"beta[_ -]?capture(?:[_ -]?(?:candidate[_ -]?pack|candidate[_ -]?queue|pack|plan|plan[_ -]?queue|queue))?|"
    r"(?:command[_ -]?principal[_ -]?authz[_ -]?response[_ -]?|authz[_ -]?response[_ -]?|response[_ -]?)?bridge[_ -]?reports?|"
    r"(?:command[_ -]?principal[_ -]?authz[_ -]?response|authz[_ -]?response|response)[_ -]?bridge|"
    r"response[_ -]?path|"
    r"response[_ -]?planning(?:[_ -]?(?:reports?|packages?))?|response[_ -]?status(?:[_ -]?reports?)?|"
    r"precondition[_ -]?(?:artifacts?|reports?)|"
    r"side[_ -]?lane(?:[_ -]?(?:artifacts?|reports?|candidate|candidates))?|"
    r"(?:reviewed[_ -]?)?identity[_ -]?contract[_ -]?decision[_ -]?record|"
    r"public[_ -]?contract[_ -]?records?(?:[_ -]?packages?)?|"
    r"public[_ -]?readiness(?:[_ -]?(?:artifacts?|checks?|reports?|status))?|"
    r"public[_ -]?header(?:[_ -]?(?:artifacts?|gate|preflight|readiness|reports?|review|scan|status))?|"
    r"passive[_ -]?(?:summar(?:y|ies)|status|reports?)|"
    r"plugin[_ -]?hub(?:[_ -]?(?:planning|readiness|reports?|support|package|package[_ -]?shape))?|"
    r"support[_ -]?tiers?(?:[_ -]?(?:readiness|reports?))?|"
    r"support[_ -]?tier[_ -]?(?:packages?|package[_ -]?shapes?)|"
    r"(?:support[_ -]?)?package[_ -]?shapes?(?:[_ -]?evidence)?|"
    r"terminal[_ -]?certificates?(?:[_ -]?(?:metadata|status|reports?))?|"
    r"child[_ -]?checker[_ -]?placeholders?|checker[_ -]?placeholders?|"
    r"command[_ -]?planning(?:[_ -]?(?:packages?|package[_ -]?shapes?))?|"
    r"command[_ -]?(?:chat[_ -]?)?response[_ -]?planning(?:[_ -]?packages?)?|"
    r"copied[_ -]?(?:response[_ -]?)?intent(?:[_ -]?planning)?(?:[_ -]?packages?|[_ -]?package[_ -]?shapes?)?|"
    r"scoped[_ -](?:non[_ -]complete[_ -])?(?:v1[_ -])?release[_ -]statements?|"
    r"scoped[_ -](?:non[_ -]complete[_ -])?(?:v1[_ -])?statements?|"
    r"(?:runtime[_ -]?principal[_ -]?lifecycle[_ -]?)?start[_ -]?end(?:[_ -]?only)?(?:[_ -]?evidence)?|"
    r"(?:public[_ -]?)?(?:player[_ -]?)?identity(?:[_ -]?promotion)?|"
    r"reviewed[_ -]?identity[_ -]?public[_ -]?contract(?:[_ -]?decision[_ -]?record)?|"
    r"(?:identity[_ -]?(?:public[_ -]?)?|player[_ -]?identity[_ -]?public[_ -]?|public[_ -]?)"
    r"contract(?:[_ -]?gate)?|"
    r"command[_ -]?(?:routing|router|response[_ -]?path)|"
    r"permission[_ -]?headers?|permissions?[_ -]?quer(?:y|ies)|principal|"
    r"permissions?/admin|permissions?|public[_ -]?abi|reply[_ -]?(?:endpoint|api|abi)|"
    r"replies[_ -]?(?:api|abi)|send[_ -]?chat[_ -]?(?:api|abi)|runtime|"
    r"runtime[_ -]?work|server[_ -]?operations?|operator[_ -]?approval|runtime[_ -]?approval|"
    r"public[_ -]?(?:api|sdk|header)|v1(?:\.0)?(?:[_ -]?(?:sdk|api|support|completion|stable|release))?|"
    r"release[_ -]?readiness|stable[_ -]?claim|"
    r"public[_ -]?route|route[_ -]?readiness|route[_ -]?snapshots?|route|"
    r"(?:complete|full|stable|production(?:[_ -]?(?:ready|grade))?)[_ -]?(?:sdk|api|support)"
    r")\b(?:\s+(?:is|are|now|becomes?|became))*\s+"
    r"\b(?:accepted|authorized|available|clear(?:ed|s)?|count(?:ed|s|ing)?|established|granted|opened|promoted|"
    r"public(?:\s+and\s+ready)?|ready|readiness|reviewed|live|enabled|allowed|operational|"
    r"resolv(?:ed|es)?|satisf(?:ied|ies|y)?|supported|unlock(?:s|ed)?)\b",
    re.IGNORECASE,
)
POSITIVE_PUBLIC_OR_RUNTIME_CLAIM_REVERSED = re.compile(
    r"\b(?:"
    r"(?:accepted|approved)[_ -]?runtime(?:[_ -]?principal[_ -]?lifecycle)?[_ -]?evidence|"
    r"(?:accepted[_ -]?)?runtime[_ -]?simulations?|"
    r"activation[_ -]?preconditions?(?:[_ -]?(?:artifacts?|reports?))?|"
    r"(?:agent[_ -]?)?handoff(?:[_ -]?(?:notes?|reports?|summar(?:y|ies)))?|"
    r"admin[_ -]?(?:authority|(?:route[_ -]?)?snapshot|status[_ -]?snapshot)|"
    r"authz(?:[_ -]?(?:ready|bridge|response))?|authorization|"
    r"final[_ -]?(?:gate|certificate|artifact)(?:[_ -]?(?:metadata|status|reports?))?|"
    r"RCON(?:[_ -]?(?:command|route|status|candidates?))?|"
    r"(?:server[_ -]?)?list[_ -]?players?(?:[_ -]?(?:status|reports?|candidates?|capture))?|"
    r"(?:server[_ -]?)?kick(?:[_ -]?players?)?(?:[_ -]?(?:status|reports?|candidates?|capture|path))?|"
    r"kick[_ -]?path(?:[_ -]?(?:status|reports?|candidates?|capture))?|"
    r"(?:beta[_ -]?)?notice[_ -]?actions?(?:[_ -]?reports?)?|"
    r"compact[_ -]?contexts?|compact[_ -]?summar(?:y|ies)|"
    r"copied[_ -]?log[_ -]?only(?:[_ -]?(?:artifacts?|reports?|copies|metadata))?|"
    r"(?:candidate[_ -]?|future[_ -]?)?multi[_ -]?surface(?:[_ -]?beta[_ -]?capture)?"
    r"(?:[_ -]?(?:candidate[_ -]?queue|checker[_ -]?matrix|capture[_ -]?pack|capture[_ -]?plan|"
    r"non[_ -]?claim[_ -]?manifest|pack|plan|plan[_ -]?queue|queue|runbook|artifacts?|manifest))?|"
    r"beta[_ -]?capture(?:[_ -]?(?:candidate[_ -]?pack|candidate[_ -]?queue|pack|plan|plan[_ -]?queue|queue))?|"
    r"(?:command[_ -]?principal[_ -]?authz[_ -]?response[_ -]?|authz[_ -]?response[_ -]?|response[_ -]?)?bridge[_ -]?reports?|"
    r"(?:command[_ -]?principal[_ -]?authz[_ -]?response|authz[_ -]?response|response)[_ -]?bridge|"
    r"response[_ -]?path|"
    r"response[_ -]?planning(?:[_ -]?(?:reports?|packages?))?|response[_ -]?status(?:[_ -]?reports?)?|"
    r"precondition[_ -]?(?:artifacts?|reports?)|"
    r"side[_ -]?lane(?:[_ -]?(?:artifacts?|reports?|candidate|candidates))?|"
    r"(?:reviewed[_ -]?)?identity[_ -]?contract[_ -]?decision[_ -]?record|"
    r"public[_ -]?contract[_ -]?records?(?:[_ -]?packages?)?|"
    r"public[_ -]?readiness(?:[_ -]?(?:artifacts?|checks?|reports?|status))?|"
    r"passive[_ -]?(?:summar(?:y|ies)|status|reports?)|"
    r"plugin[_ -]?hub(?:[_ -]?(?:planning|readiness|reports?|support|package|package[_ -]?shape))?|"
    r"support[_ -]?tiers?(?:[_ -]?(?:readiness|reports?))?|"
    r"support[_ -]?tier[_ -]?(?:packages?|package[_ -]?shapes?)|"
    r"(?:support[_ -]?)?package[_ -]?shapes?(?:[_ -]?evidence)?|"
    r"terminal[_ -]?certificates?(?:[_ -]?(?:metadata|status|reports?))?|"
    r"child[_ -]?checker[_ -]?placeholders?|checker[_ -]?placeholders?|"
    r"command[_ -]?planning(?:[_ -]?(?:packages?|package[_ -]?shapes?))?|"
    r"command[_ -]?(?:chat[_ -]?)?response[_ -]?planning(?:[_ -]?packages?)?|"
    r"copied[_ -]?(?:response[_ -]?)?intent(?:[_ -]?planning)?(?:[_ -]?packages?|[_ -]?package[_ -]?shapes?)?|"
    r"scoped[_ -](?:non[_ -]complete[_ -])?(?:v1[_ -])?release[_ -]statements?|"
    r"scoped[_ -](?:non[_ -]complete[_ -])?(?:v1[_ -])?statements?|"
    r"(?:runtime[_ -]?principal[_ -]?lifecycle[_ -]?)?start[_ -]?end(?:[_ -]?only)?(?:[_ -]?evidence)?|"
    r"(?:public[_ -]?)?(?:player[_ -]?)?identity(?:[_ -]?promotion)?|"
    r"reviewed[_ -]?identity[_ -]?public[_ -]?contract(?:[_ -]?decision[_ -]?record)?|"
    r"(?:identity[_ -]?(?:public[_ -]?)?|player[_ -]?identity[_ -]?public[_ -]?|public[_ -]?)"
    r"contract(?:[_ -]?gate)?|"
    r"public[_ -]?(?:api|abi|contract|header|sdk)|route[_ -]?snapshots?|"
    r"public[_ -]?header(?:[_ -]?(?:artifacts?|gate|preflight|readiness|reports?|review|scan|status))?|"
    r"v1(?:\.0)?(?:[_ -]?(?:sdk|api|support|completion|stable|release))?|"
    r"sdk|api|support"
    r")\b\s+"
    r"(?:is|are|now|becomes?|became)\s+"
    r"\b(?:accepted|allowed|available|clear(?:ed|s)?|complete|enabled|established|full|opened|promoted|"
    r"public|ready|reviewed|resolv(?:ed|es)?|stable|supported|unlocked|"
    r"production(?:[_ -]?(?:ready|grade))?)\b",
    re.IGNORECASE,
)
POSITIVE_PUBLIC_OR_RUNTIME_CLAIM_STATUS_FIRST = re.compile(
    r"\b(?:accepted|authorized|available|clear(?:ed|s)?|enabled|established|granted|live|opened|"
    r"operational|promoted|public|ready|resolv(?:ed|es)?|supported|unlocked)\b\s+"
    r"(?:for\s+|to\s+|is\s+|are\s+|now\s+|becomes?\s+|became\s+)*"
    r"\b(?:"
    r"(?:accepted|approved)[_ -]?runtime(?:[_ -]?principal[_ -]?lifecycle)?[_ -]?evidence|"
    r"(?:accepted[_ -]?)?runtime[_ -]?simulations?|"
    r"activation[_ -]?preconditions?(?:[_ -]?(?:artifacts?|reports?))?|"
    r"(?:agent[_ -]?)?handoff(?:[_ -]?(?:notes?|reports?|summar(?:y|ies)))?|"
    r"admin[_ -]?(?:authority|(?:route[_ -]?)?snapshot|status[_ -]?snapshot)|"
    r"authz(?:[_ -]?(?:ready|bridge|response))?|authorization|"
    r"final[_ -]?(?:gate|certificate|artifact)(?:[_ -]?(?:metadata|status|reports?))?|"
    r"RCON(?:[_ -]?(?:command|route|status|candidates?))?|"
    r"(?:server[_ -]?)?list[_ -]?players?(?:[_ -]?(?:status|reports?|candidates?|capture))?|"
    r"(?:server[_ -]?)?kick(?:[_ -]?players?)?(?:[_ -]?(?:status|reports?|candidates?|capture|path))?|"
    r"kick[_ -]?path(?:[_ -]?(?:status|reports?|candidates?|capture))?|"
    r"(?:beta[_ -]?)?notice[_ -]?actions?(?:[_ -]?reports?)?|"
    r"compact[_ -]?contexts?|compact[_ -]?summar(?:y|ies)|"
    r"copied[_ -]?log[_ -]?only(?:[_ -]?(?:artifacts?|reports?|copies|metadata))?|"
    r"(?:candidate[_ -]?|future[_ -]?)?multi[_ -]?surface(?:[_ -]?beta[_ -]?capture)?"
    r"(?:[_ -]?(?:candidate[_ -]?queue|checker[_ -]?matrix|capture[_ -]?pack|capture[_ -]?plan|"
    r"non[_ -]?claim[_ -]?manifest|pack|plan|plan[_ -]?queue|queue|runbook|artifacts?|manifest))?|"
    r"beta[_ -]?capture(?:[_ -]?(?:candidate[_ -]?pack|candidate[_ -]?queue|pack|plan|plan[_ -]?queue|queue))?|"
    r"(?:command[_ -]?principal[_ -]?authz[_ -]?response[_ -]?|authz[_ -]?response[_ -]?|response[_ -]?)?bridge[_ -]?reports?|"
    r"(?:command[_ -]?principal[_ -]?authz[_ -]?response|authz[_ -]?response|response)[_ -]?bridge|"
    r"response[_ -]?path|"
    r"response[_ -]?planning(?:[_ -]?(?:reports?|packages?))?|response[_ -]?status(?:[_ -]?reports?)?|"
    r"precondition[_ -]?(?:artifacts?|reports?)|"
    r"side[_ -]?lane(?:[_ -]?(?:artifacts?|reports?|candidate|candidates))?|"
    r"(?:reviewed[_ -]?)?identity[_ -]?contract[_ -]?decision[_ -]?record|"
    r"public[_ -]?contract[_ -]?records?(?:[_ -]?packages?)?|"
    r"public[_ -]?readiness(?:[_ -]?(?:artifacts?|checks?|reports?|status))?|"
    r"passive[_ -]?(?:summar(?:y|ies)|status|reports?)|"
    r"plugin[_ -]?hub(?:[_ -]?(?:planning|readiness|reports?|support|package|package[_ -]?shape))?|"
    r"support[_ -]?tiers?(?:[_ -]?(?:readiness|reports?))?|"
    r"support[_ -]?tier[_ -]?(?:packages?|package[_ -]?shapes?)|"
    r"(?:support[_ -]?)?package[_ -]?shapes?(?:[_ -]?evidence)?|"
    r"terminal[_ -]?certificates?(?:[_ -]?(?:metadata|status|reports?))?|"
    r"child[_ -]?checker[_ -]?placeholders?|checker[_ -]?placeholders?|"
    r"command[_ -]?planning(?:[_ -]?(?:packages?|package[_ -]?shapes?))?|"
    r"command[_ -]?(?:chat[_ -]?)?response[_ -]?planning(?:[_ -]?packages?)?|"
    r"copied[_ -]?(?:response[_ -]?)?intent(?:[_ -]?planning)?(?:[_ -]?packages?|[_ -]?package[_ -]?shapes?)?|"
    r"scoped[_ -](?:non[_ -]complete[_ -])?(?:v1[_ -])?release[_ -]statements?|"
    r"scoped[_ -](?:non[_ -]complete[_ -])?(?:v1[_ -])?statements?|"
    r"(?:runtime[_ -]?principal[_ -]?lifecycle[_ -]?)?start[_ -]?end(?:[_ -]?only)?(?:[_ -]?evidence)?|"
    r"(?:public[_ -]?)?(?:player[_ -]?)?identity(?:[_ -]?promotion)?|"
    r"reviewed[_ -]?identity[_ -]?public[_ -]?contract(?:[_ -]?decision[_ -]?record)?|"
    r"(?:identity[_ -]?(?:public[_ -]?)?|player[_ -]?identity[_ -]?public[_ -]?|public[_ -]?)"
    r"contract(?:[_ -]?gate)?|"
    r"public[_ -]?(?:api|abi|contract|header|sdk)|route[_ -]?snapshots?|"
    r"public[_ -]?header(?:[_ -]?(?:artifacts?|gate|preflight|readiness|reports?|review|scan|status))?|"
    r"v1(?:\.0)?(?:[_ -]?(?:sdk|api|support|completion|stable|release))?|"
    r"sdk|api|support"
    r")\b",
    re.IGNORECASE,
)
PASSIVE_OR_DIAGNOSTIC_PUBLIC_IDENTITY_EVIDENCE_TEXT_RE = re.compile(
    r"\b(?:"
    r"players?[_ -]?principal[_ -]?passive[_ -]?snapshots?(?:[_ -]?diff)?|"
    r"passive[_ -]?(?:principal[_ -]?)?snapshots?(?:[_ -]?diff)?|"
    r"(?:diagnostic[_ -]?)?drift(?:[_ -]?(?:checks?|diagnostics?|reports?|status|summar(?:y|ies)))?|"
    r"diagnostic[_ -]?(?:observer[_ -]?)?triage|"
    r"observer[_ -]?diagnostic[_ -]?triage|"
    r"(?:active[_ -]?)?players?[_ -]?presence(?:[_ -]?(?:reports?|status|summar(?:y|ies)|snapshots?))?|"
    r"active[_ -]?players?(?:[_ -]?(?:detected|present|presence|reports?|status|summar(?:y|ies)))?|"
    r"(?:player[_ -]?)?presence(?:[_ -]?(?:active|detected|reports?|status|summar(?:y|ies)))?|"
    r"(?:lifecycle[_ -]?|principal[_ -]?|player[_ -]?principal[_ -]?|runtime[_ -]?)?observers?(?:[_ -]?(?:enable|enabled|enablement|reports?|status))?|"
    r"(?:live[_ -]?|server[_ -]?|runtime[_ -]?)?posture(?:[_ -]?(?:checks?|reports?|status|snapshots?))?"
    r")\b[^.;:\n\r]{0,120}\b(?:"
    r"(?:accepted|approved)[_ -]?runtime(?:[_ -]?principal[_ -]?lifecycle)?[_ -]?evidence|"
    r"(?:public[_ -]?)?(?:player[_ -]?)?identity[_ -]?evidence|"
    r"principal[_ -]?evidence|"
    r"identity[_ -]?claims?"
    r")\b",
    re.IGNORECASE,
)
PASSIVE_OR_DIAGNOSTIC_PUBLIC_IDENTITY_EVIDENCE_REVERSED_TEXT_RE = re.compile(
    r"\b(?:"
    r"(?:accepted|approved)[_ -]?runtime(?:[_ -]?principal[_ -]?lifecycle)?[_ -]?evidence|"
    r"(?:public[_ -]?)?(?:player[_ -]?)?identity[_ -]?evidence|"
    r"principal[_ -]?evidence|"
    r"identity[_ -]?claims?"
    r")\b[^.;:\n\r]{0,120}\b(?:"
    r"players?[_ -]?principal[_ -]?passive[_ -]?snapshots?(?:[_ -]?diff)?|"
    r"passive[_ -]?(?:principal[_ -]?)?snapshots?(?:[_ -]?diff)?|"
    r"(?:diagnostic[_ -]?)?drift(?:[_ -]?(?:checks?|diagnostics?|reports?|status|summar(?:y|ies)))?|"
    r"diagnostic[_ -]?(?:observer[_ -]?)?triage|"
    r"observer[_ -]?diagnostic[_ -]?triage|"
    r"(?:active[_ -]?)?players?[_ -]?presence(?:[_ -]?(?:reports?|status|summar(?:y|ies)|snapshots?))?|"
    r"active[_ -]?players?(?:[_ -]?(?:detected|present|presence|reports?|status|summar(?:y|ies)))?|"
    r"(?:player[_ -]?)?presence(?:[_ -]?(?:active|detected|reports?|status|summar(?:y|ies)))?|"
    r"(?:lifecycle[_ -]?|principal[_ -]?|player[_ -]?principal[_ -]?|runtime[_ -]?)?observers?(?:[_ -]?(?:enable|enabled|enablement|reports?|status))?|"
    r"(?:live[_ -]?|server[_ -]?|runtime[_ -]?)?posture(?:[_ -]?(?:checks?|reports?|status|snapshots?))?"
    r")\b",
    re.IGNORECASE,
)
NEGATED_CLAIM_PREFIX_RE = re.compile(
    r"\b(?:blocked|cannot|does\s+not|do\s+not|excluded|excludes?|future|must\s+not|no|not|"
    r"only|outside|post-v1|prevent|prevents|require[sd]?|remain|remains|until|without)\b",
    re.IGNORECASE,
)
PASSIVE_OR_DIAGNOSTIC_IDENTITY_EVIDENCE_NEGATED_TEXT_RE = re.compile(
    r"\b(?:cannot|can't|does\s+not|do\s+not|is\s+not|are\s+not|must\s+not|never|no|not|"
    r"non[-_ ]?evidence|diagnostic[-_ ]?only|passive[-_ ]?snapshot[-_ ]?only|"
    r"does\s+not\s+count|do\s+not\s+count|counts?\s+as\s+non[-_ ]?evidence|"
    r"not\s+(?:accepted|approved|public|identity|runtime|evidence))\b",
    re.IGNORECASE,
)
NEGATED_CLAIM_SUFFIX_RE = re.compile(
    r"^\s+(?:remains?|stays?|is|are|still)?\s*(?:blocked|lacks?|missing|needs?|requires?|"
    r"not\s+(?:ready|enabled|authorized|allowed)|unauthorized|unsupported)\b",
    re.IGNORECASE,
)
CLAIM_SCOPE_SPLIT_RE = re.compile(r"[,.;:\n\r]|\s+\b(?:and|but|then|however|unless)\b\s+", re.IGNORECASE)


def is_positive_claim_value(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        return value.casefold().replace("-", "_").replace(" ", "_") in {
            "accepted",
            "allowed",
            "approved",
            "authorized",
            "available",
            "certified",
            "complete",
            "enabled",
            "granted",
            "issued",
            "live",
            "met",
            "operational",
            "passed",
            "placeholder",
            "promoted",
            "public",
            "reachable",
            "ready",
            "reviewed",
            "satisfied",
            "signed",
            "supported",
            "terminal",
            "true",
            "unlocked",
            "validated",
            "verified",
            "yes",
        }
    return False


def preceding_claim_scope(text: str, start: int) -> str:
    parts = CLAIM_SCOPE_SPLIT_RE.split(text[:start])
    return parts[-1] if parts else text[:start]


def is_negated_text_claim(text: str, match: re.Match[str]) -> bool:
    prefix = preceding_claim_scope(text, match.start())
    if re.search(
        r"\b(?:cannot|can't|do\s+not|does\s+not|must\s+not|never|no|not)\s+claims?\b",
        prefix,
        re.IGNORECASE,
    ):
        return True
    if NEGATED_CLAIM_PREFIX_RE.search(prefix) and not re.search(
        r"\b(?:claims?|reports?|says|states?)\b[^,.;:\n\r]*$",
        prefix,
        re.IGNORECASE,
    ):
        return True
    return bool(NEGATED_CLAIM_SUFFIX_RE.match(text[match.end() :]))


def contains_positive_public_or_runtime_text_claim(text: str) -> bool:
    for pattern in (
        PASSIVE_OR_DIAGNOSTIC_PUBLIC_IDENTITY_EVIDENCE_TEXT_RE,
        PASSIVE_OR_DIAGNOSTIC_PUBLIC_IDENTITY_EVIDENCE_REVERSED_TEXT_RE,
    ):
        for match in pattern.finditer(text):
            clause_start = max(
                text.rfind(".", 0, match.start()),
                text.rfind(";", 0, match.start()),
                text.rfind(":", 0, match.start()),
                text.rfind("\n", 0, match.start()),
            )
            clause = text[clause_start + 1 : match.end()]
            if PASSIVE_OR_DIAGNOSTIC_IDENTITY_EVIDENCE_NEGATED_TEXT_RE.search(clause):
                continue
            if not is_negated_text_claim(text, match):
                return True
    for pattern in (
        POSITIVE_PUBLIC_OR_RUNTIME_CLAIM_RE,
        POSITIVE_PUBLIC_OR_RUNTIME_CLAIM_REVERSED,
        POSITIVE_PUBLIC_OR_RUNTIME_CLAIM_STATUS_FIRST,
    ):
        for match in pattern.finditer(text):
            if not is_negated_text_claim(text, match):
                return True
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--query-failclosed-artifact",
        type=Path,
        default=DEFAULT_QUERY_CONTRACT,
        help="Permissions/admin query fail-closed artifact used by dependent planning checks.",
    )
    parser.add_argument(
        "--player-identity-decisions",
        type=Path,
        default=DEFAULT_PLAYER_IDENTITY_DECISIONS,
        help="Player identity public contract decisions manifest used by the route's identity gap guardrail.",
    )
    parser.add_argument(
        "--public-sdk-surfaces",
        type=Path,
        default=DEFAULT_PUBLIC_SDK_SURFACES,
        help="Public SDK surfaces manifest used by the route's identity gap guardrail.",
    )
    parser.add_argument(
        "--player-identity-private-candidate-contract",
        type=Path,
        default=DEFAULT_PLAYER_IDENTITY_PRIVATE_CANDIDATE,
        help="Private candidate-only identity contract used by the route's identity gap guardrail.",
    )
    parser.add_argument(
        "--public-header",
        type=Path,
        default=DEFAULT_PUBLIC_HEADER,
        help="Public C ABI header scanned by the route's identity gap guardrail.",
    )
    parser.add_argument(
        "--command-response-root",
        type=Path,
        help="Optional command/chat response second-source planning root.",
    )
    parser.add_argument(
        "--command-response-readiness",
        type=Path,
        help="Optional command/chat response readiness JSON.",
    )
    parser.add_argument(
        "--player-identity-artifact-root",
        type=Path,
        help="Optional artifact root forwarded to the player-identity first-evidence checker.",
    )
    parser.add_argument(
        "--player-identity-snapshot-root",
        type=Path,
        help="Optional first-evidence snapshot root forwarded to the player-identity first-evidence checker.",
    )
    parser.add_argument(
        "--player-identity-candidate-root",
        type=Path,
        help="Optional second-source candidate root forwarded to the player-identity first-evidence checker.",
    )
    parser.add_argument(
        "--lifecycle-anchor-candidates-manifest",
        "--player-identity-lifecycle-anchor-candidates-manifest",
        dest="player_identity_lifecycle_anchor_candidates_manifest",
        type=Path,
        help="Optional bound lifecycle-anchor candidates manifest forwarded to the identity checker.",
    )
    parser.add_argument(
        "--principal-invalidation-policy-manifest",
        "--player-identity-principal-invalidation-policy-manifest",
        dest="player_identity_principal_invalidation_policy_manifest",
        type=Path,
        help="Optional bound principal invalidation policy manifest forwarded to the identity checker.",
    )
    parser.add_argument(
        "--runtime-principal-lifecycle-evidence-manifest",
        "--player-identity-runtime-principal-lifecycle-evidence-manifest",
        dest="player_identity_runtime_principal_lifecycle_evidence_manifest",
        type=Path,
        help="Optional synthetic/redacted runtime-principal lifecycle shape manifest forwarded to the identity checker.",
    )
    parser.add_argument(
        "--approved-runtime-principal-lifecycle-evidence-manifest",
        "--player-identity-approved-runtime-principal-lifecycle-evidence-manifest",
        dest="player_identity_approved_runtime_principal_lifecycle_evidence_manifest",
        type=Path,
        help="Optional approved runtime-principal lifecycle evidence manifest forwarded to the identity checker.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON. The checker always emits JSON.")
    return parser.parse_args()


def identity_readiness_argv(args: argparse.Namespace | None) -> list[str]:
    argv = [sys.executable, str(SCRIPT_DIR / "check_player_identity_first_evidence_readiness.py"), "--json"]
    if args is None:
        return argv
    optional_args = (
        ("player_identity_artifact_root", "--artifact-root"),
        ("player_identity_snapshot_root", "--snapshot-root"),
        ("player_identity_candidate_root", "--candidate-root"),
        ("player_identity_lifecycle_anchor_candidates_manifest", "--lifecycle-anchor-candidates-manifest"),
        ("player_identity_principal_invalidation_policy_manifest", "--principal-invalidation-policy-manifest"),
        (
            "player_identity_runtime_principal_lifecycle_evidence_manifest",
            "--runtime-principal-lifecycle-evidence-manifest",
        ),
        (
            "player_identity_approved_runtime_principal_lifecycle_evidence_manifest",
            "--approved-runtime-principal-lifecycle-evidence-manifest",
        ),
    )
    for attr, flag in optional_args:
        value = getattr(args, attr, None)
        if value is not None:
            argv.extend([flag, str(value)])
    return argv


def route_checks(
    args: argparse.Namespace,
    *,
    current_route_blocker: str | None,
    approved_runtime_evidence_accepted: bool = False,
    public_sdk_surfaces: Path | None = None,
) -> list[tuple[str, list[str]]]:
    surfaces_path = public_sdk_surfaces or args.public_sdk_surfaces
    shared_surface_args = ["--surfaces", str(surfaces_path)]
    shared_header_args = ["--public-header", str(args.public_header)]
    route_blocker_args = ["--current-route-blocker", current_route_blocker] if current_route_blocker else []
    player_identity_gap_args = [
        "check_player_identity_public_contract_gap_report.py",
        "--decisions",
        str(args.player_identity_decisions),
        "--surfaces",
        str(surfaces_path),
        "--private-candidate-contract",
        str(args.player_identity_private_candidate_contract),
        "--public-header",
        str(args.public_header),
        "--json",
    ]
    approved_runtime = getattr(args, "player_identity_approved_runtime_principal_lifecycle_evidence_manifest", None)
    if approved_runtime is not None and approved_runtime_evidence_accepted:
        player_identity_gap_args.extend(["--approved-runtime-evidence", str(approved_runtime)])
    command_response_args = [
        "check_command_chat_response_public_readiness.py",
        *shared_surface_args,
        *shared_header_args,
        *route_blocker_args,
        "--json",
    ]
    if args.command_response_root is not None:
        command_response_args.extend(["--root", str(args.command_response_root)])
    if args.command_response_readiness is not None:
        command_response_args.extend(["--readiness", str(args.command_response_readiness)])

    query_artifact = str(args.query_failclosed_artifact)
    checks = [
        (
            "player_identity_public_contract_gap",
            player_identity_gap_args,
        ),
        (
            "permissions_query_failclosed",
            ["check_permissions_admin_query_failclosed_contract.py", query_artifact, "--json"],
        ),
        (
            "permissions_admin_public_readiness",
            [
                "check_permissions_admin_public_readiness.py",
                "--query-failclosed-artifact",
                query_artifact,
                *shared_surface_args,
                *shared_header_args,
                *route_blocker_args,
                "--json",
            ],
        ),
        (
            "command_copied_response_intent_planning",
            [
                "check_command_copied_response_intent_planning.py",
                "--query-failclosed-artifact",
                query_artifact,
                "--json",
            ],
        ),
        (
            "command_copied_response_intent_lifecycle_planning",
            [
                "check_command_copied_response_intent_lifecycle_planning.py",
                "--json",
            ],
        ),
        ("command_principal_authz_response_bridge", ["check_command_principal_authz_response_bridge.py", "--json"]),
        ("command_chat_response_public_readiness", command_response_args),
        (
            "commands_replies_public_readiness",
            [
                "check_commands_replies_public_readiness.py",
                *shared_surface_args,
                *shared_header_args,
                *route_blocker_args,
                "--json",
            ],
        ),
    ]
    if current_route_blocker is None:
        return [
            (name, argv)
            for name, argv in checks
            if name not in UPSTREAM_SKIPPED_ROUTE_CHECKS
        ]
    if current_route_blocker == "approved_runtime_evidence_missing" and not approved_runtime_evidence_accepted:
        return [
            (name, argv)
            for name, argv in checks
            if name != "player_identity_public_contract_gap"
        ]
    return checks


def validate_command_response_readiness_binding(args: argparse.Namespace) -> list[str]:
    if args.command_response_readiness is None:
        return []
    if args.command_response_root is None:
        return ["command_chat_response_public_readiness: caller-supplied readiness requires --command-response-root"]
    expected = (args.command_response_root / COMMAND_RESPONSE_DEFAULT_READINESS_NAME).resolve()
    observed = args.command_response_readiness.resolve()
    if observed != expected:
        return [
            "command_chat_response_public_readiness: caller-supplied readiness is not bound to "
            "--command-response-root"
        ]
    return []


def validate_command_response_child_readiness_context(
    args: argparse.Namespace,
    payload: dict[str, Any] | None,
) -> list[str]:
    if payload is None:
        return []
    readiness_root = payload.get("readiness_root")
    readiness_path = payload.get("readiness_path")
    blockers: list[str] = []
    if not isinstance(readiness_root, str) or not readiness_root:
        blockers.append("command_chat_response_public_readiness: child readiness_root missing or unverifiable")
    if not isinstance(readiness_path, str) or not readiness_path:
        blockers.append("command_chat_response_public_readiness: child readiness_path missing or unverifiable")
    if blockers:
        return blockers

    child_root = Path(readiness_root).resolve()
    child_readiness = Path(readiness_path).resolve()
    expected_child_readiness = child_root / COMMAND_RESPONSE_DEFAULT_READINESS_NAME
    if child_readiness != expected_child_readiness:
        blockers.append(
            "command_chat_response_public_readiness: child readiness_path is not bound to readiness_root"
        )
    if args.command_response_root is not None and child_root != args.command_response_root.resolve():
        blockers.append("command_chat_response_public_readiness: child readiness_root does not match caller root")
    if args.command_response_readiness is not None and child_readiness != args.command_response_readiness.resolve():
        blockers.append(
            "command_chat_response_public_readiness: child readiness_path does not match caller readiness"
        )
    return blockers


def validate_command_response_report_handoff_binding(payload: dict[str, Any] | None) -> list[str]:
    if payload is None:
        return []
    blockers: list[str] = []
    if payload.get("schema") != EXPECTED_ROUTE_CHECK_SCHEMAS["command_chat_response_public_readiness"]:
        blockers.append(
            "command_chat_response_public_readiness: full response-path report schema required before commands/replies handoff"
        )
    for key in ("valid", "accepted_for_planning", "planning_only", "dependency_chain_locked"):
        if payload.get(key) is not True:
            blockers.append(
                f"command_chat_response_public_readiness: {key} must be true before commands/replies handoff"
            )
    if payload.get("blockers") != []:
        blockers.append(
            "command_chat_response_public_readiness: blockers must be empty before commands/replies handoff"
        )
    for key in (
        "public_readiness_ready",
        "public_header_allowed",
        "promotion_ready",
        "public_sdk_ready",
        "public_abi_ready",
        "runtime_ready",
        "counts_toward_public_sdk",
        "counts_toward_runtime",
        "counts_toward_v1_completion",
        "public_or_runtime_accounting_allowed",
    ):
        if payload.get(key) is not False:
            blockers.append(
                f"command_chat_response_public_readiness: {key} must be false before commands/replies handoff"
            )

    missing_source_paths = [
        key
        for key in COMMAND_RESPONSE_REPORT_SOURCE_ARTIFACT_KEYS
        if not isinstance(payload.get(key), str) or not payload.get(key)
    ]
    if missing_source_paths:
        blockers.append(
            "command_chat_response_public_readiness: source-artifact paths required before commands/replies handoff"
        )
    source_hashes = payload.get("source_artifact_hashes")
    if not isinstance(source_hashes, dict):
        blockers.append(
            "command_chat_response_public_readiness: source-artifact hashes required before commands/replies handoff"
        )
    else:
        missing_source_hashes = [
            key
            for key in COMMAND_RESPONSE_REPORT_SOURCE_ARTIFACT_KEYS
            if not isinstance(source_hashes.get(key), str)
            or SHA256_RE.fullmatch(source_hashes.get(key)) is None
        ]
        if missing_source_hashes:
            blockers.append(
                "command_chat_response_public_readiness: complete source-artifact hashes required before commands/replies handoff"
            )
    return blockers


def validate_identity_planning_binding_args(args: argparse.Namespace) -> list[str]:
    lifecycle = getattr(args, "player_identity_lifecycle_anchor_candidates_manifest", None)
    principal = getattr(args, "player_identity_principal_invalidation_policy_manifest", None)
    if (lifecycle is None) != (principal is None):
        return [
            "player_identity_first_evidence_readiness: lifecycle/principal planning manifests must be supplied together"
        ]
    return []


def approved_runtime_evidence_diagnosis_path_matches(
    args: argparse.Namespace | None,
    diagnosis: dict[str, Any],
) -> bool:
    approved_runtime_manifest = (
        getattr(args, "player_identity_approved_runtime_principal_lifecycle_evidence_manifest", None)
        if args is not None
        else None
    )
    if approved_runtime_manifest is None:
        return False
    observed = diagnosis.get("path")
    if not isinstance(observed, str) or not observed:
        return False
    return Path(observed).resolve() == Path(approved_runtime_manifest).resolve()


def approved_runtime_evidence_ready_for_identity_lock(
    phase: dict[str, Any],
    args: argparse.Namespace | None = None,
) -> bool:
    diagnosis = phase.get("source_checker_approved_runtime_evidence_manifest")
    if not isinstance(diagnosis, dict):
        return False
    return (
        diagnosis.get("report_schema") == APPROVED_RUNTIME_EVIDENCE_REPORT_SCHEMA
        and diagnosis.get("input_schema") == APPROVED_RUNTIME_EVIDENCE_INPUT_SCHEMA
        and diagnosis.get("mode") == "consume"
        and diagnosis.get("ready_scope") == "runtime_evidence_only"
        and diagnosis.get("ready") is True
        and diagnosis.get("approved_runtime_evidence_present") is True
        and diagnosis.get("runtime_evidence_ready") is True
        and diagnosis.get("remaining_blockers") == []
        and diagnosis.get("blockers") == []
        and diagnosis.get("next_blocker") == "identity_public_contract_gate_missing"
        and all(diagnosis.get(key) is False for key in APPROVED_RUNTIME_EVIDENCE_FALSE_KEYS)
        and all(
            key not in diagnosis or diagnosis.get(key) is False
            for key in APPROVED_RUNTIME_EVIDENCE_OPTIONAL_FALSE_KEYS
        )
        and all(
            key not in diagnosis or not progress_claim_value_is_nonzero(diagnosis.get(key))
            for key in APPROVED_RUNTIME_EVIDENCE_OPTIONAL_ZERO_KEYS
        )
        and all(diagnosis.get(key) == [] for key in APPROVED_RUNTIME_EVIDENCE_EMPTY_KEYS)
        and diagnosis.get("observed_runtime_cases") == APPROVED_RUNTIME_EVIDENCE_OBSERVED_RUNTIME_CASES
        and diagnosis.get("consumer_cases") == APPROVED_RUNTIME_EVIDENCE_CONSUMER_CASES
        and not collect_public_or_runtime_claims(diagnosis, include_text_claims=True)
        and (args is None or approved_runtime_evidence_diagnosis_path_matches(args, diagnosis))
    )


def approved_runtime_evidence_identity_lock_binding_blockers(
    args: argparse.Namespace | None,
    phase: dict[str, Any],
) -> list[str]:
    diagnosis = phase.get("source_checker_approved_runtime_evidence_manifest")
    if not isinstance(diagnosis, dict):
        return []
    has_core_ready_signal = (
        diagnosis.get("ready") is True
        or diagnosis.get("approved_runtime_evidence_present") is True
        or diagnosis.get("runtime_evidence_ready") is True
        or diagnosis.get("remaining_blockers") == []
    )
    if not has_core_ready_signal:
        return []

    blockers: list[str] = []
    if not approved_runtime_evidence_diagnosis_path_matches(args, diagnosis):
        blockers.append("critical_path_approved_runtime_evidence_path_unbound")
    if diagnosis.get("report_schema") != APPROVED_RUNTIME_EVIDENCE_REPORT_SCHEMA:
        blockers.append("critical_path_approved_runtime_evidence_report_schema_mismatch")
    if diagnosis.get("input_schema") != APPROVED_RUNTIME_EVIDENCE_INPUT_SCHEMA:
        blockers.append("critical_path_approved_runtime_evidence_input_schema_mismatch")
    if diagnosis.get("mode") != "consume":
        blockers.append("critical_path_approved_runtime_evidence_mode_not_consume")
    if diagnosis.get("ready_scope") != "runtime_evidence_only":
        blockers.append("critical_path_approved_runtime_evidence_ready_scope_not_runtime_evidence_only")
    if diagnosis.get("next_blocker") != "identity_public_contract_gate_missing":
        blockers.append("critical_path_approved_runtime_evidence_next_blocker_unexpected")
    if diagnosis.get("blockers") != []:
        blockers.append("critical_path_approved_runtime_evidence_blockers_not_empty")
    if diagnosis.get("remaining_blockers") != []:
        blockers.append("critical_path_approved_runtime_evidence_remaining_blockers_not_empty")
    for key in APPROVED_RUNTIME_EVIDENCE_FALSE_KEYS:
        if diagnosis.get(key) is not False:
            blockers.append(f"critical_path_approved_runtime_evidence_{key}_not_false")
    for key in APPROVED_RUNTIME_EVIDENCE_OPTIONAL_FALSE_KEYS:
        if key in diagnosis and diagnosis.get(key) is not False:
            blockers.append(f"critical_path_approved_runtime_evidence_{key}_not_false")
    for key in APPROVED_RUNTIME_EVIDENCE_OPTIONAL_ZERO_KEYS:
        if key in diagnosis and progress_claim_value_is_nonzero(diagnosis.get(key)):
            blockers.append(f"critical_path_approved_runtime_evidence_{key}_not_zero")
    for key in APPROVED_RUNTIME_EVIDENCE_EMPTY_KEYS:
        if diagnosis.get(key) != []:
            blockers.append(f"critical_path_approved_runtime_evidence_{key}_not_empty")
    if diagnosis.get("observed_runtime_cases") != APPROVED_RUNTIME_EVIDENCE_OBSERVED_RUNTIME_CASES:
        blockers.append("critical_path_approved_runtime_evidence_observed_runtime_cases_mismatch")
    if diagnosis.get("consumer_cases") != APPROVED_RUNTIME_EVIDENCE_CONSUMER_CASES:
        blockers.append("critical_path_approved_runtime_evidence_consumer_cases_mismatch")
    if collect_public_or_runtime_claims(diagnosis, include_text_claims=True):
        blockers.append("critical_path_approved_runtime_evidence_public_or_runtime_claim")
    return blockers


def expected_identity_lock_blocker_for_phase(
    phase: dict[str, Any],
    args: argparse.Namespace | None = None,
) -> str:
    if approved_runtime_evidence_ready_for_identity_lock(phase, args):
        return "identity_public_contract_gate_missing"
    return "approved_runtime_evidence_missing"


def validate_identity_lock_mode(args: argparse.Namespace, phase: dict[str, Any]) -> list[str]:
    expected = expected_identity_lock_blocker_for_phase(phase, args)
    observed = phase.get("current_blocker")
    source_observed = phase.get("source_checker_primary_blocker")
    blockers: list[str] = []
    if observed in UPSTREAM_IDENTITY_LOCK_BLOCKERS and source_observed == observed:
        blockers.extend(approved_runtime_evidence_identity_lock_binding_blockers(args, phase))
        return blockers
    if observed != expected:
        blockers.append(f"critical_path_identity_gate_mode_unexpected_blocker:{observed!r}!={expected!r}")
    if source_observed != expected:
        blockers.append(
            f"critical_path_identity_readiness_mode_unexpected_blocker:{source_observed!r}!={expected!r}"
        )
    blockers.extend(approved_runtime_evidence_identity_lock_binding_blockers(args, phase))
    return blockers


def collect_public_or_runtime_claims(
    value: Any,
    *,
    path: str = "",
    include_text_claims: bool = True,
) -> list[str]:
    claims: list[str] = []

    def normalized_key(key: object) -> str:
        return normalized_claim_key(key)

    def normalized_source(value: object) -> str:
        return re.sub(r"[^a-z0-9]+", "_", str(value).casefold()).strip("_")

    def normalized_path_parts(claim_path: str) -> list[str]:
        return normalized_claim_path_parts(claim_path)

    def normalized_path_suffixes(claim_path: str) -> list[str]:
        parts = normalized_path_parts(claim_path)
        return ["_".join(parts[index:]) for index in range(len(parts))]

    def progress_value_is_nonzero(item: Any) -> bool:
        return progress_claim_value_is_nonzero(item)

    def contains_positive_claim_value(item: Any) -> bool:
        if is_positive_claim_value(item):
            return True
        if isinstance(item, list):
            return any(contains_positive_claim_value(child) for child in item)
        if isinstance(item, dict):
            return any(contains_positive_claim_value(child) for child in item.values())
        return False

    def alias_claim_value_is_positive(key_name: str, item: Any) -> bool:
        if key_name in MULTI_SURFACE_BETA_CAPTURE_SOURCE_VALUES and isinstance(item, dict):
            return False
        if downstream_promotion_certificate_alias_key_is_forbidden(key_name):
            return downstream_promotion_certificate_alias_value_is_positive(item)
        if key_name in NON_FALSE_PUBLIC_OR_RUNTIME_CLAIM_KEYS and claim_value_is_nonfalse(item):
            return True
        if public_or_runtime_progress_alias_key(key_name) and progress_value_is_nonzero(item):
            return True
        return contains_positive_claim_value(item)

    def non_authorizing_context_value_is_positive(item: Any) -> bool:
        if item is True:
            return True
        if isinstance(item, (int, float)) and not isinstance(item, bool):
            return item != 0
        if isinstance(item, str):
            return normalized_key(item) in NON_AUTHORIZING_CONTEXT_POSITIVE_STATUS_VALUES
        return False

    def path_marks_non_authorizing_context(claim_path: str) -> bool:
        return any(
            NON_AUTHORIZING_CONTEXT_RE.search(part) is not None
            for part in normalized_path_parts(claim_path)
        )

    def path_marks_multi_surface_beta_capture_context(claim_path: str) -> bool:
        return any(
            re.search(MULTI_SURFACE_BETA_CAPTURE_CONTEXT_RE, part) is not None
            for part in normalized_path_parts(claim_path)
        )

    def value_marks_multi_surface_beta_capture_context(item: Any) -> bool:
        if isinstance(item, str):
            return re.search(MULTI_SURFACE_BETA_CAPTURE_CONTEXT_RE, normalized_key(item)) is not None
        if isinstance(item, list):
            return any(value_marks_multi_surface_beta_capture_context(child) for child in item)
        if isinstance(item, dict):
            return any(
                (
                    normalized_key(key) in SOURCE_MARKER_KEYS | SOURCE_PROVENANCE_CONTEXT_KEYS
                    or normalized_key(key)
                    in {
                        "artifact_scope",
                        "classification",
                        "evidence_kind",
                        "path_type",
                        "readiness_scope",
                        "ready_scope",
                        "schema",
                        "source_kind",
                        "source_status",
                        "status",
                        "target_set",
                        "type",
                    }
                )
                and value_marks_multi_surface_beta_capture_context(child)
                for key, child in item.items()
            )
        return False

    def approved_runtime_evidence_missing_still_present(item: Any) -> bool:
        if isinstance(item, str):
            return normalized_key(item) == "approved_runtime_evidence_missing"
        if isinstance(item, list):
            return any(approved_runtime_evidence_missing_still_present(child) for child in item)
        if isinstance(item, dict):
            return any(approved_runtime_evidence_missing_still_present(child) for child in item.values())
        return item is True

    def non_authorizing_context_blocker_clearance_claim(key_name: str, item: Any) -> bool:
        if key_name in MULTI_SURFACE_BETA_CAPTURE_CLEARANCE_KEYS:
            return claim_value_is_nonfalse(item)
        if key_name == "approved_runtime_evidence_missing":
            if item is False:
                return True
            if isinstance(item, (int, float)) and not isinstance(item, bool):
                return item == 0
            if isinstance(item, str):
                return normalized_key(item) in {
                    "cleared",
                    "false",
                    "no",
                    "none",
                    "not_missing",
                    "resolved",
                    "satisfied",
                    "unblocked",
                }
            return False
        if key_name in {"current_blocker", "current_route_blocker", "next_blocker", "next_route_blocker"}:
            if isinstance(item, str):
                normalized = normalized_key(item)
                return normalized not in {
                    "approved_runtime_evidence_missing",
                    "blocked",
                    "missing",
                    "pending",
                    "unchanged",
                }
            return claim_value_is_nonfalse(item)
        if key_name in {"remaining_blockers", "remaining_route_blockers", "route_blocker"}:
            return not approved_runtime_evidence_missing_still_present(item)
        return False

    def path_marks_identity_decision_record_metadata_context(claim_path: str) -> bool:
        parts = normalized_path_parts(claim_path)
        if any(non_claiming_requirement_or_negative_key(part) for part in parts):
            return False
        return any(identity_decision_record_metadata_context_key(part) for part in parts)

    def path_marks_identity_decision_record_template_context(claim_path: str) -> bool:
        return any(
            identity_decision_record_template_context_key(part)
            for part in normalized_path_parts(claim_path)
        )

    def path_marks_identity_decision_record_downstream_context(claim_path: str) -> bool:
        return bool(
            set(normalized_path_parts(claim_path))
            & IDENTITY_DECISION_RECORD_DOWNSTREAM_CONTEXT_KEYS
        )

    def path_marks_player_identity_promotion_certificate_context(claim_path: str) -> bool:
        return any(
            player_identity_promotion_certificate_context_key(part)
            for part in normalized_path_parts(claim_path)
        )

    def path_marks_accepted_runtime_evidence_binding_context(claim_path: str) -> bool:
        parts = set(normalized_path_parts(claim_path))
        return "approved_runtime_evidence" in parts and "approved_runtime_evidence_binding" in parts

    def value_marks_non_authorizing_context(item: Any) -> bool:
        if isinstance(item, str):
            return NON_AUTHORIZING_CONTEXT_RE.search(normalized_key(item)) is not None
        if isinstance(item, list):
            return any(value_marks_non_authorizing_context(child) for child in item)
        if isinstance(item, dict):
            return any(
                (
                    normalized_key(key) in SOURCE_MARKER_KEYS | SOURCE_PROVENANCE_CONTEXT_KEYS
                    and (
                        value_marks_non_authorizing_context(child)
                        or source_marker_value_claims_positive_alias(child)
                        or value_marks_identity_decision_record_metadata(child)
                    )
                )
                or (
                    normalized_key(key)
                    in {
                        "artifact_scope",
                        "classification",
                        "evidence_kind",
                        "path_type",
                        "readiness_scope",
                        "ready_scope",
                        "schema",
                        "source_kind",
                        "source_status",
                        "status",
                        "target_set",
                        "type",
                    }
                    and value_marks_non_authorizing_context(child)
                )
                for key, child in item.items()
            )
        return False

    def source_marker_value_claims_positive_alias(item: Any) -> bool:
        if isinstance(item, str):
            marker = normalized_key(item)
            return public_or_runtime_alias_key_is_forbidden(marker) and (
                BROAD_P0_ROUTE_ALIAS_STATE_RE.search(marker) is not None
                or public_or_runtime_progress_alias_key(marker)
            )
        if isinstance(item, list):
            return any(source_marker_value_claims_positive_alias(child) for child in item)
        if isinstance(item, dict):
            return any(source_marker_value_claims_positive_alias(child) for child in item.values())
        return False

    def notice_or_bundle_status_alias_claim(
        key_name: str,
        item: Any,
        claim_path: str,
    ) -> bool:
        path_parts = normalized_path_parts(claim_path)
        if key_name in NOTICE_OR_BUNDLE_NON_PROGRESS_FALSE_ALIAS_KEYS:
            return is_positive_claim_value(item)
        if any(
            suffix in NOTICE_OR_BUNDLE_NON_PROGRESS_FALSE_ALIAS_KEYS
            for suffix in normalized_path_suffixes(claim_path)
        ):
            return is_positive_claim_value(item)
        combined_status_key_match = any(
            key_name.endswith(f"_{status_key}")
            and any(container in key_name for container in NOTICE_OR_BUNDLE_STATUS_CONTAINER_KEYS)
            for status_key in NOTICE_OR_BUNDLE_STATUS_KEYS
        )
        if key_name not in NOTICE_OR_BUNDLE_STATUS_KEYS and not combined_status_key_match:
            return False
        if not combined_status_key_match and not any(
            part in NOTICE_OR_BUNDLE_STATUS_CONTAINER_KEYS for part in path_parts
        ):
            return False
        if isinstance(item, str):
            return normalized_key(item) in NOTICE_OR_BUNDLE_POSITIVE_STATUS_VALUES
        return is_positive_claim_value(item)

    def contains_forbidden_claim_source(item: Any) -> bool:
        if isinstance(item, str):
            source = normalized_source(item)
            return (
                source in FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_VALUES
                or downstream_promotion_certificate_alias_key_is_forbidden(source)
                or FORBIDDEN_PRE_PUBLIC_CONTRACT_CLAIM_SOURCE_VALUE_RE.search(source) is not None
            )
        if isinstance(item, list):
            return any(contains_forbidden_claim_source(child) for child in item)
        if isinstance(item, dict):
            return any(contains_forbidden_claim_source(child) for child in item.values())
        return False

    def text_claim_path_is_exempt_metadata(claim_path: str) -> bool:
        exempt_path_parts = {
            "argv",
            "blocked_until",
            "blocker",
            "blocker_details",
            "blockers",
            "cannot_unlock_without",
            "claim_requires",
            "current_blocker",
            "current_route_blocker",
            "decision_required",
            "exclusion",
            "exclusions",
            "expected_schema",
            "forbidden_unlocks",
            "input_schema",
            "negative_surface_exclusions",
            "next_after_runtime_evidence",
            "next_action_sequence",
            "next_steps",
            "operator_next_commands",
            "next_blocker",
            "next_route_blocker_after_runtime_evidence",
            "non_claim",
            "non_claims",
            "promotion_requires",
            "report_schema",
            "remaining_route_blockers",
            "accepted_artifact_class",
            "accepted_review_route",
            "required",
            "required_checks",
            "required_behavior",
            "required_before_public_header",
            "required_evidence",
            "required_exclusions",
            "required_fields",
            "required_fields_or_equivalent",
            "required_policy",
            "required_properties",
            "schema",
            "schema_id",
            "schema_ids",
            "schemas",
            "source_schema",
            "source_checker_blockers",
            "source_checker_primary_blocker",
            "v1_sequence_gate",
            "why_blocked",
        }
        return any(
            normalized_key(part.split("[", 1)[0]) in exempt_path_parts
            for part in claim_path.split(".")
            if part
        )

    def path_marks_diagnostic_parent_context(claim_path: str, key_name: str) -> bool:
        parts = normalized_path_parts(claim_path)
        if parts and parts[-1] == key_name:
            parts = parts[:-1]
        return any("diagnostic" in part for part in parts)

    def non_claiming_guardrail_claim_field(
        claim_path: str,
        key_name: str,
        item: Any,
    ) -> bool:
        if non_claiming_requirement_or_negative_key(key_name):
            return True
        return (
            key_name == "diagnostic_only"
            and item is True
            and path_marks_diagnostic_parent_context(claim_path, key_name)
        )

    def post_approved_runtime_route_check_diagnostic_field(
        claim_path: str,
        key_name: str,
        item: Any,
    ) -> bool:
        return (
            key_name == "runtime_evidence_accepted"
            and item is True
            and any(
                part == "post_approved_runtime_evidence_route_check"
                for part in normalized_path_parts(claim_path)
            )
        )

    def copied_log_triplet_correlation_proof_record(
        claim_path: str,
        key_name: str,
        item: Any,
    ) -> bool:
        parts = set(normalized_path_parts(claim_path))
        return (
            key_name == "copied_log_triplet"
            and "lifecycle_correlation_proof" in parts
            and isinstance(item, dict)
            and item.get("accepted") is True
            and item.get("single_complete_sibling_set") is True
            and item.get("source") == "copied_log"
            and isinstance(item.get("non_claim"), str)
            and "does_not_promote_public_identity_or_sdk_readiness" in normalized_claim_key(item["non_claim"])
        )

    def identity_public_contract_gate_blocker_record(
        container: Any,
        key_name: str,
        item: Any,
    ) -> bool:
        if key_name != "identity_public_contract_gate_missing":
            return False
        if not isinstance(container, dict) or not isinstance(item, dict):
            return False
        if container.get("schema") != EXPECTED_ROUTE_CHECK_SCHEMAS["player_identity_public_contract_gap"]:
            return False
        return (
            item.get("active") is True
            and isinstance(item.get("cannot_unlock_without"), list)
            and bool(item.get("cannot_unlock_without"))
            and isinstance(item.get("next_auditable_blocker"), dict)
            and item.get("redactionEvidencePromotesIdentity") is False
        )

    def blocked_identity_decision_record_metadata_field(
        container: Any,
        key_name: str,
        item: Any,
    ) -> bool:
        if not isinstance(container, dict):
            return False
        if key_name != "reviewed_hash_current_contract_review_only":
            return False
        if item is not True:
            return False
        return (
            container.get("accepted_for_contract_review") is False
            and container.get("review_inputs_non_counting_until") == "runtime.lifecycle_evidence"
            and container.get("promotion_ready") is False
            and container.get("public_sdk_ready") is False
            and container.get("runtime_ready") is False
        )

    def blocked_identity_decision_record_metadata_container(container: Any) -> bool:
        return (
            isinstance(container, dict)
            and container.get("accepted_for_contract_review") is False
            and container.get("review_inputs_non_counting_until") == "runtime.lifecycle_evidence"
            and container.get("promotion_ready") is False
            and container.get("public_sdk_ready") is False
            and container.get("runtime_ready") is False
        )

    def identity_decision_record_metadata_status_claim(
        container: Any,
        claim_path: str,
        key_name: str,
        item: Any,
    ) -> bool:
        if blocked_identity_decision_record_metadata_container(container):
            return False
        if path_marks_identity_decision_record_template_context(claim_path):
            return (
                key_name in IDENTITY_DECISION_RECORD_METADATA_STATUS_KEYS
                and identity_decision_record_metadata_status_value_is_positive(item)
            )
        return (
            path_marks_identity_decision_record_downstream_context(claim_path)
            and key_name in IDENTITY_DECISION_RECORD_DOWNSTREAM_STATUS_KEYS
            and identity_decision_record_metadata_status_value_is_positive(item)
        )

    def visit(
        item_value: Any,
        claim_path: str,
        in_non_authorizing_context: bool,
        in_identity_decision_record_metadata_context: bool,
        in_multi_surface_beta_capture_context: bool,
    ) -> None:
        current_context = in_non_authorizing_context or path_marks_non_authorizing_context(claim_path)
        current_player_identity_promotion_certificate_context = (
            path_marks_player_identity_promotion_certificate_context(claim_path)
        )
        current_multi_surface_beta_capture_context = (
            in_multi_surface_beta_capture_context
            or path_marks_multi_surface_beta_capture_context(claim_path)
        )
        current_identity_decision_record_metadata_context = (
            in_identity_decision_record_metadata_context
            or path_marks_identity_decision_record_metadata_context(claim_path)
        )
        if isinstance(item_value, dict):
            current_context = current_context or value_marks_non_authorizing_context(item_value)
            current_multi_surface_beta_capture_context = (
                current_multi_surface_beta_capture_context
                or value_marks_multi_surface_beta_capture_context(item_value)
            )
            current_identity_decision_record_metadata_context = (
                current_identity_decision_record_metadata_context
                or value_marks_identity_decision_record_metadata(item_value)
            )
            declared_claim_names = [
                str(item)
                for key, item in item_value.items()
                if normalized_key(key) in SPLIT_CLAIM_NAME_KEYS and isinstance(item, str)
            ]
            declared_claim_values = [
                item
                for key, item in item_value.items()
                if normalized_key(key) in SPLIT_CLAIM_VALUE_KEYS
            ]
            for claim_name in declared_claim_names:
                claim_key = normalized_key(claim_name)
                claim_path_for_name = claim_path or "$"
                if public_or_runtime_alias_key_is_forbidden(claim_key) and any(
                    alias_claim_value_is_positive(claim_key, item) for item in declared_claim_values
                ):
                    claims.append(claim_path_for_name)
                if (
                    claim_key in FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_KEYS
                    and any(contains_forbidden_claim_source(item) for item in declared_claim_values)
                ):
                    claims.append(claim_path_for_name)
                if (
                    identity_decision_record_metadata_context_key(claim_key)
                    and any(
                        identity_decision_record_metadata_progress_value_is_positive(item)
                        for item in declared_claim_values
                    )
                ):
                    claims.append(claim_path_for_name)
            for key, item in item_value.items():
                item_path = f"{claim_path}.{key}" if claim_path else str(key)
                key_name = normalized_key(key)
                item_player_identity_promotion_certificate_context = (
                    current_player_identity_promotion_certificate_context
                    or path_marks_player_identity_promotion_certificate_context(item_path)
                )
                if (
                    player_identity_promotion_certificate_reference_key(key_name)
                    and isinstance(item, dict)
                    and (
                        not canonical_player_identity_promotion_certificate_reference_key(key_name)
                        or not strict_player_identity_promotion_certificate_reference(item)
                    )
                ):
                    claims.append(item_path)
                if (
                    item_player_identity_promotion_certificate_context
                    and key_name in PLAYER_IDENTITY_PROMOTION_CERTIFICATE_POSITIVE_KEYS
                    and is_positive_claim_value(item)
                    and not strict_player_identity_promotion_certificate_reference(item_value)
                ):
                    claims.append(item_path)
                non_claiming_guardrail_field = non_claiming_guardrail_claim_field(
                    item_path,
                    key_name,
                    item,
                )
                if (
                    public_or_runtime_alias_key_is_forbidden(key_name)
                    and alias_claim_value_is_positive(key_name, item)
                    and not non_claiming_guardrail_field
                    and not blocked_identity_decision_record_metadata_field(item_value, key_name, item)
                    and not post_approved_runtime_route_check_diagnostic_field(item_path, key_name, item)
                    and not copied_log_triplet_correlation_proof_record(item_path, key_name, item)
                    and not identity_public_contract_gate_blocker_record(item_value, key_name, item)
                ):
                    claims.append(item_path)
                if key_name in SOURCE_MARKER_KEYS and source_marker_value_claims_positive_alias(item):
                    claims.append(item_path)
                if notice_or_bundle_status_alias_claim(key_name, item, item_path):
                    claims.append(item_path)
                if (
                    key_name in SPLIT_CLAIM_VALUE_KEYS
                    and is_positive_claim_value(item)
                    and any(
                        suffix in PUBLIC_SURFACE_STATUS_ALIAS_SUFFIXES
                        for suffix in normalized_path_suffixes(item_path)
                    )
                ):
                    claims.append(item_path)
                if (
                    key_name in FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_KEYS
                    and contains_forbidden_claim_source(item)
                    and not text_claim_path_is_exempt_metadata(item_path)
                    and not path_marks_accepted_runtime_evidence_binding_context(item_path)
                ):
                    claims.append(item_path)
                if (
                    current_context
                    and key_name in NON_AUTHORIZING_CONTEXT_READY_ALIAS_KEYS
                    and non_authorizing_context_value_is_positive(item)
                ):
                    claims.append(item_path)
                if (
                    current_multi_surface_beta_capture_context
                    and non_authorizing_context_blocker_clearance_claim(key_name, item)
                ):
                    claims.append(item_path)
                if (
                    current_context
                    and key_name
                    in {
                        "approved_runtime_evidence",
                        "approved_runtime_evidence_present",
                        "runtime_evidence_present",
                        "runtime_evidence_ready",
                        "sdk_evidence_ready",
                    }
                    and alias_claim_value_is_positive(key_name, item)
                ):
                    claims.append(item_path)
                if (
                    current_context
                    and key_name in NON_AUTHORIZING_CONTEXT_ZERO_ALIAS_KEYS
                    and progress_value_is_nonzero(item)
                ):
                    claims.append(item_path)
                if (
                    current_identity_decision_record_metadata_context
                    and identity_decision_record_metadata_progress_alias_key(key_name)
                    and progress_value_is_nonzero(item)
                ):
                    claims.append(item_path)
                if (
                    current_identity_decision_record_metadata_context
                    and identity_decision_record_metadata_status_claim(item_value, item_path, key_name, item)
                ):
                    claims.append(item_path)
                if (
                    current_identity_decision_record_metadata_context
                    and key_name in SPLIT_CLAIM_VALUE_KEYS
                    and identity_decision_record_metadata_progress_value_is_positive(item)
                ):
                    claims.append(item_path)
                if key == "public_or_runtime_claims" and isinstance(item, list):
                    for claim in item:
                        if isinstance(claim, str) and claim:
                            claims.append(f"{item_path}:{claim}")
                visit(
                    item,
                    item_path,
                    current_context,
                    current_identity_decision_record_metadata_context,
                    current_multi_surface_beta_capture_context,
                )
        elif isinstance(item_value, list):
            for index, item in enumerate(item_value):
                visit(
                    item,
                    f"{claim_path}[{index}]",
                    current_context,
                    current_identity_decision_record_metadata_context,
                    current_multi_surface_beta_capture_context,
                )
        elif isinstance(item_value, str):
            if (
                include_text_claims
                and not text_claim_path_is_exempt_metadata(claim_path)
                and contains_positive_public_or_runtime_text_claim(item_value)
            ):
                claims.append(f"{claim_path}:positive_text_claim")

    visit(value, path, False, False, False)
    return sorted(set(claims))


IDENTITY_FIRST_EVIDENCE_INTERNAL_PLANNING_CLAIM_PATHS = frozenset(
    {
        "artifact_chain.accepted_reflection_inventory_chain.ready",
        "artifact_root_fallback.fallback_diagnosis.candidate_pack_count",
        "artifact_root_fallback.primary_diagnosis.reason_counts",
        "first_evidence.approved_runtime_principal_lifecycle_evidence_manifest.ready",
        "first_evidence.consume_gate.ready",
        "first_evidence.lifecycle_anchor_candidates.ready",
        "first_evidence.planning_provenance.ready",
        "first_evidence.principal_invalidation_policy.ready",
        "first_evidence.public_contract_gap_report.ready",
        "first_evidence.ready",
        "progress_signal",
        "reflection_inventory.artifact_root_diagnosis.candidate_pack_count",
        "reflection_inventory.chain_validation.ready",
        "reflection_inventory.ready",
    }
)
IDENTITY_FIRST_EVIDENCE_INTERNAL_PLANNING_CLAIM_RE = re.compile(
    r"^(?:"
    r"(?:artifact_root_fallback\.fallback_diagnosis|reflection_inventory\.artifact_root_diagnosis)"
    r"\.blocked_candidate_packs\[\d+\]\.ready|"
    r"artifact_root_fallback\.primary_diagnosis\.reason_examples\.[^.]+"
    r"\.scanned_paths\.(?:omitted_count|total_count)|"
    r"(?:first_evidence\.runtime_principal_lifecycle_evidence|next_actionable_blocker\.next_required_evidence)"
    r"\.minimum_required_runtime_observations"
    r"\[\d+\]\.diagnostic_candidate_boundary\.reason"
    r")$"
)


def identity_first_evidence_internal_planning_claim_path(claim_path: str) -> bool:
    path = claim_path.split(":", 1)[0]
    return (
        path in IDENTITY_FIRST_EVIDENCE_INTERNAL_PLANNING_CLAIM_PATHS
        or IDENTITY_FIRST_EVIDENCE_INTERNAL_PLANNING_CLAIM_RE.fullmatch(path) is not None
    )


def identity_first_evidence_source_claims(report: dict[str, Any] | None) -> list[str]:
    claims = collect_public_or_runtime_claims(report) if report is not None else []
    return [
        claim
        for claim in claims
        if not identity_first_evidence_internal_planning_claim_path(claim)
    ]


def run_check(name: str, argv: list[str]) -> dict[str, Any]:
    command = [sys.executable, str(SCRIPT_DIR / argv[0]), *argv[1:]]
    result = subprocess.run(command, cwd=REPO_ROOT, check=False, capture_output=True, text=True)

    report: dict[str, Any] | None = None
    parse_error = None
    try:
        loaded = json.loads(result.stdout)
        if isinstance(loaded, dict):
            report = loaded
        else:
            parse_error = "stdout_json_not_object"
    except json.JSONDecodeError as exc:
        parse_error = f"stdout_json_decode_error: {exc}"

    public_or_runtime_claims = []
    if report is not None:
        public_or_runtime_claims = collect_public_or_runtime_claims(report)

    report_schema = report.get("schema") if report is not None else None
    expected_schema = EXPECTED_ROUTE_CHECK_SCHEMAS.get(name)
    schema_valid = report_schema == expected_schema
    report_blockers = report.get("blockers", []) if report is not None else []
    blockers_empty = isinstance(report_blockers, list) and not report_blockers

    check_valid = (
        result.returncode == 0
        and report is not None
        and schema_valid
        and report.get("valid") is True
        and blockers_empty
        and (
            name not in REQUIRED_PLANNING_ONLY_CHECKS
            or (
                report.get("valid") is True
                and report.get("planning_only") is True
                and report.get("accepted_for_planning") is True
            )
        )
        and not public_or_runtime_claims
    )
    if name in REQUIRED_LOCKED_CHILD_CHECKS:
        check_valid = (
            check_valid
            and report is not None
            and report.get("dependency_chain_locked") is True
            and report.get("current_route_blocker") in ALLOWED_IDENTITY_LOCK_BLOCKERS
            and isinstance(report.get("remaining_route_blockers"), list)
            and report.get("remaining_route_blockers") != []
            and all(report.get(key) is False for key in REQUIRED_CHILD_ACCOUNTING_FALSE_KEYS)
        )

    return {
        "name": name,
        "argv": argv,
        "exit_code": result.returncode,
        "valid": check_valid,
        "report_schema": report_schema,
        "expected_schema": expected_schema,
        "planning_only": report.get("planning_only") if report is not None else None,
        "accepted_for_planning": report.get("accepted_for_planning") if report is not None else None,
        "dependency_chain_locked": report.get("dependency_chain_locked") if report is not None else None,
        "current_route_blocker": report.get("current_route_blocker") if report is not None else None,
        "remaining_route_blockers": report.get("remaining_route_blockers") if report is not None else None,
        "counts_toward_public_sdk": report.get("counts_toward_public_sdk") if report is not None else None,
        "counts_toward_runtime": report.get("counts_toward_runtime") if report is not None else None,
        "counts_toward_v1_completion": report.get("counts_toward_v1_completion") if report is not None else None,
        "public_or_runtime_accounting_allowed": (
            report.get("public_or_runtime_accounting_allowed") if report is not None else None
        ),
        "public_or_runtime_claims": public_or_runtime_claims,
        "blockers": report_blockers,
        "parse_error": parse_error,
        "stderr": result.stderr.strip(),
        "report_payload": report,
    }


def locked_child_post_runtime_identity_contract_quarantined(
    check: dict[str, Any],
    *,
    response_path_report_quarantined: bool = False,
) -> bool:
    blockers = check.get("blockers")
    claims = check.get("public_or_runtime_claims")
    allowed_blockers = set(POST_RUNTIME_IDENTITY_CONTRACT_CHILD_LOCK_BLOCKERS)
    if check.get("name") == "commands_replies_public_readiness" and response_path_report_quarantined:
        allowed_blockers.update(POST_RUNTIME_IDENTITY_CONTRACT_RESPONSE_REPORT_DERIVED_BLOCKERS)
    return (
        check.get("name") in REQUIRED_LOCKED_CHILD_CHECKS
        and check.get("parse_error") is None
        and check.get("report_schema") == check.get("expected_schema")
        and check.get("dependency_chain_locked") is True
        and check.get("current_route_blocker") == "identity_public_contract_gate_missing"
        and check.get("remaining_route_blockers") == ["identity_public_contract_gate_missing"]
        and all(check.get(key) is False for key in REQUIRED_CHILD_ACCOUNTING_FALSE_KEYS)
        and isinstance(claims, list)
        and set(claims).issubset(POST_RUNTIME_IDENTITY_CONTRACT_CHILD_LOCK_CLAIMS)
        and isinstance(blockers, list)
        and bool(blockers)
        and set(blockers).issubset(allowed_blockers)
    )


def identity_gap_post_runtime_contract_lock_quarantined(check: dict[str, Any]) -> bool:
    blockers = check.get("blockers")
    claims = check.get("public_or_runtime_claims")
    report = check.get("report_payload")
    if (
        check.get("name") == "player_identity_public_contract_gap"
        and check.get("parse_error") is None
        and check.get("report_schema") == check.get("expected_schema")
        and check.get("valid") is True
        and isinstance(blockers, list)
        and set(blockers).issubset(POST_RUNTIME_IDENTITY_CONTRACT_GAP_CHECK_BLOCKERS)
        and isinstance(claims, list)
        and set(claims).issubset(POST_RUNTIME_IDENTITY_CONTRACT_GAP_CHECK_CLAIMS)
    ):
        return True
    if not (
        check.get("name") == "player_identity_public_contract_gap"
        and check.get("parse_error") is None
        and check.get("report_schema") == check.get("expected_schema")
        and isinstance(blockers, list)
        and set(blockers).issubset(POST_RUNTIME_IDENTITY_CONTRACT_GAP_CHECK_BLOCKERS)
        and isinstance(claims, list)
        and set(claims).issubset(POST_RUNTIME_IDENTITY_CONTRACT_GAP_CHECK_CLAIMS)
        and isinstance(report, dict)
        and report.get("status") == "blocked"
        and report.get("current_blocker") == "identity_public_contract_gate_missing"
        and report.get("next_blocker") == "identity_public_contract_gate_missing"
        and report.get("accepted_for_contract_review") is False
        and report.get("promotion_ready") is False
        and report.get("public_sdk_ready") is False
        and report.get("public_header_allowed") is False
        and report.get("public_abi_ready") is False
        and report.get("public_api_ready") is False
        and report.get("runtime_ready") is False
        and report.get("v1_completion_evidence") is False
        and report.get("counts_toward_public_sdk") is False
        and report.get("counts_toward_runtime") is False
        and report.get("counts_toward_v1_completion") is False
        and report.get("counts_toward_complete_sdk_claim") is False
        and report.get("counts_toward_p0_dependency_chain_claim") is False
        and report.get("p0_progress_ready") is False
        and report.get("sdk_p0_progress_ready") is False
    ):
        return False
    identity_gate = report.get("identity_public_contract_gate_missing")
    post_runtime_gate = report.get("post_approved_runtime_evidence_gate")
    post_runtime_route_check = report.get("post_approved_runtime_evidence_route_check")
    post_runtime_gap = report.get("post_runtime_public_identity_gap_summary")
    return (
        isinstance(identity_gate, dict)
        and identity_gate.get("active") is True
        and isinstance(post_runtime_gate, dict)
        and post_runtime_gate.get("active") is True
        and post_runtime_gate.get("next_blocker") == "identity_public_contract_gate_missing"
        and post_runtime_gate.get("promotion_ready") is False
        and post_runtime_gate.get("public_sdk_ready") is False
        and post_runtime_gate.get("runtime_ready") is False
        and isinstance(post_runtime_route_check, dict)
        and post_runtime_route_check.get("contract_review_input_present") is True
        and post_runtime_route_check.get("diagnostic_current_blocker")
        == "identity_public_contract_gate_missing"
        and post_runtime_route_check.get("diagnostic_next_blocker")
        == "identity_public_contract_gate_missing"
        and isinstance(post_runtime_gap, dict)
        and post_runtime_gap.get("active") is True
        and post_runtime_gap.get("current_blocker") == "identity_public_contract_gate_missing"
        and post_runtime_gap.get("next_blocker") == "identity_public_contract_gate_missing"
        and post_runtime_gap.get("only_valid_post_runtime_route")
        == "identity_public_contract_gate_missing"
        and post_runtime_gap.get("approved_runtime_bundle_consumed") is True
        and post_runtime_gap.get("approved_runtime_evidence_scope")
        == "consume_only_contract_review_input"
        and post_runtime_gap.get("permissions_admin_opened") is False
        and post_runtime_gap.get("permissions_admin_ready") is False
        and post_runtime_gap.get("command_chat_response_ready") is False
        and post_runtime_gap.get("commands_replies_ready") is False
        and post_runtime_gap.get("promotion_ready") is False
        and post_runtime_gap.get("public_contract_allowed") is False
        and post_runtime_gap.get("public_header_allowed") is False
        and post_runtime_gap.get("public_abi_ready") is False
        and post_runtime_gap.get("public_api_ready") is False
        and post_runtime_gap.get("public_sdk_ready") is False
        and post_runtime_gap.get("public_readiness") is False
        and post_runtime_gap.get("runtime_ready") is False
        and post_runtime_gap.get("runtime_readiness") is False
        and post_runtime_gap.get("lookup_ready") is False
        and post_runtime_gap.get("permissions_ready") is False
        and post_runtime_gap.get("commands_ready") is False
    )


def resolved_path_text(value: Any) -> str | None:
    if not isinstance(value, (str, Path)) or not str(value):
        return None
    return str(Path(value).resolve())


def identity_manifest_source_diagnostics(
    args: argparse.Namespace | None,
    source_report: dict[str, Any] | None,
) -> dict[str, Any]:
    source_specs = {
        "lifecycle_anchor_candidates": {
            "arg": "player_identity_lifecycle_anchor_candidates_manifest",
            "report_key": "lifecycle_anchor_candidates_manifest",
            "default": DEFAULT_PLAYER_IDENTITY_LIFECYCLE_ANCHOR_CANDIDATES,
        },
        "principal_invalidation_policy": {
            "arg": "player_identity_principal_invalidation_policy_manifest",
            "report_key": "principal_invalidation_policy_manifest",
            "default": DEFAULT_PLAYER_IDENTITY_PRINCIPAL_INVALIDATION_POLICY,
        },
    }
    manifests: dict[str, Any] = {}
    for name, spec in source_specs.items():
        cli_value = getattr(args, spec["arg"], None) if args is not None else None
        expected_path = cli_value or spec["default"]
        observed_path = source_report.get(spec["report_key"]) if source_report is not None else None
        expected_resolved = resolved_path_text(expected_path)
        observed_resolved = resolved_path_text(observed_path)
        manifests[name] = {
            "source": "cli_bound" if cli_value is not None else "repo_local_default",
            "provided_by_cli": cli_value is not None,
            "expected_path": str(expected_path),
            "expected_resolved_path": expected_resolved,
            "observed_path": observed_path,
            "observed_resolved_path": observed_resolved,
            "matched": expected_resolved is not None and expected_resolved == observed_resolved,
        }
    mode = "cli_bound" if all(item["provided_by_cli"] for item in manifests.values()) else "repo_local_default"
    return {
        "mode": mode,
        "report_available": source_report is not None,
        "expected_manifests_received": all(item["matched"] for item in manifests.values()),
        "manifests": manifests,
        "non_claim": (
            "manifest source diagnostics bind identity planning inputs only; they do not promote "
            "public identity, permissions, commands, runtime readiness, or SDK completion"
        ),
    }


def build_critical_path_phase(args: argparse.Namespace | None = None) -> dict[str, Any]:
    result = subprocess.run(
        identity_readiness_argv(args),
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    report: dict[str, Any] | None = None
    parse_error = None
    try:
        loaded = json.loads(result.stdout)
        if isinstance(loaded, dict):
            report = loaded
        else:
            parse_error = "stdout_json_not_object"
    except json.JSONDecodeError as exc:
        parse_error = f"stdout_json_decode_error: {exc}"

    primary_blocker = None
    next_blocker = None
    if report is not None:
        primary_blocker = report.get("primary_blocker")
        next_blocker = report.get("next_blocker")
    source_blockers = report.get("blockers") if report is not None else None
    reported_primary_blocker = primary_blocker
    if (
        primary_blocker not in ALLOWED_IDENTITY_LOCK_BLOCKERS
        and isinstance(source_blockers, list)
        and "approved_runtime_evidence_missing" in source_blockers
    ):
        primary_blocker = "approved_runtime_evidence_missing"
    source_claims = identity_first_evidence_source_claims(report)
    manifest_sources = identity_manifest_source_diagnostics(args, report)
    approved_runtime_evidence_manifest = None
    if report is not None:
        first_evidence = report.get("first_evidence")
        if isinstance(first_evidence, dict):
            approved_runtime_evidence_manifest = first_evidence.get(
                "approved_runtime_principal_lifecycle_evidence_manifest"
            )
    if (
        primary_blocker not in ALLOWED_IDENTITY_LOCK_BLOCKERS
        and isinstance(source_blockers, list)
        and "identity_public_contract_gate_missing" in source_blockers
        and approved_runtime_evidence_ready_for_identity_lock(
            {"source_checker_approved_runtime_evidence_manifest": approved_runtime_evidence_manifest},
            args,
        )
    ):
        primary_blocker = "identity_public_contract_gate_missing"

    current_blocker = primary_blocker or next_blocker
    blocker_route = ALLOWED_IDENTITY_LOCK_BLOCKERS.get(str(current_blocker), {})
    return {
        "current_surface": "obelisk.player_identity.v1",
        "current_blocker": current_blocker,
        "source_checker_primary_blocker": primary_blocker,
        "source_checker_next_blocker": next_blocker,
        "next_action": blocker_route.get("next_action", "resolve_identity_lock_blocker"),
        "next_after_runtime_evidence": "identity_public_contract_gate_missing",
        "permissions_admin_unlocked": False,
        "command_response_unlocked": False,
        "commands_replies_unlocked": False,
        "source_checker": "check_player_identity_first_evidence_readiness.py",
        "source_checker_exit_code": result.returncode,
        "source_checker_schema": report.get("schema") if report is not None else None,
        "source_checker_parse_error": parse_error,
        "source_checker_status": report.get("status") if report is not None else None,
        "source_checker_ready": report.get("ready") if report is not None else None,
        "source_checker_accepted_for_internal_planning": (
            report.get("accepted_for_internal_planning") if report is not None else None
        ),
        "source_checker_blockers": source_blockers,
        "source_checker_reported_primary_blocker": reported_primary_blocker,
        "source_checker_public_or_runtime_claims": source_claims,
        "source_checker_manifest_sources": manifest_sources,
        "source_checker_approved_runtime_evidence_manifest": approved_runtime_evidence_manifest,
        "planning_only": True,
        "promotion_ready": report.get("promotion_ready") is True if report is not None else None,
        "public_sdk_ready": report.get("public_sdk_ready") is True if report is not None else None,
        "public_abi_ready": report.get("public_abi_ready") is True if report is not None else None,
        "runtime_ready": report.get("runtime_ready") is True if report is not None else None,
    }


def validate_critical_path_phase(phase: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if phase.get("current_surface") != "obelisk.player_identity.v1":
        blockers.append("critical_path_identity_gate_not_locked")
    if phase.get("source_checker_schema") != PLAYER_IDENTITY_FIRST_EVIDENCE_SCHEMA:
        blockers.append("critical_path_identity_readiness_schema_mismatch")
    if phase.get("source_checker_parse_error") is not None:
        blockers.append("critical_path_identity_readiness_output_invalid")
    if phase.get("source_checker_exit_code") != 1:
        blockers.append("critical_path_identity_readiness_exit_code_unexpected")
    if phase.get("source_checker_status") != "blocked":
        blockers.append("critical_path_identity_readiness_status_unexpected")
    if phase.get("source_checker_ready") is not False:
        blockers.append("critical_path_identity_readiness_ready_flag_overclaim")
    if phase.get("source_checker_accepted_for_internal_planning") is not False:
        blockers.append("critical_path_identity_readiness_ready_flag_overclaim")
    if phase.get("source_checker_primary_blocker") not in ALLOWED_IDENTITY_LOCK_BLOCKERS:
        blockers.append("critical_path_identity_readiness_blocker_missing")
    manifest_sources = phase.get("source_checker_manifest_sources")
    if not isinstance(manifest_sources, dict):
        blockers.append("critical_path_identity_readiness_manifest_sources_missing")
    elif manifest_sources.get("expected_manifests_received") is not True:
        blockers.append("critical_path_identity_readiness_expected_manifests_missing")
    source_blockers = phase.get("source_checker_blockers")
    primary_blocker = phase.get("source_checker_primary_blocker")
    if not isinstance(source_blockers, list):
        blockers.append("critical_path_identity_readiness_blockers_missing")
    elif primary_blocker in ALLOWED_IDENTITY_LOCK_BLOCKERS and primary_blocker not in source_blockers:
        blockers.append("critical_path_identity_readiness_primary_blocker_not_in_blockers")
    source_claims = phase.get("source_checker_public_or_runtime_claims")
    if isinstance(source_claims, list) and source_claims:
        blockers.append("critical_path_identity_readiness_public_or_runtime_claim")
    if phase.get("current_blocker") is None:
        blockers.append("critical_path_identity_gate_current_blocker_missing")
    if phase.get("current_blocker") not in ALLOWED_IDENTITY_LOCK_BLOCKERS:
        blockers.append("critical_path_identity_gate_unexpected_blocker")
    for key in (
        "permissions_admin_unlocked",
        "command_response_unlocked",
        "commands_replies_unlocked",
        "promotion_ready",
        "public_sdk_ready",
        "public_abi_ready",
        "runtime_ready",
    ):
        if phase.get(key) is not False:
            if key in {"promotion_ready", "public_sdk_ready", "public_abi_ready", "runtime_ready"}:
                blockers.append("critical_path_identity_readiness_ready_flag_overclaim")
            else:
                blockers.append(f"critical_path_{key}_must_stay_false")
    return blockers


def validate_locked_child_route_alignment(
    checks: list[dict[str, Any]],
    *,
    current_route_blocker: Any,
    remaining_route_blockers: list[Any],
) -> list[str]:
    blockers: list[str] = []
    expected_child_blocker = downstream_child_route_blocker(current_route_blocker)
    expected_child_blockers = [expected_child_blocker] if expected_child_blocker is not None else []
    for check in checks:
        if check["name"] not in REQUIRED_LOCKED_CHILD_CHECKS:
            continue
        if check.get("current_route_blocker") != expected_child_blocker:
            blockers.append(f"{check['name']}: current_route_blocker drifted from downstream lock")
        if check.get("remaining_route_blockers") != expected_child_blockers:
            blockers.append(f"{check['name']}: remaining_route_blockers drifted from downstream lock")
    return blockers


def build_post_evidence_p0_lock_simulation(
    *,
    critical_path_phase: dict[str, Any],
    checks: list[dict[str, Any]],
    approved_runtime_evidence_accepted: bool,
) -> dict[str, Any]:
    child_summaries: list[dict[str, Any]] = []
    checks_by_name = {check.get("name"): check for check in checks}
    for name in sorted(REQUIRED_LOCKED_CHILD_CHECKS):
        requirement = POST_EVIDENCE_P0_CHILD_GATE_REQUIREMENTS[name]
        check = checks_by_name.get(name)
        if not isinstance(check, dict):
            child_summaries.append(
                {
                    "name": name,
                    "present": False,
                    "surface": requirement["surface"],
                    "required_before_unlocking": list(requirement["required_before_unlocking"]),
                    "own_gate_required": True,
                    "accepted_runtime_identity_evidence_only_unlock_allowed": False,
                    "identity_evidence_shortcut_allowed": False,
                    "current_route_blocker": None,
                    "remaining_route_blockers": [],
                    "dependency_chain_locked": False,
                    "counts_toward_public_sdk": False,
                    "counts_toward_runtime": False,
                    "counts_toward_v1_completion": False,
                    "public_or_runtime_accounting_allowed": False,
                }
            )
            continue
        child_summaries.append(
            {
                "name": name,
                "present": True,
                "surface": requirement["surface"],
                "required_before_unlocking": list(requirement["required_before_unlocking"]),
                "own_gate_required": True,
                "accepted_runtime_identity_evidence_only_unlock_allowed": False,
                "identity_evidence_shortcut_allowed": False,
                "current_route_blocker": check.get("current_route_blocker"),
                "remaining_route_blockers": check.get("remaining_route_blockers"),
                "dependency_chain_locked": check.get("dependency_chain_locked"),
                "counts_toward_public_sdk": check.get("counts_toward_public_sdk"),
                "counts_toward_runtime": check.get("counts_toward_runtime"),
                "counts_toward_v1_completion": check.get("counts_toward_v1_completion"),
                "public_or_runtime_accounting_allowed": check.get("public_or_runtime_accounting_allowed"),
            }
        )

    current_blocker = critical_path_phase.get("current_blocker")
    simulation = {
        "schema": "obelisk.command-permission-route-post-evidence-p0-lock-simulation.v1",
        "simulation_only": True,
        "non_claim": (
            "Accepted runtime principal lifecycle evidence can move only to identity public "
            "contract review; it does not unlock permissions/admin, command response, "
            "commands/replies, runtime readiness, public SDK readiness, P0 progress, or "
            "complete SDK claim progress."
        ),
        "approved_runtime_evidence_accepted": approved_runtime_evidence_accepted,
        "current_route_blocker": current_blocker,
        "simulated_route_blocker_after_accepted_runtime_evidence": "identity_public_contract_gate_missing",
        "identity_public_contract_required": True,
        "required_identity_public_contract_decision_record": IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_REQUIREMENTS,
        "required_player_identity_promotion_certificate": PLAYER_IDENTITY_PROMOTION_CERTIFICATE_REQUIREMENTS,
        "identity_public_contract_decision_record_reviewed": False,
        "identity_public_contract_decision_record_hash_current": False,
        "identity_public_contract_decision_record_contract_review_only": False,
        "reviewed_hash_current_contract_review_only": False,
        "player_identity_promotion_certificate_accepted": False,
        "player_identity_promotion_certificate_hash_bound": False,
        "player_identity_promotion_certificate_promoted": False,
        "permissions_admin_unlock_has_hash_bound_player_identity_promotion_certificate": False,
        "cannot_unlock_without": [
            "reviewed_identity_public_contract_decision_record",
            "hash_current_source_artifacts",
            "contract_review_only_scope",
            "hash_bound_player_identity_promotion_certificate",
        ],
        "permissions_admin_unlocked": False,
        "command_response_unlocked": False,
        "commands_replies_unlocked": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "runtime_ready": False,
        "public_header_allowed": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "public_or_runtime_accounting_allowed": False,
        "stable_claim_allowed": False,
        "p0_child_checks": child_summaries,
    }
    for key in POST_EVIDENCE_P0_LOCK_FALSE_KEYS:
        simulation[key] = False
    for key in POST_EVIDENCE_P0_LOCK_ZERO_KEYS:
        simulation[key] = 0
    return simulation


def build_route_next_action_sequence(critical_path_phase: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": "current_route_lock_next_action",
            "planning_metadata_only": True,
            "current_route_blocker": critical_path_phase.get("current_blocker"),
            "next_action": critical_path_phase.get("next_action"),
            "next_after_runtime_evidence": critical_path_phase.get("next_after_runtime_evidence"),
            "approved_runtime_evidence_present": False,
            "runtime_evidence_ready": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_evidence": False,
            "counts_toward_public_sdk": False,
            "counts_toward_runtime": False,
            "counts_toward_v1_completion": False,
            "counts_toward_complete_sdk_claim": False,
            "counts_toward_p0_dependency_chain_claim": False,
            "complete_sdk_claim_progress_contribution": 0,
            "p0_dependency_chain_claim_progress_contribution": 0,
            "public_sdk_ready": False,
            "public_abi_ready": False,
            "public_header_allowed": False,
            "public_readiness_ready": False,
            "runtime_ready": False,
            "plugin_hub_ready": False,
            "plugin_hub_readiness_claim_allowed": False,
            "plugin_hub_publication_allowed": False,
            "publication_authorized": False,
            "non_claim": (
                "next_action_sequence is planning metadata only; it is not runtime "
                "evidence, SDK/P0 progress, public readiness, Plugin Hub readiness, "
                "or publication authority"
            ),
        }
    ]


def validate_post_evidence_p0_lock_simulation(simulation: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if simulation.get("schema") != "obelisk.command-permission-route-post-evidence-p0-lock-simulation.v1":
        blockers.append("post_evidence_p0_lock_simulation_schema_mismatch")
    if simulation.get("simulation_only") is not True:
        blockers.append("post_evidence_p0_lock_simulation_not_marked_simulation_only")
    if simulation.get("simulated_route_blocker_after_accepted_runtime_evidence") != "identity_public_contract_gate_missing":
        blockers.append("post_evidence_p0_lock_simulation_next_blocker_mismatch")
    if simulation.get("identity_public_contract_required") is not True:
        blockers.append("post_evidence_p0_lock_simulation_identity_contract_not_required")
    if (
        simulation.get("required_identity_public_contract_decision_record")
        != IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_REQUIREMENTS
    ):
        blockers.append("post_evidence_p0_lock_simulation_decision_record_requirements_mismatch")
    if (
        simulation.get("required_player_identity_promotion_certificate")
        != PLAYER_IDENTITY_PROMOTION_CERTIFICATE_REQUIREMENTS
    ):
        blockers.append("post_evidence_p0_lock_simulation_identity_promotion_certificate_requirements_mismatch")
    if simulation.get("cannot_unlock_without") != [
        "reviewed_identity_public_contract_decision_record",
        "hash_current_source_artifacts",
        "contract_review_only_scope",
        "hash_bound_player_identity_promotion_certificate",
    ]:
        blockers.append("post_evidence_p0_lock_simulation_cannot_unlock_without_mismatch")
    for key in POST_EVIDENCE_P0_LOCK_FALSE_KEYS:
        if simulation.get(key) is not False:
            blockers.append(f"post_evidence_p0_lock_simulation_{key}_not_false")
    for key in POST_EVIDENCE_P0_LOCK_ZERO_KEYS:
        if simulation.get(key) != 0:
            blockers.append(f"post_evidence_p0_lock_simulation_{key}_not_zero")
    if simulation.get("approved_runtime_evidence_accepted") is True:
        for child in simulation.get("p0_child_checks", []):
            if not isinstance(child, dict) or child.get("present") is not True:
                blockers.append("post_evidence_p0_lock_simulation_child_missing")
                continue
            if child.get("current_route_blocker") != "identity_public_contract_gate_missing":
                blockers.append(
                    f"{child.get('name', '<unknown>')}: post-evidence child route blocker mismatch"
                )
            if child.get("remaining_route_blockers") != ["identity_public_contract_gate_missing"]:
                blockers.append(
                    f"{child.get('name', '<unknown>')}: post-evidence child remaining blockers mismatch"
                )
            if child.get("dependency_chain_locked") is not True:
                blockers.append(f"{child.get('name', '<unknown>')}: post-evidence child must stay locked")
            for key in REQUIRED_CHILD_ACCOUNTING_FALSE_KEYS:
                if child.get(key) is not False:
                    blockers.append(f"{child.get('name', '<unknown>')}: post-evidence child {key} must stay false")
            requirement = POST_EVIDENCE_P0_CHILD_GATE_REQUIREMENTS.get(child.get("name"))
            if not isinstance(requirement, dict):
                blockers.append(f"{child.get('name', '<unknown>')}: post-evidence child gate requirement missing")
                continue
            if child.get("surface") != requirement["surface"]:
                blockers.append(f"{child.get('name', '<unknown>')}: post-evidence child surface mismatch")
            if child.get("required_before_unlocking") != requirement["required_before_unlocking"]:
                blockers.append(
                    f"{child.get('name', '<unknown>')}: post-evidence child required gates mismatch"
                )
            if child.get("own_gate_required") is not True:
                blockers.append(f"{child.get('name', '<unknown>')}: post-evidence child own gate must stay required")
            for key in (
                "accepted_runtime_identity_evidence_only_unlock_allowed",
                "identity_evidence_shortcut_allowed",
            ):
                if child.get(key) is not False:
                    blockers.append(f"{child.get('name', '<unknown>')}: post-evidence child {key} must stay false")
    return blockers


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    critical_path_phase = build_critical_path_phase(args)
    current_route_blocker = critical_path_phase.get("current_blocker")
    approved_runtime_evidence_accepted = approved_runtime_evidence_ready_for_identity_lock(
        critical_path_phase,
        args,
    )
    child_route_blocker = downstream_child_route_blocker(current_route_blocker)
    route_context_surfaces_path: Path
    route_context_surfaces: dict[str, Any]
    with tempfile.TemporaryDirectory(prefix="obelisk-command-route-gate-") as tmp:
        route_context_surfaces_path, route_context_surfaces, route_context_surface_blockers = (
            materialize_route_context_surfaces(
                args.public_sdk_surfaces,
                Path(tmp) / "public-sdk-surfaces-route-context.json",
                approved_runtime_evidence_accepted=approved_runtime_evidence_accepted,
            )
        )
        checks = []
        response_path_report: dict[str, Any] | None = None
        response_path_report_root = Path(tmp) / "command-chat-response-public-readiness"
        response_path_report_path = response_path_report_root / COMMAND_RESPONSE_DEFAULT_REPORT_NAME
        response_path_report_handoff_blockers: list[str] = []
        for name, argv in route_checks(
            args,
            current_route_blocker=child_route_blocker,
            approved_runtime_evidence_accepted=approved_runtime_evidence_accepted,
            public_sdk_surfaces=route_context_surfaces_path,
        ):
            effective_argv = list(argv)
            if name == "commands_replies_public_readiness":
                if response_path_report is not None:
                    response_path_report_handoff_blockers = (
                        validate_command_response_report_handoff_binding(response_path_report)
                    )
                    if not response_path_report_handoff_blockers:
                        response_path_report_root.mkdir(parents=True, exist_ok=True)
                        response_path_report_path.write_text(
                            json.dumps(response_path_report, indent=2, sort_keys=True),
                            encoding="utf-8",
                        )
                        effective_argv.extend(["--response-path-report", str(response_path_report_path)])
                        effective_argv.extend(["--response-path-report-root", str(response_path_report_root)])
                        response_root = args.command_response_root or response_path_report.get("readiness_root")
                        response_readiness = args.command_response_readiness or response_path_report.get("readiness_path")
                        if response_root is not None:
                            effective_argv.extend(["--response-path-root", str(response_root)])
                        if response_readiness is not None:
                            effective_argv.extend(["--response-path-readiness", str(response_readiness)])
            check = run_check(name, effective_argv)
            checks.append(check)
            if name == "command_chat_response_public_readiness":
                payload = check.get("report_payload")
                if isinstance(payload, dict):
                    response_path_report = payload
    blockers = route_context_surface_blockers
    blockers.extend(validate_command_response_readiness_binding(args))
    blockers.extend(validate_command_response_child_readiness_context(args, response_path_report))
    blockers.extend(response_path_report_handoff_blockers)
    blockers.extend(validate_identity_planning_binding_args(args))
    response_path_report_quarantined = False
    for check in checks:
        post_runtime_identity_contract_lock_quarantined = (
            approved_runtime_evidence_accepted
            and (
                locked_child_post_runtime_identity_contract_quarantined(
                    check,
                    response_path_report_quarantined=response_path_report_quarantined,
                )
                or identity_gap_post_runtime_contract_lock_quarantined(check)
            )
        )
        check["post_runtime_identity_contract_lock_quarantined"] = (
            post_runtime_identity_contract_lock_quarantined
        )
        if (
            post_runtime_identity_contract_lock_quarantined
            and check.get("name") == "player_identity_public_contract_gap"
        ):
            check["public_or_runtime_claims"] = []
        if check["name"] == "command_chat_response_public_readiness":
            response_path_report_quarantined = post_runtime_identity_contract_lock_quarantined
        if check["name"] == "commands_replies_public_readiness" and "--response-path-report" not in check["argv"]:
            blockers.append("commands_replies_public_readiness: missing composed response path report")
        if check["exit_code"] != 0 and not post_runtime_identity_contract_lock_quarantined:
            blockers.append(f"{check['name']}: checker exited {check['exit_code']}")
        if check["parse_error"] is not None:
            blockers.append(f"{check['name']}: {check['parse_error']}")
        if check["report_schema"] != check["expected_schema"]:
            blockers.append(
                f"{check['name']}: schema mismatch "
                f"{check['report_schema']!r} != {check['expected_schema']!r}"
            )
        if check["public_or_runtime_claims"] and not post_runtime_identity_contract_lock_quarantined:
            joined = ", ".join(check["public_or_runtime_claims"])
            blockers.append(f"{check['name']}: unexpected public/runtime claim: {joined}")
        if check["blockers"] and not post_runtime_identity_contract_lock_quarantined:
            blockers.append(f"{check['name']}: child blockers not empty")
        if check["name"] in REQUIRED_PLANNING_ONLY_CHECKS:
            if check["planning_only"] is not True and not post_runtime_identity_contract_lock_quarantined:
                blockers.append(f"{check['name']}: planning_only must stay true")
            if check["accepted_for_planning"] is not True and not post_runtime_identity_contract_lock_quarantined:
                blockers.append(f"{check['name']}: accepted_for_planning must stay true")
        if check["name"] in REQUIRED_LOCKED_CHILD_CHECKS:
            if check.get("dependency_chain_locked") is not True:
                blockers.append(f"{check['name']}: dependency_chain_locked must stay true")
            if check.get("current_route_blocker") not in ALLOWED_IDENTITY_LOCK_BLOCKERS:
                blockers.append(f"{check['name']}: current_route_blocker must stay an identity lock blocker")
            if not check.get("remaining_route_blockers"):
                blockers.append(f"{check['name']}: remaining_route_blockers must stay non-empty")
            for key in REQUIRED_CHILD_ACCOUNTING_FALSE_KEYS:
                if check.get(key) is not False:
                    blockers.append(f"{check['name']}: {key} must stay false")
        if not check["valid"] and not post_runtime_identity_contract_lock_quarantined:
            blockers.append(f"{check['name']}: invalid route prerequisite")
    blockers.extend(validate_critical_path_phase(critical_path_phase))
    blockers.extend(validate_identity_lock_mode(args, critical_path_phase))
    remaining_route_blockers = [current_route_blocker] if current_route_blocker is not None else []
    route_blocked = bool(remaining_route_blockers)
    route_lock_blockers = route_lock_blocked_until(current_route_blocker)
    blockers.extend(
        validate_locked_child_route_alignment(
            checks,
            current_route_blocker=current_route_blocker,
            remaining_route_blockers=remaining_route_blockers,
        )
    )
    post_evidence_p0_lock_simulation = build_post_evidence_p0_lock_simulation(
        critical_path_phase=critical_path_phase,
        checks=checks,
        approved_runtime_evidence_accepted=approved_runtime_evidence_accepted,
    )
    blockers.extend(validate_post_evidence_p0_lock_simulation(post_evidence_p0_lock_simulation))

    return {
        "schema": REPORT_SCHEMA,
        "valid": not blockers,
        "accepted_for_planning": not blockers,
        "planning_only": True,
        "route_blocked": route_blocked,
        "dependency_chain_locked": route_blocked,
        "route_lock_invariant_valid": not blockers,
        "current_route_blocker": current_route_blocker,
        "remaining_route_blockers": remaining_route_blockers,
        "next_route_action": critical_path_phase.get("next_action"),
        "next_action_sequence": build_route_next_action_sequence(critical_path_phase),
        "next_route_blocker_after_runtime_evidence": critical_path_phase.get("next_after_runtime_evidence"),
        "identity_public_contract_decision_record_required": IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_REQUIREMENTS,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "runtime_ready": False,
        "public_header_allowed": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "p0_progress_ready": False,
        "sdk_p0_progress_ready": False,
        "public_or_runtime_accounting_allowed": False,
        "dependency_chain": [
            "obelisk.player_identity.v1",
            "obelisk.permissions_admin.v1",
            "obelisk.command_chat_response_path.v1",
            "obelisk.commands_replies.v1",
        ],
        "critical_path_phase": critical_path_phase,
        "route_context_public_sdk_surfaces": route_context_surfaces,
        "route_lock": {
            "locked": route_blocked,
            "invariant_valid": not blockers,
            "blocked_until": route_lock_blockers,
            "non_claim": "route lock is an offline invariant; it does not promote identity, permissions, commands, runtime readiness, or v1 completion",
        },
        "post_evidence_p0_lock_simulation": post_evidence_p0_lock_simulation,
        "checks": [
            {key: value for key, value in check.items() if key != "report_payload"}
            for check in checks
        ],
        "blockers": blockers,
    }


def main() -> int:
    args = parse_args()
    report = build_report(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
