#!/usr/bin/env python3
"""Validate candidate-only permissions/admin query fail-closed contracts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


SCHEMA = "obelisk.permissions-admin-query-failclosed-contract.v1"
REPORT_SCHEMA = "obelisk.permissions-admin-query-failclosed-contract-check.v1"
IDENTITY_SURFACE = "obelisk.player_identity.v1"
SURFACE = "obelisk.permissions_admin.v1"
PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_SCHEMA = (
    "obelisk.player-identity-public-contract-decision-record.v1"
)
PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA = "obelisk.player-identity-promotion-certificate.v1"
NO_CREDIT_FALSE_KEYS = (
    "counts_toward_permissions_admin",
    "permissions_admin_unlock_allowed",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
    "public_or_runtime_accounting_allowed",
    "route_ready",
    "public_route_ready",
    "permissions_admin_route_ready",
    "stable_claim_allowed",
    "stable_sdk_ready",
    "plugin_hub_ready",
    "publication_ready",
)
NO_CREDIT_ZERO_KEYS = (
    "sdk_progress",
    "p0_progress",
    "complete_sdk_claim_progress_contribution",
    "p0_dependency_chain_claim_progress_contribution",
    "public_sdk_progress_contribution",
    "runtime_progress_contribution",
)

REQUIRED_QUERY_FIELDS = frozenset(
    (
        "plugin_owner_token",
        "principal_handle",
        "principal_generation",
        "principal_scope_flags",
        "server_process_epoch",
        "action",
        "action_size",
        "resource_scope",
        "resource_scope_size",
        "request_flags",
    )
)
REQUIRED_QUERY_FIELD_SEQUENCE = (
    "plugin_owner_token",
    "principal_handle",
    "principal_generation",
    "principal_scope_flags",
    "server_process_epoch",
    "action",
    "action_size",
    "resource_scope",
    "resource_scope_size",
    "request_flags",
)
REQUIRED_QUERY_FIELD_TYPES = {
    "plugin_owner_token": "uint64_owner_token",
    "principal_handle": "uint64_opaque",
    "principal_generation": "uint64",
    "principal_scope_flags": "uint64_flags",
    "server_process_epoch": "uint64",
    "action": "copied_bytes",
    "action_size": "size_t",
    "resource_scope": "copied_bytes",
    "resource_scope_size": "size_t",
    "request_flags": "uint64_flags",
}
REQUIRED_DECISIONS = frozenset(("deny", "allow", "unknown"))
REQUIRED_DECISION_SEQUENCE = ("deny", "allow", "unknown")
REQUIRED_DECISION_FIELDS = frozenset(("decision", "reason_flags"))
REQUIRED_DECISION_FIELD_SEQUENCE = ("decision", "reason_flags")
REQUIRED_PROVENANCE_FIELDS = frozenset(
    (
        "policy_source_id",
        "policy_source_generation",
        "authority_kind",
        "authority_generation",
        "policy_epoch",
    )
)
REQUIRED_RECOGNIZED_AUTHORITY_KINDS = frozenset(("operator-config", "runtime-local"))
REQUIRED_ALLOW_CAPABLE_AUTHORITY_KINDS = frozenset(("runtime-local",))
FORBIDDEN_ALLOW_CAPABLE_AUTHORITY_KINDS = frozenset(
    (
        "operator-config",
        "plugin-supplied-authority",
        "remote-service-authority",
        "cross-process-shared-authority",
    )
)
REQUIRED_FAIL_CLOSED_CASES = frozenset(
    (
        "stale_principal",
        "scope_mismatch",
        "stale_principal_scope_flags",
        "process_mismatch",
        "missing_principal",
        "missing_runtime_principal_identity",
        "command_text_principal_claim",
        "command_text_permission_claim",
        "operator_config_principal_claim",
        "operator_config_permission_claim",
        "operator_config_allow_capability_claim",
        "plugin_supplied_authority_claim",
        "missing_action",
        "malformed_action_size",
        "action_size_exceeds_max",
        "malformed_resource_scope_size",
        "resource_scope_size_exceeds_max",
        "missing_principal_handle",
        "principal_handle_only",
        "missing_principal_generation",
        "missing_principal_scope_flags",
        "missing_server_process_epoch",
        "missing_principal_provenance",
        "principal_generation_mismatch",
        "plugin_supplied_principal_tuple",
        "plugin_supplied_principal_provenance",
        "server_process_epoch_mismatch",
        "unsupported_principal_scope_flags",
        "missing_plugin_owner_token",
        "zero_plugin_owner_token",
        "unknown_plugin_owner_token",
        "unloading_plugin_owner_token",
        "owner_token_identity_or_permission_claim",
        "missing_capability",
        "rate_limit_exceeded",
        "unknown_authority",
        "missing_authority_kind",
        "missing_policy_source",
        "missing_policy_source_generation",
        "policy_source_generation_mismatch",
        "missing_policy_epoch",
        "missing_authority_generation",
        "authority_generation_mismatch",
        "plugin_supplied_provenance",
        "command_text_policy_provenance_claim",
        "operator_config_policy_provenance_claim",
    )
)
REQUIRED_FAIL_CLOSED_CASE_SEQUENCE = (
    "stale_principal",
    "scope_mismatch",
    "stale_principal_scope_flags",
    "process_mismatch",
    "missing_principal",
    "missing_runtime_principal_identity",
    "command_text_principal_claim",
    "command_text_permission_claim",
    "operator_config_principal_claim",
    "operator_config_permission_claim",
    "operator_config_allow_capability_claim",
    "plugin_supplied_authority_claim",
    "missing_action",
    "malformed_action_size",
    "action_size_exceeds_max",
    "malformed_resource_scope_size",
    "resource_scope_size_exceeds_max",
    "missing_principal_handle",
    "principal_handle_only",
    "missing_principal_generation",
    "missing_principal_scope_flags",
    "missing_server_process_epoch",
    "missing_principal_provenance",
    "principal_generation_mismatch",
    "plugin_supplied_principal_tuple",
    "plugin_supplied_principal_provenance",
    "server_process_epoch_mismatch",
    "unsupported_principal_scope_flags",
    "missing_plugin_owner_token",
    "zero_plugin_owner_token",
    "unknown_plugin_owner_token",
    "unloading_plugin_owner_token",
    "owner_token_identity_or_permission_claim",
    "missing_capability",
    "rate_limit_exceeded",
    "unknown_authority",
    "missing_authority_kind",
    "missing_policy_source",
    "missing_policy_source_generation",
    "policy_source_generation_mismatch",
    "missing_policy_epoch",
    "missing_authority_generation",
    "authority_generation_mismatch",
    "plugin_supplied_provenance",
    "command_text_policy_provenance_claim",
    "operator_config_policy_provenance_claim",
)
REQUIRED_REASON_FLAG_SEQUENCE = REQUIRED_FAIL_CLOSED_CASE_SEQUENCE
REQUIRED_FAIL_CLOSED_RESULT_BY_CASE = {
    **{name: "deny" for name in REQUIRED_FAIL_CLOSED_CASE_SEQUENCE},
    "unknown_authority": "unknown",
}
REQUIRED_REASON_FLAGS_POLICY = {
    "classification": "internal_candidate_only",
    "encoding": "uint64_flags",
    "source": "obelisk_internal_query_evaluator",
    "public_header_allowed": False,
    "public_cache_abi_allowed": False,
    "plugin_supplied_flags_allowed": False,
    "operator_config_flags_allowed": False,
    "command_text_flags_allowed": False,
    "allow_requires_zero_reason_flags": True,
    "deny_unknown_require_nonzero_reason_flags": True,
    "unknown_authority_result": "unknown",
    "runtime_ready": False,
}
REQUIRED_EXCLUSIONS = frozenset(
    (
        "permission_groups",
        "admin_groups",
        "grants",
        "ban",
        "kick",
        "commands",
        "replies",
        "storage",
        "ue_pointers",
        "ResourceHandle",
        "lookup",
        "mutation",
        "return_override",
    )
)
REQUIRED_NON_CLAIMS = frozenset(
    (
        "candidate-only pre-ABI permissions/admin query contract",
        "does not add public headers, runtime wiring, public cache ABI, command responses, commands, replies, storage, groups, grants, ban/kick, mutation, lookup, ResourceHandle, UE pointers, or return override",
        "allow decisions require policy provenance and fail closed on missing or unknown authority",
        "principal_handle alone never authorizes; generation, scope flags, server process epoch, and runtime-owned provenance are required before allow",
        "command text and operator config cannot establish principal identity or permission claims before runtime principal observation",
        "plugin-supplied provenance, plugin-supplied authority, and invalid owner tokens cannot establish identity or permission authority",
        "only a reviewed, hash-bound, current player-identity promotion certificate can satisfy the upstream identity dependency; identity aliases, stale decision records, route reports, and runtime evidence substitutes remain non-counting",
        "generated, scaffold, placeholder, template, stale, or hash-unbound upstream certificates cannot satisfy the upstream identity dependency",
        "nested readiness, progress, unlock, route, public, runtime, stable, Plugin Hub, publication, or SDK/P0 accounting aliases remain non-counting until the full hash-bound dependency chain is accepted",
        "runtime-window artifacts, beta/Discord notices, no-users status, package installs, side-lanes, passive evidence, unblocked/allowed aliases, and generic identity-present aliases cannot unlock readiness",
        "RCON, ListPlayers, Kick, ServerListPlayers, ServerKickPlayer, admin snapshots, static thunk, route candidate, source-ready, status, and command aliases are admin orientation or operational metadata only and cannot unlock readiness or progress",
        "promotion, public SDK readiness, and runtime readiness require a separate reviewed ABI and runtime gate",
        "v1 remains false for this candidate-only pre-ABI planning artifact",
    )
)
REQUIRED_PRINCIPAL_RUNTIME_IDENTITY_POLICY = {
    "config_enables_surface_only": True,
    "runtime_observation_establishes_identity": True,
    "runtime_principal_required_for_permission_authority": True,
    "principal_handle_alone_authorizes": False,
    "principal_handle_only_creates_identity_allowed": False,
    "principal_handle_only_creates_permission_allowed": False,
    "command_text_principal_claim_allowed": False,
    "operator_config_principal_claim_allowed": False,
    "command_text_permission_claim_allowed": False,
    "operator_config_permission_claim_allowed": False,
}
REQUIRED_PRINCIPAL_PROVENANCE_POLICY = {
    "principal_tuple_source": "runtime_owned_player_identity_observation",
    "plugin_supplied_principal_tuple_allowed": False,
    "command_supplied_principal_tuple_allowed": False,
    "operator_config_supplied_principal_tuple_allowed": False,
    "plugin_supplied_principal_provenance_allowed": False,
    "runtime_owned_principal_provenance_required_before_allow": True,
    "principal_tuple_provenance_required_before_allow": True,
    "principal_generation_provenance_required_before_allow": True,
    "principal_scope_provenance_required_before_allow": True,
    "server_process_epoch_required_before_allow": True,
    "principal_handle_generation_scope_epoch_required_before_allow": True,
    "missing_principal_provenance_result": "deny",
    "missing_server_process_epoch_result": "deny",
    "principal_handle_only_result": "deny",
    "stale_principal_result": "deny",
    "stale_principal_scope_flags_result": "deny",
    "principal_generation_mismatch_result": "deny",
    "scope_mismatch_result": "deny",
    "process_mismatch_result": "deny",
    "server_process_epoch_mismatch_result": "deny",
    "unsupported_principal_scope_flags_result": "deny",
    "plugin_supplied_principal_tuple_result": "deny",
    "plugin_supplied_principal_provenance_result": "deny",
    "public_abi_field_allowed": False,
    "runtime_ready": False,
}
REQUIRED_OWNER_TOKEN_POLICY = {
    "owner_token_source": "runtime_assigned_plugin_owner_token",
    "nonzero_owner_token_required_before_policy_evaluation": True,
    "live_owner_required_before_policy_evaluation": True,
    "owner_token_validation_precedes_policy_evaluation": True,
    "owner_token_validation_before_rate_budget": True,
    "owner_token_validation_before_candidate_cache_read": True,
    "unknown_owner_token_result": "deny",
    "unloading_owner_token_result": "deny",
    "zero_owner_token_result": "deny",
    "missing_owner_token_result": "deny",
    "invalid_owner_token_cannot_create_identity_or_permission": True,
    "owner_token_does_not_establish_principal_identity": True,
    "owner_token_does_not_grant_permission": True,
    "owner_cleanup_invalidates_query_budget": True,
    "owner_cleanup_invalidates_candidate_cache": True,
    "plugin_supplied_owner_identity_allowed": False,
    "public_abi_field_allowed": False,
    "runtime_ready": False,
}
REQUIRED_POLICY_PROVENANCE_POLICY = {
    "policy_provenance_source": "runtime_owned_policy_evaluator",
    "policy_source_id_required_before_allow": True,
    "policy_source_generation_required_before_allow": True,
    "authority_kind_required_before_allow": True,
    "authority_generation_required_before_allow": True,
    "policy_epoch_required_before_allow": True,
    "complete_policy_provenance_required_before_allow": True,
    "policy_source_id_generation_authority_kind_generation_epoch_required_before_allow": True,
    "plugin_supplied_policy_provenance_allowed": False,
    "plugin_supplied_policy_provenance_creates_authority_allowed": False,
    "command_text_policy_provenance_claim_allowed": False,
    "operator_config_policy_provenance_claim_allowed": False,
    "operator_config_allow_provenance_allowed": False,
    "missing_policy_source_result": "deny",
    "missing_policy_source_generation_result": "deny",
    "policy_source_generation_mismatch_result": "deny",
    "missing_authority_kind_result": "deny",
    "missing_authority_generation_result": "deny",
    "authority_generation_mismatch_result": "deny",
    "missing_policy_epoch_result": "deny",
    "unknown_authority_result": "unknown",
    "plugin_supplied_policy_provenance_result": "deny",
    "public_abi_field_allowed": False,
    "runtime_ready": False,
}
REQUIRED_QUERY_TEXT_POLICY = {
    "action_required": True,
    "action_max_bytes": 128,
    "resource_scope_required": False,
    "resource_scope_max_bytes": 256,
    "bytes_are_copied": True,
    "utf8_decoding_required_before_allow": False,
    "command_parser_claim_allowed": False,
}
REQUIRED_ABUSE_POLICY = {
    "rate_limited_per_plugin_owner_token": True,
    "budget_cleanup_on_plugin_owner_cleanup": True,
    "burst_exhaustion_result": "deny_or_unknown",
    "malformed_query_observable": True,
    "audit_records_redacted": True,
    "audit_exposes_ue_pointers_raw_params_or_secret_policy": False,
    "state_public_cache_abi": False,
    "process_local_owner_scoped": True,
}
REQUIRED_SEQUENCE_GATE = {
    "player_identity_required_before_permission_query": True,
    "query_result_provenance_required_before_command_response": True,
    "command_response_dependency_promoted": False,
    "command_response_contract_required_before_commands_replies": True,
    "commands_replies_admin_mutation_storage_operator_ingress_allowed": False,
    "query_result_contains_command_or_reply_handle": False,
}
REQUIRED_ARTIFACT_IDENTITY = {
    "artifact_kind": SCHEMA,
    "artifact_status": "candidate_only_pre_abi_contract",
    "dependency_surface": IDENTITY_SURFACE,
}
REQUIRED_DEPENDENCY_CONTEXT = {
    "upstream_surface": IDENTITY_SURFACE,
    "upstream_surface_status": "planning_only",
    "required_lifecycle_anchor_schema": "obelisk.players-identity-lifecycle-anchor-candidates.v1",
    "required_principal_invalidation_schema": "obelisk.players-identity-principal-invalidation-policy.v1",
    "required_runtime_evidence_schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
    "required_identity_public_contract_decision_record_schema": (
        PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_SCHEMA
    ),
    "required_identity_public_contract_decision_record_id": "reviewed_identity_public_contract_decision_record",
    "required_identity_public_contract_review_status": "reviewed",
    "required_identity_promotion_certificate_schema": PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
    "required_identity_promotion_certificate_surface": IDENTITY_SURFACE,
    "required_identity_promotion_certificate_required_by_surface": SURFACE,
    "required_identity_promotion_certificate_chain_position": 1,
    "required_identity_promotion_certificate_required_by_chain_position": 2,
    "required_identity_promotion_certificate_reviewed_artifact_hash": (
        "evidence.reviewed_surface_record_sha256"
    ),
    "required_identity_promotion_certificate_hash_policy": (
        "evidence.reviewed_artifact_hash must equal evidence.reviewed_surface_record_sha256"
    ),
    "missing_mismatched_or_stale_identity_certificate_counts": False,
    "identity_alias_or_stale_source_unlock_allowed": False,
    "identity_decision_record_alone_unlock_allowed": False,
    "runtime_evidence_alone_unlock_allowed": False,
    "public_identity_required_before_promotion": True,
    "public_identity_promoted": False,
    "permissions_admin_public_abi_promoted": False,
    "command_response_dependency_promoted": False,
}

FORBIDDEN_COORDINATE_KEYS = frozenset(
    (
        "address",
        "function_address",
        "gobject_index",
        "gobjects_index",
        "name_index",
        "fname_index",
        "object_address",
        "object_index",
        "raw_param_address",
        "ue_pointer",
        "uobject_address",
    )
)
NEGATIVE_CONTEXT_TOKENS = (
    "blocker",
    "deny",
    "exclude",
    "exclusion",
    "fail_closed",
    "forbid",
    "forbidden",
    "negative",
    "non_claim",
    "reject",
)
FORBIDDEN_SURFACE_RE = re.compile(
    r"\b("
    r"groups?|"
    r"permission[_ -]?groups?|"
    r"admin[_ -]?groups?|"
    r"grants?|grant[_ -]?(?:api|revoke)|"
    r"ban(?:[_ -]?player)?|"
    r"kick(?:[_ -]?player)?|"
    r"commands?|command[_ -]?router|"
    r"replies|reply(?:[_ -]?api)?|send[_ -]?chat|"
    r"storage|persistence|"
    r"ue[_ -]?pointers?|uobject|ufunction|raw[_ -]?params?|"
    r"resourcehandle|resource[_ -]?handle|"
    r"lookup|mutation|return[_ -]?override"
    r")\b",
    re.IGNORECASE,
)
READY_OVERCLAIM_KEYS = frozenset(
    (
        "api_complete",
        "api_full",
        "api_production_grade",
        "api_production_ready",
        "api_stable",
        "accepted_runtime_evidence_ready",
        "admin_authority_ready",
        "admin_route_snapshot_ready",
        "admin_snapshot_ready",
        "admin_status_snapshot_ready",
        "beta_notice_ready",
        "beta_notice_sent",
        "command_router_allowed",
        "command_candidate_ready",
        "complete_api",
        "complete_sdk",
        "complete_support",
        "counts_toward_public_sdk",
        "counts_toward_runtime",
        "counts_toward_v1_completion",
        "full_api",
        "full_sdk",
        "full_support",
        "identity_contract_reviewed",
        "identity_observed",
        "identity_present",
        "identity_ready",
        "identity_unblocked",
        "identity_public_contract_gate_accepted",
        "identity_public_contract_gate_missing",
        "identity_public_contract_gate_missing_accepted",
        "identity_public_contract_gate_missing_passed",
        "identity_public_contract_gate_missing_resolved",
        "identity_public_contract_gate_missing_unblocked",
        "identity_public_contract_gate_missing_unlocked",
        "identity_public_contract_gate_passed",
        "identity_public_contract_gate_resolved",
        "no_players_status_ready",
        "no_users_passive_wait_ready",
        "no_users_status_ready",
        "package_install_unblocked",
        "operator_approval_granted",
        "package_install_accepted",
        "package_install_ready",
        "package_shape_accepted",
        "package_shape_install_accepted",
        "package_shape_install_ready",
        "package_shape_ready",
        "package_shape_support_ready",
        "permission_header_allowed",
        "permission_header_unblocked",
        "permissions_admin_ready",
        "permissions_admin_unblocked",
        "permissions_query_ready",
        "permissions_query_unblocked",
        "permissions_unlocked",
        "permissions_unblocked",
        "plugin_hub_counts_toward_completion",
        "plugin_hub_counts_toward_public_sdk",
        "plugin_hub_counts_toward_v1_completion",
        "plugin_hub_package_published",
        "plugin_hub_planning_accepted",
        "plugin_hub_planning_ready",
        "plugin_hub_planning_supported",
        "plugin_hub_ready",
        "plugin_hub_readiness_claim_allowed",
        "plugin_hub_support_tier_ready",
        "principal_ready",
        "principal_observed",
        "principal_present",
        "principal_unblocked",
        "production_grade_api",
        "production_grade_sdk",
        "production_grade_support",
        "production_ready_api",
        "production_ready_sdk",
        "production_ready_support",
        "promoted",
        "promote_ready",
        "promotion_ready",
        "public",
        "public_allowed",
        "public_enabled",
        "public_ready",
        "public_supported",
        "public_unblocked",
        "public_unlocked",
        "public_or_runtime_accounting_allowed",
        "public_api",
        "public_api_allowed",
        "public_api_enabled",
        "public_api_public",
        "public_api_ready",
        "public_api_supported",
        "public_abi_ready",
        "public_bridge_abi_allowed",
        "public_reply_abi_ready",
        "public_route_ready",
        "public_route_unblocked",
        "public_response_abi_allowed",
        "public_response_path_ready",
        "route_candidate_ready",
        "public_sdk_ready",
        "public_sdk_unblocked",
        "route_ready",
        "route_unblocked",
        "route_readiness_ready",
        "runtime_approval",
        "runtime_approval_granted",
        "runtime_window_artifact_ready",
        "runtime_window_authorized",
        "runtime_window_closure_ready",
        "runtime_window_execution_ready",
        "runtime_window_plan_ready",
        "runtime_window_ready",
        "runtime_ready",
        "runtime_unblocked",
        "runtime_readiness_allowed",
        "runtime_work_authorized",
        "sdk_complete",
        "sdk_full",
        "sdk_production_grade",
        "sdk_production_ready",
        "sdk_stable",
        "send_chat_ready",
        "server_operations_authorized",
        "side_lane_accepted",
        "side_lane_artifact_accepted",
        "side_lane_artifact_ready",
        "side_lane_ready",
        "source_ready",
        "stable_claim_allowed",
        "stable_api",
        "stable_sdk",
        "stable_support",
        "support_complete",
        "support_full",
        "support_production_grade",
        "support_production_ready",
        "support_stable",
        "v1",
        "v1_completion_ready",
        "v1_completion_unblocked",
        "v1_enabled",
        "v1_promoted",
        "v1_ready",
        "v1_unblocked",
    )
)
PROGRESS_OVERCLAIM_KEYS = frozenset(
    (
        "claim_progress",
        "claim_progress_contribution",
        "claim_progress_percent",
        "claim_progress_ratio",
        "complete_sdk_claim_progress_contribution",
        "complete_sdk_claim_progress_percent",
        "complete_sdk_claim_progress_ratio",
        "complete_sdk_progress",
        "complete_sdk_progress_contribution",
        "complete_sdk_progress_percent",
        "complete_sdk_progress_ratio",
        "p0_dependency_chain_claim_progress_contribution",
        "p0_dependency_chain_claim_progress_percent",
        "p0_dependency_chain_claim_progress_ratio",
        "p0_dependency_chain_progress",
        "p0_dependency_chain_progress_contribution",
        "p0_dependency_chain_progress_percent",
        "p0_dependency_chain_progress_ratio",
        "p0_progress",
        "p0_progress_contribution",
        "p0_progress_percent",
        "p0_progress_ratio",
        "progress",
        "progress_contribution",
        "progress_percent",
        "progress_ratio",
        "public_sdk_progress",
        "public_sdk_progress_contribution",
        "public_sdk_progress_percent",
        "public_sdk_progress_ratio",
        "runtime_progress",
        "runtime_progress_contribution",
        "runtime_progress_percent",
        "runtime_progress_ratio",
        "sdk_progress",
        "sdk_progress_contribution",
        "sdk_progress_percent",
        "sdk_progress_ratio",
        "v1_completion_contribution",
        "v1_completion_progress",
        "v1_completion_progress_contribution",
    )
)
PUBLIC_ALIAS_OVERCLAIM_KEYS = frozenset(
    (
        "public",
        "public_allowed",
        "public_enabled",
        "public_ready",
        "public_supported",
        "public_unblocked",
        "public_unlocked",
    )
)
BROAD_PROGRESS_OVERCLAIM_KEY_RE = re.compile(
    r"(?:^|_)(?:"
    r"credits?|"
    r"progress(?:_(?:contribution|percent|ratio|ready))?|"
    r"readiness_credit|"
    r"sdk_credit|"
    r"sdk_completion_credit"
    r")(?:_|$)"
)
BROAD_READY_OVERCLAIM_KEY_RE = re.compile(
    r"^(?:"
    r"(?:complete|full|stable|production(?:_ready|_grade)?)_(?:sdk|api|support)"
    r"(?:_(?:ready|allowed|supported|enabled|public))?|"
    r"(?:sdk|api|support)_(?:complete|full|stable|production(?:_ready|_grade)?)"
    r"(?:_(?:ready|allowed|supported|enabled|public))?|"
    r"public_api(?:_(?:ready|allowed|supported|enabled|public))?|"
    r"(?:permissions?_admin|permissions?_quer(?:y|ies)|permission_header|public_(?:header|route|sdk)|"
    r"admin_(?:route_)?snapshot|admin_status_snapshot|"
    r"rcon(?:_command|_route|_status)?|list_players?|kick(?:_player)?|kickplayer|server_(?:list_players|kick_player)|"
    r"static(?:_admin)?_thunk|source|"
    r"route|runtime|runtime_window|v1(?:_completion)?|stable_claim)"
    r"(?:_(?:ready|allowed|enabled|public|unblocked|unlocked))?"
    r")$"
)
GENERIC_NESTED_READY_OVERCLAIM_KEY_RE = re.compile(
    r"(?:^|_)(?:ready|readiness|unblocked|unlocked|supported|enabled|allowed|"
    r"complete|completion|promoted|promotion)$"
)
POSITIVE_OVERCLAIM_VALUES = frozenset(
    (
        "allowed",
        "accepted",
        "approved",
        "available",
        "enabled",
        "live",
        "operational",
        "observed",
        "present",
        "promoted",
        "public",
        "ready",
        "sent",
        "supported",
        "true",
        "unblocked",
        "unlocked",
        "yes",
    )
)
SHORTCUT_ARTIFACT_OVERCLAIM_KEYS = frozenset(
    (
        "beta_notice",
        "beta_capture",
        "beta_capture_candidate",
        "beta_capture_pack",
        "discord_notice",
        "discord_sent",
        "inline_certificate",
        "inline_promotion_certificate",
        "inline_player_identity_promotion_certificate",
        "inline_permissions_admin_promotion_certificate",
        "player_identity_promotion_certificate",
        "player_identity_promotion_certificate_inline",
        "permissions_admin_promotion_certificate",
        "permissions_admin_promotion_certificate_inline",
        "no_players_status",
        "no_users_passive_wait",
        "no_users_status",
        "package_install",
        "package_shape",
        "package_shape_install",
        "package_shape_support",
        "passive_evidence",
        "passive_monitor",
        "passive_snapshot",
        "passive_summary",
        "admin_route_snapshot",
        "admin_snapshot",
        "admin_status_snapshot",
        "admin_capture_candidate",
        "admin_target",
        "copied_admin_target",
        "kick",
        "kick_player",
        "kickplayer",
        "kick_path_capture_candidate",
        "kick_path_candidate",
        "list_player_capture_candidate",
        "list_player_candidate",
        "list_players_candidate",
        "plugin_hub",
        "plugin_hub_planning",
        "plugin_hub_support_tier",
        "rcon_command_candidate",
        "rcon_command_route",
        "rcon_command_status",
        "rcon",
        "rcon_status",
        "rcon_route_candidate",
        "route_candidate",
        "route_candidates",
        "command_candidate",
        "command_candidates",
        "command_source",
        "route_source",
        "admin_source",
        "runtime_window",
        "runtime_window_artifact",
        "runtime_window_closure",
        "runtime_window_execution",
        "runtime_window_plan",
        "runtime_status_report",
        "runtime_evidence_status",
        "runtime_evidence_status_report",
        "beta_runtime_status",
        "copied_runtime_status_report",
        "scoped_release_statement",
        "scoped_statement",
        "copy_artifact",
        "status_artifact",
        "server_kick_player",
        "server_list_players",
        "side_lane",
        "side_lane_artifact",
        "source_ready",
        "start_end_evidence",
        "start_end_only",
        "start_end_only_evidence",
        "runtime_principal_lifecycle_start_end_evidence",
        "runtime_principal_start_end_evidence",
        "static_admin_thunk",
        "static_thunk",
        "transfer_b_accept_candidate",
        "transfer_b_accept_route",
        "transfer_baccept_candidate",
        "transfer_baccept_route",
        "multi_surface_beta_capture_pack",
        "multi_surface_beta_capture_plan_queue",
        "support_tier",
        "support_tier_metadata",
        "support_tier_report",
        "terminal_certificate",
        "terminal_status_certificate",
    )
)
EXACT_PROMOTION_CREDIT_ALIAS_KEYS = frozenset(
    (
        "approved_runtime_evidence",
        "beta",
        "complete_sdk",
        "discord",
        "p0",
        "package_shape",
        "passive_snapshot",
        "plugin_hub",
        "public_sdk",
        "ready",
        "runtime_ready",
        "scoped_release_statement",
        "stable_sdk",
        "support_tier",
    )
)
SHORTCUT_ARTIFACT_SOURCE_KEYS = frozenset(
    (
        "artifact_provenance",
        "evidence_provenance",
        "metadata_provenance",
        "provenance",
        "provenance_marker",
        "provenance_markers",
        "review_provenance",
        "route_provenance",
        "snapshot_provenance",
        "admin_source",
        "admin_sources",
        "command",
        "command_candidate",
        "command_candidates",
        "command_source",
        "command_sources",
        "route",
        "route_candidate",
        "route_candidates",
        "route_source",
        "route_sources",
        "source",
        "source_class",
        "source_classes",
        "source_kind",
        "source_kinds",
        "source_path",
        "source_paths",
        "sources",
        "source_marker",
        "source_markers",
        "source_provenance",
        "source_provenances",
    )
)
SHORTCUT_ARTIFACT_STATUS_KEYS = frozenset(
    (
        "accepted",
        "allowed",
        "approved",
        "available",
        "outcome",
        "ready",
        "result",
        "state",
        "status",
        "supported",
        "value",
        "verdict",
    )
)
READY_OVERCLAIM_STRINGS = {
    "command response path is live": "public_response_path_ready",
    "complete sdk support is enabled": "complete_sdk_support",
    "promoted": "promoted",
    "public abi is ready": "public_abi_ready",
    "public api is ready": "public_api_ready",
    "public sdk ready": "public_sdk_ready",
    "permissions/admin is public and ready": "permissions_admin_ready",
    "identity contract reviewed": "identity_contract_reviewed",
    "identity present": "identity_present",
    "principal present": "principal_present",
    "identity observed": "identity_observed",
    "principal observed": "principal_observed",
    "principal ready": "principal_ready",
    "permissions query ready": "permissions_query_ready",
    "permissions query unblocked": "permissions_query_unblocked",
    "permissions unlocked": "permissions_unlocked",
    "permissions unblocked": "permissions_unblocked",
    "permission header allowed": "permission_header_allowed",
    "permission header unblocked": "permission_header_unblocked",
    "admin authority ready": "admin_authority_ready",
    "accepted runtime evidence ready": "accepted_runtime_evidence_ready",
    "inline promotion certificate is promoted": "inline_promotion_certificate",
    "inline player identity promotion certificate is promoted": "inline_player_identity_promotion_certificate",
    "runtime status report is ready": "runtime_status_report_ready",
    "runtime evidence status report is ready": "runtime_evidence_status_report_ready",
    "copied runtime status report is ready": "copied_runtime_status_report_ready",
    "beta runtime status is ready": "beta_runtime_status_ready",
    "approved runtime evidence ready": "approved_runtime_evidence_ready",
    "beta is ready": "beta_ready",
    "discord is sent": "discord_sent",
    "discord sent": "discord_sent",
    "p0 is ready": "p0_ready",
    "p0 ready": "p0_ready",
    "multi-surface beta capture pack is ready": "multi_surface_beta_capture_pack_ready",
    "terminal certificate is ready": "terminal_certificate_ready",
    "support tier is supported": "support_tier_supported",
    "scoped release statement is ready": "scoped_release_statement_ready",
    "beta notice sent": "beta_notice_sent",
    "beta notice ready": "beta_notice_ready",
    "discord notice sent": "discord_sent",
    "runtime window ready": "runtime_window_ready",
    "runtime window unblocked": "runtime_window_ready",
    "runtime-window artifact is ready": "runtime_window_artifact_ready",
    "runtime-window plan is ready": "runtime_window_plan_ready",
    "no users status ready": "no_users_status_ready",
    "no-users passive wait ready": "no_users_passive_wait_ready",
    "package install accepted": "package_install_accepted",
    "package install is accepted": "package_install_accepted",
    "package install ready": "package_install_ready",
    "package install is ready": "package_install_ready",
    "package shape accepted": "package_shape_accepted",
    "package shape is accepted": "package_shape_accepted",
    "package shape ready": "package_shape_ready",
    "package shape is ready": "package_shape_ready",
    "plugin hub planning is supported": "plugin_hub_planning_supported",
    "plugin hub ready": "plugin_hub_ready",
    "side-lane artifact is ready": "side_lane_artifact_ready",
    "side lane artifact is ready": "side_lane_artifact_ready",
    "side lane ready": "side_lane_ready",
    "reply endpoint is live": "public_reply_abi_ready",
    "runtime ready": "runtime_ready",
    "source ready": "source_ready",
    "source-ready": "source_ready",
    "admin snapshot ready": "admin_snapshot_ready",
    "admin snapshot is ready": "admin_snapshot_ready",
    "admin status snapshot ready": "admin_status_snapshot_ready",
    "admin status snapshot is ready": "admin_status_snapshot_ready",
    "rcon route ready": "rcon_route_ready",
    "rcon ready": "rcon_ready",
    "rcon status ready": "rcon_status_ready",
    "listplayers ready": "list_players_ready",
    "list players ready": "list_players_ready",
    "kickplayer ready": "kick_player_ready",
    "kick player ready": "kick_player_ready",
    "static thunk ready": "static_thunk_ready",
    "static admin thunk ready": "static_admin_thunk_ready",
    "route candidate ready": "route_candidate_ready",
    "command candidate ready": "command_candidate_ready",
    "route ready": "route_ready",
    "route-ready": "route_ready",
    "public route ready": "public_route_ready",
    "public-route ready": "public_route_ready",
    "permissions admin route ready": "permissions_admin_route_ready",
    "permissions/admin route ready": "permissions_admin_route_ready",
    "public ready": "public_ready",
    "public allowed": "public_allowed",
    "promotion ready": "promotion_ready",
    "promote ready": "promote_ready",
    "stable claim allowed": "stable_claim_allowed",
    "v1 enabled": "v1_enabled",
    "v1 completion ready": "v1_completion_ready",
    "v1 promoted": "v1_promoted",
    "v1 ready": "v1_ready",
}
OVERCLAIM_NEGATIVE_PREFIXES = (
    "$.negative_surface_exclusions",
    "$.non_claims",
    "$.promotion_gate.blockers",
)
POSITIVE_PUBLIC_OR_RUNTIME_CLAIM_RE = re.compile(
    r"\b(?:"
    r"accepted[_ -]?runtime[_ -]?evidence|admin[_ -]?(?:authority|(?:route[_ -]?)?snapshot|status[_ -]?snapshot)|identity[_ -]?(?:public[_ -]?)?contract|"
    r"command[_ -]?(?:routing|router|response[_ -]?path)|"
    r"permission[_ -]?headers?|permissions?[_ -]?quer(?:y|ies)|permissions?|principal|"
    r"rcon(?:[_ -]?(?:command|route|status))?|list[_ -]?players?|kick(?:[_ -]?players?)?|"
    r"static[_ -]?(?:admin[_ -]?)?thunks?|source[_ -]?ready|"
    r"permissions?/admin|permissions?|public[_ -]?abi|reply[_ -]?(?:endpoint|api|abi)|"
    r"replies[_ -]?(?:api|abi)|send[_ -]?chat[_ -]?(?:api|abi)|runtime|"
    r"runtime[_ -]?work|server[_ -]?operations?|operator[_ -]?approval|runtime[_ -]?approval|"
    r"public[_ -]?(?:api|sdk|header)|v1[_ -]?completion|stable[_ -]?claim|"
    r"(?:complete|full|stable|production(?:[_ -]?(?:ready|grade))?)[_ -]?(?:sdk|api|support)"
    r")\b(?:\s+(?:is|are))?\s+"
    r"\b(?:authorized|granted|public(?:\s+and\s+ready)?|ready|readiness|live|enabled|allowed|"
    r"operational|supported|unblocked)\b",
    re.IGNORECASE,
)
POSITIVE_PUBLIC_OR_RUNTIME_CLAIM_REVERSED = re.compile(
    r"\b(?:public[_ -]?(?:api|abi)|sdk|api|support)\b\s+"
    r"(?:is|are|now|becomes?|became)\s+"
    r"\b(?:complete|full|stable|production(?:[_ -]?(?:ready|grade))?|public|ready|supported|unblocked)\b",
    re.IGNORECASE,
)
NEGATED_CLAIM_PREFIX_RE = re.compile(
    r"\b(?:blocked|cannot|does\s+not|do\s+not|excluded|excludes?|future|must\s+not|no|not|"
    r"only|outside|post-v1|prevent|prevents|remain|remains|without)\b",
    re.IGNORECASE,
)
NEGATED_CLAIM_SUFFIX_RE = re.compile(
    r"^\s+(?:remains?|stays?|is|are)?\s*(?:blocked|not\s+(?:ready|enabled|authorized|allowed)|"
    r"unauthorized|unsupported)\b",
    re.IGNORECASE,
)
CLAIM_SCOPE_SPLIT_RE = re.compile(r"[,.;:\n\r]|\s+\b(?:and|but|then|however|unless)\b\s+", re.IGNORECASE)
FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_KEYS = frozenset(
    (
        "authority_claim_source",
        "identity_claim_source",
        "identity_source",
        "permission_claim_source",
        "permission_source",
        "principal_claim_source",
        "principal_source",
    )
)
FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_VALUES = frozenset(
    (
        "command text",
        "command-text",
        "command_text",
        "operator config",
        "operator-config",
        "operator_config",
    )
)
FORBIDDEN_ADMIN_SOURCE_TERMS = frozenset(
    (
        "command_candidate",
        "admin_route_snapshot",
        "admin_snapshot",
        "admin_status_snapshot",
        "kick",
        "kick_player",
        "kickplayer",
        "list_players",
        "listplayers",
        "rcon",
        "route_candidate",
        "server_kick_player",
        "server_list_players",
        "serverkickplayer",
        "serverlistplayers",
        "static_admin_thunk",
        "static_thunk",
        "staticadminthunk",
        "staticthunk",
    )
)


@dataclass
class Validation:
    blockers: list[dict[str, Any]]
    query_fields: list[str]
    decisions: list[str]
    decision_fields: list[str]
    provenance_fields: list[str]
    reason_flags: list[str]
    fail_closed_cases: list[str]
    recognized_authority_kinds: list[str]
    allow_capable_authority_kinds: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, nargs="?", help="Permissions/admin query candidate contract to validate.")
    parser.add_argument("--json", action="store_true", help="Emit a JSON report.")
    parser.add_argument(
        "--emit-template",
        type=Path,
        help="Write the canonical permissions/admin query fail-closed candidate template and exit.",
    )
    parser.add_argument("--promote", action="store_true", help="Check promote readiness; candidate-only contracts fail closed.")
    parser.add_argument(
        "--public-readiness",
        action="store_true",
        help="Check public SDK readiness; candidate-only contracts fail closed.",
    )
    parser.add_argument(
        "--runtime-readiness",
        action="store_true",
        help="Check runtime readiness; candidate-only contracts fail closed.",
    )
    return parser.parse_args()


def add(blockers: list[dict[str, Any]], reason: str, label: str, **extra: Any) -> None:
    blocker = {"reason": reason, "label": label}
    blocker.update(extra)
    blockers.append(blocker)


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


def build_template_manifest() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "artifact_identity": dict(REQUIRED_ARTIFACT_IDENTITY),
        "artifact_status": "candidate_only",
        "readiness_classification": "planning_only",
        "pre_abi": True,
        "public_header_allowed": False,
        "public_cache_abi_allowed": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "runtime_promotion_allowed": False,
        "v1": False,
        "query_contract": {
            "kind": "query_only_fail_closed_permission_check",
            "mutation_allowed": False,
            "command_response_allowed": False,
            "public_cache_allowed": False,
            "fields": [
                {
                    "name": name,
                    "type": REQUIRED_QUERY_FIELD_TYPES[name],
                    "copied": True,
                    "source": "obelisk_owned_copy",
                    "consumer_visible": True,
                }
                for name in REQUIRED_QUERY_FIELD_SEQUENCE
            ],
        },
        "decision_contract": {
            "decision_fields": list(REQUIRED_DECISION_FIELD_SEQUENCE),
            "results": [
                {
                    "decision": decision,
                    "fail_closed": decision != "allow",
                    "requires_provenance": decision == "allow",
                }
                for decision in REQUIRED_DECISION_SEQUENCE
            ],
            "provenance_fields": sorted(REQUIRED_PROVENANCE_FIELDS),
            "allow_without_provenance_allowed": False,
            "unknown_authority_result": "unknown",
        },
        "fail_closed_reason_flags": {
            **dict(REQUIRED_REASON_FLAGS_POLICY),
            "flags": [
                {
                    "name": name,
                    "case": name,
                    "bit_index": bit_index,
                    "fail_closed": True,
                    "allow_allowed": False,
                    "consumer_result": REQUIRED_FAIL_CLOSED_RESULT_BY_CASE[name],
                }
                for bit_index, name in enumerate(REQUIRED_REASON_FLAG_SEQUENCE)
            ],
        },
        "authority_policy": {
            "recognized_authority_kinds": sorted(REQUIRED_RECOGNIZED_AUTHORITY_KINDS),
            "allow_capable_authority_kinds": sorted(REQUIRED_ALLOW_CAPABLE_AUTHORITY_KINDS),
            "allowed_authority_kinds": sorted(REQUIRED_RECOGNIZED_AUTHORITY_KINDS),
            "operator_config_allow_capable": False,
            "plugin_supplied_authority_allowed": False,
            "plugin_supplied_authority_creates_identity_allowed": False,
            "plugin_supplied_authority_creates_permission_allowed": False,
            "command_text_authority_allowed": False,
            "operator_config_authority_creates_permission_allowed": False,
            "remote_authority_allowed": False,
            "cross_process_authority_allowed": False,
            "unknown_authority_fails_closed": True,
        },
        "principal_runtime_identity_policy": dict(REQUIRED_PRINCIPAL_RUNTIME_IDENTITY_POLICY),
        "principal_provenance_policy": dict(REQUIRED_PRINCIPAL_PROVENANCE_POLICY),
        "owner_token_policy": dict(REQUIRED_OWNER_TOKEN_POLICY),
        "policy_provenance_policy": dict(REQUIRED_POLICY_PROVENANCE_POLICY),
        "dependency_context": dict(REQUIRED_DEPENDENCY_CONTEXT),
        "query_text_policy": dict(REQUIRED_QUERY_TEXT_POLICY),
        "abuse_policy": dict(REQUIRED_ABUSE_POLICY),
        "sequence_gate": dict(REQUIRED_SEQUENCE_GATE),
        "fail_closed_cases": [
            {
                "case": case,
                "consumer_result": REQUIRED_FAIL_CLOSED_RESULT_BY_CASE[case],
                "fail_closed": True,
                "allow_allowed": False,
            }
            for case in REQUIRED_FAIL_CLOSED_CASE_SEQUENCE
        ],
        "negative_surface_exclusions": sorted(REQUIRED_EXCLUSIONS),
        "promotion_gate": {
            "ready": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "blockers": [
                "candidate_only_pre_abi_contract",
                "public_abi_review_missing",
                "runtime_evidence_missing",
            ],
        },
        "non_claims": sorted(REQUIRED_NON_CLAIMS),
    }


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


def is_negative_context(trail: str) -> bool:
    lowered = trail.casefold()
    return any(token in lowered for token in NEGATIVE_CONTEXT_TOKENS)


def normalized_key(value: Any) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value))
    return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")


def is_source_overclaim_key(key_name: str) -> bool:
    return (
        "source_overclaim" in key_name
        or "source_overclaims" in key_name
        or "source_overclaimed" in key_name
    )


def is_source_overclaim_count_key(key_name: str) -> bool:
    return (
        "count" in key_name
        or "flag_count" in key_name
        or "total_flag" in key_name
    )


def zero_source_overclaim_count_value(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return value == 0
    if isinstance(value, str):
        return normalized_key(value) in {"0", "0_0", "zero"}
    return False


def contains_source_overclaim_zero_marker(value: Any, *, source_overclaim_context: bool = False) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            key_name = normalized_key(key)
            child_context = source_overclaim_context or is_source_overclaim_key(key_name)
            if child_context and is_source_overclaim_count_key(key_name) and zero_source_overclaim_count_value(child):
                return True
            if contains_source_overclaim_zero_marker(child, source_overclaim_context=child_context):
                return True
        return False
    if isinstance(value, list):
        return any(
            contains_source_overclaim_zero_marker(item, source_overclaim_context=source_overclaim_context)
            for item in value
        )
    return False


def source_overclaim_zero_has_positive_status_alias(value: dict[str, Any]) -> bool:
    return any(
        normalized_key(key) in SHORTCUT_ARTIFACT_STATUS_KEYS
        and contains_positive_overclaim_value(child)
        for key, child in value.items()
    )


def is_positive_overclaim_value(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        return normalized_key(value) in POSITIVE_OVERCLAIM_VALUES
    return False


def contains_positive_overclaim_value(value: Any) -> bool:
    if is_positive_overclaim_value(value):
        return True
    if isinstance(value, list):
        return any(contains_positive_overclaim_value(item) for item in value)
    if isinstance(value, dict):
        return any(
            contains_positive_overclaim_value(child)
            for key, child in value.items()
            if normalized_key(key) in SHORTCUT_ARTIFACT_STATUS_KEYS
        )
    return False


def progress_overclaim_key(key_name: str) -> bool:
    return (
        key_name in PROGRESS_OVERCLAIM_KEYS
        or BROAD_PROGRESS_OVERCLAIM_KEY_RE.search(key_name) is not None
    )


def progress_overclaim_value_is_nonzero(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = normalized_key(value)
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
            "zero",
        }:
            return False
        if re.fullmatch(r"0+\s*/\s*[1-9]\d*", value.strip().casefold()):
            return False
        if re.fullmatch(r"0+(?:\.0+)?\s*(?:%|percent)", value.strip().casefold()):
            return False
        return True
    if isinstance(value, list):
        return any(progress_overclaim_value_is_nonzero(item) for item in value)
    if isinstance(value, dict):
        return any(progress_overclaim_value_is_nonzero(item) for item in value.values())
    return False


def value_marks_shortcut_artifact(value: Any) -> bool:
    if isinstance(value, str):
        normalized = normalized_key(value)
        return normalized in EXACT_PROMOTION_CREDIT_ALIAS_KEYS or any(
            term in normalized for term in SHORTCUT_ARTIFACT_OVERCLAIM_KEYS
        )
    if isinstance(value, list):
        return any(value_marks_shortcut_artifact(item) for item in value)
    if isinstance(value, dict):
        return any(value_marks_shortcut_artifact(item) for item in value.values())
    return False


def preceding_claim_scope(text: str, start: int) -> str:
    parts = CLAIM_SCOPE_SPLIT_RE.split(text[:start])
    return parts[-1] if parts else text[:start]


def public_or_runtime_claim_is_negated(text: str, match: re.Match[str]) -> bool:
    prefix = preceding_claim_scope(text, match.start())
    if NEGATED_CLAIM_PREFIX_RE.search(prefix) and not re.search(
        r"\b(?:claims?|reports?|says|states?)\b[^,.;:\n\r]*$",
        prefix,
        re.IGNORECASE,
    ):
        return True
    return bool(NEGATED_CLAIM_SUFFIX_RE.match(text[match.end() :]))


def contains_positive_public_or_runtime_claim(text: str) -> bool:
    for pattern in (POSITIVE_PUBLIC_OR_RUNTIME_CLAIM_RE, POSITIVE_PUBLIC_OR_RUNTIME_CLAIM_REVERSED):
        for match in pattern.finditer(text):
            if not public_or_runtime_claim_is_negated(text, match):
                return True
    return False


def find_forbidden_coordinate(value: Any, trail: str = "$") -> tuple[str, str] | None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if key in FORBIDDEN_COORDINATE_KEYS:
                return str(key), child_trail
            found = find_forbidden_coordinate(child, child_trail)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = find_forbidden_coordinate(child, f"{trail}[{index}]")
            if found is not None:
                return found
    return None


def find_forbidden_surface(value: Any, trail: str = "$") -> tuple[str, str] | None:
    if is_negative_context(trail):
        return None
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if FORBIDDEN_SURFACE_RE.search(str(key)) and child is not False:
                return str(key), child_trail
            found = find_forbidden_surface(child, child_trail)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = find_forbidden_surface(child, f"{trail}[{index}]")
            if found is not None:
                return found
    elif isinstance(value, str) and FORBIDDEN_SURFACE_RE.search(value):
        return value, trail
    return None


def contains_forbidden_pre_runtime_claim_source(value: Any) -> bool:
    if isinstance(value, str):
        normalized = normalized_key(value)
        return normalized in FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_VALUES or any(
            term in normalized for term in FORBIDDEN_ADMIN_SOURCE_TERMS
        )
    if isinstance(value, list):
        return any(contains_forbidden_pre_runtime_claim_source(item) for item in value)
    if isinstance(value, dict):
        return any(contains_forbidden_pre_runtime_claim_source(item) for item in value.values())
    return False


def find_forbidden_pre_runtime_claim_source(value: Any, trail: str = "$") -> tuple[str, str] | None:
    if is_negative_context(trail):
        return None
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            key_name = normalized_key(key)
            if key_name in FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_KEYS and contains_forbidden_pre_runtime_claim_source(child):
                return str(key), child_trail
            found = find_forbidden_pre_runtime_claim_source(child, child_trail)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = find_forbidden_pre_runtime_claim_source(child, f"{trail}[{index}]")
            if found is not None:
                return found
    return None


def collect_overclaim_fields(value: Any, trail: str = "$") -> list[dict[str, str]]:
    if any(trail.startswith(prefix) for prefix in OVERCLAIM_NEGATIVE_PREFIXES):
        return []
    found: list[dict[str, str]] = []
    if isinstance(value, dict):
        if contains_source_overclaim_zero_marker(value) and source_overclaim_zero_has_positive_status_alias(value):
            found.append({"reason": "source_overclaim_zero_status_alias_overclaim", "label": trail})
        shortcut_source_context = any(
            value_marks_shortcut_artifact(child)
            for key, child in value.items()
            if normalized_key(key) in SHORTCUT_ARTIFACT_SOURCE_KEYS
        )
        if shortcut_source_context:
            for key, child in value.items():
                if normalized_key(key) in SHORTCUT_ARTIFACT_STATUS_KEYS and contains_positive_overclaim_value(child):
                    found.append({"reason": "shortcut_artifact_source_overclaim", "label": f"{trail}.{key}"})
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            key_name = normalized_key(key)
            if key_name in READY_OVERCLAIM_KEYS and child is True:
                found.append({"reason": f"{key_name}_overclaim", "label": child_trail})
            elif key_name in PUBLIC_ALIAS_OVERCLAIM_KEYS and contains_positive_overclaim_value(child):
                found.append({"reason": f"{key_name}_overclaim", "label": child_trail})
            elif key_name in EXACT_PROMOTION_CREDIT_ALIAS_KEYS and contains_positive_overclaim_value(child):
                found.append({"reason": f"{key_name}_overclaim", "label": child_trail})
            elif key_name in SHORTCUT_ARTIFACT_OVERCLAIM_KEYS and contains_positive_overclaim_value(child):
                found.append({"reason": f"{key_name}_overclaim", "label": child_trail})
            elif progress_overclaim_key(key_name) and progress_overclaim_value_is_nonzero(child):
                found.append({"reason": f"{key_name}_overclaim", "label": child_trail})
            elif BROAD_READY_OVERCLAIM_KEY_RE.fullmatch(key_name) and is_positive_overclaim_value(child):
                found.append({"reason": "public_or_runtime_readiness_overclaim", "label": child_trail})
            elif (
                GENERIC_NESTED_READY_OVERCLAIM_KEY_RE.search(key_name) is not None
                and not any(
                    token in key_name
                    for token in (
                        "blocked_until",
                        "forbidden",
                        "must_remain",
                        "never_count",
                        "non_evidence",
                        "not_sufficient",
                        "rejected",
                        "required",
                        "requires",
                    )
                )
                and not key_name.endswith("_count")
                and (
                    progress_overclaim_value_is_nonzero(child)
                    if progress_overclaim_key(key_name)
                    else contains_positive_overclaim_value(child)
                )
            ):
                found.append({"reason": "generic_readiness_or_progress_alias_overclaim", "label": child_trail})
            found.extend(collect_overclaim_fields(child, child_trail))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(collect_overclaim_fields(child, f"{trail}[{index}]"))
    elif isinstance(value, str):
        text = value.casefold()
        for needle, reason in READY_OVERCLAIM_STRINGS.items():
            if needle in text:
                found.append({"reason": f"{reason}_string_overclaim", "label": trail})
        if contains_positive_public_or_runtime_claim(value):
            found.append({"reason": "positive_public_or_runtime_claim", "label": trail})
    return found


def validate_query_contract(contract: Any, blockers: list[dict[str, Any]]) -> list[str]:
    if not isinstance(contract, dict):
        add(blockers, "query_contract_missing", "$.query_contract")
        return []
    if contract.get("kind") != "query_only_fail_closed_permission_check":
        add(blockers, "query_contract_kind_not_query_only_fail_closed", "$.query_contract.kind")
    for key in ("mutation_allowed", "command_response_allowed", "public_cache_allowed"):
        if contract.get(key) is not False:
            add(blockers, f"query_contract_{key}_not_false", f"$.query_contract.{key}")

    fields = contract.get("fields")
    if not isinstance(fields, list):
        add(blockers, "query_fields_not_list", "$.query_contract.fields")
        return []

    names: list[str] = []
    for index, field in enumerate(fields):
        label = f"$.query_contract.fields[{index}]"
        if not isinstance(field, dict):
            add(blockers, "query_field_invalid", label)
            continue
        name = field.get("name")
        if not isinstance(name, str) or not name:
            add(blockers, "query_field_name_missing", f"{label}.name")
            continue
        names.append(name)
        if name not in REQUIRED_QUERY_FIELDS:
            add(blockers, "query_field_unexpected", f"{label}.name", field=name)
        expected_type = REQUIRED_QUERY_FIELD_TYPES.get(name)
        if expected_type is not None and field.get("type") != expected_type:
            add(
                blockers,
                "query_field_type_mismatch",
                f"{label}.type",
                field=name,
                expected=expected_type,
                value=field.get("type"),
            )
        if field.get("copied") is not True:
            add(blockers, "query_field_not_copied", f"{label}.copied", field=name)
        if field.get("source") != "obelisk_owned_copy":
            add(blockers, "query_field_source_not_obelisk_copy", f"{label}.source", field=name)
        if field.get("consumer_visible") is not True:
            add(blockers, "query_field_not_consumer_visible_candidate", f"{label}.consumer_visible", field=name)

    missing = REQUIRED_QUERY_FIELDS - set(names)
    if missing:
        add(blockers, "query_fields_missing_required", "$.query_contract.fields", missing=sorted(missing))
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        add(blockers, "query_fields_duplicate", "$.query_contract.fields", fields=duplicates)
    if names != list(REQUIRED_QUERY_FIELD_SEQUENCE):
        add(
            blockers,
            "query_fields_sequence_mismatch",
            "$.query_contract.fields",
            expected=list(REQUIRED_QUERY_FIELD_SEQUENCE),
            value=names,
        )
    return names


def validate_decision_contract(contract: Any, blockers: list[dict[str, Any]]) -> tuple[list[str], list[str], list[str]]:
    if not isinstance(contract, dict):
        add(blockers, "decision_contract_missing", "$.decision_contract")
        return [], [], []
    if contract.get("allow_without_provenance_allowed") is not False:
        add(blockers, "allow_without_provenance_allowed_not_false", "$.decision_contract.allow_without_provenance_allowed")
    if contract.get("unknown_authority_result") != "unknown":
        add(
            blockers,
            "unknown_authority_result_not_explicit_unknown",
            "$.decision_contract.unknown_authority_result",
            expected="unknown",
            value=contract.get("unknown_authority_result"),
        )

    fields = contract.get("decision_fields")
    if not isinstance(fields, list):
        add(blockers, "decision_fields_not_list", "$.decision_contract.decision_fields")
        field_names: list[str] = []
    else:
        field_names = [item for item in fields if isinstance(item, str)]
        if len(field_names) != len(fields):
            add(blockers, "decision_field_invalid", "$.decision_contract.decision_fields")
        unexpected = set(field_names) - REQUIRED_DECISION_FIELDS
        if unexpected:
            add(
                blockers,
                "decision_fields_unexpected",
                "$.decision_contract.decision_fields",
                fields=sorted(unexpected),
            )
        missing = REQUIRED_DECISION_FIELDS - set(field_names)
        if missing:
            add(
                blockers,
                "decision_fields_missing_required",
                "$.decision_contract.decision_fields",
                missing=sorted(missing),
            )
        duplicates = sorted({name for name in field_names if field_names.count(name) > 1})
        if duplicates:
            add(blockers, "decision_fields_duplicate", "$.decision_contract.decision_fields", fields=duplicates)
        if field_names != list(REQUIRED_DECISION_FIELD_SEQUENCE):
            add(
                blockers,
                "decision_fields_sequence_mismatch",
                "$.decision_contract.decision_fields",
                expected=list(REQUIRED_DECISION_FIELD_SEQUENCE),
                value=field_names,
            )

    result_names: list[str] = []
    results = contract.get("results")
    if not isinstance(results, list):
        add(blockers, "decision_results_not_list", "$.decision_contract.results")
    else:
        for index, result in enumerate(results):
            label = f"$.decision_contract.results[{index}]"
            if not isinstance(result, dict):
                add(blockers, "decision_result_invalid", label)
                continue
            name = result.get("decision")
            if not isinstance(name, str) or not name:
                add(blockers, "decision_result_name_missing", f"{label}.decision")
                continue
            result_names.append(name)
            if name not in REQUIRED_DECISIONS:
                add(blockers, "decision_result_unexpected", f"{label}.decision", decision=name)
            if name == "allow" and result.get("requires_provenance") is not True:
                add(blockers, "allow_decision_missing_provenance_requirement", f"{label}.requires_provenance")
            if name in {"deny", "unknown"} and result.get("fail_closed") is not True:
                add(blockers, "deny_unknown_decision_not_fail_closed", f"{label}.fail_closed", decision=name)
    missing_results = REQUIRED_DECISIONS - set(result_names)
    if missing_results:
        add(blockers, "decision_results_missing_required", "$.decision_contract.results", missing=sorted(missing_results))
    duplicates = sorted({name for name in result_names if result_names.count(name) > 1})
    if duplicates:
        add(blockers, "decision_results_duplicate", "$.decision_contract.results", decisions=duplicates)
    if result_names != list(REQUIRED_DECISION_SEQUENCE):
        add(
            blockers,
            "decision_results_sequence_mismatch",
            "$.decision_contract.results",
            expected=list(REQUIRED_DECISION_SEQUENCE),
            value=result_names,
        )

    provenance = contract.get("provenance_fields")
    if not isinstance(provenance, list):
        add(blockers, "provenance_fields_not_list", "$.decision_contract.provenance_fields")
        provenance_names: list[str] = []
    else:
        provenance_names = [item for item in provenance if isinstance(item, str)]
        if len(provenance_names) != len(provenance):
            add(blockers, "provenance_field_invalid", "$.decision_contract.provenance_fields")
        unexpected = set(provenance_names) - REQUIRED_PROVENANCE_FIELDS
        if unexpected:
            add(
                blockers,
                "provenance_fields_unexpected",
                "$.decision_contract.provenance_fields",
                fields=sorted(unexpected),
            )
        missing = REQUIRED_PROVENANCE_FIELDS - set(provenance_names)
        if missing:
            add(
                blockers,
                "provenance_fields_missing_required",
                "$.decision_contract.provenance_fields",
                missing=sorted(missing),
            )
        duplicates = sorted({name for name in provenance_names if provenance_names.count(name) > 1})
        if duplicates:
            add(blockers, "provenance_fields_duplicate", "$.decision_contract.provenance_fields", fields=duplicates)

    return result_names, field_names, sorted(provenance_names)


def validate_authority_kind_list(
    value: Any,
    *,
    label: str,
    required: frozenset[str],
    blockers: list[dict[str, Any]],
    missing_reason: str,
    unexpected_reason: str,
) -> list[str]:
    if not isinstance(value, list):
        add(blockers, missing_reason, label)
        return []
    names = [item for item in value if isinstance(item, str)]
    if len(names) != len(value):
        add(blockers, "authority_kind_invalid", label)
    missing = required - set(names)
    if missing:
        add(blockers, missing_reason, label, missing=sorted(missing))
    unexpected = set(names) - required
    if unexpected:
        add(blockers, unexpected_reason, label, authority_kinds=sorted(unexpected))
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        add(blockers, "authority_kind_duplicate", label, authority_kinds=duplicates)
    return names


def validate_authority_policy(policy: Any, blockers: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    if not isinstance(policy, dict):
        add(blockers, "authority_policy_missing", "$.authority_policy")
        return [], []
    recognized = validate_authority_kind_list(
        policy.get("recognized_authority_kinds"),
        label="$.authority_policy.recognized_authority_kinds",
        required=REQUIRED_RECOGNIZED_AUTHORITY_KINDS,
        blockers=blockers,
        missing_reason="authority_recognized_kinds_missing_required",
        unexpected_reason="authority_recognized_kinds_unexpected",
    )
    allow_capable = validate_authority_kind_list(
        policy.get("allow_capable_authority_kinds"),
        label="$.authority_policy.allow_capable_authority_kinds",
        required=REQUIRED_ALLOW_CAPABLE_AUTHORITY_KINDS,
        blockers=blockers,
        missing_reason="authority_allow_capable_kinds_missing_required",
        unexpected_reason="authority_allow_capable_kinds_unexpected",
    )
    forbidden_allow_capable = set(allow_capable) & FORBIDDEN_ALLOW_CAPABLE_AUTHORITY_KINDS
    if forbidden_allow_capable:
        add(
            blockers,
            "authority_forbidden_allow_capable_kind",
            "$.authority_policy.allow_capable_authority_kinds",
            authority_kinds=sorted(forbidden_allow_capable),
        )

    legacy_allowed = policy.get("allowed_authority_kinds")
    if legacy_allowed is not None:
        legacy_names = [item for item in legacy_allowed if isinstance(item, str)] if isinstance(legacy_allowed, list) else []
        if not isinstance(legacy_allowed, list) or set(legacy_names) != REQUIRED_RECOGNIZED_AUTHORITY_KINDS:
            add(blockers, "authority_allowed_kinds_must_match_recognized_legacy_alias", "$.authority_policy.allowed_authority_kinds")
        if isinstance(legacy_allowed, list) and len(legacy_names) != len(legacy_allowed):
            add(blockers, "authority_kind_invalid", "$.authority_policy.allowed_authority_kinds")
        legacy_duplicates = sorted({name for name in legacy_names if legacy_names.count(name) > 1})
        if legacy_duplicates:
            add(
                blockers,
                "authority_allowed_kinds_duplicate_legacy_alias",
                "$.authority_policy.allowed_authority_kinds",
                authority_kinds=legacy_duplicates,
            )
    for key in (
        "command_text_authority_allowed",
        "plugin_supplied_authority_allowed",
        "plugin_supplied_authority_creates_identity_allowed",
        "plugin_supplied_authority_creates_permission_allowed",
        "operator_config_authority_creates_permission_allowed",
        "remote_authority_allowed",
        "cross_process_authority_allowed",
    ):
        if policy.get(key) is not False:
            add(blockers, f"authority_{key}_not_false", f"$.authority_policy.{key}")
    if policy.get("unknown_authority_fails_closed") is not True:
        add(blockers, "unknown_authority_not_fail_closed", "$.authority_policy.unknown_authority_fails_closed")
    if policy.get("operator_config_allow_capable") is not False:
        add(blockers, "operator_config_allow_capable_not_false", "$.authority_policy.operator_config_allow_capable")
    return recognized, allow_capable


def validate_principal_runtime_identity_policy(policy: Any, blockers: list[dict[str, Any]]) -> None:
    label = "$.principal_runtime_identity_policy"
    if not isinstance(policy, dict):
        add(blockers, "principal_runtime_identity_policy_missing", label)
        return
    for key, expected in REQUIRED_PRINCIPAL_RUNTIME_IDENTITY_POLICY.items():
        if policy.get(key) is not expected:
            add(
                blockers,
                f"principal_runtime_identity_policy_{key}_invalid",
                f"{label}.{key}",
                expected=expected,
                value=policy.get(key),
            )


def validate_principal_provenance_policy(policy: Any, blockers: list[dict[str, Any]]) -> None:
    validate_exact_mapping(
        policy,
        label="$.principal_provenance_policy",
        required=REQUIRED_PRINCIPAL_PROVENANCE_POLICY,
        missing_reason="principal_provenance_policy_missing",
        fields_reason="principal_provenance_policy_fields_mismatch",
        invalid_prefix="principal_provenance_policy",
        blockers=blockers,
    )


def validate_owner_token_policy(policy: Any, blockers: list[dict[str, Any]]) -> None:
    validate_exact_mapping(
        policy,
        label="$.owner_token_policy",
        required=REQUIRED_OWNER_TOKEN_POLICY,
        missing_reason="owner_token_policy_missing",
        fields_reason="owner_token_policy_fields_mismatch",
        invalid_prefix="owner_token_policy",
        blockers=blockers,
    )


def validate_policy_provenance_policy(policy: Any, blockers: list[dict[str, Any]]) -> None:
    validate_exact_mapping(
        policy,
        label="$.policy_provenance_policy",
        required=REQUIRED_POLICY_PROVENANCE_POLICY,
        missing_reason="policy_provenance_policy_missing",
        fields_reason="policy_provenance_policy_fields_mismatch",
        invalid_prefix="policy_provenance_policy",
        blockers=blockers,
    )


def validate_query_text_policy(policy: Any, blockers: list[dict[str, Any]]) -> None:
    label = "$.query_text_policy"
    if not isinstance(policy, dict):
        add(blockers, "query_text_policy_missing", label)
        return
    if set(policy) != set(REQUIRED_QUERY_TEXT_POLICY):
        add(
            blockers,
            "query_text_policy_fields_mismatch",
            label,
            missing=sorted(set(REQUIRED_QUERY_TEXT_POLICY) - set(policy)),
            unexpected=sorted(set(policy) - set(REQUIRED_QUERY_TEXT_POLICY)),
        )
    for key, expected in REQUIRED_QUERY_TEXT_POLICY.items():
        if policy.get(key) != expected:
            add(
                blockers,
                f"query_text_policy_{key}_invalid",
                f"{label}.{key}",
                expected=expected,
                value=policy.get(key),
            )


def validate_abuse_policy(policy: Any, blockers: list[dict[str, Any]]) -> None:
    validate_exact_mapping(
        policy,
        label="$.abuse_policy",
        required=REQUIRED_ABUSE_POLICY,
        missing_reason="abuse_policy_missing",
        fields_reason="abuse_policy_fields_mismatch",
        invalid_prefix="abuse_policy",
        blockers=blockers,
    )


def validate_sequence_gate(gate: Any, blockers: list[dict[str, Any]]) -> None:
    validate_exact_mapping(
        gate,
        label="$.sequence_gate",
        required=REQUIRED_SEQUENCE_GATE,
        missing_reason="sequence_gate_missing",
        fields_reason="sequence_gate_fields_mismatch",
        invalid_prefix="sequence_gate",
        blockers=blockers,
    )


def validate_exact_mapping(
    value: Any,
    *,
    label: str,
    required: dict[str, Any],
    missing_reason: str,
    fields_reason: str,
    invalid_prefix: str,
    blockers: list[dict[str, Any]],
) -> None:
    if not isinstance(value, dict):
        add(blockers, missing_reason, label)
        return
    if set(value) != set(required):
        add(
            blockers,
            fields_reason,
            label,
            missing=sorted(set(required) - set(value)),
            unexpected=sorted(set(value) - set(required)),
        )
    for key, expected in required.items():
        if value.get(key) != expected:
            add(
                blockers,
                f"{invalid_prefix}_{key}_invalid",
                f"{label}.{key}",
                expected=expected,
                value=value.get(key),
            )


def validate_fail_closed_cases(cases: Any, blockers: list[dict[str, Any]]) -> list[str]:
    if not isinstance(cases, list):
        add(blockers, "fail_closed_cases_not_list", "$.fail_closed_cases")
        return []
    names: list[str] = []
    for index, case in enumerate(cases):
        label = f"$.fail_closed_cases[{index}]"
        if not isinstance(case, dict):
            add(blockers, "fail_closed_case_invalid", label)
            continue
        name = case.get("case")
        if not isinstance(name, str) or not name:
            add(blockers, "fail_closed_case_name_missing", f"{label}.case")
            continue
        names.append(name)
        if name not in REQUIRED_FAIL_CLOSED_CASES:
            add(blockers, "fail_closed_case_unexpected", f"{label}.case", case=name)
        if case.get("fail_closed") is not True:
            add(blockers, "fail_closed_case_not_fail_closed", f"{label}.fail_closed", case=name)
        if case.get("allow_allowed") is not False:
            add(blockers, "fail_closed_case_allow_not_forbidden", f"{label}.allow_allowed", case=name)
        if case.get("consumer_result") not in {"deny", "unknown"}:
            add(blockers, "fail_closed_case_consumer_result_not_denied_or_unknown", f"{label}.consumer_result", case=name)
        expected_result = REQUIRED_FAIL_CLOSED_RESULT_BY_CASE.get(name)
        if expected_result is not None and case.get("consumer_result") != expected_result:
            add(
                blockers,
                "fail_closed_case_consumer_result_mismatch",
                f"{label}.consumer_result",
                case=name,
                expected=expected_result,
                value=case.get("consumer_result"),
            )
    missing = REQUIRED_FAIL_CLOSED_CASES - set(names)
    if missing:
        add(blockers, "fail_closed_cases_missing_required", "$.fail_closed_cases", missing=sorted(missing))
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        add(blockers, "fail_closed_cases_duplicate", "$.fail_closed_cases", cases=duplicates)
    if names != list(REQUIRED_FAIL_CLOSED_CASE_SEQUENCE):
        add(
            blockers,
            "fail_closed_cases_sequence_mismatch",
            "$.fail_closed_cases",
            expected=list(REQUIRED_FAIL_CLOSED_CASE_SEQUENCE),
            value=names,
        )
    return names


def validate_reason_flags(contract: Any, blockers: list[dict[str, Any]]) -> list[str]:
    label = "$.fail_closed_reason_flags"
    if not isinstance(contract, dict):
        add(blockers, "reason_flags_contract_missing", label)
        return []

    required_keys = set(REQUIRED_REASON_FLAGS_POLICY) | {"flags"}
    if set(contract) != required_keys:
        add(
            blockers,
            "reason_flags_contract_fields_mismatch",
            label,
            missing=sorted(required_keys - set(contract)),
            unexpected=sorted(set(contract) - required_keys),
        )
    for key, expected in REQUIRED_REASON_FLAGS_POLICY.items():
        if contract.get(key) != expected:
            add(
                blockers,
                f"reason_flags_{key}_invalid",
                f"{label}.{key}",
                expected=expected,
                value=contract.get(key),
            )

    flags = contract.get("flags")
    if not isinstance(flags, list):
        add(blockers, "reason_flags_not_list", f"{label}.flags")
        return []

    names: list[str] = []
    bit_indexes: list[int] = []
    for index, flag in enumerate(flags):
        flag_label = f"{label}.flags[{index}]"
        if not isinstance(flag, dict):
            add(blockers, "reason_flag_invalid", flag_label)
            continue
        expected_keys = {"name", "case", "bit_index", "fail_closed", "allow_allowed", "consumer_result"}
        if set(flag) != expected_keys:
            add(
                blockers,
                "reason_flag_fields_mismatch",
                flag_label,
                missing=sorted(expected_keys - set(flag)),
                unexpected=sorted(set(flag) - expected_keys),
            )

        name = flag.get("name")
        if not isinstance(name, str) or not name:
            add(blockers, "reason_flag_name_missing", f"{flag_label}.name")
            continue
        names.append(name)
        if name not in REQUIRED_FAIL_CLOSED_CASES:
            add(blockers, "reason_flag_unexpected", f"{flag_label}.name", flag=name)
        if flag.get("case") != name:
            add(blockers, "reason_flag_case_mismatch", f"{flag_label}.case", flag=name, value=flag.get("case"))

        bit_index = flag.get("bit_index")
        if isinstance(bit_index, bool) or not isinstance(bit_index, int):
            add(blockers, "reason_flag_bit_index_invalid", f"{flag_label}.bit_index", flag=name, value=bit_index)
        else:
            bit_indexes.append(bit_index)
            if bit_index < 0 or bit_index >= 64:
                add(blockers, "reason_flag_bit_index_out_of_uint64_range", f"{flag_label}.bit_index", flag=name)

        if flag.get("fail_closed") is not True:
            add(blockers, "reason_flag_not_fail_closed", f"{flag_label}.fail_closed", flag=name)
        if flag.get("allow_allowed") is not False:
            add(blockers, "reason_flag_allow_not_forbidden", f"{flag_label}.allow_allowed", flag=name)
        if flag.get("consumer_result") not in {"deny", "unknown"}:
            add(blockers, "reason_flag_consumer_result_not_denied_or_unknown", f"{flag_label}.consumer_result", flag=name)
        expected_result = REQUIRED_FAIL_CLOSED_RESULT_BY_CASE.get(name)
        if expected_result is not None and flag.get("consumer_result") != expected_result:
            add(
                blockers,
                "reason_flag_consumer_result_mismatch",
                f"{flag_label}.consumer_result",
                flag=name,
                expected=expected_result,
                value=flag.get("consumer_result"),
            )

    missing = REQUIRED_FAIL_CLOSED_CASES - set(names)
    if missing:
        add(blockers, "reason_flags_missing_required", f"{label}.flags", missing=sorted(missing))
    name_duplicates = sorted({name for name in names if names.count(name) > 1})
    if name_duplicates:
        add(blockers, "reason_flags_duplicate", f"{label}.flags", flags=name_duplicates)
    if names != list(REQUIRED_REASON_FLAG_SEQUENCE):
        add(
            blockers,
            "reason_flags_sequence_mismatch",
            f"{label}.flags",
            expected=list(REQUIRED_REASON_FLAG_SEQUENCE),
            value=names,
        )
    duplicates = sorted({bit for bit in bit_indexes if bit_indexes.count(bit) > 1})
    if duplicates:
        add(blockers, "reason_flag_bit_index_duplicate", f"{label}.flags", bit_indexes=duplicates)
    expected_bit_by_name = {name: index for index, name in enumerate(REQUIRED_REASON_FLAG_SEQUENCE)}
    for name, bit_index in zip(names, bit_indexes):
        expected_bit = expected_bit_by_name.get(name)
        if expected_bit is not None and bit_index != expected_bit:
            add(
                blockers,
                "reason_flag_bit_index_name_mismatch",
                f"{label}.flags",
                flag=name,
                expected=expected_bit,
                value=bit_index,
            )
    expected_bits = set(range(len(REQUIRED_REASON_FLAG_SEQUENCE)))
    actual_bits = set(bit_indexes)
    if actual_bits and actual_bits != expected_bits:
        add(
            blockers,
            "reason_flag_bit_index_sequence_mismatch",
            f"{label}.flags",
            missing=sorted(expected_bits - actual_bits),
            unexpected=sorted(actual_bits - expected_bits),
        )
    return names


def validate_negative_exclusions(exclusions: Any, blockers: list[dict[str, Any]]) -> None:
    if not isinstance(exclusions, list):
        add(blockers, "negative_surface_exclusions_not_list", "$.negative_surface_exclusions")
        return
    exclusion_set = {item for item in exclusions if isinstance(item, str)}
    if len(exclusion_set) != len(exclusions):
        add(blockers, "negative_surface_exclusion_invalid", "$.negative_surface_exclusions")
    missing = REQUIRED_EXCLUSIONS - exclusion_set
    if missing:
        add(blockers, "negative_surface_exclusions_missing_required", "$.negative_surface_exclusions", missing=sorted(missing))


def validate_promotion_gate(gate: Any, blockers: list[dict[str, Any]]) -> None:
    if not isinstance(gate, dict):
        add(blockers, "promotion_gate_missing", "$.promotion_gate")
        return
    for key in ("ready", "promotion_ready", "public_sdk_ready", "runtime_ready"):
        if gate.get(key) is not False:
            add(blockers, f"promotion_gate_{key}_not_false", f"$.promotion_gate.{key}")
    gate_blockers = gate.get("blockers")
    required = {"candidate_only_pre_abi_contract", "public_abi_review_missing", "runtime_evidence_missing"}
    if not isinstance(gate_blockers, list) or not required.issubset(set(gate_blockers)):
        add(blockers, "promotion_gate_missing_required_blockers", "$.promotion_gate.blockers")


def validate_manifest(payload: dict[str, Any], *, check_mode: str) -> Validation:
    blockers: list[dict[str, Any]] = []
    if payload.get("schema") != SCHEMA:
        add(blockers, "schema_mismatch", "$.schema")
        return Validation(blockers, [], [], [], [], [], [], [], [])
    if payload.get("artifact_status") != "candidate_only":
        add(blockers, "status_not_candidate_only", "$.artifact_status")
    if payload.get("readiness_classification") != "planning_only":
        add(blockers, "readiness_classification_not_planning_only", "$.readiness_classification")
    if payload.get("pre_abi") is not True:
        add(blockers, "pre_abi_not_true", "$.pre_abi")
    for key in (
        "public_header_allowed",
        "public_cache_abi_allowed",
        "promotion_ready",
        "public_sdk_ready",
        "runtime_ready",
        "runtime_promotion_allowed",
        "v1",
    ):
        if payload.get(key) is not False:
            add(blockers, f"{key}_not_false", f"$.{key}")
    for key in NO_CREDIT_FALSE_KEYS:
        if key in payload and payload.get(key) is not False:
            add(blockers, f"{key}_not_false", f"$.{key}")
    for key in NO_CREDIT_ZERO_KEYS:
        if key in payload and payload.get(key) != 0:
            add(blockers, f"{key}_not_zero", f"$.{key}")

    validate_exact_mapping(
        payload.get("artifact_identity"),
        label="$.artifact_identity",
        required=REQUIRED_ARTIFACT_IDENTITY,
        missing_reason="artifact_identity_missing",
        fields_reason="artifact_identity_fields_mismatch",
        invalid_prefix="artifact_identity",
        blockers=blockers,
    )
    validate_exact_mapping(
        payload.get("dependency_context"),
        label="$.dependency_context",
        required=REQUIRED_DEPENDENCY_CONTEXT,
        missing_reason="dependency_context_missing",
        fields_reason="dependency_context_fields_mismatch",
        invalid_prefix="dependency_context",
        blockers=blockers,
    )
    query_fields = validate_query_contract(payload.get("query_contract"), blockers)
    decisions, decision_fields, provenance_fields = validate_decision_contract(payload.get("decision_contract"), blockers)
    recognized_authority_kinds, allow_capable_authority_kinds = validate_authority_policy(
        payload.get("authority_policy"), blockers
    )
    validate_principal_runtime_identity_policy(payload.get("principal_runtime_identity_policy"), blockers)
    validate_principal_provenance_policy(payload.get("principal_provenance_policy"), blockers)
    validate_owner_token_policy(payload.get("owner_token_policy"), blockers)
    validate_policy_provenance_policy(payload.get("policy_provenance_policy"), blockers)
    validate_query_text_policy(payload.get("query_text_policy"), blockers)
    validate_abuse_policy(payload.get("abuse_policy"), blockers)
    validate_sequence_gate(payload.get("sequence_gate"), blockers)
    fail_closed_cases = validate_fail_closed_cases(payload.get("fail_closed_cases"), blockers)
    reason_flags = validate_reason_flags(payload.get("fail_closed_reason_flags"), blockers)
    validate_negative_exclusions(payload.get("negative_surface_exclusions"), blockers)
    validate_promotion_gate(payload.get("promotion_gate"), blockers)

    non_claims = payload.get("non_claims")
    if not isinstance(non_claims, list) or not REQUIRED_NON_CLAIMS.issubset(set(non_claims)):
        add(blockers, "non_claims_missing_required", "$.non_claims")

    coordinate = find_forbidden_coordinate(payload)
    if coordinate is not None:
        field, trail = coordinate
        add(blockers, "ue_coordinate_or_pointer_leakage", trail, field=field)

    forbidden = find_forbidden_surface(payload)
    if forbidden is not None:
        value, trail = forbidden
        add(blockers, "forbidden_surface_claim", trail, value=value)
    claim_source = find_forbidden_pre_runtime_claim_source(payload)
    if claim_source is not None:
        field, trail = claim_source
        add(blockers, "pre_runtime_principal_or_permission_claim_source", trail, field=field)
    for overclaim in collect_overclaim_fields(payload):
        add(blockers, overclaim["reason"], overclaim["label"])

    if check_mode != "consume":
        add(blockers, f"{check_mode}_blocked_for_candidate_only_pre_abi_contract", "$")
        add(blockers, "candidate_only_permissions_admin_query_contract_not_readiness_evidence", "$")

    return Validation(
        blockers,
        query_fields,
        decisions,
        decision_fields,
        provenance_fields,
        reason_flags,
        fail_closed_cases,
        recognized_authority_kinds,
        allow_capable_authority_kinds,
    )


def build_report(payload: dict[str, Any], validation: Validation, *, check_mode: str) -> dict[str, Any]:
    report = {
        "schema": REPORT_SCHEMA,
        "input_schema": payload.get("schema"),
        "mode": check_mode,
        "ready": not validation.blockers,
        "valid": not validation.blockers,
        "candidate_only": payload.get("artifact_status") == "candidate_only",
        "pre_abi": payload.get("pre_abi") is True,
        "public_header_allowed": False,
        "public_cache_abi_allowed": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "v1": False,
        "query_fields": validation.query_fields,
        "decisions": validation.decisions,
        "decision_fields": validation.decision_fields,
        "provenance_fields": validation.provenance_fields,
        "reason_flags": validation.reason_flags,
        "fail_closed_cases": validation.fail_closed_cases,
        "recognized_authority_kinds": validation.recognized_authority_kinds,
        "allow_capable_authority_kinds": validation.allow_capable_authority_kinds,
        "blockers": [blocker["reason"] for blocker in validation.blockers],
        "blocker_details": validation.blockers,
    }
    report.update({key: False for key in NO_CREDIT_FALSE_KEYS})
    report.update({key: 0 for key in NO_CREDIT_ZERO_KEYS})
    return report


def main() -> int:
    args = parse_args()
    check_mode = mode(args)
    if args.emit_template is not None:
        payload = build_template_manifest()
        args.emit_template.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 0
    if args.manifest is None:
        raise SystemExit("manifest is required unless --emit-template is used")
    payload = load_json(args.manifest)
    validation = validate_manifest(payload, check_mode=check_mode)
    report = build_report(payload, validation, check_mode=check_mode)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif validation.blockers:
        for blocker in validation.blockers:
            print(f"{blocker['reason']}: {blocker['label']}", file=sys.stderr)
    return 0 if not validation.blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
