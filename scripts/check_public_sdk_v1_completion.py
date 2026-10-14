#!/usr/bin/env python3
"""Fail-closed checker for the Obelisk v1.0 complete-SDK claim."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import check_player_identity_runtime_principal_lifecycle_approved_evidence as approved_runtime_principal_lifecycle_evidence
from native_prototype_guardrails import native_prototype_header_symbols


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
DEFAULT_SCOPED_RELEASE_STATEMENT = (
    REPO_ROOT / "docs" / "SCOPED_NON_COMPLETE_V1_RELEASE_STATEMENT.md"
)
DEFAULT_PUBLIC_HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"
DEFAULT_CONTRACT_DECISIONS_DIR = REPO_ROOT / "docs"
DEFAULT_COMMAND_PERMISSION_ROUTE_GATE = REPO_ROOT / "scripts" / "check_command_permission_route_gate.py"
DEFAULT_INVENTORY_COPIED_SIGNALS_STABILITY = (
    REPO_ROOT / "scripts" / "check_inventory_item_copied_signals_stability.py"
)
DEFAULT_OBJECT_IDENTITY_RESOURCE_HANDLE_READINESS = (
    REPO_ROOT / "scripts" / "check_object_identity_resource_handle_public_contract_readiness.py"
)
DEFAULT_MISSION_TRANSFER_DINO_TRIBE_OUTCOME_ACCOUNTING = (
    REPO_ROOT / "scripts" / "check_mission_transfer_dino_tribe_v1_outcome_accounting.py"
)
DEFAULT_STRUCTURE_CENSUS_READINESS = REPO_ROOT / "scripts" / "check_structure_census_readiness.py"
DEFAULT_STRUCTURE_BUILD_POLICY_OFFLINE_INTAKE = (
    REPO_ROOT / "scripts" / "check_structure_build_policy_offline_intake.py"
)
DEFAULT_COMMAND_RESPONSE_PUBLIC_CONTRACT_DECISIONS = (
    REPO_ROOT / "docs" / "command_chat_response_public_contract_decisions.json"
)
DEFAULT_COMMANDS_REPLIES_PUBLIC_CONTRACT_DECISIONS = (
    REPO_ROOT / "docs" / "commands_replies_public_contract_decisions.json"
)
COMMAND_RESPONSE_PUBLIC_READINESS_SOURCE_ARTIFACT_KEYS = (
    "readiness_path",
    "decisions_path",
    "surfaces_path",
    "public_header_path",
)
COMMANDS_REPLIES_PUBLIC_READINESS_SOURCE_ARTIFACT_KEYS = (
    "decisions_path",
    "surfaces_path",
    "public_header_path",
)
COMMANDS_REPLIES_RESPONSE_PATH_REPORT_NAME = "command-chat-response-public-readiness.json"
COMMAND_RESPONSE_READINESS_PRODUCER_SCRIPT = "scripts/compare_reflection_snapshots.py"
COMMAND_RESPONSE_READINESS_OUTPUT_NAME = "command-chat-response-route-planning-readiness.json"
COMMAND_RESPONSE_READINESS_TARGET_SET = "command-chat-response-route-planning"
REQUIRED_PRINCIPAL_LIFECYCLE_EVENT_ROLES = (
    "session_start",
    "session_start_rejected",
    "session_end",
)
APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_BUNDLE = (
    "approved_runtime_principal_lifecycle_evidence_bundle"
)
APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER = "approved_runtime_evidence_missing"
IDENTITY_PUBLIC_CONTRACT_GATE_MISSING_BLOCKER = "identity_public_contract_gate_missing"
STANDING_LAUNCH_AUTHORITY_RECORDED = True
STANDING_LAUNCH_AUTHORITY_SOURCE = "2026-06-06_operator_standing_launch_authority"
STANDING_OR_CURRENT_SCOPE_REQUIREMENT = (
    "recorded standing launch authority can prepare necessary ObeliskSDK runtime "
    "windows; otherwise an exact current-turn operator approval is required; "
    "this completion report grants no evidence, readiness, publication, or SDK progress"
)
OBJECT_IDENTITY_RESOURCE_HANDLE_DECISIONS_FILENAME = (
    "object_identity_resource_handle_public_contract_decisions.json"
)
MISSION_TRANSFER_DINO_TRIBE_REQUIRED_LEAVES_ORDER = (
    "mission",
    "transfer",
    "dino_policy",
    "tribe_policy",
    "buff_status",
)
MISSION_TRANSFER_DINO_TRIBE_REQUIRED_LEAVES = set(
    MISSION_TRANSFER_DINO_TRIBE_REQUIRED_LEAVES_ORDER
)
MULTI_SURFACE_BETA_CAPTURE_TARGETS = (
    "player_principal_lifecycle",
    "permissions_admin",
    "command_chat_response_path",
    "commands_replies",
    "inventory_item_copied_signals",
    "inventory_items_mutation",
    "transfer",
    "mission",
    "dino_policy",
    "tribe_policy",
    "buff_status",
)
MULTI_SURFACE_BETA_CAPTURE_CANDIDATE_QUEUE_ARTIFACT_SCHEMAS = (
    "obelisk.multi-surface-beta-capture-plan.v1",
    "obelisk.multi-surface-beta-capture-pack.v1",
    "obelisk.multi-surface-beta-capture-checker-matrix.v1",
    "obelisk.multi-surface-beta-capture-non-claim-manifest.v1",
)
MULTI_SURFACE_BETA_CAPTURE_CANDIDATE_QUEUE_ARTIFACT_NAMES = (
    "multi-surface-capture-plan.json",
    "checker-command-matrix.json",
    "non-claim-manifest.json",
    "operator-runbook.md",
    "manifest.json",
    "README.md",
)
MULTI_SURFACE_BETA_CAPTURE_CANDIDATE_QUEUE_NON_EVIDENCE_REASON = (
    "multi_surface_beta_capture_pack_not_approved_runtime_evidence"
)
PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA = (
    "obelisk.player-identity-promotion-certificate.v1"
)
PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA = (
    "obelisk.permissions-admin-promotion-certificate.v1"
)
COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA = (
    "obelisk.command-chat-response-path-promotion-certificate.v1"
)
COMMANDS_REPLIES_PROMOTION_CERTIFICATE_SCHEMA = (
    "obelisk.commands-replies-promotion-certificate.v1"
)
REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH = (
    "evidence.reviewed_surface_record_sha256"
)
REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH_POLICY = (
    "must match the reviewed surface record hash carried by the certificate"
)
PLAYER_IDENTITY_PROMOTION_CERTIFICATE_BUILD_REPORT_SCHEMA = (
    "obelisk.player-identity-promotion-certificate-build-report.v1"
)
PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_BUILD_REPORT_SCHEMA = (
    "obelisk.permissions-admin-promotion-certificate-build-report.v1"
)
COMMAND_RESPONSE_PROMOTION_CERTIFICATE_BUILD_REPORT_SCHEMA = (
    "obelisk.command-chat-response-path-promotion-certificate-build-report.v1"
)
COMMANDS_REPLIES_PROMOTION_CERTIFICATE_BUILD_REPORT_SCHEMA = (
    "obelisk.commands-replies-promotion-certificate-build-report.v1"
)
PROMOTION_CERTIFICATE_BUILD_REPORT_SCHEMAS = frozenset(
    (
        PLAYER_IDENTITY_PROMOTION_CERTIFICATE_BUILD_REPORT_SCHEMA,
        PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_BUILD_REPORT_SCHEMA,
        COMMAND_RESPONSE_PROMOTION_CERTIFICATE_BUILD_REPORT_SCHEMA,
        COMMANDS_REPLIES_PROMOTION_CERTIFICATE_BUILD_REPORT_SCHEMA,
    )
)
PROMOTION_CERTIFICATE_BINDING_INLINE_SHAPE_KEYS = frozenset(
    (
        "schema",
        "surface_id",
        "promotion_status",
        "certificate_status",
        "planning_only",
        "non_authorizing",
        "v1_dependency_chain",
        "v1_dependency_chain_position",
        "required_by_surface",
        "required_by_v1_dependency_chain_position",
        "required_prior_surface",
        "required_prior_certificate_schema",
        "required_reviewed_artifact_hash",
        "reviewed_artifact_hash_policy",
        "missing_mismatched_or_stale_certificate_counts",
        "evidence",
        "input_bindings",
        "certificate_binding",
        "certificate_written",
        "certificate_sha256",
        "certificate_path",
        "certificate_artifact_schema",
        "output_certificate",
        "output_certificate_path",
        "sdk_progress",
        "counts_toward_v1_completion",
    )
)
PROMOTION_CERTIFICATE_BINDING_VALID_KEYS = frozenset(
    (
        "identity_surface_certificate_binding_valid",
        "permissions_admin_surface_certificate_binding_valid",
        "command_response_surface_certificate_binding_valid",
        "commands_replies_surface_certificate_binding_valid",
    )
)
PROMOTION_CERTIFICATE_REPORT_CONTAINER_KEYS = frozenset(
    (
        "certificate_artifact_schema",
        "certificate_binding",
        "certificate_path",
        "certificate_sha256",
        "certificate_written",
        "output_certificate",
        "output_certificate_path",
    )
)
PROMOTION_CERTIFICATE_HASH_BINDING_REFERENCE_KEYS = frozenset(
    (
        "player_identity_promotion_certificate",
        "permissions_admin_promotion_certificate",
        "command_response_promotion_certificate",
        "commands_replies_promotion_certificate",
    )
)
PLAYER_IDENTITY_PUBLIC_CONTRACT_REQUIRED_BLOCKERS = {
    "runtime.lifecycle_evidence",
    "privacy.identifier_redaction",
    "lifetime.generation_scope_invalidation",
    "abi.public_pod_contract",
    "lifecycle.owner_cleanup",
    "separation.downstream_surfaces",
}
PLAYER_IDENTITY_PUBLIC_CONTRACT_GATE_INPUT_REQUIRED_FALSE_KEYS = (
    "contract_reviewed",
    "identity_contract_ready",
    "identity_header_allowed",
    "principal_handle_abi_ready",
    "public_identity_ready",
    "promotion_blocker_resolved",
    "promotion_ready",
    "public_sdk_ready",
    "runtime_ready",
    "public_header_allowed",
    "v1_completion_evidence",
)
CANONICAL_MANIFEST_RELEASE_CLAIM = "no-v1-stable-release-claim-post-rc-surface-inventory"
CANONICAL_SURFACE_IDS = {
    "obelisk.arkapi_compatibility.v1",
    "obelisk.chat.local_routing.v1",
    "obelisk.chat_message.v1",
    "obelisk.command_chat_response_path.v1",
    "obelisk.commands_replies.v1",
    "obelisk.debug_raw_process_event.v1",
    "obelisk.descriptors.v1",
    "obelisk.gameplay_policy_event.v1",
    "obelisk.gameplay_tick_callbacks.v1",
    "obelisk.inventory_item_copied_signals.v1",
    "obelisk.inventory_items_mutation.v1",
    "obelisk.lifecycle_config_logging.v1",
    "obelisk.lifecycle_ops_recovery.v1",
    "obelisk.mission_transfer_dino_tribe.v1",
    "obelisk.object_identity_resource_handle.v1",
    "obelisk.operator_ingress_storage.v1",
    "obelisk.permissions_admin.v1",
    "obelisk.player_identity.v1",
    "obelisk.player_services_economy_mobility.v1",
    "obelisk.process_local_timers.v1",
    "obelisk.structure_census.v1",
}
CANONICAL_V1_COMPLETION_BLOCKERS = {
    "obelisk.player_identity.v1",
    "obelisk.permissions_admin.v1",
    "obelisk.commands_replies.v1",
    "obelisk.command_chat_response_path.v1",
    "obelisk.inventory_items_mutation.v1",
    "obelisk.lifecycle_ops_recovery.v1",
    "obelisk.structure_census.v1",
    "obelisk.mission_transfer_dino_tribe.v1",
    "obelisk.object_identity_resource_handle.v1",
    "obelisk.player_services_economy_mobility.v1",
    "obelisk.operator_ingress_storage.v1",
    "obelisk.gameplay_tick_callbacks.v1",
}
CANONICAL_V1_COMPLETION_BLOCKER_ORDER = (
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
CANONICAL_V1_DEPENDENCY_SEQUENCE = (
    "obelisk.player_identity.v1",
    "obelisk.permissions_admin.v1",
    "obelisk.command_chat_response_path.v1",
    "obelisk.commands_replies.v1",
)
CANONICAL_V1_REQUIRED_DEPENDENCY_CHAIN = CANONICAL_V1_DEPENDENCY_SEQUENCE
P0_DEPENDENCY_CHAIN_SCOPED_NON_COMPLETE_ALLOWED_OUTCOMES = {"excluded", "post-v1"}
CANONICAL_ACTIVE_SIDE_LANE_REVIEW_BLOCKERS = {
    "obelisk.lifecycle_ops_recovery.v1",
    "obelisk.player_services_economy_mobility.v1",
    "obelisk.operator_ingress_storage.v1",
    "obelisk.gameplay_tick_callbacks.v1",
}
CANONICAL_EXPERIMENTAL_SURFACE_IDS = {
    "obelisk.gameplay_policy_event.v1",
    "obelisk.chat_message.v1",
    "obelisk.chat.local_routing.v1",
    "obelisk.inventory_item_copied_signals.v1",
}
CANONICAL_EXPERIMENTAL_RELEASE_STATEMENT_TEXT = {
    "obelisk.gameplay_policy_event.v1": ("GameplayPolicyEvent", "not included in v1"),
    "obelisk.chat_message.v1": ("ChatMessageEvent", "not included in v1"),
    "obelisk.chat.local_routing.v1": ("chat routing", "not included in v1"),
    "obelisk.inventory_item_copied_signals.v1": ("inventory copied signals", "not included in v1"),
}
CANONICAL_STABLE_RELEASE_CLAIM_REQUIRES = (
    "v1_completion_required is true in this manifest",
    "every v1_required_dependency_chain surface is promoted with evidence before complete/full/production SDK wording",
    "every non-chain v1_sdk_completion_blocker is promoted or explicitly named as excluded/post-v1 in the v1 release statement",
    "non-P0 minimum promoted demand families are promoted or satisfied by explicit v1_completion_equivalent_for records before complete/full/production SDK wording; no demand-family equivalent or legacy completion alias may satisfy a P0 dependency-chain surface",
    "no promoted-experimental-only surface remains unresolved",
    "the release ships a reviewed SDK compatibility statement based on docs/SDK_V1_COMPATIBILITY.md and docs/public_sdk_surfaces.json",
)
CANONICAL_STABLE_RELEASE_NOT_SUFFICIENT = (
    "runtime/core-first RC readiness",
    "internal runtime stability",
    "Foundation/Plugin Hub seed package shape",
    "GameplayPolicyEvent, ChatMessageEvent, and inventory item copied-signal seeds",
)
CANONICAL_INSTALLED_SDK_PACKAGE_SHAPE = {
    "component": "SDK",
    "status": "package-shape-evidence-only",
    "installed_files": (
        "include/obelisk/ObeliskApi.h",
        "lib/cmake/Obelisk/ObeliskConfig.cmake",
        "lib/cmake/Obelisk/ObeliskConfigVersion.cmake",
        "lib/cmake/Obelisk/ObeliskTargets.cmake",
    ),
    "not_sufficient_for": (
        "v1_completion_required",
        "stable_release_contract.claim_allowed",
        "release package readiness or public package availability",
        "Plugin Hub seed/package publication",
        "promotion of blocked gameplay, identity, permissions, command, storage, or mutation surfaces",
    ),
    "non_claim_exports": {
        "Obelisk_RUNTIME_READINESS_CLAIM_ALLOWED": False,
        "Obelisk_RUNTIME_LIVE_OP_APPROVAL_ALLOWED": False,
        "Obelisk_PLUGIN_HUB_PUBLICATION_ALLOWED": False,
        "Obelisk_PLUGIN_HUB_READINESS_CLAIM_ALLOWED": False,
        "Obelisk_SUPPORT_TIER_ACTIVATION_ALLOWED": False,
        "Obelisk_V1_COMPLETION_CLAIM_ALLOWED": False,
        "Obelisk_PUBLIC_MODULE_SDK_COVERAGE_CLAIM_ALLOWED": False,
        "Obelisk_PRODUCTION_STABLE_SDK_CLAIM_ALLOWED": False,
    },
}
INSTALLED_SDK_PACKAGE_SHAPE_FORBIDDEN_POSITIVE_CLAIM_KEYS = (
    "Obelisk_RUNTIME_READINESS_CLAIM_ALLOWED",
    "Obelisk_RUNTIME_LIVE_OP_APPROVAL_ALLOWED",
    "Obelisk_PLUGIN_HUB_PUBLICATION_ALLOWED",
    "Obelisk_PLUGIN_HUB_READINESS_CLAIM_ALLOWED",
    "Obelisk_SUPPORT_TIER_ACTIVATION_ALLOWED",
    "Obelisk_PRODUCTION_STABLE_SDK_CLAIM_ALLOWED",
    "Obelisk_PUBLIC_MODULE_SDK_COVERAGE_CLAIM_ALLOWED",
    "Obelisk_V1_COMPLETION_CLAIM_ALLOWED",
    "abi_layout_ready",
    "abi_layout_validated",
    "counts_toward_complete_sdk_claim",
    "cmake_config_ready",
    "cmake_package_ready",
    "cmake_package_support_tier_ready",
    "cmake_package_v1_completion_ready",
    "cmake_targets_ready",
    "components_sdk_ready",
    "headers_count_toward_complete_sdk_claim",
    "installed_headers_ready",
    "installed_sdk_consumer_tests_ready",
    "installed_sdk_consumer_tests_v1_completion_ready",
    "installed_sdk_package_ready",
    "installed_sdk_release_ready",
    "obelisk_config_cmake_ready",
    "obelisk_targets_cmake_ready",
    "owner_token_registration_ready",
    "owner_token_sdk_consumer_ready",
    "cross_event_identity_ready",
    "cross_event_object_identity_ready",
    "lookup_ready",
    "mutation_ready",
    "object_identity_ready",
    "object_lookup_ready",
    "object_mutation_ready",
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
    "public_package_available",
    "public_package_published",
    "public_package_ready",
    "plugin_hub_publication_allowed",
    "plugin_hub_counts_toward_completion",
    "plugin_hub_counts_toward_public_sdk",
    "plugin_hub_counts_toward_v1_completion",
    "plugin_hub_readiness_claim_allowed",
    "plugin_hub_readiness_allowed",
    "plugin_hub_readiness_ready",
    "plugin_hub_ready",
    "plugin_hub_package_published",
    "plugin_hub_seed_ready",
    "plugin_hub_seed_package_publication",
    "plugin_hub_support_tier_ready",
    "promoted_for_claim_count",
    "promotion_ready",
    "public_abi_available",
    "public_header_allowed",
    "public_header_available",
    "public_module_sdk_coverage_claim_allowed",
    "public_module_sdk_coverage_ready",
    "public_module_sdk_covered",
    "public_header_ready",
    "public_headers_ready",
    "public_headers_available",
    "public_lookup_ready",
    "public_mutation_ready",
    "public_sdk_coverage_ready",
    "public_sdk_ready",
    "persistent_handle_ready",
    "persistent_identity_ready",
    "persistent_object_identity_ready",
    "post_callback_handle_ready",
    "post_callback_object_validity_ready",
    "post_callback_resource_handle_ready",
    "post_callback_validity_ready",
    "release_statement_ready",
    "release_package_allowed",
    "release_package_available",
    "release_package_published",
    "release_package_ready",
    "release_packaged",
    "release_statement_bookkeeping_counts_toward_completion",
    "release_statement_counts_toward_completion",
    "release_statement_outcomes_satisfy_completion",
    "sdk_package_available",
    "sdk_package_published",
    "sdk_package_ready",
    "sdk_consumer_tests_count_toward_complete_sdk_claim",
    "sdk_consumer_tests_ready",
    "sdk_coverage_complete",
    "resource_handle_ready",
    "resource_lookup_ready",
    "runtime_object_negative_samples_ready",
    "runtime_sample_ready",
    "serial_policy_ready",
    "serial_reuse_ready",
    "serial_wraparound_ready",
    "stable_claim_allowed",
    "stable_sdk_ready",
    "struct_size_ready",
    "struct_size_validated",
    "scoped_release_statement_counts_toward_complete_sdk_claim",
    "scoped_release_statement_counts_toward_completion",
    "scoped_release_statement_outcomes_satisfy_completion",
    "scoped_release_statement_ready",
    "runtime_live_op_approval_allowed",
    "runtime_readiness_claim_allowed",
    "support_tier_activation_allowed",
    "support_tier_activated",
    "support_tier_allowed",
    "support_tier_ready",
    "support_tier_supported",
    "stable_release_contract_claim_allowed",
    "v1_completion_claim_allowed",
    "v1_completion_ready",
    "v1_completion_required",
)
INSTALLED_SDK_PACKAGE_SHAPE_FORBIDDEN_ALIAS_KEYS = (
    "promoted_demand_family_equivalents",
    "v1_completion_equivalent_for",
)
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
    "approved_bundle_request_accepted",
    "approved_notice_action",
    "approved_player_notice_action",
    "approved_runtime_bundle_request_accepted",
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
NOTICE_OR_BUNDLE_STATUS_CONTAINER_KEYS = {
    "accepted_notice_action",
    "active_notice",
    "active_notice_action",
    "active_notice_report",
    "approved_notice_action",
    "approved_bundle",
    "beta_notice",
    "beta_notice_attestation",
    "beta_notice_send",
    "beta_notice_send_attestation",
    "bot_notice",
    "bundle_acceptance",
    "confirmed_beta_notice_report",
    "confirmed_notice_report",
    "discord_beta_bridge",
    "discord_beta_bridge_bot_notice",
    "discord_beta_bot_notice",
    "discord_bot_notice",
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
SOURCE_READY_STATUS_ALIAS_KEYS = (
    "runtime_evidence_status",
    "runtime_evidence_status_ready",
    "sdk_status_ready",
    "sdk_status_report_ready",
    "source_binding_ready",
    "source_bindings_ready",
    "source_checker_ready",
    "source_checker_status",
    "source_ready",
    "source_readiness_ready",
    "source_readiness_status",
    "source_state",
    "source_status",
    "sources_ready",
    "status_artifact_ready",
    "status_report_ready",
    "status_report_state",
    "status_report_status",
    "status_snapshot_ready",
)
RECENT_NON_EVIDENCE_DIAGNOSTIC_POSITIVE_ALIAS_KEYS = (
    "event_split_accepted",
    "event_split_ready",
    "lifecycle_event_split_accepted",
    "lifecycle_event_split_ready",
    "player_principal_lifecycle_event_split_accepted",
    "player_principal_lifecycle_event_split_ready",
    "post_runtime_contract_gap_accepted",
    "post_runtime_contract_gap_ready",
    "post_runtime_contract_gap_resolved",
    "post_runtime_contract_ready",
    "ready_log_evidence_split_accepted",
    "ready_log_evidence_split_ready",
    "route_sample_accepted",
    "route_sample_ready",
    "route_samples_accepted",
    "route_samples_ready",
)
SCOPED_RELEASE_STATEMENT_ALLOWED_BLOCKERS = {
    "command_permission_route_gate_blockers_not_empty",
    "command_permission_route_gate_invalid",
    "command_permission_route_gate_lock_unexpected",
    "command_permission_route_gate_not_planning_only",
    "complete_sdk_claim_requires_promoted_demand_families",
    "stable_release_contract_claim_not_allowed",
    "v1_completion_required_false",
    "promoted_experimental_surfaces_unresolved",
    "v1_sdk_completion_blockers_unresolved",
    "p0_dependency_chain_outcomes_scoped_non_complete_only",
    "v1_required_dependency_chain_unpromoted",
    "planning_surfaces_unresolved_for_v1_claim",
    "top_level_planning_surfaces_unresolved_for_v1_claim",
}
COMMAND_PERMISSION_ROUTE_GATE_FORBIDDEN_CLAIM_KEYS = (
    "contract_reviewed",
    "contract_review_artifact_ready",
    "contract_review_ready",
    "identity_contract_ready",
    "identity_header_allowed",
    "principal_handle_abi_ready",
    "public_contract_allowed",
    "public_contract_artifact_ready",
    "public_contract_ready",
    "public_contract_review_ready",
    "public_identity_ready",
    "reviewed_public_contract",
    "reviewed_public_contract_ready",
    "promotion_ready",
    "public_sdk_ready",
    "public_sdk_readiness_allowed",
    "public_sdk_readiness_ready",
    "public_sdk",
    "module_sdk_ready",
    "sdk_ready",
    "dino_sdk_ready",
    "mission_sdk_ready",
    "transfer_sdk_ready",
    "tribe_sdk_ready",
    "buff_sdk_ready",
    "buff_status_sdk_ready",
    "public_module_ready",
    "public_module_sdk_ready",
    "public_dino_sdk_ready",
    "public_mission_sdk_ready",
    "public_transfer_sdk_ready",
    "public_tribe_sdk_ready",
    "public_buff_sdk_ready",
    "public_buff_status_sdk_ready",
    "public_abi_ready",
    "public_abi_available",
    "public_abi_allowed",
    "public_api_ready",
    "public_callback_ready",
    "public_descriptor_ready",
    "public_capability_ready",
    "public_reply_abi_ready",
    "public_response_path_ready",
    "callback_ready",
    "descriptor_ready",
    "capability_ready",
    "dispatcher_ready",
    "runtime_ready",
    "runtime_readiness_allowed",
    "runtime_readiness_ready",
    "runtime_v1_ready",
    "runtime_hook_ready",
    "runtime_hook_wiring_ready",
    "runtime_wiring_ready",
    "runtime_observer_approved",
    "runtime_validated",
    "runtime_validation_ready",
    "runtime_work_authorized",
    "send_chat_ready",
    "activation_preconditions_met",
    "approved_runtime_evidence_ready",
    "approved_runtime_evidence_binding",
    "approved_runtime_evidence_binding_accepted",
    "approved_runtime_evidence_binding_acceptance",
    "approved_runtime_evidence_binding_present",
    "approved_runtime_evidence_binding_ready",
    "approved_runtime_evidence_binding_counts_as_approved_runtime_evidence",
    "start_end_evidence",
    "start_end_evidence_accepted",
    "start_end_evidence_acceptance",
    "start_end_evidence_ready",
    "start_end_only_evidence",
    "start_end_only_evidence_accepted",
    "start_end_only_evidence_acceptance",
    "start_end_only_evidence_ready",
    "session_start_end_evidence",
    "session_start_end_evidence_accepted",
    "session_start_end_evidence_acceptance",
    "session_start_end_evidence_ready",
    "session_start_and_end_evidence",
    "session_start_and_end_evidence_accepted",
    "session_start_and_end_evidence_acceptance",
    "session_start_and_end_evidence_ready",
    "complete_sdk_claim_allowed",
    "approved_runtime_evidence_missing_cleared",
    "approved_runtime_evidence_missing_resolved",
    "blocker_cleared",
    "blocker_resolved",
    "clears_approved_runtime_evidence_missing",
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
    "resolves_approved_runtime_evidence_missing",
    "counts_toward_complete_sdk",
    "counts_toward_complete_sdk_claim",
    "counts_toward_sdk",
    "counts_toward_p0_dependency_chain",
    "counts_toward_p0_dependency_chain_claim",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    *NOTICE_OR_BUNDLE_NON_PROGRESS_FALSE_ALIAS_KEYS,
    "p0_ready",
    "p0_dependency_ready",
    "p0_dependency_chain_accounted",
    "p0_accounting_counts_as_promoted_surface",
    "sdk_accounting_counts_as_completed_surface",
    "p0_dependency_chain_ready",
    "plugin_hub_ready",
    "plugin_hub_readiness_allowed",
    "plugin_hub_readiness_claim_allowed",
    "plugin_hub_readiness_ready",
    "public_or_runtime_accounting_allowed",
    "public_header_allowed",
    "public_header_ready",
    "public_readiness_ready",
    "request_check_ready",
    "request_pack_ready",
    "approved_bundle_request_accepted",
    "approved_bundle_request_ready",
    "approved_runtime_bundle_request_accepted",
    "approved_runtime_bundle_request_ready",
    *SOURCE_READY_STATUS_ALIAS_KEYS,
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
    "permissions_ready",
    "permission_ready",
    "command_router_allowed",
    "runtime_delivery_allowed",
    "runtime_readiness_allowed",
    "route_ready",
    "route_readiness_ready",
    "route_check_accepted",
    "route_check_acceptance",
    "route_gate_accepted",
    "route_gate_acceptance",
    "check_join_in_progress_planning_acceptance",
    "check_join_in_progress_1_0_planning_acceptance",
    "check_join_in_progress10_planning_acceptance",
    "checkjoininprogress_planning_acceptance",
    "checkjoininprogress_1_0_planning_acceptance",
    "checkjoininprogress10_planning_acceptance",
    *RECENT_NON_EVIDENCE_DIAGNOSTIC_POSITIVE_ALIAS_KEYS,
    "public_response_path_allowed",
    "v1_completion_evidence",
    "v1_completion_ready",
    "stable_claim_allowed",
    "authorizes_discord",
    "discord_authorized",
    "discord_notice_authorized",
    "authorizes_server_work",
    "authorizes_server_operations",
    "authorizes_workspace_work",
    "authorizes_workspace_writes",
    "workspace_writes_authorized",
    "live_ops_authorized",
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
    "standing_launch_authority",
    "standing_launch_authority_accepted",
    "standing_launch_authority_acceptance",
    "standing_launch_authority_ready",
    "standing_launch_authority_counts_as_approved_runtime_evidence",
    "standing_launch_authority_counts_as_runtime_evidence",
    "standing_launch_authority_counts_toward_sdk",
    "standing_launch_authority_counts_toward_p0_dependency_chain",
    "standing_launch_authority_counts_toward_complete_sdk_claim",
    "operator_approval_granted",
    "runtime_approval",
    "runtime_approval_granted",
    "runtime_work_authorized",
    "marker_env_changes_authorized",
    "publication_authorized",
    "discord_authorized_by_request",
    "discord_authorized_by_this_report",
    "server_operations_authorized",
    "side_lane_promoted",
    "structure_build_policy_ready",
    "v1_complete",
    "v1_completion",
    "v1_release_ready",
    *SOURCE_READY_STATUS_ALIAS_KEYS,
    *RECENT_NON_EVIDENCE_DIAGNOSTIC_POSITIVE_ALIAS_KEYS,
)
COMMAND_PERMISSION_ROUTE_GATE_FORBIDDEN_SOURCE_KEYS = {
    "approved_runtime_evidence_source",
    "authority_claim_source",
    "authz_principal_source",
    "claim_source",
    "claim_sources",
    "command_principal_source",
    "diagnostic_source",
    "evidence_source",
    "evidence_sources",
    "identity_claim_source",
    "planning_source",
    "permission_principal_source",
    "principal_claim_source",
    "principal_source",
    "principal_sources",
    "public_identity_source",
    "readiness_source",
    "readiness_sources",
    "runtime_evidence_source",
    "runtime_evidence_sources",
    "runtime_identity_source",
    "source",
    "sources",
    "source_kind",
    "source_kinds",
    "source_value",
    "source_values",
    "status_source",
}
COMMAND_PERMISSION_ROUTE_GATE_FORBIDDEN_SOURCE_VALUE_RE = re.compile(
    r"(?:"
    r"(?:approved_?)?runtime(?:_local|_evidence|_lifecycle|_observation|_observed|_principal.*evidence)?|"
    r"approved_runtime_principal_lifecycle_evidence|"
    r"runtime_principal_lifecycle_evidence|"
    r"runtime_lifecycle_evidence|"
    r"players?_identity_runtime_principal_lifecycle_evidence|"
    r"reviewed_identity_public_contract|"
    r"identity_public_contract|"
    r"(?:players?_?)?identity_?lifecycle_?anchor_?candidates?|"
    r"lifecycle_?anchor_?(?:candidates?|report|evidence)|"
    r"check_?join_?in_?progress(?:_?(?:1_?0|10|planning|diagnostic|offline|candidate(?:_?only)?|accept(?:ed|ance)|readiness|report|status|evidence|artifacts?|summary|source))*|"
    r"(?:session_?start_?rejected|rejected_?session_?start)(?:_?(?:1_?0|10|planning|diagnostic|offline|candidate(?:_?only)?|accept(?:ed|ance)|readiness|report|status|evidence|artifacts?|summary|source|check_?join_?in_?progress))+|"
    r"(?:diagnostic|offline|candidate(?:_?only)?|planning)(?:_?(?:check_?join_?in_?progress|session_?start_?rejected|rejected_?session_?start)(?:_?(?:1_?0|10|planning|accept(?:ed|ance)|readiness|report|status|evidence|artifacts?|summary|source))?)+|"
    r"(?:session_?start(?:_?and)?_?end|start_?end)(?:_?only)?_?evidence|"
    r"activation_?preconditions?|"
    r"pre_?activation(?:_?(?:consistency|report|status|readiness|ready))?|"
    r"(?:runtime_?window_?|evidence_?|approved_?runtime_?)closure(?:_?(?:artifact|artifacts|bundle|bundles|request|requests|report|reports|output|outputs|summary|summaries|status|execution|executor))?|"
    r"closure_?(?:artifact|artifacts|bundle|bundles|request|requests|report|reports|output|outputs|summary|summaries|status|execution|executor)|"
    r"(?:runtime_?window_?)?(?:planner|executor)(?:_?(?:artifact|output|report|status))?|"
    r"beta_?notice(?:_?(?:prep|send|sent|attestation|confirmed))?|"
    r"(?:discord_?)?beta_?bridge(?:_?(?:bot_?)?notice|_?config|_?events?|_?plans?|_?reports?|_?status)?|"
    r"discord_?beta_?bot_?notice|discord_?bot_?notice|bot_?notice|"
    r"(?:multi_?surface_?)?beta_?capture(?:_?(?:candidates?|intake|plan|plans|queue|queues|readiness|report|reports|session|sessions|status|surface|surfaces))?|"
    r"multi_?surface_?beta_?packs?|"
    r"multi_?surface(?:_?beta)?(?:_?(?:capture|candidate|candidates|intake|plan|plans|queue|queues|surface|surfaces))(?:_?(?:capture|candidate|candidates|intake|plan|plans|queue|queues|readiness|report|reports|session|sessions|status))?|"
    r"(?:player_?principal|permissions?_?admin|admin|commands?|command_?chat_?response|commands_?replies|dino|dino_?policy|tribe|tribe_?policy|buff|buff_?status|inventory|transfer|mission)(?:_?surface)?_?beta_?capture(?:_?(?:candidate|candidates|plan|plans|queue|queues|readiness|report|reports|status))?|"
    r"request_?pack|"
    r"request_?check|"
    r"(?:approved_?)?(?:runtime_?)?bundle_?requests?|"
    r"public_?reachability|"
    r"(?:route_?bound_?)?identity_?source(?:_?(?:forward|forwarded|forwarding))?|"
    r"(?:offline_?)?hardening(?:_?(?:artifact|metadata|report|status|summary))?|"
    r"ready_?log_?evidence_?splits?(?:_?(?:diagnostic|evidence|readiness|ready|reports?|status|summary|summaries))?|"
    r"(?:player_?principal_?)?lifecycle_?event_?splits?(?:_?(?:diagnostic|evidence|readiness|ready|reports?|status|summary|summaries))?|"
    r"post_?runtime_?contract_?gap(?:_?(?:diagnostic|readiness|ready|reports?|status|summary|summaries))?|"
    r"route_?samples?(?:_?(?:diagnostic|evidence|readiness|ready|reports?|status|summary|summaries))?|"
    r"preflight(?:_?sidecar)?|"
    r"operator_?(?:approval_?)?receipts?|"
    r"(?:live_?)?(?:validation|ops)_?sidecars?|"
    r"players?_?notice_?actions?|"
    r"players?_?notices?|"
    r"confirmed_?(?:beta_?)?notice(?:_?(?:report|reports|sent|status|attestation|confirmation|confirmed))?|"
    r"notice_?reports?|"
    r"notice_?(?:actions?|dry_?runs?|bundles?|sent|accepted)|"
    r"discord_?notices?|"
    r"(?:discord_?)?beta_?bridge(?:_?(?:bot_?)?notice|_?config|_?events?|_?plans?|_?reports?|_?status)?|"
    r"discord_?beta_?bot_?notice|discord_?bot_?notice|bot_?notice|"
    r"runtime_?window(?:_?(?:activation|executor|execution|manifest|plan|planner|preflight|prepar(?:ed|ation)?|readiness|ready|request|status))?|"
    r"standing_?(?:launch_?)?authority|"
    r"(?:sdk_?)?status_?reports?|"
    r"(?:runtime_?evidence_?)?status_?reports?|"
    r"(?:source|sources|source_?readiness|status_?report)(?:_?(?:ready|readiness|state|status))?|"
    r"(?:principal_?)?start_?end_?contract_?inputs?|"
    r"(?:session_?start(?:_?and)?_?end|start_?end)(?:_?only)?_?contract_?inputs?|"
    r"install(?:ed)?_?runtime(?:_?(?:checks?|ok|ready|reports?|status))?|"
    r"runtime_?install(?:ed)?(?:_?(?:checks?|ok|ready|reports?|status))?|"
    r"(?:install|installed|package)_?(?:sdk_?)?(?:package|shape|check|evidence|layout|success|succeed(?:ed)?|install|installed)(?:_?(?:checks?|ok|ready|reports?|status|success|succeed(?:ed)?))?|"
    r"find_?package(?:_?(?:obelisk|sdk|components?|success|succeed(?:ed)?|found|ready|reports?|status))?|"
    r"cmake_?(?:package|config|components?)(?:_?(?:check|found|ready|reports?|status|success|succeed(?:ed)?))?|"
    r"component_?sdk(?:_?(?:check|found|ready|reports?|status|success|succeed(?:ed)?))?|"
    r"broadcasts?(?:_?(?:checks?|ok|reports?|sent|status|notices?))?|"
    r"rcon(?:_?(?:checks?|commands?|counts?|player_?counts?|ok|ready|reachable|reports?|service|status))?|"
    r"window_?manifests?|"
    r"window_?request_?checks?|"
    r"route_?planning(?:_?(?:reports?|readiness|snapshots?|status|simulations?))?|"
    r"planning_?route(?:_?(?:reports?|readiness|snapshots?|status|simulations?))?|"
    r"route_?(?:simulations?|lock_?simulations?|check_?readiness|readiness)|"
    r"post_?evidence_?identity_?locks?|"
    r"identity_?locks?|"
    r"(?:generated_?)?(?:promotion_?)?cert(?:ificate)?(?:_?(?:artifact|binding|build|builder|generation|metadata|output|report|status|summary))?|"
    r"(?:public_?debug|debug_?public)_?boundary(?:_?(?:fix|fixes|metadata|report|status|summary))?|"
    r"placeholder_?(?:runtime_?)?evidence|"
    r"public_identity"
    r")"
)
SECONDARY_REPORT_FORBIDDEN_COMPLETION_CLAIM_KEYS = (
    *INSTALLED_SDK_PACKAGE_SHAPE_FORBIDDEN_POSITIVE_CLAIM_KEYS,
    "complete_sdk_blockers_promoted_count",
    "complete_sdk_blockers_promoted_for_claim_count",
    "complete_sdk_blockers_promoted_for_claim_ratio",
    "claim_progress_contribution",
    "complete_sdk_claim_count",
    "complete_sdk_claim_progress_contribution",
    "complete_sdk_claim_progress_percent",
    "complete_sdk_claim_progress_ratio",
    "complete_sdk_allowed",
    "complete_sdk_progress_contribution",
    "complete_sdk_progress_percent",
    "complete_sdk_progress_ratio",
    "complete_sdk_completion_count",
    "counts_toward_p0_dependency_chain_claim",
    "p0_chain_promoted_count",
    "p0_chain_progress_ratio",
    "p0_chain_promoted_ratio",
    "p0_ready",
    "p0_dependency_ready",
    "p0_dependency_chain_accounted",
    "p0_dependency_chain_ready",
    "p0_accounting_counts_as_promoted_surface",
    "p0_dependency_chain_claim_progress_ratio",
    "p0_dependency_chain_claim_count",
    "p0_dependency_chain_progress_ratio",
    "p0_dependency_chain_claim_progress_contribution",
    "p0_dependency_chain_progress_contribution",
    "p0_dependency_chain_promoted_for_claim_count",
    "p0_dependency_chain_promoted_for_claim_ratio",
    "p0_dependency_chain_promoted_count",
    "activation_preconditions_met",
    "approved_runtime_evidence_ready",
    "approved_runtime_evidence_binding",
    "approved_runtime_evidence_binding_accepted",
    "approved_runtime_evidence_binding_acceptance",
    "approved_runtime_evidence_binding_present",
    "approved_runtime_evidence_binding_ready",
    "approved_runtime_evidence_binding_counts_as_approved_runtime_evidence",
    "start_end_evidence",
    "start_end_evidence_accepted",
    "start_end_evidence_acceptance",
    "start_end_evidence_ready",
    "start_end_only_evidence",
    "start_end_only_evidence_accepted",
    "start_end_only_evidence_acceptance",
    "start_end_only_evidence_ready",
    "session_start_end_evidence",
    "session_start_end_evidence_accepted",
    "session_start_end_evidence_acceptance",
    "session_start_end_evidence_ready",
    "session_start_and_end_evidence",
    "session_start_and_end_evidence_accepted",
    "session_start_and_end_evidence_acceptance",
    "session_start_and_end_evidence_ready",
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
    "standing_launch_authority",
    "standing_launch_authority_accepted",
    "standing_launch_authority_acceptance",
    "standing_launch_authority_ready",
    "standing_launch_authority_counts_as_approved_runtime_evidence",
    "standing_launch_authority_counts_as_runtime_evidence",
    "standing_launch_authority_counts_toward_sdk",
    "standing_launch_authority_counts_toward_p0_dependency_chain",
    "standing_launch_authority_counts_toward_complete_sdk_claim",
    "promoted_for_claim_ratio",
    "abi_ready",
    "abi_layout_accepted",
    "abi_layout_approved",
    "abi_layout_claim_allowed",
    "abi_layout_complete",
    "abi_layout_ready",
    "api_ready",
    "callback_ready",
    "capability_ready",
    "complete_sdk_claim_allowed",
    "approved_runtime_evidence_missing_cleared",
    "approved_runtime_evidence_missing_resolved",
    "clears_approved_runtime_evidence_missing",
    "resolves_approved_runtime_evidence_missing",
    "counts_toward_complete_sdk",
    "counts_toward_complete_sdk_claim",
    "counts_toward_sdk",
    "counts_toward_p0_dependency_chain",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    *NOTICE_OR_BUNDLE_NON_PROGRESS_FALSE_ALIAS_KEYS,
    *RECENT_NON_EVIDENCE_DIAGNOSTIC_POSITIVE_ALIAS_KEYS,
    "descriptor_ready",
    "dino_sdk_ready",
    "dispatcher_ready",
    "contract_review_artifact_ready",
    "contract_review_ready",
    "identity_contract_ready",
    "identity_public_contract_ready",
    "module_ready",
    "module_sdk_ready",
    "object_identity_allowed",
    "object_identity_available",
    "object_identity_public",
    "object_identity_ready",
    "object_lookup_allowed",
    "object_lookup_available",
    "object_lookup_public",
    "object_lookup_ready",
    "owner_token_identity_ready",
    "owner_token_lifecycle_ready",
    "owner_token_registration_ready",
    "owner_token_sdk_consumer_ready",
    "player_identity_allowed",
    "player_identity_available",
    "player_identity_public",
    "player_identity_ready",
    "player_principal_allowed",
    "player_principal_available",
    "player_principal_public",
    "player_principal_ready",
    "principal_handle_allowed",
    "principal_handle_available",
    "principal_handle_public",
    "principal_handle_ready",
    "pod_layout_accepted",
    "pod_layout_approved",
    "pod_layout_claim_allowed",
    "pod_layout_complete",
    "pod_layout_ready",
    "public_contract_allowed",
    "public_contract_artifact_ready",
    "public_contract_ready",
    "public_contract_review_ready",
    "public_api_ready",
    "public_callback_ready",
    "public_capability_ready",
    "public_descriptor_ready",
    "public_dino_sdk_ready",
    "public_mission_sdk_ready",
    "public_transfer_sdk_ready",
    "public_tribe_sdk_ready",
    "public_buff_sdk_ready",
    "public_buff_status_sdk_ready",
    "public_module_ready",
    "public_module_sdk_ready",
    "public_or_runtime_accounting_allowed",
    "support_ready",
    "sdk_ready",
    "production_grade",
    "production_grade_ready",
    "production_ready",
    "public_abi_ready",
    "public_abi_available",
    "rc_ready",
    "rc_readiness_ready",
    "release_candidate_ready",
    "release_candidate_readiness_ready",
    "release_grade",
    "release_grade_ready",
    "release_ready",
    "release_readiness_ready",
    "reviewed_public_contract",
    "reviewed_public_contract_ready",
    "resource_handle_allowed",
    "resource_handle_available",
    "resource_handle_public",
    "resource_handle_ready",
    "route_ready",
    "route_readiness_ready",
    "route_check_accepted",
    "route_check_acceptance",
    "route_gate_accepted",
    "route_gate_acceptance",
    "check_join_in_progress_planning_acceptance",
    "check_join_in_progress_1_0_planning_acceptance",
    "check_join_in_progress10_planning_acceptance",
    "checkjoininprogress_planning_acceptance",
    "checkjoininprogress_1_0_planning_acceptance",
    "checkjoininprogress10_planning_acceptance",
    "request_check_ready",
    "request_pack_ready",
    "approved_bundle_request_accepted",
    "approved_bundle_request_ready",
    "approved_runtime_bundle_request_accepted",
    "approved_runtime_bundle_request_ready",
    "public_reachability_counts_as_approved_runtime_evidence",
    "public_reachability_ready",
    "public_reachability_satisfies_runtime_evidence",
    "public_reachability_unlock_allowed",
    "route_bound_identity_source_forwarding_ready",
    "identity_source_forwarding_ready",
    "runtime_v1_ready",
    "runtime_readiness_allowed",
    "runtime_readiness_ready",
    "runtime_hook_ready",
    "runtime_hook_wiring_ready",
    "runtime_observer_approved",
    "runtime_validated",
    "runtime_validation_ready",
    "runtime_wiring_ready",
    "v1_completion_ready",
    "v1_complete",
    "v1_completion",
    "v1_release_ready",
    "stable_claim_allowed",
    "stable_sdk_claim_allowed",
    "stable_v1_sdk",
    "stable_ready",
    "plugin_hub_ready",
    "plugin_hub_readiness_allowed",
    "plugin_hub_readiness_claim_allowed",
    "plugin_hub_readiness_ready",
    "struct_size_accepted",
    "struct_size_approved",
    "struct_size_claim_allowed",
    "struct_size_complete",
    "struct_size_public_abi_ready",
    "struct_size_ready",
    "struct_size_validated",
    "struct_size_verified",
    "v1_stable_sdk",
    "v1_sdk_stable",
    "public_sdk_ready",
    "public_sdk_readiness_allowed",
    "public_sdk_readiness_ready",
    "promotion_ready",
    "runtime_ready",
    "runtime_work_authorized",
    "marker_env_changes_authorized",
    "publication_authorized",
    "discord_authorized_by_request",
    "discord_authorized_by_this_report",
    "p0_accounting_counts_as_promoted_surface",
    "sdk_accounting_counts_as_completed_surface",
    "sdk_completion_progress_percent",
    "sdk_completion_progress_ratio",
    "sdk_completion_count",
    "v1_completion_contribution",
    "v1_completion_count",
    "v1_completion_progress_percent",
    "v1_completion_progress_ratio",
    *SOURCE_READY_STATUS_ALIAS_KEYS,
    *RECENT_NON_EVIDENCE_DIAGNOSTIC_POSITIVE_ALIAS_KEYS,
)
SECONDARY_REPORT_SPLIT_CLAIM_DESCRIPTOR_KEYS = {
    "aliases",
    "claim",
    "claim_key",
    "claim_name",
    "claim_names",
    "claim_scope",
    "claims",
    "display_name",
    "display_names",
    "field",
    "field_name",
    "field_names",
    "fields",
    "heading",
    "headings",
    "label",
    "labels",
    "metric",
    "metric_name",
    "metric_names",
    "metrics",
    "name",
    "names",
    "readiness_key",
    "readiness_keys",
    "section",
    "section_name",
    "section_names",
    "sections",
    "subject",
    "subjects",
    "summary_name",
    "summary_names",
    "title",
    "titles",
}
SECONDARY_REPORT_SPLIT_CLAIM_STATUS_KEYS = {
    "allowed",
    "availability",
    "availabilities",
    "claim_value",
    "claim_values",
    "declared_support_tier",
    "declared_support_tiers",
    "enabled",
    "flag",
    "flags",
    "outcome",
    "outcomes",
    "publication",
    "publications",
    "readiness",
    "result",
    "results",
    "state",
    "states",
    "status",
    "statuses",
    "support_tier",
    "support_tiers",
    "tier",
    "tiers",
    "value",
    "values",
}
SECONDARY_REPORT_COMPLETION_PROGRESS_VALUE_KEYS = {
    "claim_count",
    "completion_count",
    "count",
    "counted",
    "progress",
    "progress_count",
    "progress_percent",
    "progress_ratio",
    "promoted_count",
    "promoted_for_claim_count",
    "ratio",
}
SECONDARY_REPORT_SPLIT_COMPLETION_DESCRIPTOR_RE = re.compile(
    r"\b(?:complete|full|stable|public|production(?: ready| grade)?|release grade)\s+"
    r"(?:sdk|api|support)\b|"
    r"\b(?:sdk|api|support)\s+v?1(?: 0)?\b|"
    r"\bv1(?: 0)?\s+(?:stable|sdk|api|support|completion)\b|"
    r"\b(?:public\s+(?:sdk|api|abi|header)|runtime\s+(?:readiness|ready|delivery|v1)|"
    r"stable\s+claim|v1\s+completion)\b|"
    r"\b(?:(?:installed|public|release|sdk)\s+)?sdk\s+package\b|"
    r"\b(?:installed|public|release)\s+package\b|"
    r"\b(?:plugin\s+hub|pluginhub)\b|"
    r"\bsupport\s+tier\b",
    re.IGNORECASE,
)
BROAD_RELEASE_SUPPORT_TIER_VALUE_KEYS = {
    "release_supported",
    "release_supported_seed",
}
SECONDARY_REPORT_STANDALONE_COMPLETION_STATUS_VALUE_KEYS = {
    "complete",
    "completed",
    "found",
    "full",
    "generated",
    "production_grade",
    "production_ready",
    "release_grade",
    "release_ready",
    "release_supported",
    "release_supported_seed",
    "stable",
    "stable_sdk",
    "success",
    "succeeded",
    "unblocked",
    "v1_completion",
    "v1_sdk_stable",
    "v1_stable_sdk",
}
SECONDARY_REPORT_STANDALONE_COMPLETION_CONTEXT_RE = re.compile(
    r"\b(?:complete|full|stable|public|production|release|sdk|api|support|"
    r"v1|route|runtime|plugin\s+hub|pluginhub)\b",
    re.IGNORECASE,
)
SECONDARY_REPORT_POSITIVE_COMPLETION_TEXT_RE = re.compile(
    r"\b(?:complete|full|stable|production(?:[-_ ]?(?:ready|grade))?)\s+"
    r"(?:sdk|api|support)\b.{0,80}"
    r"\b(?:allow(?:ed)?|available|complete(?:d)?|count(?:ed|s)?|enabled|progress|"
    r"promoted|public|ready|release(?:d)?|ship(?:ped|s)?|support(?:ed)?|"
    r"satisf(?:y|ies|ied)|unblocked|unlocked|[1-9][0-9]*(?:\.[0-9]+)?%?|[1-9][0-9]*\s*/\s*[1-9][0-9]*)\b|"
    r"\b(?:allow(?:ed)?|available|complete(?:d)?|count(?:ed|s)?|enabled|progress|"
    r"promoted|public|ready|release(?:d)?|ship(?:ped|s)?|support(?:ed)?|"
    r"satisf(?:y|ies|ied)|unblocked|unlocked|[1-9][0-9]*(?:\.[0-9]+)?%?|[1-9][0-9]*\s*/\s*[1-9][0-9]*)\b"
    r".{0,80}\b(?:complete|full|stable|production(?:[-_ ]?(?:ready|grade))?)\s+"
    r"(?:sdk|api|support)\b|"
    r"\bv1(?:\.0)?\s+(?:stable|completion|(?:sdk|api|support))\b.{0,80}"
    r"\b(?:allow(?:ed)?|available|complete(?:d)?|count(?:ed|s)?|enabled|progress|"
    r"promoted|public|ready|release(?:d)?|ship(?:ped|s)?|support(?:ed)?|"
    r"satisf(?:y|ies|ied)|unblocked|unlocked|[1-9][0-9]*(?:\.[0-9]+)?%?|[1-9][0-9]*\s*/\s*[1-9][0-9]*)\b|"
    r"\b(?:complete|full|stable|production(?:[-_ ]?(?:ready|grade))?)\s+"
    r"(?:sdk|api|support)\s+(?:claim\s+)?progress\b"
    r"|"
    r"\b(?:public\s+(?:sdk|api|abi|header|package|module\s+sdk(?:\s+coverage)?)|"
    r"(?:installed|release|sdk)\s+package|plugin\s+hub|pluginhub|support\s+tier|"
    r"runtime\s+(?:readiness|ready|delivery|v1)|route\s+(?:readiness|ready)|"
    r"public\s+route|(?:sdk|api|support)\s+v?1(?:\.?0)?|"
    r"v1(?:\.?0)?\s+(?:sdk|api|support))\b.{0,80}"
    r"\b(?:allow(?:ed)?|available|complete(?:d)?|count(?:ed|s)?|enabled|progress|"
    r"promoted|public|publish(?:ed)?|ready|release(?:d)?|ship(?:ped|s)?|"
    r"support(?:ed)?|satisf(?:y|ies|ied)|unblocked|unlocked|"
    r"[1-9][0-9]*(?:\.[0-9]+)?%?|[1-9][0-9]*\s*/\s*[1-9][0-9]*)\b|"
    r"\b(?:allow(?:ed)?|available|complete(?:d)?|count(?:ed|s)?|enabled|progress|"
    r"promoted|public|publish(?:ed)?|ready|release(?:d)?|ship(?:ped|s)?|"
    r"support(?:ed)?|satisf(?:y|ies|ied)|unblocked|unlocked|"
    r"[1-9][0-9]*(?:\.[0-9]+)?%?|[1-9][0-9]*\s*/\s*[1-9][0-9]*)\b"
    r".{0,80}\b(?:public\s+(?:sdk|api|abi|header|package|module\s+sdk(?:\s+coverage)?)|"
    r"(?:installed|release|sdk)\s+package|plugin\s+hub|pluginhub|support\s+tier|"
    r"runtime\s+(?:readiness|ready|delivery|v1)|route\s+(?:readiness|ready)|"
    r"public\s+route|(?:sdk|api|support)\s+v?1(?:\.?0)?|"
    r"v1(?:\.?0)?\s+(?:sdk|api|support))\b|"
    r"\b(?:package[-_ ]?shape|installed[-_ ]?(?:headers?|sdk[-_ ]?headers?))\b.{0,80}"
    r"\b(?:is|are|declares?|proves?|validates?|unlock(?:ed|s)?|satisf(?:y|ies)|enables?)\b.{0,80}"
    r"\b(?:v1(?:\.?0)?[-_ ]?support|support[-_ ]?tier|release[-_ ]?supported|sdk[-_ ]?support|"
    r"complete[-_ ]?(?:sdk|api)|stable[-_ ]?(?:sdk|api|support)|public[-_ ]?(?:sdk|api|support)|"
    r"production[-_ ]?ready[-_ ]?(?:sdk|api|support))\b|"
    r"\b(?:public[-_ ]+headers?|installed[-_ ]+headers?|obelisk[-_ ]*api(?:\.h|[-_ ]+h)?|"
    r"cmake[-_ ]+package|cmake[-_ ]+config|"
    r"obelisk[-_ ]*config(?:\.cmake|[-_ ]+cmake)?|obelisk[-_ ]*targets(?:\.cmake|[-_ ]+cmake)?|"
    r"installed[-_ ]+sdk[-_ ]+consumer[-_ ]+tests?|sdk[-_ ]+consumer[-_ ]+tests?)\b.{0,80}"
    r"\b(?:is|are|declares?|proves?|validates?|unlock(?:ed|s)?|satisf(?:y|ies)|enables?|counts?)\b.{0,80}"
    r"\b(?:runtime[-_ ]+readiness|public[-_ ]+sdk|public[-_ ]+abi|support[-_ ]+tier|"
    r"v1(?:\.?0)?[-_ ]?(?:completion|support)|complete[-_ ]+(?:sdk|api)|"
    r"stable[-_ ]+(?:sdk|api|support)|production[-_ ]?ready[-_ ]?(?:sdk|api|support))\b|"
    r"\b(?:runtime[-_ ]+readiness|public[-_ ]+sdk|public[-_ ]+abi|support[-_ ]+tier|"
    r"v1(?:\.?0)?[-_ ]?(?:completion|support)|complete[-_ ]+(?:sdk|api)|"
    r"stable[-_ ]+(?:sdk|api|support)|production[-_ ]?ready[-_ ]?(?:sdk|api|support))\b.{0,80}"
    r"\b(?:is|are|declares?|proves?|validates?|unlock(?:ed|s)?|satisf(?:y|ies)|enables?|counts?)\b.{0,80}"
    r"\b(?:public[-_ ]+headers?|installed[-_ ]+headers?|obelisk[-_ ]*api(?:\.h|[-_ ]+h)?|"
    r"cmake[-_ ]+package|cmake[-_ ]+config|"
    r"obelisk[-_ ]*config(?:\.cmake|[-_ ]+cmake)?|obelisk[-_ ]*targets(?:\.cmake|[-_ ]+cmake)?|"
    r"installed[-_ ]+sdk[-_ ]+consumer[-_ ]+tests?|sdk[-_ ]+consumer[-_ ]+tests?)\b|"
    r"\b(?:route[-_ ]?check|route[-_ ]?gate|command[-_ ]?permission[-_ ]?route(?:[-_ ]?(?:check|gate))?)\b.{0,80}"
    r"\b(?:accept(?:ed|ance)|pass(?:es|ed)?|green|satisf(?:y|ies|ied)|unlock(?:ed|s)?|"
    r"validates?|enables?)\b.{0,80}"
    r"\b(?:complete[-_ ]?(?:sdk|api)|full[-_ ]?(?:sdk|api)|production[-_ ]?ready[-_ ]?(?:sdk|api|support)|"
    r"stable[-_ ]?(?:sdk|api|support)|public[-_ ]?sdk|public[-_ ]?route|route[-_ ]?readiness|"
    r"sdk[-_ ]?completion|v1[-_ ]?completion|support|status)\b|"
    r"\b(?:scoped[-_ ]?non[-_ ]?complete(?:[-_ ]?outcomes?)?|"
    r"scoped[-_ ]?(?:v1[-_ ]?)?release[-_ ]?statements?|release[-_ ]?statement[-_ ]?bookkeeping)\b.{0,80}"
    r"\b(?:accept(?:ed|ance)|complete(?:d)?|ready|green|pass(?:es|ed)?|"
    r"satisf(?:y|ies|ied)|unlock(?:ed|s)?|counts?|counted|progress)\b",
    re.IGNORECASE,
)
SECONDARY_REPORT_POSITIVE_COMPLETION_TEXT_NEGATORS = re.compile(
    r"\b(?:blocked|cannot|can't|does\s+not|do\s+not|false|insufficient|must\s+not|"
    r"never|no|non[-_ ]?claim|non[-_ ]?promotional|not|planning[-_ ]?only|"
    r"bookkeeping[-_ ]?only|without)\b",
    re.IGNORECASE,
)
BROAD_CLAIM_TEXT_CLAUSE_SPLIT_RE = re.compile(
    r"[.;:\n\r]|(?:\s+\b(?:and|but|however|yet)\b\s+)",
    re.IGNORECASE,
)
BROAD_ROUTE_GATE_CLAIM_KEY_RE = re.compile(
    r"^(?:"
    r"(?:complete|full|stable|production(?:_ready|_grade)?)_(?:sdk|api|support)"
    r"(?:_(?:ready|allowed|supported|enabled|public))?|"
    r"(?:sdk|api|support)_(?:complete|full|stable|production(?:_ready|_grade)?)"
    r"(?:_(?:ready|allowed|supported|enabled|public))?|"
    r"public_api(?:_(?:ready|allowed|supported|enabled|public))?|"
    r"(?:public_)?route(?:_readiness)?_(?:ready|allowed|supported|enabled|public)"
    r")$"
)
ROUTE_GATE_OVERRIDE_TEST_ENV = "OBELISK_SDK_COMPLETION_ALLOW_ROUTE_GATE_OVERRIDE_FOR_TESTS"
SUBPROCESS_CACHE_DIR_TEST_ENV = "OBELISK_PUBLIC_SDK_V1_COMPLETION_SUBPROCESS_CACHE_DIR"
HELPER_SUBPROCESS_TIMEOUT_ENV = "OBELISK_PUBLIC_SDK_V1_COMPLETION_HELPER_TIMEOUT_SECONDS"
HELPER_SUBPROCESS_TIMEOUT_SECONDS = 60.0
SECONDARY_REPORT_COMPLETION_CLAIM_WITHOUT_BLOCKER = (
    "secondary_report_completion_claim_without_blocker"
)
POST_RUNTIME_P0_CHAIN_SHORTCUT_MARKER_RE = re.compile(
    r"(?:"
    r"(?:players?_identity_)?public_header_gate(?:_(?:proposal|check|readiness|report|status))?|"
    r"(?:players?_identity_)?public_contract(?:_(?:gap|readiness|review|decision_record|decision_record_template))(?:_(?:check|report|status|template))?|"
    r"(?:reviewed_)?identity_public_contract(?:_(?:gap|readiness|decision_record|gate|record|report|review|status|template))?|"
    r"(?:public_)?contract_gap(?:_(?:check|readiness|report|status))?|"
    r"(?:public_)?contract_readiness(?:_(?:check|report|status))?|"
    r"decision_record(?:_(?:draft|skeleton|template))?|"
    r"(?:reviewed_)?decision_record_template|"
    r"(?:offline_?)?hardening(?:_(?:artifact|metadata|report|status|summary))?|"
    r"(?:player_identity|permissions_admin|command_chat_response_path|commands_replies)?_?promotion_certificate"
    r"(?:_(?:build|builder|generation|metadata|report|template)(?:_report)?)?|"
    r"(?:player_identity|permissions_admin|command_chat_response_path|commands_replies)?_?"
    r"(?:generated_?)?(?:promotion_?)?cert(?:ificate)?"
    r"(?:_(?:artifact|binding|build|builder|generation|metadata|output|report|status|summary)(?:_report)?)?|"
    r"(?:multi_surface_)?beta_capture_pack(?:_(?:check|metadata|report|status))?|"
    r"multi_surface_beta_pack(?:_(?:check|metadata|report|status))?|"
    r"active_?notice(?:_?(?:action|accepted|ready|report|sent|status|updated?))?|"
    r"(?:installed_sdk_|sdk_)?package_shape(?:_(?:check|evidence|metadata|report|status))?|"
    r"package_shape_scoped_release_metadata|"
    r"structure_?build_?policy(?:_?offline_?intake)?(?:_(?:check|evidence|metadata|report|status))?|"
    r"(?:public_?debug|debug_?public)_?boundary(?:_?(?:fix|fixes|metadata|report|status|summary))?|"
    r"scoped_release(?:_(?:metadata|statement_metadata|package_metadata|report|status))?|"
    r"scoped_non_complete(?:_(?:metadata|release_statement_metadata|report|status))?|"
    r"(?:principal_)?start_end(?:_only)?(?:_evidence)?(?:_(?:artifact|bundle|check|manifest|report|status))?|"
    r"session_start_end(?:_only)?(?:_evidence)?(?:_(?:artifact|bundle|check|manifest|report|status))?|"
    r"(?:sdk_|runtime_evidence_|source_ready_)?status_report(?:_(?:ready|state|status))?|"
    r"status_report_only|"
    r"source_overclaim(?:_(?:component_count|diagnostic|diagnostics|report|summary|total|zero))?"
    r")",
    re.IGNORECASE,
)
SOURCE_OVERCLAIM_MARKER_KEYS = frozenset(
    (
        "source_overclaim_total",
        "source_overclaim_total_flag_count",
        "source_overclaim_component_count",
        "source_overclaim_count",
    )
)
POST_RUNTIME_P0_CHAIN_RUNTIME_FORBIDDEN_MARKERS = (
    ("public_header_gate", "public_header_gate_report_not_approved_runtime_evidence"),
    ("public_contract_gap", "public_contract_gap_report_not_approved_runtime_evidence"),
    ("public_contract_readiness", "public_contract_review_status_not_approved_runtime_evidence"),
    ("identity_public_contract", "public_contract_review_status_not_approved_runtime_evidence"),
    ("decision_record", "decision_record_template_not_approved_runtime_evidence"),
    ("offline_hardening", "offline_hardening_not_approved_runtime_evidence"),
    ("promotion_certificate", "promotion_certificate_not_approved_runtime_evidence"),
    ("generated_cert", "generated_cert_report_not_approved_runtime_evidence"),
    ("generated_certificate", "generated_cert_report_not_approved_runtime_evidence"),
    ("promotion_cert", "promotion_certificate_not_approved_runtime_evidence"),
    ("beta_capture_pack", MULTI_SURFACE_BETA_CAPTURE_CANDIDATE_QUEUE_NON_EVIDENCE_REASON),
    ("multi_surface_beta_pack", MULTI_SURFACE_BETA_CAPTURE_CANDIDATE_QUEUE_NON_EVIDENCE_REASON),
    ("active_notice", "active_notice_not_approved_runtime_evidence"),
    ("package_shape", "package_shape_not_approved_runtime_evidence"),
    ("structure_build_policy", "structure_build_policy_offline_intake_not_approved_runtime_evidence"),
    ("scoped_release", "scoped_release_metadata_not_approved_runtime_evidence"),
    ("scoped_non_complete", "scoped_release_metadata_not_approved_runtime_evidence"),
    ("public_debug_boundary", "public_debug_boundary_not_approved_runtime_evidence"),
    ("debug_public_boundary", "public_debug_boundary_not_approved_runtime_evidence"),
    ("start_end", "start_end_only_evidence_not_approved_runtime_evidence"),
    ("status_report", "status_report_not_approved_runtime_evidence"),
    ("source_overclaim", "source_overclaim_zero_not_approved_runtime_evidence"),
)
SIDE_LANE_COMPLETION_ACCOUNTING_FALSE_ALIAS_KEYS = {
    "approved_runtime_evidence",
    "approved_runtime_evidence_present",
    "approved_runtime_evidence_ready",
    "approved_runtime_evidence_binding",
    "approved_runtime_evidence_binding_accepted",
    "approved_runtime_evidence_binding_acceptance",
    "approved_runtime_evidence_binding_present",
    "approved_runtime_evidence_binding_ready",
    "approved_runtime_evidence_binding_counts_as_approved_runtime_evidence",
    "authorizes_runtime_work",
    "authorizes_server_work",
    "authorizes_server_operations",
    "authorizes_workspace_work",
    "authorizes_workspace_writes",
    "complete_sdk_allowed",
    "complete_sdk_claim_allowed",
    "complete_sdk_ready",
    "approved_runtime_evidence_missing_cleared",
    "approved_runtime_evidence_missing_resolved",
    "blocker_cleared",
    "blocker_resolved",
    "clears_approved_runtime_evidence_missing",
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
    "resolves_approved_runtime_evidence_missing",
    *RECENT_NON_EVIDENCE_DIAGNOSTIC_POSITIVE_ALIAS_KEYS,
    "activation_preconditions_met",
    "counts_as_approved_runtime_evidence",
    "counts_as_passive_evidence",
    "counts_as_passive_snapshot_evidence",
    "counts_as_runtime_evidence",
    "counts_as_sdk_evidence",
    "counts_toward_complete_sdk",
    "counts_toward_complete_sdk_claim",
    "counts_toward_sdk",
    "counts_toward_p0_dependency_chain",
    "counts_toward_complete_sdk_claim_now",
    "counts_toward_p0_dependency_chain_claim_now",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_p0_dependency_chain_claim",
    "counts_toward_v1_completion",
    "public_or_runtime_accounting_allowed",
    "readiness_counts_toward_v1_accounting",
    *NOTICE_OR_BUNDLE_NON_PROGRESS_FALSE_ALIAS_KEYS,
    "live_ops_authorized",
    "marker_env_changes_authorized",
    "p0_dependency_chain_accounted",
    "p0_accounting_counts_as_promoted_surface",
    "sdk_accounting_counts_as_completed_surface",
    "p0_dependency_chain_ready",
    "p0_dependency_ready",
    "p0_ready",
    "passive_snapshot_evidence_allowed",
    "passive_snapshot_counts_as_evidence",
    "passive_snapshot_counts_as_runtime_evidence",
    "passive_snapshot_counts_as_sdk_evidence",
    "read_live_logs",
    "reads_live_logs",
    "runtime_capture_authorized",
    "runtime_work_authorized",
    "runtime_evidence_present",
    "runtime_evidence_ready",
    "start_end_evidence",
    "start_end_evidence_accepted",
    "start_end_evidence_acceptance",
    "start_end_evidence_ready",
    "start_end_only_evidence",
    "start_end_only_evidence_accepted",
    "start_end_only_evidence_acceptance",
    "start_end_only_evidence_ready",
    "session_start_end_evidence",
    "session_start_end_evidence_accepted",
    "session_start_end_evidence_acceptance",
    "session_start_end_evidence_ready",
    "session_start_and_end_evidence",
    "session_start_and_end_evidence_accepted",
    "session_start_and_end_evidence_acceptance",
    "session_start_and_end_evidence_ready",
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
    "standing_launch_authority",
    "standing_launch_authority_accepted",
    "standing_launch_authority_acceptance",
    "standing_launch_authority_ready",
    "sdk_evidence_ready",
    "standing_launch_authority_counts_as_approved_runtime_evidence",
    "standing_launch_authority_counts_as_runtime_evidence",
    "standing_launch_authority_counts_toward_sdk",
    "standing_launch_authority_counts_toward_p0_dependency_chain",
    "standing_launch_authority_counts_toward_complete_sdk_claim",
    "server_operations_authorized",
    "stable_claim_allowed",
    "stable_sdk_claim_allowed",
    "stable_sdk_ready",
    "abi_layout_ready",
    "abi_layout_validated",
    "cmake_config_ready",
    "cmake_targets_ready",
    "components_sdk_ready",
    "installed_headers_ready",
    "module_ready",
    "module_sdk_ready",
    "obelisk_config_cmake_ready",
    "obelisk_targets_cmake_ready",
    "owner_token_registration_ready",
    "owner_token_sdk_consumer_ready",
    "package_shape_ready",
    "package_shape_v1_completion_ready",
    "package_shape_counts_toward_completion",
    "package_shape_counts_toward_public_sdk",
    "package_shape_counts_toward_v1_completion",
    "plugin_hub_package_published",
    "plugin_hub_counts_toward_completion",
    "plugin_hub_counts_toward_public_sdk",
    "plugin_hub_counts_toward_v1_completion",
    "plugin_hub_ready",
    "plugin_hub_readiness_allowed",
    "plugin_hub_readiness_claim_allowed",
    "plugin_hub_readiness_ready",
    "plugin_hub_seed_ready",
    "plugin_hub_support_tier_ready",
    "public_abi_available",
    "public_header_allowed",
    "public_header_available",
    "public_headers_available",
    "public_module_ready",
    "public_module_sdk_ready",
    "public_module_sdk_coverage_ready",
    "public_module_sdk_covered",
    "public_sdk_coverage_ready",
    "public_sdk_readiness_allowed",
    "public_sdk_readiness_ready",
    "release_statement_ready",
    "release_statement_bookkeeping_counts_toward_completion",
    "release_statement_counts_toward_completion",
    "release_statement_outcomes_satisfy_completion",
    "runtime_live_op_approval_allowed",
    "runtime_readiness_claim_allowed",
    "runtime_readiness_allowed",
    "runtime_readiness_ready",
    "scoped_release_statement_counts_toward_complete_sdk_claim",
    "scoped_release_statement_counts_toward_completion",
    "scoped_release_statement_outcomes_satisfy_completion",
    "scoped_release_statement_ready",
    "sdk_coverage_complete",
    "struct_size_ready",
    "struct_size_validated",
    "support_tier_activated",
    "support_tier_allowed",
    "support_tier_supported",
    "v1_complete",
    "v1_completion_claim_allowed",
    "v1_completion",
    "v1_completion_evidence",
    "v1_completion_ready",
    "v1_release_ready",
    "v1_ready",
    "workspace_writes_authorized",
    "discord_authorized_by_request",
    "discord_authorized_by_this_report",
    "publication_authorized",
    "request_pack_ready",
    "route_ready",
    "side_lane_promoted",
    "structure_build_policy_ready",
    "active_notice_ready",
    "active_notice_sent",
    "active_notice_accepted",
    "active_notice_updated",
    "active_notice_counts_toward_sdk",
    "active_notice_counts_toward_p0_dependency_chain",
    "active_notice_counts_toward_complete_sdk_claim",
    "check_join_in_progress_planning_acceptance",
    "check_join_in_progress_1_0_planning_acceptance",
    "check_join_in_progress10_planning_acceptance",
    "checkjoininprogress_planning_acceptance",
    "checkjoininprogress_1_0_planning_acceptance",
    "checkjoininprogress10_planning_acceptance",
    "approved_bundle_request_accepted",
    "approved_bundle_request_ready",
    "approved_runtime_bundle_request_accepted",
    "approved_runtime_bundle_request_ready",
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
}
SIDE_LANE_COMPLETION_ACCOUNTING_ZERO_ALIAS_KEYS = {
    "claim_progress_contribution",
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
    "complete_sdk_blockers_promoted_for_claim_count",
    "complete_sdk_blockers_promoted_for_claim_ratio",
    "p0_dependency_chain_claim_progress_contribution",
    "p0_dependency_chain_claim_progress_percent",
    "p0_dependency_chain_claim_progress_ratio",
    "p0_dependency_chain_credit",
    "p0_dependency_chain_credits",
    "p0_dependency_chain_promoted_for_claim_count",
    "p0_dependency_chain_promoted_for_claim_ratio",
    "p0_dependency_chain_progress_contribution",
    "p0_dependency_chain_progress_percent",
    "p0_dependency_chain_progress_ratio",
    "p0_chain_promoted_count",
    "p0_chain_promoted_ratio",
    "p0_dependency_progress_contribution",
    "p0_credit",
    "p0_credits",
    "promoted_count",
    "promoted_for_claim_count",
    "promoted_for_claim_ratio",
    "progress",
    "public_sdk_progress_contribution",
    "release_statement_complete_sdk_progress_contribution",
    "runtime_progress_contribution",
    "sdk_credit",
    "sdk_credits",
    "sdk_completion_credit",
    "sdk_completion_credits",
    "scoped_release_statement_claim_progress_contribution",
    "scoped_release_statement_complete_sdk_progress_contribution",
    *SOURCE_OVERCLAIM_MARKER_KEYS,
    "v1_completion_contribution",
    "v1_completion_credit",
    "v1_completion_credits",
}
ACTIONABLE_PATH_NON_AUTHORIZING_FALSE_KEYS = (
    "approved_runtime_evidence",
    "approved_runtime_evidence_present",
    "approved_runtime_evidence_ready",
    "approved_runtime_evidence_binding",
    "approved_runtime_evidence_binding_accepted",
    "approved_runtime_evidence_binding_acceptance",
    "approved_runtime_evidence_binding_present",
    "approved_runtime_evidence_binding_ready",
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
    "runtime_capture_authorized",
    "reads_live_logs",
    "read_live_logs",
    "authorizes_discord",
    "discord_authorized",
    "discord_authorized_by_request",
    "discord_authorized_by_this_report",
    "discord_notice_authorized",
    "publication_authorized",
    "notice_action_authorized",
    "player_notice_action_authorized",
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
    "counts_toward_complete_sdk_claim_now",
    "counts_toward_p0_dependency_chain_claim_now",
    "public_or_runtime_accounting_allowed",
    "passive_snapshot_evidence_allowed",
    "passive_snapshot_counts_as_evidence",
    "passive_snapshot_counts_as_runtime_evidence",
    "passive_snapshot_counts_as_sdk_evidence",
    "runtime_evidence_present",
    "runtime_evidence_ready",
    "start_end_evidence",
    "start_end_evidence_accepted",
    "start_end_evidence_acceptance",
    "start_end_evidence_ready",
    "start_end_only_evidence",
    "start_end_only_evidence_accepted",
    "start_end_only_evidence_acceptance",
    "start_end_only_evidence_ready",
    "session_start_end_evidence",
    "session_start_end_evidence_accepted",
    "session_start_end_evidence_acceptance",
    "session_start_end_evidence_ready",
    "session_start_and_end_evidence",
    "session_start_and_end_evidence_accepted",
    "session_start_and_end_evidence_acceptance",
    "session_start_and_end_evidence_ready",
    "sdk_evidence_ready",
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
    "standing_launch_authority",
    "standing_launch_authority_accepted",
    "standing_launch_authority_acceptance",
    "standing_launch_authority_ready",
    "standing_launch_authority_counts_as_approved_runtime_evidence",
    "standing_launch_authority_counts_as_runtime_evidence",
    "standing_launch_authority_counts_toward_sdk",
    "standing_launch_authority_counts_toward_p0_dependency_chain",
    "standing_launch_authority_counts_toward_complete_sdk_claim",
    "ready",
    "complete_sdk_allowed",
    "complete_sdk_claim_allowed",
    "complete_sdk_ready",
    "approved_runtime_evidence_missing_cleared",
    "approved_runtime_evidence_missing_resolved",
    "clears_approved_runtime_evidence_missing",
    "resolves_approved_runtime_evidence_missing",
    "activation_preconditions_met",
    "promotion_ready",
    "request_pack_ready",
    "route_ready",
    "check_join_in_progress_planning_acceptance",
    "check_join_in_progress_1_0_planning_acceptance",
    "check_join_in_progress10_planning_acceptance",
    "checkjoininprogress_planning_acceptance",
    "checkjoininprogress_1_0_planning_acceptance",
    "checkjoininprogress10_planning_acceptance",
    "public_sdk_ready",
    "public_sdk_readiness_allowed",
    "public_sdk_readiness_ready",
    "public_abi_ready",
    "public_header_allowed",
    "runtime_ready",
    "runtime_readiness_allowed",
    "runtime_readiness_ready",
    "plugin_hub_ready",
    "plugin_hub_readiness_allowed",
    "plugin_hub_readiness_claim_allowed",
    "plugin_hub_readiness_ready",
    "stable_claim_allowed",
    "stable_sdk_claim_allowed",
    "stable_sdk_ready",
    "v1_completion",
    "v1_completion_ready",
    *NOTICE_OR_BUNDLE_NON_PROGRESS_FALSE_ALIAS_KEYS,
    "approved_bundle_request_accepted",
    "approved_bundle_request_ready",
    "approved_runtime_bundle_request_accepted",
    "approved_runtime_bundle_request_ready",
    "public_reachability_counts_as_approved_runtime_evidence",
    "public_reachability_ready",
    "public_reachability_satisfies_runtime_evidence",
    "public_reachability_unlock_allowed",
    "route_bound_identity_source_forwarding_ready",
    "identity_source_forwarding_ready",
)
ACTIONABLE_PATH_ZERO_KEYS = (
    "claim_progress_contribution",
    "complete_sdk_claim_progress_contribution",
    "complete_sdk_progress_contribution",
    "p0_dependency_chain_claim_progress_contribution",
    "p0_dependency_chain_progress_contribution",
    "p0_dependency_progress_contribution",
    "public_sdk_progress_contribution",
    "runtime_progress_contribution",
    "v1_completion_contribution",
    "progress",
)
NON_COUNTING_COMPLETION_CONTEXT_RE = re.compile(
    r"(?:"
    r"(?:player_?)?notice(?:_?(?:action|bundle|dry_run|sent|accepted))?|"
    r"active_?notice(?:_?(?:action|accepted|ready|report|sent|status|updated?))?|"
    r"confirmed_?(?:beta_?)?notice(?:_?(?:report|reports|sent|status|attestation|confirmation|confirmed))?|"
    r"beta_?notice(?:_?(?:prep|send|sent|attestation|confirmed))?|"
    r"discord_?notice|"
    r"(?:discord_?)?beta_?bridge(?:_?(?:bot_?)?notice|_?config|_?events?|_?plans?|_?reports?|_?status)?|"
    r"discord_?beta_?bot_?notice|discord_?bot_?notice|bot_?notice|"
    r"passive(?:_?(?:snapshot|observation|activity|latest|capture|triplet))?|"
    r"passive_?monitors?|"
    r"diagnostic(?:_?(?:only|summary|triage|observer))?|"
    r"(?:player_?principal_?)?lifecycle_?(?:event|events|role|roles|triplet|proof|"
    r"artifact|evidence|observer|status|report|summary|partial|candidate|diagnostic|observed)(?:_?(?:artifact|evidence|proof|ready|status|summary|observed))*|"
    r"(?:partial_?)?(?:role|event)_?triplet(?:_?(?:artifact|evidence|proof|ready|status|summary))?|"
    r"(?:partial_?)?lifecycle_?(?:event|role)s?(?:_?(?:artifact|evidence|proof|ready|status|summary|observed))?|"
    r"ready_?log_?evidence_?splits?(?:_?(?:diagnostic|evidence|readiness|ready|report|status|summary))?|"
    r"(?:player_?principal_?)?lifecycle_?event_?splits?(?:_?(?:diagnostic|evidence|readiness|ready|report|status|summary))?|"
    r"post_?runtime_?contract_?gap(?:_?(?:diagnostic|readiness|ready|report|status|summary))?|"
    r"route_?samples?(?:_?(?:diagnostic|evidence|readiness|ready|report|status|summary))?|"
    r"(?:session_?start|session_?end|handle_?new_?player|on_?logout)(?:_?(?:observed|proof|ready|status|artifact|evidence))?|"
    r"(?:session_?start(?:_?and)?_?end|start_?end)(?:_?only)?_?evidence|"
    r"(?:principal_?)?start_?end_?contract_?inputs?|"
    r"(?:session_?start(?:_?and)?_?end|start_?end)(?:_?only)?_?contract_?inputs?|"
    r"check_?join_?in_?progress(?:_?(?:1_?0|10|planning|diagnostic|offline|candidate(?:_?only)?|accept(?:ed|ance)|readiness|report|status|evidence|artifacts?|summary|source))*|"
    r"(?:session_?start_?rejected|rejected_?session_?start)(?:_?(?:1_?0|10|planning|diagnostic|offline|candidate(?:_?only)?|accept(?:ed|ance)|readiness|report|status|evidence|artifacts?|summary|source|check_?join_?in_?progress))+|"
    r"(?:diagnostic|offline|candidate(?:_?only)?|planning)(?:_?(?:check_?join_?in_?progress|session_?start_?rejected|rejected_?session_?start)(?:_?(?:1_?0|10|planning|accept(?:ed|ance)|readiness|report|status|evidence|artifacts?|summary|source))?)+|"
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
    r"(?:multi_?surface_?)?beta_?capture(?:_?(?:candidates?|intake|plan|plans|queue|queues|readiness|report|reports|session|sessions|status|surface|surfaces))?|"
    r"multi_?surface_?beta_?packs?|"
    r"multi_?surface(?:_?beta)?(?:_?(?:capture|candidate|candidates|intake|plan|plans|queue|queues|surface|surfaces))(?:_?(?:capture|candidate|candidates|intake|plan|plans|queue|queues|readiness|report|reports|session|sessions|status))?|"
    r"(?:player_?principal|permissions?_?admin|admin|commands?|command_?chat_?response|commands_?replies|dino|dino_?policy|tribe|tribe_?policy|buff|buff_?status|inventory|transfer|mission)(?:_?surface)?_?beta_?capture(?:_?(?:candidate|candidates|plan|plans|queue|queues|readiness|report|reports|status))?|"
    r"request_?(?:pack|check|artifact|preflight|readiness)|"
    r"(?:fastest_?)?next_?sdk_?unblock(?:_?(?:summary|report))?|"
    r"action(?:able)?_?paths?|action_?path(?:_?(?:candidate|summary|report|status))?|"
    r"(?:approved_?)?(?:runtime_?)?bundle_?requests?|"
    r"approved_?runtime_?evidence_?binding(?:_?(?:accept(?:ed|ance)|present|readiness|ready|report|status|source))?|"
    r"approved_?runtime_?manifests?|"
    r"accepted_?artifact_?class(?:_?(?:artifact|artifacts|metadata|report|reports|status))?|"
    r"binding_?required(?:_?(?:artifact|artifacts|metadata|report|reports|status))?|"
    r"public_?reachability(?:_?(?:check|ready|report))?|"
    r"(?:reviewed_?)?(?:identity_?)?public_?contract(?:_?(?:artifact|decision|decisions|input|readiness|ready|record|records|report|review))?|"
    r"contract_?review(?:_?(?:artifact|decision|decisions|input|readiness|ready|record|records|report))?|"
    r"(?:offline_?)?hardening(?:_?(?:artifact|metadata|report|status|summary))?|"
    r"(?:route_?bound_?)?identity_?source(?:_?(?:forward|forwarded|forwarding|readiness|report))?|"
    r"window_?request_?check|"
    r"player_?principal_?lifecycle_?window_?request|"
    r"runtime_?window(?:_?(?:activation|executor|execution|manifest|plan|planner|preflight|prepar(?:ed|ation)?|readiness|ready|request|status))?|"
    r"standing_?(?:launch_?)?authority|"
    r"install(?:ed)?_?runtime(?:_?(?:checks?|ok|ready|reports?|status))?|"
    r"runtime_?install(?:ed)?(?:_?(?:checks?|ok|ready|reports?|status))?|"
    r"(?:install|installed|package)_?(?:sdk_?)?(?:package|shape|check|evidence|layout|success|succeed(?:ed)?|install|installed)(?:_?(?:checks?|ok|ready|reports?|status|success|succeed(?:ed)?))?|"
    r"find_?package(?:_?(?:obelisk|sdk|components?|success|succeed(?:ed)?|found|ready|reports?|status))?|"
    r"cmake_?(?:package|config|components?)(?:_?(?:check|found|ready|reports?|status|success|succeed(?:ed)?))?|"
    r"component_?sdk(?:_?(?:check|found|ready|reports?|status|success|succeed(?:ed)?))?|"
    r"broadcasts?(?:_?(?:checks?|ok|reports?|sent|status|notices?))?|"
    r"rcon(?:_?(?:checks?|commands?|counts?|player_?counts?|ok|ready|reachable|reports?|service|status))?|"
    r"(?:public_?|installed_?)?headers?|"
    r"(?:public_?)?obelisk_?api_?headers?|"
    r"obeliskapi|obelisk_?api_?h|"
    r"cmake_?(?:package|config)|"
    r"obelisk_?config(?:_?cmake)?|obelisk_?targets(?:_?cmake)?|"
    r"components?_?sdk|"
    r"(?:installed_?)?sdk_?consumer_?tests?|"
    r"(?:installed_?)?sdk_?consumer_?guardrails?|"
    r"(?:public_?)?abi_?consumer_?guardrails?|"
    r"(?:post_?init|after_?init|outside_?init)_?call_?process_?event(?:_?(?:guardrails?|tests?|skipped|rejected|passed|status|reports?))?|"
    r"call_?process_?event_?(?:post_?init|after_?init|outside_?init)(?:_?(?:guardrails?|tests?|skipped|rejected|passed|status|reports?))?|"
    r"tests_?sdk_?(?:installed_?)?consumer|"
    r"(?:installed_?)?sdk_?package_?shape|"
    r"(?:sdk_?)?package_?(?:exact|non_?exact)(?:_?(?:check|evidence|install|report|status))?|"
    r"(?:generated_?)?(?:promotion_?)?cert(?:ificate)?(?:_?(?:artifact|binding|build|builder|generation|metadata|output|report|status|summary))?|"
    r"(?:public_?debug|debug_?public)_?boundary(?:_?(?:fix|fixes|metadata|report|status|summary))?|"
    r"package_?shape|"
    r"plugin_?hub(?:_?(?:wording|seed|package|support|publication|readiness))?|"
    r"support_?tier|"
    r"scoped_?non_?complete(?:_?only)?|"
    r"scoped_?(?:non_?complete_?)?(?:v1_?)?release_?statements?|"
    r"release_?statement(?:_?bookkeeping)?|"
    r"route_?planning(?:_?(?:report|readiness|snapshot|status|simulation))?|"
    r"planning_?route(?:_?(?:report|readiness|snapshot|status|simulation))?|"
    r"route_?(?:simulation|lock_?simulation|check_?readiness|readiness|snapshot|snapshots|snapshot_?report|status_?snapshot)|"
    r"status_?(?:snapshot|artifact|report)|"
    r"(?:sdk_?)?status_?reports?|"
    r"(?:runtime_?evidence_?)?status_?reports?|"
    r"copied_?logs?_?only(?:_?(?:artifact|artifacts|report|reports|status))?|"
    r"post_?evidence_?identity_?lock|"
    r"identity_?lock(?:_?(?:simulation|readiness|report))?|"
    r"transfer_?(?:script_?struct|baccept)_?readiness|"
    r"buff_?status_?readiness|"
    r"dino_?scalar_?readiness|"
    r"tribe_?scalar_?boundary_?readiness|"
    r"scalar_?boundary_?readiness|"
    r"mission_?transfer_?dino_?tribe(?:_?buff)?_?accounting|"
    r"structure_?build_?policy(?:_?offline_?intake)?(?:_?(?:check|evidence|metadata|report|status))?|"
    r"side_?lane|"
    r"(?:route_?gate_?)?post_?evidence_?p0_?lock_?simulation|"
    r"simulation_?only"
    r")",
    re.IGNORECASE,
)
NON_COUNTING_COMPLETION_READINESS_ALIAS_KEYS = {
    "candidate_ready",
    "accepted_for_contract_review",
    "activation_preconditions_met",
    "activation_ready",
    "abi_layout_ready",
    "abi_layout_validated",
    "abi_consumer_guardrail_passed",
    "abi_consumer_guardrails_passed",
    "call_process_event_post_init_guardrail_passed",
    "call_process_event_post_init_rejected",
    "call_process_event_post_init_skipped",
    "call_process_event_post_init_test_passed",
    "approved_runtime_evidence_binding",
    "approved_runtime_evidence_binding_accepted",
    "approved_runtime_evidence_binding_acceptance",
    "approved_runtime_evidence_binding_present",
    "approved_runtime_evidence_binding_ready",
    "approved_runtime_manifest_present",
    "approved_runtime_manifest_referenced",
    "cmake_config_ready",
    "cmake_package_found",
    "cmake_package_succeeded",
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
    "component_sdk_found",
    "component_sdk_succeeded",
    "components_sdk_ready",
    "confirmed",
    "confirmed_send",
    *RECENT_NON_EVIDENCE_DIAGNOSTIC_POSITIVE_ALIAS_KEYS,
    "counts_as_approved_runtime_evidence",
    "counts_as_passive_evidence",
    "counts_as_passive_snapshot_evidence",
    "counts_as_runtime_evidence",
    "counts_as_sdk_evidence",
    "approved_runtime_evidence_missing_cleared",
    "approved_runtime_evidence_missing_resolved",
    "blocker_cleared",
    "blocker_resolved",
    "clears_approved_runtime_evidence_missing",
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
    "resolves_approved_runtime_evidence_missing",
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
    "find_package_found",
    "find_package_succeeded",
    "installed_headers_ready",
    "installed_sdk_consumer_tests_ready",
    "installed_sdk_consumer_tests_v1_completion_ready",
    "installed_sdk_package_ready",
    "installed_sdk_release_ready",
    "obelisk_config_cmake_ready",
    "obelisk_targets_cmake_ready",
    "owner_token_registration_ready",
    "owner_token_sdk_consumer_ready",
    "outcome",
    "package_available",
    "package_check_passed",
    "package_check_succeeded",
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
    "passive_triplet_ready",
    "passive_snapshot_counts_as_evidence",
    "passive_snapshot_counts_as_runtime_evidence",
    "passive_snapshot_counts_as_sdk_evidence",
    "preconditions_met",
    "precondition_ready",
    "post_init_call_process_event_guardrail_passed",
    "post_init_call_process_event_rejected",
    "post_init_call_process_event_skipped",
    "post_init_call_process_event_test_passed",
    "start_end_evidence",
    "start_end_evidence_accepted",
    "start_end_evidence_acceptance",
    "start_end_evidence_ready",
    "start_end_only_evidence",
    "start_end_only_evidence_accepted",
    "start_end_only_evidence_acceptance",
    "start_end_only_evidence_ready",
    "session_start_end_evidence",
    "session_start_end_evidence_accepted",
    "session_start_end_evidence_acceptance",
    "session_start_end_evidence_ready",
    "session_start_and_end_evidence",
    "session_start_and_end_evidence_accepted",
    "session_start_and_end_evidence_acceptance",
    "session_start_and_end_evidence_ready",
    "runtime_window_activation_ready_under_recorded_standing_launch_authority",
    "runtime_window_closure_accepted",
    "runtime_window_closure_complete",
    "runtime_window_closure_ready",
    "runtime_window_preparation_ready",
    "runtime_window_prepared",
    "runtime_window_ready",
    "runtime_readiness_allowed",
    "runtime_readiness_ready",
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
    "module_ready",
    "module_sdk_ready",
    "public_module_ready",
    "public_module_sdk_ready",
    "public_module_sdk_coverage_claim_allowed",
    "public_module_sdk_coverage_ready",
    "public_module_sdk_covered",
    "public_package_available",
    "public_package_published",
    "public_package_ready",
    "public_sdk_coverage_ready",
    "public_sdk_readiness_allowed",
    "public_sdk_readiness_ready",
    "readiness_ready",
    "ready",
    "reviewed_public_contract",
    "reviewed_public_contract_ready",
    "release_statement_ready",
    "release_package_allowed",
    "release_package_available",
    "release_package_published",
    "release_package_ready",
    "release_packaged",
    "release_statement_bookkeeping_counts_toward_completion",
    "release_statement_counts_toward_completion",
    "release_statement_outcomes_satisfy_completion",
    "release_supported",
    "release_supported_seed",
    "request_check_ready",
    "request_pack_ready",
    "approved_bundle_request_ready",
    "approved_runtime_bundle_request_ready",
    "active_notice_ready",
    "active_notice_sent",
    "active_notice_accepted",
    "active_notice_updated",
    "active_notice_counts_toward_sdk",
    "active_notice_counts_toward_p0_dependency_chain",
    "active_notice_counts_toward_complete_sdk_claim",
    "check_join_in_progress_planning_acceptance",
    "check_join_in_progress_1_0_planning_acceptance",
    "check_join_in_progress10_planning_acceptance",
    "checkjoininprogress_planning_acceptance",
    "checkjoininprogress_1_0_planning_acceptance",
    "checkjoininprogress10_planning_acceptance",
    "public_reachability_ready",
    "public_reachability_counts_as_evidence",
    "public_reachability_counts_as_runtime_evidence",
    "public_reachability_counts_as_sdk_evidence",
    "public_reachability_counts_toward_runtime_evidence",
    "public_reachability_counts_toward_sdk_evidence",
    "route_bound_identity_source_forwarding_ready",
    "identity_source_forwarding_ready",
    "result",
    "route_ready",
    "side_lane_promoted",
    "structure_build_policy_ready",
    "sdk_consumer_guardrail_passed",
    "sdk_consumer_guardrails_passed",
    "sdk_package_available",
    "sdk_package_published",
    "sdk_package_ready",
    "source_binding_ready",
    *SOURCE_READY_STATUS_ALIAS_KEYS,
    "state",
    "status",
    "struct_size_ready",
    "struct_size_validated",
    "support_tier",
    "support_tier_activated",
    "support_tier_ready",
    "support_tier_activation_ready",
    "support_tier_activation_allowed",
    "support_tier_allowed",
    "support_tier_supported",
    "support_tiers",
    "send_performed",
    "scoped_release_statement_counts_toward_complete_sdk_claim",
    "scoped_release_statement_counts_toward_completion",
    "scoped_release_statement_outcomes_satisfy_completion",
    "scoped_release_statement_ready",
    "sdk_coverage_complete",
    "standing_authority",
    "standing_authority_accepted",
    "standing_authority_acceptance",
    "standing_authority_ready",
    "standing_launch_authority",
    "standing_launch_authority_accepted",
    "standing_launch_authority_acceptance",
    "standing_launch_authority_ready",
    "stable_sdk_ready",
    "stable_sdk_claim_allowed",
    "tier",
    "tiers",
}
NON_COUNTING_COMPLETION_READINESS_ALIAS_SUFFIXES = (
    "_allowed",
    "_accepted",
    "_acceptance",
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
    "_performed",
    "_reachable",
    "_rejected",
    "_readiness",
    "_ready",
    "_result",
    "_resolved",
    "_satisfied",
    "_state",
    "_status",
    "_skipped",
    "_supported",
    "_success",
    "_succeeded",
    "_found",
    "_unblocked",
    "_unlocked",
    "_validated",
)
NON_COUNTING_COMPLETION_READINESS_ALIAS_EXEMPT_KEYS = {
    "review_status",
}
NON_COUNTING_COMPLETION_PROGRESS_ALIAS_SUFFIXES = (
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
NON_COUNTING_COMPLETION_POSITIVE_STATUS_VALUES = NOTICE_OR_BUNDLE_POSITIVE_STATUS_VALUES | {
    "allowed",
    "activated",
    "available",
    "built",
    "candidate_only_accepted",
    "candidate_ready",
    "closed",
    "complete",
    "completed",
    "complete_triplet",
    "complete_triplet_present",
    "covered",
    "counted",
    "counts",
    "enabled",
    "green",
    "found",
    "generated",
    "live",
    "met",
    "ok",
    "operational",
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
    "release_supported_seed",
    "referenced",
    "reviewed",
    "resolved",
    "satisfied",
    "success",
    "succeeded",
    "sdk_ready",
    "stable",
    "stable_claim_allowed",
    "stable_ready",
    "stable_sdk",
    "stable_sdk_ready",
    "supported",
    "true",
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
OBJECT_IDENTITY_RESOURCE_HANDLE_REQUIRED_FALSE_KEYS = (
    "promotion_ready",
    "public_sdk_ready",
    "runtime_ready",
    "public_resource_handle_ready",
    "post_callback_resource_handle_ready",
    "serialPolicyReady",
    "resourceLookupReady",
    "postCallbackHandleReady",
    "objectIdentityReady",
    "runtimeSampleReady",
    "offline_artifacts_unlock_public_lookup_identity_runtime_sdk",
)
OBJECT_IDENTITY_RESOURCE_HANDLE_FORBIDDEN_READY_KEYS = (
    *OBJECT_IDENTITY_RESOURCE_HANDLE_REQUIRED_FALSE_KEYS,
    "cross_event_identity_ready",
    "cross_event_object_identity_ready",
    "lookup_ready",
    "mutation_ready",
    "object_identity_ready",
    "object_lookup_ready",
    "object_mutation_ready",
    "persistent_handle_ready",
    "persistent_identity_ready",
    "persistent_object_identity_ready",
    "post_callback_handle_ready",
    "post_callback_object_validity_ready",
    "post_callback_validity_ready",
    "public_abi_ready",
    "public_contract_allowed",
    "public_header_allowed",
    "public_lookup_ready",
    "public_mutation_ready",
    "public_object_identity_ready",
    "public_object_lookup_ready",
    "release_ready",
    "resource_handle_ready",
    "resource_lookup_ready",
    "runtime_object_negative_samples_ready",
    "serial_policy_ready",
    "serial_reuse_ready",
    "serial_wraparound_ready",
    "v1_completion_ready",
)
OBJECT_IDENTITY_RESOURCE_HANDLE_STRICT_NEXT_BLOCKER = (
    "runtime rejected object samples, runtime serial reuse/wraparound semantics, "
    "lookup privacy, and ResourceHandle lifetime semantics under future approved live-ops brief"
)
OBJECT_IDENTITY_RESOURCE_HANDLE_OFFLINE_ARTIFACT_POLICY = "candidate-only"
COMMAND_PERMISSION_ROUTE_GATE_POSITIVE_CLAIM_RE = re.compile(
    r"\b(?:"
    r"reply\s+api|reply\s+abi|send[-\s]?chat\s+api|command\s+router|"
    r"send[-\s]?chat\s+abi|reply\s+endpoint|command\s+routing|permissions/admin|replies\s+api|"
    r"response\s+path|runtime\s+delivery|runtime\s+readiness|runtime\s+work|"
    r"public\s+route|route\s+readiness|route|"
    r"server\s+operations?|operator\s+approval|runtime\s+approval|"
    r"public\s+abi|public\s+sdk|public\s+header|v1\s+completion|"
    r"(?:complete|full|stable|production(?:[-\s]?(?:ready|grade))?)\s+(?:sdk|api|support)"
    r")\b.{0,80}\b(?:is|are|now|becomes?|became)?\s*"
    r"\b(?:authorized|granted|public|ready|available|allowed|enabled|promoted|supported|unblock(?:ed|s)?|unlock(?:ed|s)?|accepted|live|operational)\b",
    re.IGNORECASE,
)
COMMAND_PERMISSION_ROUTE_GATE_POSITIVE_CLAIM_REVERSED = re.compile(
    r"\b(?:authorized|granted|public|ready|available|allowed|enabled|promoted|supported|unblock(?:ed|s)?|unlock(?:ed|s)?|accepted|live|operational)\b"
    r".{0,80}\b(?:"
    r"reply\s+api|reply\s+abi|reply\s+endpoint|send[-\s]?chat\s+api|command\s+router|"
    r"response\s+path|runtime\s+delivery|runtime\s+readiness|runtime\s+work|"
    r"public\s+route|route\s+readiness|route|"
    r"server\s+operations?|operator\s+approval|runtime\s+approval|"
    r"public\s+abi|public\s+sdk|public\s+header|v1\s+completion|"
    r"(?:complete|full|stable|production(?:[-\s]?(?:ready|grade))?)\s+(?:sdk|api|support)"
    r")\b",
    re.IGNORECASE,
)
COMMAND_PERMISSION_ROUTE_GATE_BROAD_REVERSED_CLAIM_RE = re.compile(
    r"\b(?:public[-\s_]+(?:api|abi)|sdk|api|support)\b\s+"
    r"(?:is|are|now|becomes?|became)\s+"
    r"\b(?:complete|full|stable|production[-\s]?(?:ready|grade)|public|ready|supported)\b",
    re.IGNORECASE,
)
COMMAND_PERMISSION_ROUTE_GATE_NEGATED_CLAIM_RE = re.compile(
    r"\b(?:no|not|never|without|does\s+not|do\s+not|cannot|can't|must\s+not|"
    r"blocked|planning[- ]only|non[- ]claim|false)\b",
    re.IGNORECASE,
)
STRICT_PROMOTION_EVIDENCE_SURFACE_IDS = CANONICAL_V1_COMPLETION_BLOCKERS | CANONICAL_EXPERIMENTAL_SURFACE_IDS
RUNTIME_EVIDENCE_READY_SCOPE = "runtime_evidence_only"
PUBLIC_CONTRACT_REVIEW_READY_SCOPE = "contract_review_input_only"
BUNDLE_BUILDER_INPUTS_READY_SCOPE = "bundle_builder_inputs_only"
PROMOTION_EVIDENCE_FORBIDDEN_READY_SCOPES = {
    "approved_runtime",
    "approved_runtime_binding",
    "approved_runtime_evidence",
    "approved_runtime_evidence_binding",
    "approved_runtime_evidence_binding_only",
    "approved_runtime_evidence_only",
    "approved_runtime_only",
    "accepted_runtime_evidence_precondition",
    "accepted_runtime_evidence_precondition_only",
    "accepted_runtime_evidence_preconditions",
    "accepted_runtime_evidence_preconditions_only",
    "accepted_artifact_class",
    "accepted_artifact_class_only",
    "accepted_artifact_class_report",
    "accepted_artifact_class_report_only",
    "activation_preconditions",
    "activation_preconditions_only",
    "offline_pre_activation_consistency",
    "offline_pre_activation_consistency_only",
    "pre_activation_consistency",
    "pre_activation_consistency_only",
    "preactivation_consistency",
    "preactivation_consistency_only",
    "approved_bundle",
    BUNDLE_BUILDER_INPUTS_READY_SCOPE,
    "contract_review",
    "contract_review_input",
    PUBLIC_CONTRACT_REVIEW_READY_SCOPE,
    "contract_review_only",
    "public_contract_review",
    "public_contract_review_input",
    "public_contract_review_input_only",
    "public_contract_review_only",
    "reviewed_public_contract",
    "reviewed_public_contract_only",
    "diagnostic",
    "diagnostic_lifecycle",
    "diagnostic_lifecycle_only",
    "diagnostic_only",
    "ready_log_evidence_split",
    "ready_log_evidence_split_only",
    "lifecycle_event_split",
    "lifecycle_event_split_only",
    "player_principal_lifecycle_event_split_summary",
    "player_principal_lifecycle_event_split_summary_only",
    "post_runtime_contract_gap",
    "post_runtime_contract_gap_only",
    "post_runtime_contract_gap_diagnostic",
    "post_runtime_contract_gap_diagnostic_only",
    "route_sample",
    "route_sample_only",
    "route_samples",
    "route_samples_only",
    "check_join_in_progress_offline_acceptance",
    "check_join_in_progress_offline_acceptance_only",
    "checkjoininprogress_offline_acceptance",
    "checkjoininprogress_offline_acceptance_only",
    "check_join_in_progress_1_0_planning_acceptance",
    "check_join_in_progress_1_0_planning_acceptance_only",
    "checkjoininprogress_1_0_planning_acceptance",
    "checkjoininprogress_1_0_planning_acceptance_only",
    "check_join_in_progress10_planning_acceptance",
    "check_join_in_progress10_planning_acceptance_only",
    "checkjoininprogress10_planning_acceptance",
    "checkjoininprogress10_planning_acceptance_only",
    "check_join_in_progress_planning_acceptance",
    "check_join_in_progress_planning_acceptance_only",
    "checkjoininprogress_planning_acceptance",
    "checkjoininprogress_planning_acceptance_only",
    "check_join_in_progress_candidate_only",
    "checkjoininprogress_candidate_only",
    "session_start_rejected_offline_acceptance",
    "session_start_rejected_offline_acceptance_only",
    "offline_session_start_rejected_acceptance",
    "offline_session_start_rejected_acceptance_only",
    "candidate_only_session_start_rejected_acceptance",
    "candidate_only_session_start_rejected_acceptance_only",
    "session_start_rejected_planning_acceptance",
    "session_start_rejected_planning_acceptance_only",
    "rejected_session_start_planning_acceptance",
    "rejected_session_start_planning_acceptance_only",
    "start_end_evidence",
    "start_end_evidence_only",
    "start_end_only_evidence",
    "start_end_only_evidence_only",
    "session_start_end_evidence",
    "session_start_end_evidence_only",
    "session_start_and_end_evidence",
    "session_start_and_end_evidence_only",
    "standing_authority",
    "standing_authority_only",
    "standing_launch_authority",
    "standing_launch_authority_only",
    "helper",
    "helper_artifact",
    "helper_artifact_only",
    "helper_only",
    "identity_contract",
    "identity_contract_only",
    "identity_public_contract",
    "identity_public_contract_only",
    "notice_action",
    "notice_action_only",
    "notice_dry_run",
    "notice_dry_run_only",
    "beta_notice",
    "beta_notice_only",
    "bot_notice",
    "bot_notice_only",
    "discord_beta_bot_notice",
    "discord_beta_bot_notice_only",
    "discord_beta_bridge",
    "discord_beta_bridge_bot_notice",
    "discord_beta_bridge_bot_notice_only",
    "discord_beta_bridge_config",
    "discord_beta_bridge_config_only",
    "discord_beta_bridge_event",
    "discord_beta_bridge_event_only",
    "discord_beta_bridge_only",
    "discord_bot_notice",
    "discord_bot_notice_only",
    "beta_capture",
    "beta_capture_only",
    "beta_capture_plan",
    "beta_capture_plan_only",
    "beta_capture_queue",
    "beta_capture_queue_only",
    "multi_surface",
    "multi_surface_beta_capture",
    "multi_surface_beta_capture_only",
    "multi_surface_beta_capture_plan",
    "multi_surface_beta_capture_plan_only",
    "multi_surface_beta_capture_plan_queue",
    "multi_surface_beta_capture_plan_queue_only",
    "multi_surface_beta_pack",
    "multi_surface_beta_pack_only",
    "multi_surface_beta_capture_queue",
    "multi_surface_beta_capture_queue_only",
    "multi_surface_candidate_queue",
    "multi_surface_candidate_queue_only",
    "confirmed_notice",
    "confirmed_notice_only",
    "confirmed_notice_report",
    "confirmed_notice_report_only",
    "beta_notice_prep",
    "beta_notice_prep_only",
    "beta_notice_send",
    "beta_notice_send_only",
    "beta_notice_send_attestation",
    "beta_notice_send_attestation_only",
    "player_notice",
    "player_notice_action",
    "player_notice_action_only",
    "player_notice_only",
    "lifecycle_anchor",
    "lifecycle_anchor_candidates",
    "lifecycle_anchor_candidates_only",
    "lifecycle_anchor_only",
    "live_ops_sidecar",
    "live_validation_sidecar",
    "installed_runtime",
    "installed_runtime_only",
    "runtime_install",
    "runtime_install_only",
    "runtime_installed",
    "runtime_installed_only",
    "broadcast",
    "broadcast_only",
    "broadcast_ok",
    "broadcast_ok_only",
    "rcon",
    "rcon_count",
    "rcon_count_only",
    "rcon_counts",
    "rcon_counts_only",
    "rcon_only",
    "rcon_ok",
    "rcon_ok_only",
    "rcon_player_count",
    "rcon_player_count_only",
    "rcon_player_counts",
    "rcon_player_counts_only",
    "operator_approval_receipt",
    "operator_approval_receipt_only",
    "operator_receipt",
    "operator_receipt_only",
    "observer_event_triage",
    "observer_event_triage_non_evidence",
    "observer_event_triage_only",
    "passive_observation",
    "passive_observation_only",
    "passive_activity_triage",
    "passive_activity_triage_non_evidence",
    "passive_activity_triage_only",
    "passive_latest_summary",
    "passive_latest_summary_only",
    "passive_snapshot",
    "passive_snapshot_diff",
    "passive_snapshot_diff_only",
    "passive_snapshot_latest",
    "passive_snapshot_latest_only",
    "passive_snapshot_only",
    "closed_agent_note",
    "closed_agent_note_only",
    "closed_agent_notes",
    "closed_agent_notes_only",
    "closed_agent_report",
    "closed_agent_report_only",
    "closed_agent_summary",
    "closed_agent_summary_only",
    "closed_worker_note",
    "closed_worker_note_only",
    "closed_worker_notes",
    "closed_worker_notes_only",
    "closed_worker_report",
    "closed_worker_report_only",
    "closed_worker_summary",
    "closed_worker_summary_only",
    "copied_log_only",
    "copied_log_only_artifact",
    "copied_log_only_report",
    "package_shape",
    "package_shape_evidence",
    "package_shape_evidence_only",
    "package_shape_only",
    "package_check",
    "package_check_only",
    "package_install",
    "package_install_only",
    "package_exact",
    "package_exact_only",
    "package_non_exact",
    "package_non_exact_only",
    "sdk_package_shape",
    "sdk_package_shape_only",
    "sdk_package_exact",
    "sdk_package_exact_only",
    "sdk_package_non_exact",
    "sdk_package_non_exact_only",
    "installed_sdk",
    "installed_sdk_only",
    "installed_sdk_package_shape",
    "installed_sdk_package_shape_only",
    "installed_sdk_package_exact",
    "installed_sdk_package_exact_only",
    "installed_sdk_package_non_exact",
    "installed_sdk_package_non_exact_only",
    "install_evidence",
    "install_evidence_only",
    "install_package",
    "install_package_only",
    "installed_sdk_evidence",
    "installed_sdk_evidence_only",
    "find_package",
    "find_package_only",
    "cmake_package_check",
    "cmake_package_check_only",
    "component_sdk_check",
    "component_sdk_check_only",
    "route_planning",
    "route_planning_only",
    "route_planning_report",
    "route_planning_report_only",
    "planning_route",
    "planning_route_only",
    "planning_route_report",
    "planning_route_report_only",
    "command_chat_response_route_planning",
    "command_chat_response_route_planning_only",
    "copied_bool",
    "copied_bool_only",
    "copied_bool_policy_slice",
    "copied_bool_policy_slice_only",
    "fixture_boundary",
    "fixture_boundary_only",
    "placeholder_provenance",
    "preflight",
    "preflight_only",
    "post_window_replay",
    "post_window_replay_only",
    "closure_artifact",
    "closure_artifact_only",
    "closure_report",
    "closure_report_only",
    "evidence_closure",
    "evidence_closure_only",
    "evidence_closure_report",
    "evidence_closure_report_only",
    "request_pack",
    "request_pack_only",
    "request_artifact",
    "request_artifact_only",
    "request_check",
    "request_check_only",
    "request_check_readiness",
    "request_check_readiness_only",
    "request_preflight",
    "request_preflight_only",
    "approved_bundle_request",
    "approved_bundle_request_only",
    "approved_runtime_bundle_request",
    "approved_runtime_bundle_request_only",
    "public_reachability",
    "public_reachability_only",
    "route_bound_identity_source_forwarding",
    "route_bound_identity_source_forwarding_only",
    "identity_source_forwarding",
    "identity_source_forwarding_only",
    "window_request_check",
    "window_request_check_only",
    RUNTIME_EVIDENCE_READY_SCOPE,
    "runtime_replay",
    "runtime_replay_fixture",
    "runtime_replay_fixture_only",
    "runtime_replay_only",
    "abi_consumer_guardrail",
    "abi_consumer_guardrail_only",
    "abi_consumer_guardrails",
    "abi_consumer_guardrails_only",
    "call_process_event_post_init",
    "call_process_event_post_init_only",
    "post_init_call_process_event",
    "post_init_call_process_event_only",
    "sdk_consumer_guardrail",
    "sdk_consumer_guardrail_only",
    "sdk_consumer_guardrails",
    "sdk_consumer_guardrails_only",
    "runtime_window",
    "runtime_window_plan",
    "runtime_window_plan_only",
    "runtime_window_planner",
    "runtime_window_planner_only",
    "runtime_window_executor",
    "runtime_window_executor_only",
    "runtime_window_execution",
    "runtime_window_execution_only",
    "runtime_window_closure",
    "runtime_window_closure_only",
    "runtime_window_executor_closure",
    "runtime_window_executor_closure_only",
    "internal_fixture_boundary",
    "internal_fixture_boundary_only",
    "internal_only",
    "live_ops_sidecar_only",
    "live_validation_sidecar_only",
    "mission_copied_bool",
    "mission_copied_bool_only",
    "mission_copied_bool_fixture_boundary",
    "mission_copied_bool_fixture_boundary_only",
    "readiness_only",
    "report_only",
    "scoped_non_complete",
    "scoped_non_complete_only",
    "scoped_non_complete_release_statement",
    "scoped_non_complete_release_statement_only",
    "scoped_release_statement",
    "scoped_release_statement_only",
    "transfer_scriptstruct_readiness",
    "transfer_scriptstruct_readiness_only",
    "transfer_script_struct_readiness",
    "transfer_script_struct_readiness_only",
    "transfer_baccept_readiness",
    "transfer_baccept_readiness_only",
    "dino_scalar_readiness",
    "dino_scalar_readiness_only",
    "scalar_only_readiness",
    "scalar_only_readiness_only",
    "buff_status_readiness",
    "buff_status_readiness_only",
    "tribe_scalar_boundary_readiness",
    "tribe_scalar_boundary_readiness_only",
    "scalar_boundary_readiness",
    "scalar_boundary_readiness_only",
    "post_evidence_p0_lock_simulation",
    "post_evidence_p0_lock_simulation_only",
    "post_evidence_identity_lock",
    "post_evidence_identity_lock_only",
    "route_simulation",
    "route_simulation_only",
    "route_lock_simulation",
    "route_lock_simulation_only",
    "identity_lock",
    "identity_lock_only",
    "route_gate_post_evidence_p0_lock_simulation",
    "route_gate_post_evidence_p0_lock_simulation_only",
    "simulation_only",
    "window_manifest",
    "window_manifest_only",
    "binding_required",
    "binding_required_only",
    "binding_required_report",
    "binding_required_report_only",
}
PROMOTION_EVIDENCE_SCOPE_KEYS = {
    "accounting_scope",
    "artifact_scope",
    "claim_scope",
    "evidence_scope",
    "promotion_scope",
    "readiness_scope",
    "ready_scope",
    "source_scope",
    "validation_scope",
}
PROMOTION_EVIDENCE_REQUIRED_TERMS = {
    "obelisk.player_identity.v1": (
        "obelisk.core-dump-evidence-pack.v1",
        "obelisk.reflection-inventory-pack.v1",
        "ServerListPlayers",
        "ServerKickPlayer",
        "approved runtime principal lifecycle evidence",
        "accepted login/logout lifecycle ordering and principal invalidation semantics",
        "principal privacy, invalidation, and cross-instance semantics",
        "append-only POD C ABI design with capability gates, owner-scoped cleanup, and SDK consumer tests",
    ),
    "obelisk.permissions_admin.v1": (
        "query-only fail-closed permission checks over copied principals",
        "stale principal, scope mismatch, missing generation, missing owner token, unknown authority source, and missing policy provenance fail closed",
        "allow decisions carry policy_source_id, policy_source_generation, authority_kind, authority_generation, and policy_epoch provenance",
        "promoted copied principal semantics",
    ),
    "obelisk.command_chat_response_path.v1": (
        "promoted player identity/principal semantics",
        "promoted permission/authority checks for directed responses",
        "copied append-only response ABI with capability gates and owner-scoped cleanup",
        "privacy, redaction, rate-limit, abuse, audit, and cross-instance routing semantics for command/chat responses",
        "no raw UE pointer, raw ProcessEvent parameter, or raw FString response API",
    ),
    "obelisk.commands_replies.v1": (
        "promoted player identity/principal semantics",
        "promoted permission/authority model",
        "obelisk.command_chat_response_path.v1 dependency resolved through its own future promotion gate for replies/send-chat",
        "command lifecycle, abuse, rate-limit, and moderation boundaries",
        "copied append-only command/reply ABI with capability gates, owner-scoped cleanup, and SDK consumer tests",
    ),
}
PLAYER_IDENTITY_REQUEST_PACK_NON_EVIDENCE_TERMS = (
    "prepared_at_utc",
    "request packs",
    "preflight readiness",
    "window manifests",
    "observer env files",
    "operator approval receipts",
    "operator receipts",
    "live-validation sidecars",
    "live-ops sidecars",
    "do not satisfy approved runtime principal lifecycle evidence",
    "public identity promotion",
    "public ABI/SDK readiness",
    "runtime readiness",
    "v1 SDK completion",
)
APPROVED_RUNTIME_EVIDENCE_CLASSIFICATION_KEYS = {
    "artifact_status",
    "evidence_kind",
    "input_schema",
    "readiness_classification",
    "classification",
    "evidence_classification",
    "ready_scope",
    "review_scope",
    "schema",
    "source_kind",
    "source_schema",
    "source_scope",
    "source_value",
    "source_values",
    "status",
}
APPROVED_RUNTIME_EVIDENCE_FORBIDDEN_MARKERS = (
    ("observer_event_triage", "observer_event_triage_not_approved_runtime_evidence"),
    ("observer_event_triage_non_evidence", "observer_event_triage_not_approved_runtime_evidence"),
    ("approved_runtime_evidence_binding", "approved_runtime_evidence_binding_not_approved_runtime_evidence"),
    ("approved_runtime_binding", "approved_runtime_evidence_binding_not_approved_runtime_evidence"),
    ("check_join_in_progress_offline", "checkjoininprogress_session_start_rejected_offline_acceptance_not_approved_runtime_evidence"),
    ("checkjoininprogress_offline", "checkjoininprogress_session_start_rejected_offline_acceptance_not_approved_runtime_evidence"),
    ("check_join_in_progress_1_0_planning", "checkjoininprogress_session_start_rejected_offline_acceptance_not_approved_runtime_evidence"),
    ("checkjoininprogress_1_0_planning", "checkjoininprogress_session_start_rejected_offline_acceptance_not_approved_runtime_evidence"),
    ("check_join_in_progress10_planning", "checkjoininprogress_session_start_rejected_offline_acceptance_not_approved_runtime_evidence"),
    ("checkjoininprogress10_planning", "checkjoininprogress_session_start_rejected_offline_acceptance_not_approved_runtime_evidence"),
    ("check_join_in_progress_planning", "checkjoininprogress_session_start_rejected_offline_acceptance_not_approved_runtime_evidence"),
    ("checkjoininprogress_planning", "checkjoininprogress_session_start_rejected_offline_acceptance_not_approved_runtime_evidence"),
    ("check_join_in_progress_candidate", "checkjoininprogress_session_start_rejected_offline_acceptance_not_approved_runtime_evidence"),
    ("checkjoininprogress_candidate", "checkjoininprogress_session_start_rejected_offline_acceptance_not_approved_runtime_evidence"),
    ("session_start_rejected_offline", "checkjoininprogress_session_start_rejected_offline_acceptance_not_approved_runtime_evidence"),
    ("offline_session_start_rejected", "checkjoininprogress_session_start_rejected_offline_acceptance_not_approved_runtime_evidence"),
    ("session_start_rejected_planning", "checkjoininprogress_session_start_rejected_offline_acceptance_not_approved_runtime_evidence"),
    ("rejected_session_start_planning", "checkjoininprogress_session_start_rejected_offline_acceptance_not_approved_runtime_evidence"),
    ("session_start_rejected_candidate", "checkjoininprogress_session_start_rejected_offline_acceptance_not_approved_runtime_evidence"),
    ("candidate_session_start_rejected", "checkjoininprogress_session_start_rejected_offline_acceptance_not_approved_runtime_evidence"),
    ("principal_start_end_contract_input", "start_end_contract_input_not_approved_runtime_evidence"),
    ("session_start_end_contract_input", "start_end_contract_input_not_approved_runtime_evidence"),
    ("session_start_and_end_contract_input", "start_end_contract_input_not_approved_runtime_evidence"),
    ("start_end_contract_input", "start_end_contract_input_not_approved_runtime_evidence"),
    ("start_end_only_evidence", "start_end_only_evidence_not_approved_runtime_evidence"),
    ("start_end_evidence", "start_end_only_evidence_not_approved_runtime_evidence"),
    ("session_start_end_evidence", "start_end_only_evidence_not_approved_runtime_evidence"),
    ("session_start_and_end_evidence", "start_end_only_evidence_not_approved_runtime_evidence"),
    ("standing_launch_authority", "standing_launch_authority_not_approved_runtime_evidence"),
    ("standing_authority", "standing_launch_authority_not_approved_runtime_evidence"),
    ("passive_snapshot_latest", "passive_latest_summary_not_approved_runtime_evidence"),
    ("passive_snapshot_diff", "passive_latest_summary_not_approved_runtime_evidence"),
    ("passive_activity_triage", "passive_activity_triage_not_approved_runtime_evidence"),
    ("passive_latest_summary", "passive_latest_summary_not_approved_runtime_evidence"),
    ("latest_summary", "passive_latest_summary_not_approved_runtime_evidence"),
    ("active_passive_monitor", "active_monitor_not_approved_runtime_evidence"),
    ("active_monitor", "active_monitor_not_approved_runtime_evidence"),
    ("passive_snapshot", "passive_snapshot_not_approved_runtime_evidence"),
    ("passive_observation", "passive_snapshot_not_approved_runtime_evidence"),
    ("passive_capture", "passive_snapshot_not_approved_runtime_evidence"),
    ("player_principal_passive_snapshot", "passive_snapshot_not_approved_runtime_evidence"),
    ("ready_log_evidence_split", "ready_log_evidence_split_not_approved_runtime_evidence"),
    ("player_principal_lifecycle_event_split_summary", "lifecycle_event_split_summary_not_approved_runtime_evidence"),
    ("lifecycle_event_split_summary", "lifecycle_event_split_summary_not_approved_runtime_evidence"),
    ("lifecycle_event_split", "lifecycle_event_split_summary_not_approved_runtime_evidence"),
    ("post_runtime_contract_gap_diagnostic", "post_runtime_contract_gap_diagnostic_not_approved_runtime_evidence"),
    ("post_runtime_contract_gap", "post_runtime_contract_gap_diagnostic_not_approved_runtime_evidence"),
    ("route_samples", "route_sample_not_approved_runtime_evidence"),
    ("route_sample", "route_sample_not_approved_runtime_evidence"),
    ("copied_log_only", "copied_log_only_not_approved_runtime_evidence"),
    ("window_manifest", "window_manifest_not_approved_runtime_evidence"),
    ("accepted_artifact_class", "accepted_artifact_class_not_approved_runtime_evidence"),
    ("binding_required", "binding_required_not_approved_runtime_evidence"),
    ("request_pack", "request_pack_not_approved_runtime_evidence"),
    ("request_check", "request_check_not_approved_runtime_evidence"),
    ("approved_bundle_request", "approved_bundle_request_not_approved_runtime_evidence"),
    ("public_reachability", "public_reachability_not_approved_runtime_evidence"),
    ("public_contract_readiness", "public_contract_review_status_not_approved_runtime_evidence"),
    ("public_contract_review", "public_contract_review_status_not_approved_runtime_evidence"),
    ("reviewed_public_contract", "public_contract_review_status_not_approved_runtime_evidence"),
    ("reviewed_identity_public_contract", "public_contract_review_status_not_approved_runtime_evidence"),
    ("identity_public_contract", "public_contract_review_status_not_approved_runtime_evidence"),
    ("contract_review", "public_contract_review_status_not_approved_runtime_evidence"),
    ("offline_hardening", "offline_hardening_not_approved_runtime_evidence"),
    ("route_bound_identity_source_forwarding", "identity_source_forwarding_not_approved_runtime_evidence"),
    ("identity_source_forwarding", "identity_source_forwarding_not_approved_runtime_evidence"),
    ("preflight", "preflight_not_approved_runtime_evidence"),
    ("activation_preconditions", "activation_preconditions_not_approved_runtime_evidence"),
    ("closure_report", "closure_report_not_approved_runtime_evidence"),
    ("evidence_closure", "closure_report_not_approved_runtime_evidence"),
    ("beta_notice", "beta_notice_not_approved_runtime_evidence"),
    ("discord_beta_bridge_bot_notice", "discord_beta_bridge_not_approved_runtime_evidence"),
    ("discord_beta_bridge_config", "discord_beta_bridge_not_approved_runtime_evidence"),
    ("discord_beta_bridge_event", "discord_beta_bridge_not_approved_runtime_evidence"),
    ("discord_beta_bridge", "discord_beta_bridge_not_approved_runtime_evidence"),
    ("discord_beta_bot_notice", "discord_beta_bridge_not_approved_runtime_evidence"),
    ("discord_bot_notice", "discord_beta_bridge_not_approved_runtime_evidence"),
    ("bot_notice", "discord_beta_bridge_not_approved_runtime_evidence"),
    ("multi_surface_beta_capture_pack", MULTI_SURFACE_BETA_CAPTURE_CANDIDATE_QUEUE_NON_EVIDENCE_REASON),
    ("multi_surface_beta_pack", MULTI_SURFACE_BETA_CAPTURE_CANDIDATE_QUEUE_NON_EVIDENCE_REASON),
    ("multi_surface_beta_capture_checker_matrix", MULTI_SURFACE_BETA_CAPTURE_CANDIDATE_QUEUE_NON_EVIDENCE_REASON),
    ("multi_surface_beta_capture_non_claim_manifest", MULTI_SURFACE_BETA_CAPTURE_CANDIDATE_QUEUE_NON_EVIDENCE_REASON),
    ("multi_surface_capture_plan", MULTI_SURFACE_BETA_CAPTURE_CANDIDATE_QUEUE_NON_EVIDENCE_REASON),
    ("checker_command_matrix", MULTI_SURFACE_BETA_CAPTURE_CANDIDATE_QUEUE_NON_EVIDENCE_REASON),
    ("operator_runbook", MULTI_SURFACE_BETA_CAPTURE_CANDIDATE_QUEUE_NON_EVIDENCE_REASON),
    ("multi_surface_beta_capture", "multi_surface_beta_capture_not_approved_runtime_evidence"),
    ("multi_surface_candidate_queue", "multi_surface_beta_capture_not_approved_runtime_evidence"),
    ("beta_capture_plan", "multi_surface_beta_capture_not_approved_runtime_evidence"),
    ("beta_capture_queue", "multi_surface_beta_capture_not_approved_runtime_evidence"),
    ("confirmed_notice", "confirmed_notice_not_approved_runtime_evidence"),
    ("route_simulation", "route_simulation_not_approved_runtime_evidence"),
    ("post_evidence_identity_lock", "post_evidence_identity_lock_not_approved_runtime_evidence"),
    ("identity_lock", "identity_lock_not_approved_runtime_evidence"),
    ("operator_approval_receipt", "operator_receipt_not_approved_runtime_evidence"),
    ("operator_receipt", "operator_receipt_not_approved_runtime_evidence"),
    ("live_validation_sidecar", "live_sidecar_not_approved_runtime_evidence"),
    ("live_ops_sidecar", "live_sidecar_not_approved_runtime_evidence"),
    ("installed_runtime", "installed_runtime_not_approved_runtime_evidence"),
    ("runtime_install", "installed_runtime_not_approved_runtime_evidence"),
    ("runtime_installed", "installed_runtime_not_approved_runtime_evidence"),
    ("install_package", "package_shape_not_approved_runtime_evidence"),
    ("package_install", "package_shape_not_approved_runtime_evidence"),
    ("package_check", "package_shape_not_approved_runtime_evidence"),
    ("find_package", "package_shape_not_approved_runtime_evidence"),
    ("cmake_package_check", "package_shape_not_approved_runtime_evidence"),
    ("component_sdk_check", "package_shape_not_approved_runtime_evidence"),
    ("generated_cert", "generated_cert_report_not_approved_runtime_evidence"),
    ("generated_certificate", "generated_cert_report_not_approved_runtime_evidence"),
    ("promotion_cert", "promotion_certificate_not_approved_runtime_evidence"),
    ("public_debug_boundary", "public_debug_boundary_not_approved_runtime_evidence"),
    ("debug_public_boundary", "public_debug_boundary_not_approved_runtime_evidence"),
    ("abi_consumer_guardrail", "abi_consumer_guardrail_not_approved_runtime_evidence"),
    ("sdk_consumer_guardrail", "abi_consumer_guardrail_not_approved_runtime_evidence"),
    ("post_init_call_process_event", "post_init_call_process_event_not_approved_runtime_evidence"),
    ("call_process_event_post_init", "post_init_call_process_event_not_approved_runtime_evidence"),
    ("broadcast", "broadcast_status_not_approved_runtime_evidence"),
    ("rcon", "rcon_status_not_approved_runtime_evidence"),
    ("player_notice_action", "player_notice_action_not_approved_runtime_evidence"),
    ("player_notice", "player_notice_action_not_approved_runtime_evidence"),
    ("notice_dry_run", "player_notice_action_not_approved_runtime_evidence"),
    ("discord_notice", "player_notice_action_not_approved_runtime_evidence"),
    ("runtime_window_plan", "runtime_window_plan_not_approved_runtime_evidence"),
    ("runtime_window_planner", "runtime_window_plan_not_approved_runtime_evidence"),
    ("runtime_window_closure", "runtime_window_closure_not_approved_runtime_evidence"),
    ("runtime_window_executor_closure", "runtime_window_closure_not_approved_runtime_evidence"),
    ("runtime_window_executor", "runtime_window_executor_not_approved_runtime_evidence"),
    ("runtime_window_execution", "runtime_window_executor_not_approved_runtime_evidence"),
    ("runtime_evidence_status", "status_report_not_approved_runtime_evidence"),
    ("sdk_status_report", "status_report_not_approved_runtime_evidence"),
    ("status_report", "status_report_not_approved_runtime_evidence"),
    ("source_readiness", "source_ready_status_report_not_approved_runtime_evidence"),
    ("source_ready", "source_ready_status_report_not_approved_runtime_evidence"),
    ("sources_ready", "source_ready_status_report_not_approved_runtime_evidence"),
    ("source_status", "source_ready_status_report_not_approved_runtime_evidence"),
    ("approved_runtime_manifest", "approved_runtime_manifest_reference_not_approved_runtime_evidence"),
    ("partial_lifecycle", "partial_lifecycle_events_not_approved_runtime_evidence"),
    ("partial_role_triplet", "partial_lifecycle_events_not_approved_runtime_evidence"),
    ("partial_event_triplet", "partial_lifecycle_events_not_approved_runtime_evidence"),
    ("lifecycle_event_proof", "partial_lifecycle_events_not_approved_runtime_evidence"),
    ("lifecycle_role_proof", "partial_lifecycle_events_not_approved_runtime_evidence"),
    ("lifecycle_roles_observed", "partial_lifecycle_events_not_approved_runtime_evidence"),
    ("session_start_observed", "partial_lifecycle_events_not_approved_runtime_evidence"),
    ("session_end_observed", "partial_lifecycle_events_not_approved_runtime_evidence"),
)
APPROVED_RUNTIME_PARTIAL_LIFECYCLE_MARKERS = (
    "partial_lifecycle",
    "partial_role_triplet",
    "partial_event_triplet",
    "lifecycle_event_proof",
    "lifecycle_role_proof",
    "lifecycle_event_split",
    "lifecycle_event_split_summary",
    "player_principal_lifecycle_event_split_summary",
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
APPROVED_RUNTIME_DIAGNOSTIC_MISMATCH_TEXT_RE = re.compile(
    r"(?:diagnostic[-_ ]?(?:candidates?|only)|"
    r"observer[-_ ]?event[-_ ]?triage(?:[-_ ]?non[-_ ]?evidence)?|"
    r"fname[-_ ]?mismatch|f[-_ ]?name[-_ ]?mismatch|"
    r"ready[-_ ]?log[-_ ]?evidence[-_ ]?split|"
    r"(?:player[-_ ]?principal[-_ ]?)?lifecycle[-_ ]?event[-_ ]?split(?:[-_ ]?summary)?|"
    r"post[-_ ]?runtime[-_ ]?contract[-_ ]?gap(?:[-_ ]?diagnostic)?|"
    r"route[-_ ]?samples?|"
    r"HandleNewPlayer.{0,80}(?:mismatch|rejected)|"
    r"rejected.{0,80}HandleNewPlayer)",
    re.IGNORECASE,
)
NON_PUBLIC_CHECKJOIN_REJECTED_OFFLINE_ACCEPTANCE_RE = re.compile(
    r"(?:"
    r"check_?join_?in_?progress(?:_?(?:1_?0|10|planning|diagnostic|offline|candidate(?:_?only)?|non_?evidence|accept(?:ed|ance)|readiness|report|status|evidence|artifacts?|summary|source))+|"
    r"(?:session_?start_?rejected|rejected_?session_?start)(?:_?(?:1_?0|10|planning|diagnostic|offline|candidate(?:_?only)?|non_?evidence|accept(?:ed|ance)|readiness|report|status|evidence|artifacts?|summary|source|check_?join_?in_?progress))+|"
    r"(?:diagnostic|offline|candidate(?:_?only)?|non_?evidence|planning)(?:_?(?:check_?join_?in_?progress|session_?start_?rejected|rejected_?session_?start)(?:_?(?:1_?0|10|planning|accept(?:ed|ance)|readiness|report|status|evidence|artifacts?|summary|source))?)+"
    r")",
    re.IGNORECASE,
)
APPROVED_EVIDENCE_CLAIM_KEYS = {
    "approved_evidence_claim",
    "approved_runtime_evidence_claim",
    "evidence_claim",
    "runtime_evidence_claim",
}
APPROVED_EVIDENCE_CLAIM_NONE_VALUES = {
    "",
    "0",
    "absent",
    "false",
    "missing",
    "no",
    "none",
    "not_applicable",
    "not_approved",
    "unapproved",
}
REQUIRED_PROMOTED_SURFACE_DEPENDENCIES = {
    "obelisk.permissions_admin.v1": (
        "obelisk.player_identity.v1",
    ),
    "obelisk.command_chat_response_path.v1": (
        "obelisk.player_identity.v1",
        "obelisk.permissions_admin.v1",
    ),
    "obelisk.commands_replies.v1": (
        "obelisk.player_identity.v1",
        "obelisk.permissions_admin.v1",
        "obelisk.command_chat_response_path.v1",
    ),
    "obelisk.player_services_economy_mobility.v1": (
        "obelisk.player_identity.v1",
        "obelisk.permissions_admin.v1",
        "obelisk.command_chat_response_path.v1",
        "obelisk.operator_ingress_storage.v1",
    ),
}
PROMOTION_EVIDENCE_NEGATIVE_CONTEXT_KEYS = {
    "argv",
    "blockers",
    "candidate",
    "missing",
    "non_claim",
    "non_claims",
    "planning",
    "requires",
    "todo",
    "todos",
    "unresolved",
}
PROMOTION_EVIDENCE_NEGATIVE_TERM_CONTEXT = re.compile(
    r"\b(?:blocked|candidate(?:-only)?|insufficient|missing|needs?|no|not|planning|requires?|todo|unresolved|without)\b",
    re.IGNORECASE,
)
STRICT_PROMOTION_EVIDENCE_PATH_DENY_MARKERS = (
    "approved_bundle",
    "approved-bundle",
    "approved_runtime",
    "approved-runtime",
    "approved_runtime_binding",
    "approved-runtime-binding",
    "approved_runtime_evidence_binding",
    "approved-runtime-evidence-binding",
    "approved_runtime_bundle",
    "approved-runtime-bundle",
    "approved_bundle_request",
    "approved-bundle-request",
    "approved_runtime_bundle_request",
    "approved-runtime-bundle-request",
    "accepted_runtime_evidence_precondition",
    "accepted-runtime-evidence-precondition",
    "accepted_runtime_evidence_preconditions",
    "accepted-runtime-evidence-preconditions",
    "accepted_artifact_class",
    "accepted-artifact-class",
    "accepted_artifact_class_report",
    "accepted-artifact-class-report",
    "activation_preconditions",
    "activation-preconditions",
    "offline_pre_activation_consistency",
    "offline-pre-activation-consistency",
    "pre_activation_consistency",
    "pre-activation-consistency",
    "candidate",
    "diagnostic",
    "diagnostic_only",
    "diagnostic_lifecycle",
    "check_join_in_progress_offline_acceptance",
    "checkjoininprogress_offline_acceptance",
    "check_join_in_progress_1_0_planning_acceptance",
    "checkjoininprogress_1_0_planning_acceptance",
    "check_join_in_progress10_planning_acceptance",
    "checkjoininprogress10_planning_acceptance",
    "check_join_in_progress_planning_acceptance",
    "checkjoininprogress_planning_acceptance",
    "check_join_in_progress_candidate_only",
    "checkjoininprogress_candidate_only",
    "session_start_rejected_offline_acceptance",
    "offline_session_start_rejected_acceptance",
    "candidate_only_session_start_rejected_acceptance",
    "session_start_rejected_planning_acceptance",
    "rejected_session_start_planning_acceptance",
    "start_end_evidence",
    "start-end-evidence",
    "start_end_only_evidence",
    "start-end-only-evidence",
    "session_start_end_evidence",
    "session-start-end-evidence",
    "session_start_and_end_evidence",
    "session-start-and-end-evidence",
    "standing_authority",
    "standing-authority",
    "standing_launch_authority",
    "standing-launch-authority",
    "helper",
    "helper_artifact",
    "helper_only",
    "admin_thunk",
    "admin_thunks",
    "chat_message_event_seed",
    "chat_seed",
    "contract_review",
    "contract-review",
    "contract_review_input",
    "contract-review-input",
    "copied_bool",
    "copied-bool",
    "copied_bool_policy_slice",
    "copied-bool-policy-slice",
    "copied_log_only",
    "copied-log-only",
    "copied_log_only_artifact",
    "copied-log-only-artifact",
    "copied_log_only_report",
    "copied-log-only-report",
    "copied_data",
    "core_first",
    "descriptor_catalog",
    "descriptor_preflight",
    "event_seed",
    "gameplay_policy_event_seed",
    "inventory_policy_event",
    "item_return",
    "item_return_event",
    "live_validation",
    "live-validation",
    "live_ops",
    "live-ops",
    "live_ops_sidecar",
    "live-ops-sidecar",
    "lifecycle_anchor",
    "lifecycle-anchor",
    "lifecycle_anchor_candidates",
    "lifecycle-anchor-candidates",
    "identity_contract",
    "identity-contract",
    "identity_public_contract",
    "identity-public-contract",
    "notice_action",
    "notice-action",
    "notice_dry_run",
    "notice-dry-run",
    "beta_notice",
    "beta-notice",
    "beta_notice_prep",
    "beta-notice-prep",
    "beta_notice_send",
    "beta-notice-send",
    "beta_notice_send_attestation",
    "beta-notice-send-attestation",
    "confirmed_notice",
    "confirmed-notice",
    "confirmed_notice_report",
    "confirmed-notice-report",
    "confirmed_beta_notice_report",
    "confirmed-beta-notice-report",
    "active_passive_monitor",
    "active-passive-monitor",
    "active_monitor",
    "active-monitor",
    "passive_monitor",
    "passive-monitor",
    "notice_report",
    "notice-report",
    "player_notice",
    "player-notice",
    "player_notice_action",
    "player-notice-action",
    "discord_notice",
    "discord-notice",
    "bot_notice",
    "bot-notice",
    "discord_beta_bridge",
    "discord-beta-bridge",
    "discord_beta_bridge_bot_notice",
    "discord-beta-bridge-bot-notice",
    "discord_beta_bot_notice",
    "discord-beta-bot-notice",
    "discord_bot_notice",
    "discord-bot-notice",
    "multi_surface_beta_pack",
    "multi-surface-beta-pack",
    "public_reachability",
    "public-reachability",
    "route_bound_identity_source_forwarding",
    "route-bound-identity-source-forwarding",
    "identity_source_forwarding",
    "identity-source-forwarding",
    "fixture_boundary",
    "fixture-boundary",
    "internal_fixture_boundary",
    "internal-fixture-boundary",
    "package_shape",
    "package_shape_evidence",
    "package_shape_only",
    "package_check",
    "package-check",
    "package_install",
    "package-install",
    "package_exact",
    "package-exact",
    "package_non_exact",
    "package-non-exact",
    "sdk_package_shape",
    "sdk_package_exact",
    "sdk-package-exact",
    "sdk_package_non_exact",
    "sdk-package-non-exact",
    "installed_sdk",
    "installed_sdk_package_shape",
    "installed_sdk_package_exact",
    "installed-sdk-package-exact",
    "installed_sdk_package_non_exact",
    "installed-sdk-package-non-exact",
    "install_evidence",
    "install_package",
    "install-package",
    "installed_sdk_evidence",
    "find_package",
    "find-package",
    "cmake_package_check",
    "cmake-package-check",
    "component_sdk_check",
    "component-sdk-check",
    "abi_consumer_guardrail",
    "abi-consumer-guardrail",
    "sdk_consumer_guardrail",
    "sdk-consumer-guardrail",
    "post_init_call_process_event",
    "post-init-call-process-event",
    "call_process_event_post_init",
    "call-process-event-post-init",
    "placeholder",
    "placeholder_provenance",
    "planning",
    "plugin_hub",
    "pluginhub",
    "plugin_hub_seed",
    "orientation",
    "passive_observation",
    "passive-observation",
    "passive_activity_triage",
    "passive-activity-triage",
    "passive_latest_summary",
    "passive-latest-summary",
    "passive_snapshot_diff",
    "passive-snapshot-diff",
    "passive_snapshot_latest",
    "passive-snapshot-latest",
    "passive_snapshot",
    "passive-snapshot",
    "latest_summary",
    "latest-summary",
    "closed_agent_note",
    "closed-agent-note",
    "closed_agent_notes",
    "closed-agent-notes",
    "closed_agent_report",
    "closed-agent-report",
    "closed_agent_summary",
    "closed-agent-summary",
    "closed_worker_note",
    "closed-worker-note",
    "closed_worker_notes",
    "closed-worker-notes",
    "closed_worker_report",
    "closed-worker-report",
    "closed_worker_summary",
    "closed-worker-summary",
    "offline_hardening",
    "offline-hardening",
    "offline_hardening_report",
    "offline-hardening-report",
    "offline_gate_hardening",
    "offline-gate-hardening",
    "route_planning",
    "route-planning",
    "route_planning_report",
    "route-planning-report",
    "planning_route",
    "planning-route",
    "planning_route_report",
    "planning-route-report",
    "route_planning_readiness",
    "route-planning-readiness",
    "command_chat_response_route_planning",
    "command-chat-response-route-planning",
    "command_chat_response_route_planning_readiness",
    "command-chat-response-route-planning-readiness",
    "preflight",
    "preflight-pre",
    "preflight-post",
    "transfer_scriptstruct_readiness",
    "transfer-scriptstruct-readiness",
    "transfer_script_struct_readiness",
    "transfer-script-struct-readiness",
    "transfer_baccept_readiness",
    "transfer-baccept-readiness",
    "check_transfer_baccept_readiness",
    "dino_scalar_readiness",
    "dino-scalar-readiness",
    "check_dino_scalar_readiness",
    "scalar_only_readiness",
    "scalar-only-readiness",
    "buff_status_readiness",
    "buff-status-readiness",
    "check_buff_status_readiness",
    "tribe_scalar_boundary_readiness",
    "tribe-scalar-boundary-readiness",
    "scalar_boundary_readiness",
    "scalar-boundary-readiness",
    "check_tribe_scalar_boundary_readiness",
    "post_evidence_p0_lock_simulation",
    "post-evidence-p0-lock-simulation",
    "route_gate_post_evidence_p0_lock_simulation",
    "route-gate-post-evidence-p0-lock-simulation",
    "command_permission_route_post_evidence_p0_lock_simulation",
    "command-permission-route-post-evidence-p0-lock-simulation",
    "mission_copied_bool",
    "mission-copied-bool",
    "mission_copied_bool_fixture_boundary",
    "mission-copied-bool-fixture-boundary",
    "request_artifact",
    "request_check",
    "request-check",
    "request_preflight",
    "request_check_readiness",
    "request-check-readiness",
    "window_request_check",
    "window-request-check",
    "approved_bundle_request",
    "approved-bundle-request",
    "approved_runtime_bundle_request",
    "approved-runtime-bundle-request",
    "public_reachability",
    "public-reachability",
    "route_bound_identity_source_forwarding",
    "route-bound-identity-source-forwarding",
    "identity_source_forwarding",
    "identity-source-forwarding",
    "post_window_replay",
    "post-window-replay",
    "readiness",
    "readiness_only",
    "readiness-only",
    "report_only",
    "report-only",
    "closure_artifact",
    "closure-artifact",
    "closure_report",
    "closure-report",
    "evidence_closure",
    "evidence-closure",
    "evidence_closure_report",
    "evidence-closure-report",
    "runtime_window_closure",
    "runtime-window-closure",
    "runtime_window_executor_closure",
    "runtime-window-executor-closure",
    "request_pack",
    "request-pack",
    "route_simulation",
    "route-simulation",
    "route_lock_simulation",
    "route-lock-simulation",
    "post_evidence_identity_lock",
    "post-evidence-identity-lock",
    "identity_lock",
    "identity-lock",
    "runtime_replay",
    "runtime-replay",
    "runtime_replay_fixture",
    "runtime-replay-fixture",
    "operator_approval_receipt",
    "operator-approval-receipt",
    "operator_receipt",
    "operator-receipt",
    "observer_event_triage",
    "observer-event-triage",
    "observer_event_triage_non_evidence",
    "observer-event-triage-non-evidence",
    "window_manifest",
    "window-manifest",
    "binding_required",
    "binding-required",
    "binding_required_report",
    "binding-required-report",
    "generated_cert_report",
    "generated-cert-report",
    "generated_certificate_report",
    "generated-certificate-report",
    "promotion_cert_report",
    "promotion-cert-report",
    "promotion_certificate_report",
    "promotion-certificate-report",
    "public_debug_boundary",
    "public-debug-boundary",
    "public_debug_boundary_fix",
    "public-debug-boundary-fix",
    "debug_public_boundary",
    "debug-public-boundary",
    "runtime_window",
    "runtime-window",
    "runtime_window_plan",
    "runtime-window-plan",
    "runtime_window_planner",
    "runtime-window-planner",
    "runtime_window_executor",
    "runtime-window-executor",
    "runtime_window_execution",
    "runtime-window-execution",
    "runtime_window_closure",
    "runtime-window-closure",
    "runtime_window_executor_closure",
    "runtime-window-executor-closure",
    "approved_runtime_manifest",
    "approved-runtime-manifest",
    "approved_runtime_principal_lifecycle_evidence",
    "approved-runtime-principal-lifecycle-evidence",
    "ready_log_evidence_split",
    "ready-log-evidence-split",
    "lifecycle_event_split",
    "lifecycle-event-split",
    "player_principal_lifecycle_event_split_summary",
    "player-principal-lifecycle-event-split-summary",
    "post_runtime_contract_gap",
    "post-runtime-contract-gap",
    "post_runtime_contract_gap_diagnostic",
    "post-runtime-contract-gap-diagnostic",
    "route_sample",
    "route-sample",
    "route_samples",
    "route-samples",
    "scoped_non_complete",
    "scoped-non-complete",
    "scoped_release_statement",
    "scoped-release-statement",
    "static_candidate",
    "static_target",
    "return_only",
    "consume-only",
    "consume_only",
    "evidence-only",
    "evidence_only",
)
STRICT_PROMOTION_EVIDENCE_SCHEMA_KEYS = {
    "artifact_schema",
    "classification",
    "classifications",
    "descriptor_preflight",
    "evidence_classification",
    "evidence_classifications",
    "evidence_kind",
    "evidence_kinds",
    "evidence_terms",
    "input_target_set",
    "output_target_set",
    "pack",
    "packs",
    "promotion_terms",
    "readiness_classification",
    "readiness_classifications",
    "release_readiness_target_sets",
    "contract_kind",
    "schema",
    "schemas",
    "source_kind",
    "source_kinds",
    "source_value",
    "source_values",
    "status",
    "source_target_sets",
    "target_set",
    "target_sets",
    "terms",
}
STRICT_PROMOTION_EVIDENCE_SOURCE_MARKER_KEYS = {
    "evidence_kind",
    "evidence_kinds",
    "source_kind",
    "source_kinds",
    "source_value",
    "source_values",
    "source_target_sets",
    "target_set",
    "target_sets",
}
STRICT_PROMOTION_EVIDENCE_SOURCE_ONLY_DENY_MARKERS = re.compile(
    r"(?:approved[-_ ]?runtime(?:[-_ ]?(?:principal[-_ ]?lifecycle)?[-_ ]?evidence)?|"
    r"approved[-_ ]?runtime[-_ ]?evidence[-_ ]?binding|"
    r"accepted[-_ ]?runtime[-_ ]?evidence[-_ ]?preconditions?|"
    r"runtime[-_ ]?(?:principal[-_ ]?)?lifecycle[-_ ]?evidence|"
    r"(?:session[-_ ]?start(?:[-_ ]?and)?[-_ ]?end|start[-_ ]?end)(?:[-_ ]?only)?[-_ ]?evidence|"
    r"standing[-_ ]?(?:launch[-_ ]?)?authority|"
    r"diagnostic[-_ ]?(?:only[-_ ]?)?(?:principal[-_ ]?)?lifecycle|"
    r"ready[-_ ]?log[-_ ]?evidence[-_ ]?splits?(?:[-_ ]?(?:diagnostic|evidence|readiness|ready|reports?|status|summar(?:y|ies)))?|"
    r"(?:player[-_ ]?principal[-_ ]?)?lifecycle[-_ ]?event[-_ ]?splits?(?:[-_ ]?(?:diagnostic|evidence|readiness|ready|reports?|status|summar(?:y|ies)))?|"
    r"post[-_ ]?runtime[-_ ]?contract[-_ ]?gap(?:[-_ ]?(?:diagnostic|readiness|ready|reports?|status|summar(?:y|ies)))?|"
    r"route[-_ ]?samples?(?:[-_ ]?(?:diagnostic|evidence|readiness|ready|reports?|status|summar(?:y|ies)))?|"
    r"check[-_ ]?join[-_ ]?in[-_ ]?progress(?:[-_ ]?(?:diagnostic|offline|candidate(?:[-_ ]?only)?|accept(?:ed|ance)|readiness|reports?|status|evidence|artifacts?|summar(?:y|ies)|source))?|"
    r"(?:session[-_ ]?start[-_ ]?rejected|rejected[-_ ]?session[-_ ]?start)(?:[-_ ]?(?:diagnostic|offline|candidate(?:[-_ ]?only)?|accept(?:ed|ance)|readiness|reports?|status|evidence|artifacts?|summar(?:y|ies)|source|check[-_ ]?join[-_ ]?in[-_ ]?progress))+|"
    r"(?:diagnostic|offline|candidate(?:[-_ ]?only)?)(?:[-_ ]?(?:check[-_ ]?join[-_ ]?in[-_ ]?progress|session[-_ ]?start[-_ ]?rejected|rejected[-_ ]?session[-_ ]?start)(?:[-_ ]?(?:accept(?:ed|ance)|readiness|reports?|status|evidence|artifacts?|summar(?:y|ies)|source))?)+|"
    r"helpers?|helper[-_ ]?artifacts?|"
    r"closure[-_ ]?(?:artifacts?|reports?|requests?|summar(?:y|ies))?|evidence[-_ ]?closure(?:[-_ ]?(?:artifacts?|reports?|requests?|summar(?:y|ies)))?|"
    r"activation[-_ ]?preconditions?|pre[-_ ]?activation[-_ ]?consistency|"
    r"request[-_ ]?(?:checks?|check[-_ ]?readiness|packs?|artifacts?|manifests?|preflights?)|"
    r"(?:approved[-_ ]?)?(?:runtime[-_ ]?)?bundle[-_ ]?requests?|"
    r"public[-_ ]?reachability|"
    r"(?:route[-_ ]?bound[-_ ]?)?identity[-_ ]?source(?:[-_ ]?(?:forward|forwarded|forwarding))?|"
    r"accepted[-_ ]?artifact[-_ ]?class(?:[-_ ]?(?:artifacts?|metadata|reports?|status))?|"
    r"binding[-_ ]?required(?:[-_ ]?(?:artifacts?|metadata|reports?|status))?|"
    r"(?:offline[-_ ]?)?hardening(?:[-_ ]?(?:artifacts?|metadata|reports?|status|summar(?:y|ies)))?|"
    r"player[-_ ]?principal[-_ ]?lifecycle[-_ ]?window[-_ ]?request[-_ ]?checks?|"
    r"runtime[-_ ]?window(?:[-_ ]?(?:plans?|planners?|executors?|execution|activations?|manifests?|preflights?|prepar(?:ed|ation)?|readiness|ready|requests?|status))?|"
    r"approved[-_ ]?runtime[-_ ]?manifests?|"
    r"identity[-_ ]?(?:public[-_ ]?)?contract(?:[-_ ]?gate[-_ ]?missing)?|"
    r"contract[-_ ]?review(?:[-_ ]?inputs?)?|"
    r"(?:players?[-_ ]?)?notice[-_ ]?actions?|"
    r"confirmed[-_ ]?(?:beta[-_ ]?)?notice(?:[-_ ]?(?:reports?|sent|status|attestations?|confirmation|confirmed))?|"
    r"notice[-_ ]?reports?|"
    r"(?:players?[-_ ]?)?notice[-_ ]?dry[-_ ]?runs?|"
    r"beta[-_ ]?notices?(?:[-_ ]?(?:prep|send|sent|attestation|confirmed))?|"
    r"discord[-_ ]?notices?|"
    r"(?:discord[-_ ]?)?beta[-_ ]?bridge(?:[-_ ]?(?:bot[-_ ]?)?notice|[-_ ]?config|[-_ ]?events?|[-_ ]?plans?|[-_ ]?reports?|[-_ ]?status)?|"
    r"discord[-_ ]?beta[-_ ]?bot[-_ ]?notice|discord[-_ ]?bot[-_ ]?notice|bot[-_ ]?notice|"
    r"multi[-_ ]?surface[-_ ]?beta[-_ ]?packs?|"
    r"(?:generated[-_ ]?)?(?:promotion[-_ ]?)?cert(?:ificate)?(?:[-_ ]?(?:artifacts?|bindings?|build|builder|generation|metadata|outputs?|reports?|status|summar(?:y|ies)))?|"
    r"(?:public[-_ ]?debug|debug[-_ ]?public)[-_ ]?boundary(?:[-_ ]?(?:fix(?:es)?|metadata|reports?|status|summar(?:y|ies)))?|"
    r"(?:install|installed|package)[-_ ]?(?:sdk[-_ ]?)?(?:package|shape|check|evidence|layout|success|succeed(?:ed)?|install|installed)(?:[-_ ]?(?:checks?|ok|ready|reports?|status|success|succeed(?:ed)?))?|"
    r"find[-_ ]?package(?:[-_ ]?(?:obelisk|sdk|components?|success|succeed(?:ed)?|found|ready|reports?|status))?|"
    r"cmake[-_ ]?(?:package|config|components?)(?:[-_ ]?(?:check|found|ready|reports?|status|success|succeed(?:ed)?))?|"
    r"component[-_ ]?sdk(?:[-_ ]?(?:check|found|ready|reports?|status|success|succeed(?:ed)?))?|"
    r"(?:abi|sdk)[-_ ]?consumer[-_ ]?guardrails?|"
    r"(?:post[-_ ]?init|after[-_ ]?init|outside[-_ ]?init)[-_ ]?call[-_ ]?process[-_ ]?event(?:[-_ ]?(?:guardrails?|tests?|skipped|rejected|passed|status|reports?))?|"
    r"call[-_ ]?process[-_ ]?event[-_ ]?(?:post[-_ ]?init|after[-_ ]?init|outside[-_ ]?init)(?:[-_ ]?(?:guardrails?|tests?|skipped|rejected|passed|status|reports?))?|"
    r"passive[-_ ]?(?:snapshots?|observations?|captures?)|"
    r"passive[-_ ]?activity[-_ ]?triage(?:[-_ ]?non[-_ ]?evidence)?|"
    r"observer[-_ ]?event[-_ ]?triage(?:[-_ ]?non[-_ ]?evidence)?|"
    r"player[-_ ]?principal[-_ ]?passive[-_ ]?snapshots?|"
    r"copied[-_ ]?logs?[-_ ]?only(?:[-_ ]?(?:artifacts?|reports?|status))?|"
    r"(?:mission[-_ ]?)?copied[-_ ]?bool(?:[-_ ]?policy[-_ ]?slices?)?|"
    r"(?:internal[-_ ]?)?fixture[-_ ]?boundar(?:y|ies)|"
    r"(?:passive[-_ ]?)?latest[-_ ]?summar(?:y|ies)|"
    r"passive[-_ ]?snapshot[-_ ]?(?:latest|diff)|"
    r"closed[-_ ]?(?:agent|worker)(?:[-_ ]?(?:notes?|reports?|status|summar(?:y|ies)))?|"
    r"transfer[-_ ]?(?:script[-_ ]?struct|baccept)[-_ ]?readiness|"
    r"dino[-_ ]?scalar[-_ ]?readiness|"
    r"scalar[-_ ]?only[-_ ]?readiness|"
    r"buff[-_ ]?status[-_ ]?readiness|"
    r"tribe[-_ ]?scalar[-_ ]?boundary[-_ ]?readiness|"
    r"scalar[-_ ]?boundary[-_ ]?readiness|"
    r"(?:redacted[-_ ]?)?ufunction[-_ ]?(?:chain[-_ ]?)?snapshots?|"
    r"ufunction[-_ ]?snapshot[-_ ]?manifests?|"
    r"redacted[-_ ]?ufunction[-_ ]?signatures|"
    r"(?:route[-_ ]?gate[-_ ]?)?post[-_ ]?evidence[-_ ]?p0[-_ ]?lock[-_ ]?simulation|"
    r"route[-_ ]?(?:simulations?|lock[-_ ]?simulations?|check[-_ ]?readiness|readiness)|"
    r"post[-_ ]?evidence[-_ ]?identity[-_ ]?locks?|identity[-_ ]?locks?|"
    r"report[-_ ]?only|readiness[-_ ]?only|"
    r"scoped[-_ ]?non[-_ ]?complete(?:[-_ ]?only)?|"
    r"scoped[-_ ]?(?:non[-_ ]?complete[-_ ]?)?(?:v1[-_ ]?)?release[-_ ]?statements?|"
    r"non[-_ ]?complete[-_ ]?(?:v1[-_ ]?)?release[-_ ]?statements?)",
    re.IGNORECASE,
)
STRICT_PROMOTION_EVIDENCE_SCHEMA_DENY_MARKERS = re.compile(
    r"(?:candidate|placeholder(?:[-_ ]?provenance)?|planning|approved[-_ ]?(?:runtime[-_ ]?)?bundle|approved[-_ ]?runtime[-_ ]?evidence[-_ ]?binding|accepted[-_ ]?runtime[-_ ]?evidence[-_ ]?preconditions?|accepted[-_ ]?artifact[-_ ]?class(?:[-_ ]?(?:artifacts?|metadata|reports?|status))?|binding[-_ ]?required(?:[-_ ]?(?:artifacts?|metadata|reports?|status))?|plugin[-_ ]?hub|package[-_ ]?shape|package[-_ ]?(?:exact|non[-_ ]?exact)|core[-_ ]?first|"
    r"activation[-_ ]?preconditions?|pre[-_ ]?activation[-_ ]?consistency|"
    r"closure[-_ ]?(?:artifacts?|reports?|requests?|summar(?:y|ies))?|evidence[-_ ]?closure(?:[-_ ]?(?:artifacts?|reports?|requests?|summar(?:y|ies)))?|"
    r"contract[-_ ]?review(?:[-_ ]?inputs?)?|"
    r"diagnostic[-_ ]?(?:only[-_ ]?)?(?:principal[-_ ]?)?lifecycle|"
    r"ready[-_ ]?log[-_ ]?evidence[-_ ]?splits?(?:[-_ ]?(?:diagnostic|evidence|readiness|ready|reports?|status|summar(?:y|ies)))?|"
    r"(?:player[-_ ]?principal[-_ ]?)?lifecycle[-_ ]?event[-_ ]?splits?(?:[-_ ]?(?:diagnostic|evidence|readiness|ready|reports?|status|summar(?:y|ies)))?|"
    r"post[-_ ]?runtime[-_ ]?contract[-_ ]?gap(?:[-_ ]?(?:diagnostic|readiness|ready|reports?|status|summar(?:y|ies)))?|"
    r"route[-_ ]?samples?(?:[-_ ]?(?:diagnostic|evidence|readiness|ready|reports?|status|summar(?:y|ies)))?|"
    r"check[-_ ]?join[-_ ]?in[-_ ]?progress(?:[-_ ]?(?:diagnostic|offline|candidate(?:[-_ ]?only)?|accept(?:ed|ance)|readiness|reports?|status|evidence|artifacts?|summar(?:y|ies)|source))?|"
    r"(?:session[-_ ]?start[-_ ]?rejected|rejected[-_ ]?session[-_ ]?start)(?:[-_ ]?(?:diagnostic|offline|candidate(?:[-_ ]?only)?|accept(?:ed|ance)|readiness|reports?|status|evidence|artifacts?|summar(?:y|ies)|source|check[-_ ]?join[-_ ]?in[-_ ]?progress))+|"
    r"(?:diagnostic|offline|candidate(?:[-_ ]?only)?)(?:[-_ ]?(?:check[-_ ]?join[-_ ]?in[-_ ]?progress|session[-_ ]?start[-_ ]?rejected|rejected[-_ ]?session[-_ ]?start)(?:[-_ ]?(?:accept(?:ed|ance)|readiness|reports?|status|evidence|artifacts?|summar(?:y|ies)|source))?)+|"
    r"helpers?|helper[-_ ]?artifacts?|"
    r"players?[-_ ]?identity[-_ ]?principal[-_ ]?invalidation[-_ ]?policy|"
    r"players?[-_ ]?identity[-_ ]?runtime[-_ ]?principal[-_ ]?lifecycle[-_ ]?evidence|"
    r"players?[-_ ]?identity[-_ ]?lifecycle[-_ ]?anchor[-_ ]?candidates?|"
    r"(?:session[-_ ]?start(?:[-_ ]?and)?[-_ ]?end|start[-_ ]?end)(?:[-_ ]?only)?[-_ ]?evidence|"
    r"standing[-_ ]?(?:launch[-_ ]?)?authority|"
    r"(?:offline[-_ ]?)?hardening(?:[-_ ]?(?:artifacts?|metadata|reports?|status|summar(?:y|ies)))?|"
    r"players?[-_ ]?principal[-_ ]?passive[-_ ]?snapshots?|"
    r"passive[-_ ]?(?:snapshots?|observations?|captures?)|"
    r"passive[-_ ]?activity[-_ ]?triage(?:[-_ ]?non[-_ ]?evidence)?|"
    r"observer[-_ ]?event[-_ ]?triage(?:[-_ ]?non[-_ ]?evidence)?|"
    r"copied[-_ ]?logs?[-_ ]?only(?:[-_ ]?(?:artifacts?|reports?|status))?|"
    r"(?:mission[-_ ]?)?copied[-_ ]?bool(?:[-_ ]?policy[-_ ]?slices?)?|"
    r"(?:internal[-_ ]?)?fixture[-_ ]?boundar(?:y|ies)|"
    r"(?:passive[-_ ]?)?latest[-_ ]?summar(?:y|ies)|"
    r"passive[-_ ]?snapshot[-_ ]?(?:latest|diff)|"
    r"closed[-_ ]?(?:agent|worker)(?:[-_ ]?(?:notes?|reports?|status|summar(?:y|ies)))?|"
    r"(?:players?[-_ ]?)?notice[-_ ]?actions?|"
    r"confirmed[-_ ]?(?:beta[-_ ]?)?notice(?:[-_ ]?(?:reports?|sent|status|attestations?|confirmation|confirmed))?|"
    r"notice[-_ ]?reports?|"
    r"(?:players?[-_ ]?)?notice[-_ ]?dry[-_ ]?runs?|"
    r"beta[-_ ]?notices?(?:[-_ ]?(?:prep|send|sent|attestation|confirmed))?|"
    r"discord[-_ ]?notices?|"
    r"(?:discord[-_ ]?)?beta[-_ ]?bridge(?:[-_ ]?(?:bot[-_ ]?)?notice|[-_ ]?config|[-_ ]?events?|[-_ ]?plans?|[-_ ]?reports?|[-_ ]?status)?|"
    r"discord[-_ ]?beta[-_ ]?bot[-_ ]?notice|discord[-_ ]?bot[-_ ]?notice|bot[-_ ]?notice|"
    r"multi[-_ ]?surface[-_ ]?beta[-_ ]?packs?|"
    r"principal[-_ ]?invalidation[-_ ]?policy|"
    r"lifecycle[-_ ]?anchor[-_ ]?candidates?|"
    r"request[-_ ]?(?:checks?|check[-_ ]?readiness|packs?|artifacts?|manifests?|preflights?)|"
    r"(?:approved[-_ ]?)?(?:runtime[-_ ]?)?bundle[-_ ]?requests?|"
    r"public[-_ ]?reachability|"
    r"(?:route[-_ ]?bound[-_ ]?)?identity[-_ ]?source(?:[-_ ]?(?:forward|forwarded|forwarding))?|"
    r"player[-_ ]?principal[-_ ]?lifecycle[-_ ]?window[-_ ]?request[-_ ]?checks?|"
    r"runtime[-_ ]?window(?:[-_ ]?(?:plans?|planners?|executors?|execution|activations?|manifests?|preflights?|prepar(?:ed|ation)?|readiness|ready|requests?|status))?|"
    r"runtime[-_ ]?window[-_ ]?closure(?:[-_ ]?(?:artifacts?|reports?|requests?|summar(?:y|ies)|executors?))?|"
    r"runtime[-_ ]?window[-_ ]?executor[-_ ]?closure(?:[-_ ]?(?:artifacts?|reports?|requests?|summar(?:y|ies)))?|"
    r"approved[-_ ]?runtime[-_ ]?manifests?|"
    r"operator[-_ ]?(?:approval[-_ ]?)?receipts?|window[-_ ]?manifests?|"
    r"(?:(?:post[-_ ]?window[-_ ]?)?runtime[-_ ]?replay(?:[-_ ]?fixtures?)?|"
    r"post[-_ ]?window[-_ ]?replay(?:[-_ ]?fixtures?)?)|"
    r"install(?:ed)?[-_ ]?(?:sdk[-_ ]?)?(?:evidence|layout|package|package[-_ ]?shape)|"
    r"(?:install|installed|package)[-_ ]?(?:sdk[-_ ]?)?(?:package|shape|check|evidence|layout|success|succeed(?:ed)?|install|installed)(?:[-_ ]?(?:checks?|ok|ready|reports?|status|success|succeed(?:ed)?))?|"
    r"(?:generated[-_ ]?)?(?:promotion[-_ ]?)?cert(?:ificate)?(?:[-_ ]?(?:artifacts?|bindings?|build|builder|generation|metadata|outputs?|reports?|status|summar(?:y|ies)))?|"
    r"(?:public[-_ ]?debug|debug[-_ ]?public)[-_ ]?boundary(?:[-_ ]?(?:fix(?:es)?|metadata|reports?|status|summar(?:y|ies)))?|"
    r"find[-_ ]?package(?:[-_ ]?(?:obelisk|sdk|components?|success|succeed(?:ed)?|found|ready|reports?|status))?|"
    r"cmake[-_ ]?(?:package|config|components?)(?:[-_ ]?(?:check|found|ready|reports?|status|success|succeed(?:ed)?))?|"
    r"component[-_ ]?sdk(?:[-_ ]?(?:check|found|ready|reports?|status|success|succeed(?:ed)?))?|"
    r"(?:abi|sdk)[-_ ]?consumer[-_ ]?guardrails?|"
    r"(?:post[-_ ]?init|after[-_ ]?init|outside[-_ ]?init)[-_ ]?call[-_ ]?process[-_ ]?event(?:[-_ ]?(?:guardrails?|tests?|skipped|rejected|passed|status|reports?))?|"
    r"call[-_ ]?process[-_ ]?event[-_ ]?(?:post[-_ ]?init|after[-_ ]?init|outside[-_ ]?init)(?:[-_ ]?(?:guardrails?|tests?|skipped|rejected|passed|status|reports?))?|"
    r"package[-_ ]?(?:exact|non[-_ ]?exact)|"
    r"live[-_ ]?(?:validation|ops)(?:[-_ ]?sidecars?)?|"
    r"install(?:ed)?[-_ ]?runtime(?:[-_ ]?(?:checks?|ok|ready|reports?|status))?|"
    r"runtime[-_ ]?install(?:ed)?(?:[-_ ]?(?:checks?|ok|ready|reports?|status))?|"
    r"broadcasts?(?:[-_ ]?(?:checks?|ok|reports?|sent|status|notices?))?|"
    r"rcon(?:[-_ ]?(?:checks?|commands?|counts?|player[-_ ]?counts?|ok|ready|reachable|reports?|service|status))?|"
    r"transfer[-_ ]?(?:script[-_ ]?struct|baccept)[-_ ]?readiness|"
    r"dino[-_ ]?scalar[-_ ]?readiness|"
    r"scalar[-_ ]?only[-_ ]?readiness|"
    r"buff[-_ ]?status[-_ ]?readiness|"
    r"tribe[-_ ]?scalar[-_ ]?boundary[-_ ]?readiness|"
    r"scalar[-_ ]?boundary[-_ ]?readiness|"
    r"(?:redacted[-_ ]?)?ufunction[-_ ]?(?:chain[-_ ]?)?snapshots?|"
    r"ufunction[-_ ]?snapshot[-_ ]?manifests?|"
    r"redacted[-_ ]?ufunction[-_ ]?signatures|"
    r"(?:route[-_ ]?gate[-_ ]?)?post[-_ ]?evidence[-_ ]?p0[-_ ]?lock[-_ ]?simulation|"
    r"route[-_ ]?(?:simulations?|lock[-_ ]?simulations?|check[-_ ]?readiness|readiness)|"
    r"post[-_ ]?evidence[-_ ]?identity[-_ ]?locks?|identity[-_ ]?locks?|"
    r"copied[-_ ]?data|(?:chat[-_ ]?message|gameplay[-_ ]?policy[-_ ]?event|event|chat)[-_ ]?seeds?|"
    r"static[-_ ]?(?:orientation|candidate|target|discovery)|native[-_ ]?ufunction[-_ ]?registration[-_ ]?static[-_ ]?discovery|"
    r"admin[-_ ]?thunks?|orientation|preflight|readiness|"
    r"report[-_ ]?only|readiness[-_ ]?only|"
    r"scoped[-_ ]?non[-_ ]?complete(?:[-_ ]?only)?|"
    r"scoped[-_ ]?(?:non[-_ ]?complete[-_ ]?)?(?:v1[-_ ]?)?release[-_ ]?statements?|"
    r"non[-_ ]?complete[-_ ]?(?:v1[-_ ]?)?release[-_ ]?statements?|"
    r"item[-_ ]?return[-_ ]?only|return[-_ ]?only|descriptor[-_ ]?preflight|"
    r"descriptor[-_ ]?catalog|consume[-_ ]?only|evidence[-_ ]?only)",
    re.IGNORECASE,
)
CANONICAL_DEBUG_ONLY_SURFACE_IDS = {
    "obelisk.debug_raw_process_event.v1",
}
NON_PROMOTIONAL_ARTIFACT_REFERENCE_KEYS = {
    "argv",
    "artifact",
    "artifacts",
    "command",
    "commands",
    "current_evidence",
    "fixture_path",
    "input",
    "inputs",
    "manifest",
    "manifests",
    "manifest_entry",
    "output",
    "outputs",
    "output_name",
    "path",
    "paths",
    "producer",
    "producers",
    "readiness",
    "readiness_artifact",
    "readiness_artifacts",
    "report",
    "reports",
    "source",
    "sources",
    "source_artifact",
    "source_artifacts",
    "source_binding",
    "source_bindings",
    "source_manifest",
    "source_manifests",
    "source_snapshot",
    "source_snapshots",
}
STRUCTURED_PROMOTION_EVIDENCE_REFERENCE_KEYS = {
    "public_contract_readiness_report",
}
PUBLIC_CONTRACT_REVIEW_STATUS_REFERENCE_KEYS = {
    "public_contract_readiness_report",
}
PUBLIC_CONTRACT_REVIEW_STATUS_REFERENCE_ALLOWED_SURFACE_IDS = {
    "obelisk.player_identity.v1",
}
NON_PROMOTIONAL_ARTIFACT_REFERENCE_KEY_SUFFIXES = (
    "_artifact",
    "_artifacts",
    "_command",
    "_commands",
    "_input",
    "_inputs",
    "_output",
    "_outputs",
    "_path",
    "_paths",
    "_readiness",
    "_report",
    "_reports",
    "_snapshot",
    "_snapshots",
    "_source",
    "_sources",
)
NON_PROMOTIONAL_ARTIFACT_REFERENCE_KEY_MARKERS = re.compile(
    r"(?:"
    r"(?:player_principal_)?passive_snapshot(?:_(?:diff|latest))?|"
    r"passive_activity_triage(?:_non_evidence)?|"
    r"observer_event_triage(?:_non_evidence)?|"
    r"passive_latest_summary|latest_summary|passive_observation|passive_capture|"
    r"closed_(?:agent|worker)(?:_(?:notes?|reports?|status|summar(?:y|ies)))?|"
    r"copied_logs?_only(?:_(?:artifacts?|reports?|status))?|"
    r"diagnostic(?:_only)?(?:_runtime)?(?:_summary|_lifecycle|_candidates?)?|"
    r"ready_log_evidence_splits?(?:_(?:diagnostic|evidence|readiness|ready|reports?|status|summar(?:y|ies)))?|"
    r"(?:player_principal_)?lifecycle_event_splits?(?:_(?:diagnostic|evidence|readiness|ready|reports?|status|summar(?:y|ies)))?|"
    r"post_runtime_contract_gap(?:_(?:diagnostic|readiness|ready|reports?|status|summar(?:y|ies)))?|"
    r"route_samples?(?:_(?:diagnostic|evidence|readiness|ready|reports?|status|summar(?:y|ies)))?|"
    r"approved_runtime_evidence_binding|"
    r"(?:session_start(?:_and)?_end|start_end)(?:_only)?_evidence|"
    r"standing_(?:launch_)?authority|"
    r"check_join_in_progress(?:_(?:diagnostic|offline|candidate(?:_only)?|accept(?:ed|ance)|readiness|reports?|status|evidence|artifacts?|summar(?:y|ies)|source))?|"
    r"(?:session_start_rejected|rejected_session_start)(?:_(?:diagnostic|offline|candidate(?:_only)?|accept(?:ed|ance)|readiness|reports?|status|evidence|artifacts?|summar(?:y|ies)|source|check_join_in_progress))+|"
    r"(?:diagnostic|offline|candidate(?:_only)?)(?:_(?:check_join_in_progress|session_start_rejected|rejected_session_start)(?:_(?:accept(?:ed|ance)|readiness|reports?|status|evidence|artifacts?|summar(?:y|ies)|source))?)+|"
    r"activation_preconditions?|pre_activation_consistency|"
    r"closure_(?:artifacts?|reports?|requests?|summar(?:y|ies))|evidence_closure(?:_(?:artifacts?|reports?|requests?|summar(?:y|ies)))?|"
    r"request_(?:checks?|check_readiness|packs?|artifacts?|manifests?|preflights?)|"
    r"(?:approved_)?(?:runtime_)?bundle_requests?|"
    r"accepted_artifact_class(?:_(?:artifacts?|metadata|reports?|status))?|"
    r"binding_required(?:_(?:artifacts?|metadata|reports?|status))?|"
    r"public_reachability|"
    r"(?:reviewed_)?(?:identity_)?public_contract(?:_(?:artifact|decisions?|input|readiness|records?|report|review))?|"
    r"contract_review(?:_(?:artifact|decisions?|input|readiness|records?|report))?|"
    r"(?:offline_?)?hardening(?:_?(?:artifacts?|metadata|reports?|status|summar(?:y|ies)))?|"
    r"(?:route_bound_)?identity_source(?:_(?:forward|forwarded|forwarding))?|"
    r"confirmed_(?:beta_)?notice(?:_(?:reports?|sent|status|attestations?|confirmation|confirmed))?|"
    r"notice_reports?|"
    r"window_request_check|"
    r"player_principal_lifecycle_window_request(?:_check)?|"
    r"runtime_window(?:_(?:plans?|planners?|executors?|execution|activations?|manifests?|preflights?|prepar(?:ed|ation)?|readiness|ready|requests?|status))?|"
    r"runtime_window_closure(?:_(?:artifacts?|reports?|requests?|summar(?:y|ies)|executors?))?|"
    r"runtime_window_executor_closure(?:_(?:artifacts?|reports?|requests?|summar(?:y|ies)))?|"
    r"approved_runtime_manifests?|"
    r"(?:player_)?notice_action|player_notice|notice_dry_run|discord_notice|"
    r"beta_notice(?:_(?:prep|send|sent|attestation|confirmed))?|"
    r"(?:discord_)?beta_bridge(?:_(?:bot_?)?notice|_config|_events?|_plans?|_reports?|_status)?|"
    r"discord_beta_bot_notice|discord_bot_notice|bot_notice|"
    r"multi_surface_beta_packs?|"
    r"(?:active_?)?passive_monitors?(?:_(?:session|status|summary|snapshot|tick|ticks))?|"
    r"active_monitors?(?:_(?:session|status|summary|snapshot|tick|ticks))?|"
    r"install(?:ed)?_runtime(?:_(?:checks?|ok|ready|reports?|status))?|"
    r"runtime_install(?:ed)?(?:_(?:checks?|ok|ready|reports?|status))?|"
    r"broadcasts?(?:_(?:checks?|ok|reports?|sent|status|notices?))?|"
    r"rcon(?:_(?:checks?|commands?|counts?|player_?counts?|ok|ready|reachable|reports?|service|status))?|"
    r"(?:installed_sdk_)?package_shape|sdk_package_shape|"
    r"install(?:ed)?_sdk(?:_package_shape|_evidence|_layout|_package)?|"
    r"(?:install|installed|package)_(?:sdk_)?(?:package|shape|check|evidence|layout|success|succeeded|install|installed)(?:_(?:checks?|ok|ready|reports?|status|success|succeeded))?|"
    r"(?:generated_?)?(?:promotion_?)?cert(?:ificate)?(?:_?(?:artifacts?|bindings?|build|builder|generation|metadata|outputs?|reports?|status|summar(?:y|ies)))?|"
    r"(?:public_?debug|debug_?public)_?boundary(?:_?(?:fix(?:es)?|metadata|reports?|status|summar(?:y|ies)))?|"
    r"find_package(?:_(?:obelisk|sdk|components?|success|succeeded|found|ready|reports?|status))?|"
    r"cmake_(?:package|config|components?)(?:_(?:check|found|ready|reports?|status|success|succeeded))?|"
    r"component_sdk(?:_(?:check|found|ready|reports?|status|success|succeeded))?|"
    r"(?:abi|sdk)_consumer_guardrails?|"
    r"(?:post_init|after_init|outside_init)_call_process_event(?:_(?:guardrails?|tests?|skipped|rejected|passed|status|reports?))?|"
    r"call_process_event_(?:post_init|after_init|outside_init)(?:_(?:guardrails?|tests?|skipped|rejected|passed|status|reports?))?|"
    r"package_(?:exact|non_?exact)|"
    r"install_evidence|package_shape_evidence|"
    r"(?:mission_)?copied_bool(?:_policy_slices?)?|"
    r"(?:internal_)?fixture_boundar(?:y|ies)|"
    r"report_only|readiness_only|"
    r"command_chat_response_route_planning|route_planning(?:_report)?|"
    r"planning_route(?:_report)?|"
    r"transfer_(?:script_?struct|baccept)_readiness|"
    r"dino_scalar_readiness|scalar_only_readiness|"
    r"buff_status_readiness|"
    r"tribe_scalar_boundary_readiness|scalar_boundary_readiness|"
    r"source_bindings?|source_manifest|source_snapshot|snapshot_root|fixture_path|"
    r"ufunction_snapshot|ufunction_chain_snapshot|redacted_ufunction_signatures|"
    r"(?:route_gate_)?post_evidence_p0_lock_simulation|"
    r"route_(?:simulation|lock_simulation|check_readiness|readiness)|"
    r"post_evidence_identity_lock|identity_lock|"
    r"scoped_non_complete"
    r")",
    re.IGNORECASE,
)
NON_PROMOTIONAL_ARTIFACT_REFERENCE_VALUE_MARKERS = re.compile(
    r"(?:"
    r"(?:player_principal_)?passive_snapshot(?:_(?:diff|latest))?|"
    r"passive_activity_triage(?:_non_evidence)?|"
    r"observer_event_triage(?:_non_evidence)?|"
    r"passive_latest_summary|latest_summary|passive_observation|passive_capture|"
    r"closed_(?:agent|worker)(?:_(?:notes?|reports?|status|summar(?:y|ies)))?|"
    r"copied_logs?_only(?:_(?:artifacts?|reports?|status))?|"
    r"diagnostic(?:_only)?(?:_runtime)?(?:_summary|_lifecycle|_candidates?)|"
    r"runtime_observer(?:_log)?_diagnostic(?:_only)?_summary|"
    r"ready_log_evidence_splits?(?:_(?:diagnostic|evidence|readiness|ready|reports?|status|summar(?:y|ies)))?|"
    r"(?:player_principal_)?lifecycle_event_splits?(?:_(?:diagnostic|evidence|readiness|ready|reports?|status|summar(?:y|ies)))?|"
    r"post_runtime_contract_gap(?:_(?:diagnostic|readiness|ready|reports?|status|summar(?:y|ies)))?|"
    r"route_samples?(?:_(?:diagnostic|evidence|readiness|ready|reports?|status|summar(?:y|ies)))?|"
    r"approved_runtime_evidence_binding|"
    r"(?:session_start(?:_and)?_end|start_end)(?:_only)?_evidence|"
    r"standing_(?:launch_)?authority|"
    r"check_join_in_progress(?:_(?:diagnostic|offline|candidate(?:_only)?|accept(?:ed|ance)|readiness|reports?|status|evidence|artifacts?|summar(?:y|ies)|source))?|"
    r"(?:session_start_rejected|rejected_session_start)(?:_(?:diagnostic|offline|candidate(?:_only)?|accept(?:ed|ance)|readiness|reports?|status|evidence|artifacts?|summar(?:y|ies)|source|check_join_in_progress))+|"
    r"(?:diagnostic|offline|candidate(?:_only)?)(?:_(?:check_join_in_progress|session_start_rejected|rejected_session_start)(?:_(?:accept(?:ed|ance)|readiness|reports?|status|evidence|artifacts?|summar(?:y|ies)|source))?)+|"
    r"activation_preconditions?|pre_activation_consistency|"
    r"closure_(?:artifacts?|reports?|requests?|summar(?:y|ies))|evidence_closure(?:_(?:artifacts?|reports?|requests?|summar(?:y|ies)))?|"
    r"request_(?:checks?|check_readiness|packs?|artifacts?|manifests?|preflights?)|"
    r"(?:approved_)?(?:runtime_)?bundle_requests?|"
    r"accepted_artifact_class(?:_(?:artifacts?|metadata|reports?|status))?|"
    r"binding_required(?:_(?:artifacts?|metadata|reports?|status))?|"
    r"public_reachability|"
    r"(?:reviewed_)?(?:identity_)?public_contract(?:_(?:artifact|decisions?|input|readiness|records?|report|review))?|"
    r"contract_review(?:_(?:artifact|decisions?|input|readiness|records?|report))?|"
    r"(?:route_bound_)?identity_source(?:_(?:forward|forwarded|forwarding))?|"
    r"confirmed_(?:beta_)?notice(?:_(?:reports?|sent|status|attestations?|confirmation|confirmed))?|"
    r"notice_reports?|"
    r"window_request_check|"
    r"player_principal_lifecycle_window_request(?:_check)?|"
    r"runtime_window(?:_(?:plans?|planners?|executors?|execution|activations?|manifests?|preflights?|prepar(?:ed|ation)?|readiness|ready|requests?|status))?|"
    r"runtime_window_closure(?:_(?:artifacts?|reports?|requests?|summar(?:y|ies)|executors?))?|"
    r"runtime_window_executor_closure(?:_(?:artifacts?|reports?|requests?|summar(?:y|ies)))?|"
    r"approved_runtime_manifests?|"
    r"(?:player_)?notice_action|player_notice|notice_dry_run|discord_notice|"
    r"beta_notice(?:_(?:prep|send|sent|attestation|confirmed))?|"
    r"(?:discord_)?beta_bridge(?:_(?:bot_?)?notice|_config|_events?|_plans?|_reports?|_status)?|"
    r"discord_beta_bot_notice|discord_bot_notice|bot_notice|"
    r"multi_surface_beta_packs?|"
    r"(?:active_?)?passive_monitors?(?:_(?:session|status|summary|snapshot|tick|ticks))?|"
    r"active_monitors?(?:_(?:session|status|summary|snapshot|tick|ticks))?|"
    r"install(?:ed)?_runtime(?:_(?:checks?|ok|ready|reports?|status))?|"
    r"runtime_install(?:ed)?(?:_(?:checks?|ok|ready|reports?|status))?|"
    r"broadcasts?(?:_(?:checks?|ok|reports?|sent|status|notices?))?|"
    r"rcon(?:_(?:checks?|commands?|counts?|player_?counts?|ok|ready|reachable|reports?|service|status))?|"
    r"(?:installed_sdk_)?package_shape|sdk_package_shape|package_shape_evidence|"
    r"install(?:ed)?_sdk(?:_package_shape|_evidence|_layout|_package)?|"
    r"(?:install|installed|package)_(?:sdk_)?(?:package|shape|check|evidence|layout|success|succeeded|install|installed)(?:_(?:checks?|ok|ready|reports?|status|success|succeeded))?|"
    r"find_package(?:_(?:obelisk|sdk|components?|success|succeeded|found|ready|reports?|status))?|"
    r"cmake_(?:package|config|components?)(?:_(?:check|found|ready|reports?|status|success|succeeded))?|"
    r"component_sdk(?:_(?:check|found|ready|reports?|status|success|succeeded))?|"
    r"(?:abi|sdk)_consumer_guardrails?|"
    r"(?:post_init|after_init|outside_init)_call_process_event(?:_(?:guardrails?|tests?|skipped|rejected|passed|status|reports?))?|"
    r"call_process_event_(?:post_init|after_init|outside_init)(?:_(?:guardrails?|tests?|skipped|rejected|passed|status|reports?))?|"
    r"package_(?:exact|non_?exact)|"
    r"install_evidence|"
    r"(?:mission_)?copied_bool(?:_policy_slices?)?|"
    r"(?:internal_)?fixture_boundar(?:y|ies)|"
    r"report_only|readiness_only|"
    r"command_chat_response_route_planning|route_planning(?:_readiness|_report)?|"
    r"planning_route(?:_readiness|_report)?|"
    r"transfer_(?:script_?struct|baccept)_readiness|"
    r"dino_scalar_readiness|scalar_only_readiness|"
    r"buff_status_readiness|"
    r"tribe_scalar_boundary_readiness|scalar_boundary_readiness|"
    r"source_bindings?|source_manifest|source_snapshot|snapshot_root|fixture_path|"
    r"ufunction_snapshot|ufunction_chain_snapshot|redacted_ufunction_signatures|"
    r"ufunction_snapshot_manifest|redacted_ufunction_signatures|"
    r"offline_core|sdk_buffs|candidate_only|"
    r"(?:route_gate_)?post_evidence_p0_lock_simulation|"
    r"route_(?:simulation|lock_simulation|check_readiness|readiness)|"
    r"post_evidence_identity_lock|identity_lock|"
    r"compare_reflection_snapshots|scoped_non_complete"
    r")",
    re.IGNORECASE,
)
MANIFEST_BACKED_BLOCKED_HEADER_SURFACE_IDS = {
    "obelisk.gameplay_tick_callbacks.v1",
    "obelisk.inventory_items_mutation.v1",
    "obelisk.lifecycle_ops_recovery.v1",
    "obelisk.mission_transfer_dino_tribe.v1",
    "obelisk.object_identity_resource_handle.v1",
    "obelisk.operator_ingress_storage.v1",
    "obelisk.player_services_economy_mobility.v1",
    "obelisk.structure_census.v1",
}
ALLOWED_GENERIC_EVIDENCE_DIRS = {
    "tests/sdk_consumer",
    "tests/sdk_installed_consumer",
}
PROMOTION_EVIDENCE_ALLOWED_PREFIXES = (
    "tests/abi/",
    "tests/core/",
    "tests/sdk_consumer/",
    "tests/sdk_installed_consumer/",
    "scripts/test_",
)
GENERIC_SCRIPT_EVIDENCE_DENYLIST = {
    "scripts/check_release_readiness.sh",
    "scripts/check_public_sdk_v1_completion.py",
}
PROMOTED_SURFACE_TEST_EXECUTION_ARTIFACT_SCHEMA = (
    "obelisk.promoted-surface-test-execution-artifact.v1"
)
PROMOTED_SURFACE_TEST_EXECUTION_PRODUCER = "obelisk.promoted-surface-test-execution-runner.v1"
PROMOTED_SURFACE_TEST_EXECUTION_CHECKER = "scripts/check_public_sdk_v1_completion.py"
PROMOTED_SURFACE_TEST_EXECUTION_INPUT_BINDINGS = {
    "public_sdk_surfaces": DEFAULT_MANIFEST,
    "public_header": DEFAULT_PUBLIC_HEADER,
}
PROMOTED_SURFACE_TEST_EXECUTION_COMMIT_KEYS = (
    "head",
    "current_head",
    "git_head",
    "obelisk_commit",
)
PROMOTED_SURFACE_TEST_EXECUTION_HASH_KEYS = (
    "output_hash",
    "output_sha256",
    "stdout_sha256",
    "stderr_sha256",
    "combined_output_sha256",
    "provenance_hash",
    "artifact_hash",
    "artifact_sha256",
)
PROMOTED_SURFACE_TEST_EXECUTION_COMMAND_MARKERS = {
    "obelisk.player_identity.v1": (
        "player_identity",
        "player_identity_promotion",
        "obelisk_player_identity_v1",
    ),
    "obelisk.permissions_admin.v1": (
        "permissions_admin",
        "permissions_admin_promotion",
        "obelisk_permissions_admin_v1",
    ),
    "obelisk.command_chat_response_path.v1": (
        "command_chat_response",
        "command_response",
        "command_chat_response_path",
        "obelisk_command_chat_response_path_v1",
    ),
    "obelisk.commands_replies.v1": (
        "commands_replies",
        "command_replies",
        "obelisk_commands_replies_v1",
    ),
}
SHA256_RE = re.compile(r"[0-9a-fA-F]{64}")
UTC_TIMESTAMP_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})"
)
RELEASE_STATEMENT_CANONICAL_ROW_DELIMITER_RE = r"[:\uff1a\ufe55\ua789\u2236]"
RELEASE_STATEMENT_DETAIL_SEPARATOR_RE = r"[-\u2010-\u2015\u2212]"
RELEASE_STATEMENT_ALTERNATE_ROW_DELIMITER_RE = rf"\s+{RELEASE_STATEMENT_DETAIL_SEPARATOR_RE}\s+"
AFFIRMATIVE_RELEASE_CLAIM_PATTERNS = (
    r"\b(?:complete|full|production|production[- ]?grade|release[- ]?grade|stable)\s+"
    r"(?:[a-z0-9_/+-]+\s+){0,5}(?:sdk|api|support)\b",
    r"\b(?:sdk|api|surface|capability|support)\s+"
    r"(?:is|are|remains?|stays?)\s+"
    r"(?:complete|full|production|production[- ]?grade|release[- ]?grade|stable|available|ready|supported|included|shipped|"
    r"public|promoted)\b",
    r"\b[a-z0-9_ /+-]{2,80}\s+(?:is|are)\s+"
    r"(?:available|ready|supported|included|shipped|public|promoted)\s+in\s+v1\b",
    r"\b(?:this|statement|release)\s+"
    r"(?:declares?|approves?|allows?|authorizes?|ships?)\b.{0,80}"
    r"\b(?:production[- ]?grade|release[- ]?grade)\b.{0,80}\b(?:sdk|api|support)\b",
    r"\b(?:sdk|api|support)\b.{0,80}\b(?:production[- ]?grade|release[- ]?grade)\b.{0,80}"
    r"\b(?:available|included|ready|released|shipped|supported|public|promoted|ships?)\b",
    r"\bv1(?:\.0)?\s+stable\b.{0,80}"
    r"\b(?:available|complete|full|included|production[- ]?ready|ready|released|"
    r"shipped|stable|supported|public|promoted)\b",
)
FORBIDDEN_RELEASE_STATEMENT_BROAD_CLAIM_PATTERNS = (
    r"\b(?:this|statement|release)\s+"
    r"(?:is|declares?|approves?|allows?|authorizes?)\s+"
    r"(?:the\s+)?(?:complete|full|production|stable)\s+"
    r"(?:sdk|api|support)\b",
    r"\bv1(?:\.0)?\s+stable(?:\s+(?:sdk|api|support|release|claim|approval|wording))?\b",
    r"\b(?:obelisk\s+)?v1(?:\.0)?\s+(?:sdk|api|support)?\s*"
    r"(?:is|are|becomes?|became|reaches?)\s+stable\b",
    r"\b(?:sdk|api|support)\s+v?1(?:\.0)?\s*[:,-]\s*"
    r"(?:complete|full|production[- ]?ready|stable)\b",
    r"\b(?:public\s+|obelisk\s+)?(?:sdk|api|support)\s+"
    r"(?:is|are|remains?|stays?)\s+"
    r"(?:complete|full|production[- ]?ready|production[- ]?grade|production|stable|ready|supported|public)\b",
    r"\b(?:ga|generally[- ]available)\s+(?:sdk|api|support)\b.{0,80}"
    r"\b(?:available|published|ready|released|shipped)\b",
    r"\b(?:sdk|api|support)\b.{0,40}\b(?:ga|generally[- ]available)\b",
    r"\b1\.0\s+stable\s+(?:sdk|api|support)\b",
    r"\b(?:complete|full|prod(?:uction)?[- ]?ready|production[- ]?grade|"
    r"release[- ]?grade|production|stable)\s+"
    r"(?:[a-z0-9_/+-]+\s+){1,5}(?:sdk|api|support)\b.{0,80}"
    r"\b(?:allowed|available|complete|full|included|production[- ]?ready|ready|released|"
    r"shipped|stable|supported|public|promoted)\b",
    r"\b(?:this|statement|release)\s+"
    r"(?:is|declares?|approves?|allows?|authorizes?|ships?)\b.{0,80}"
    r"\b(?:complete|full|prod(?:uction)?[- ]?ready|production[- ]?grade|release[- ]?grade|"
    r"production|stable)\s+(?:[a-z0-9_/+-]+\s+){0,5}(?:sdk|api|support)\b",
    r"\b(?:public\s+|obelisk\s+)?(?:sdk|api|support)\s+"
    r"(?:is|are|remains?|stays?)\s+"
    r"(?:release[- ]?grade)\b",
    r"\b(?:public\s+)?(?:sdk|api|support)\b.{0,80}"
    r"\b(?:release[- ]?grade|production[- ]?grade)\b.{0,80}"
    r"\b(?:allowed|available|included|ready|released|shipped|supported|public|promoted|ships?)\b",
    r"\b(?:complete|full|prod(?:uction)?[- ]?ready|production[- ]?grade|release[- ]?grade|production|stable)[- ]+"
    r"(?:sdk|api|support)\b.{0,80}"
    r"\b(?:allowed|available|complete|full|included|production[- ]?ready|ready|released|"
    r"shipped|stable|supported|public|promoted)\b",
    r"\b(?:(?:complete|full|prod(?:uction)?[- ]?ready|production[- ]?grade|"
    r"release[- ]?grade|production|stable)\s*(?:/|,|\band\b|\bor\b)?\s*){1,6}"
    r"(?:sdk|api|support)(?:\s+claim)?\s+"
    r"\b(?:pass(?:es|ed)?|green|satisf(?:y|ies|ied)|unlocks?)\b",
    r"\b(?:public\s+|obelisk\s+)?(?:sdk|api|support)\s+v1(?:\.0)?\s+"
    r"(?:is|are|remains?|stays?)\s+"
    r"\b(?:allowed|available|complete|full|included|production[- ]?ready|production|ready|released|"
    r"shipped|stable|supported|public|promoted)\b",
    r"\b(?:public\s+|obelisk\s+)?(?:sdk|api|support)\s+v1(?:\.0)?\s+"
    r"(?:ships?|launch(?:es|ed)?|goes?\s+live|went\s+live|"
    r"(?:is|are)?\s*generally\s+available|(?:is|are|reaches?)\s+ga)\b",
    r"\b(?:installed\s+|public\s+|release\s+)?(?:sdk\s+)?package\s+"
    r"(?:is|are|becomes?|became)?\s*"
    r"\b(?:allowed|available|published|ready|released|shipped|public)\b",
    r"\b(?:installed\s+|public\s+|release\s+)?(?:sdk\s+)?package\s+"
    r"(?:ships?|launch(?:es|ed)?|goes?\s+live|went\s+live|"
    r"(?:is|are)?\s*generally\s+available|(?:is|are|reaches?)\s+ga)\b",
    r"\b(?:installed\s+sdk|public\s+sdk|release\s+package|installed\s+package|"
    r"public\s+package|sdk|package\s+shape|foundation\s+package)\b.{0,80}"
    r"\bsupport[_ -]?tier\b.{0,40}\brelease[- ]supported(?:\s+seed)?\b",
    r"\bsupport[_ -]?tier\b.{0,40}\brelease[- ]supported(?:\s+seed)?\b.{0,80}"
    r"\b(?:installed\s+sdk|public\s+sdk|release\s+package|installed\s+package|"
    r"public\s+package|sdk|package\s+shape|foundation\s+package)\b",
    r"\b(?:public\s+headers?|installed\s+headers?|obelisk\s*api(?:\.h|\s+h)?|"
    r"cmake\s+package|cmake\s+config|"
    r"obelisk\s*config(?:\.cmake|\s+cmake)?|obelisk\s*targets(?:\.cmake|\s+cmake)?|"
    r"installed\s+sdk\s+consumer\s+tests?|sdk\s+consumer\s+tests?)\b.{0,80}"
    r"\b(?:proves?|validates?|unlocks?|satisf(?:y|ies)|enables?|counts?)\b.{0,80}"
    r"\b(?:runtime\s+readiness|public\s+sdk|public\s+abi|support\s+tier|"
    r"v1(?:\.0)?\s+(?:completion|support)|complete\s+(?:sdk|api)|"
    r"stable\s+(?:sdk|api|support)|production[- ]?ready\s+(?:sdk|api|support))\b",
    r"\b(?:runtime\s+readiness|public\s+sdk|public\s+abi|support\s+tier|"
    r"v1(?:\.0)?\s+(?:completion|support)|complete\s+(?:sdk|api)|"
    r"stable\s+(?:sdk|api|support)|production[- ]?ready\s+(?:sdk|api|support))\b.{0,80}"
    r"\b(?:proves?|validates?|unlocks?|satisf(?:y|ies)|enables?|counts?)\b.{0,80}"
    r"\b(?:public\s+headers?|installed\s+headers?|obelisk\s*api(?:\.h|\s+h)?|"
    r"cmake\s+package|cmake\s+config|"
    r"obelisk\s*config(?:\.cmake|\s+cmake)?|obelisk\s*targets(?:\.cmake|\s+cmake)?|"
    r"installed\s+sdk\s+consumer\s+tests?|sdk\s+consumer\s+tests?)\b",
    r"\bv1(?:\.0)?\s+(?:sdk|api|support)\s+"
    r"(?:ships?|launch(?:es|ed)?|goes?\s+live|went\s+live|"
    r"(?:is|are)?\s*generally\s+available|(?:is|are|reaches?)\s+ga)\b",
    r"\b(?:complete|full|prod(?:uction)?[- ]?ready|production[- ]?grade|release[- ]?grade|production|stable)\s+"
    r"(?:sdk|api|support)\s+"
    r"(?:ships?|launch(?:es|ed)?|goes?\s+live|went\s+live|"
    r"(?:is|are)?\s*generally\s+available)\b",
    r"\b(?:this|statement|release)\s+"
    r"(?:is|declares?|approves?|allows?|authorizes?)\s+"
    r"(?:a\s+)?v1(?:\.0)?\s+stable(?:\s+(?:sdk|api|support|release|claim))?\b",
    r"\b(?:player[-_ ]?identity|player[-_ ]?principal|playeridentity|"
    r"permissions?/admin|permissions?[-_ ]?admin|permissionsadmin|permissions?|admin|"
    r"command[-_ ]?(?:chat[-_ ]?)?responses?|commandresponse|"
    r"commands?/replies|commands?[-_ ]?replies|command[-_ ]?router|"
    r"inventory[-_ ]?(?:identity|lookup|mutation)|item[-_ ]?(?:identity|lookup|mutation|handles?)|"
    r"give[-_ ]?item|remove[-_ ]?item|object[-_ ]?identity|uobject[-_ ]?identity|"
    r"object[-_ ]?lookup|resource[-_ ]?handles?|resourcehandle|missions?|"
    r"buff(?:/status|[-_ ]?status)?|buffstatus|buffs?)\s+"
    r"(?:sdk|api|surface|support)\b.{0,80}"
    r"\b(?:available|complete|full|included|production[- ]?ready|ready|released|"
    r"shipped|stable|supported|public|promoted)\b",
    r"\b(?:available|complete|full|included|production[- ]?ready|ready|released|"
    r"shipped|stable|supported|public|promoted)\b.{0,80}"
    r"\b(?:player[-_ ]?identity|player[-_ ]?principal|playeridentity|"
    r"permissions?/admin|permissions?[-_ ]?admin|permissionsadmin|permissions?|admin|"
    r"command[-_ ]?(?:chat[-_ ]?)?responses?|commandresponse|"
    r"commands?/replies|commands?[-_ ]?replies|command[-_ ]?router|"
    r"inventory[-_ ]?(?:identity|lookup|mutation)|item[-_ ]?(?:identity|lookup|mutation|handles?)|"
    r"give[-_ ]?item|remove[-_ ]?item|object[-_ ]?identity|uobject[-_ ]?identity|"
    r"object[-_ ]?lookup|resource[-_ ]?handles?|resourcehandle|missions?|"
    r"buff(?:/status|[-_ ]?status)?|buffstatus|buffs?)\s+"
    r"(?:sdk|api|surface|support)\b",
    r"\bv1(?:\.0)?\s+(?:includes?|supports?|ships?|exposes?|provides?|offers?|covers?|has)\b.{0,80}"
    r"\b(?:player[-_ ]?identity|player[-_ ]?principal|playeridentity|"
    r"permissions?/admin|permissions?[-_ ]?admin|permissionsadmin|permissions?|admin|"
    r"command[-_ ]?(?:chat[-_ ]?)?responses?|commandresponse|"
    r"commands?/replies|commands?[-_ ]?replies|command[-_ ]?router|"
    r"inventory[-_ ]?(?:identity|lookup|mutation)|item[-_ ]?(?:identity|lookup|mutation|handles?)|"
    r"give[-_ ]?item|remove[-_ ]?item|object[-_ ]?identity|uobject[-_ ]?identity|"
    r"object[-_ ]?lookup|resource[-_ ]?handles?|resourcehandle|missions?|"
    r"buff(?:/status|[-_ ]?status)?|buffstatus|buffs?)\b",
    r"\b(?:player[-_ ]?identity|player[-_ ]?principal|playeridentity|"
    r"permissions?/admin|permissions?[-_ ]?admin|permissionsadmin|permissions?|admin|"
    r"command[-_ ]?(?:chat[-_ ]?)?responses?|commandresponse|"
    r"commands?/replies|commands?[-_ ]?replies|command[-_ ]?router|"
    r"inventory[-_ ]?(?:identity|lookup|mutation)|item[-_ ]?(?:identity|lookup|mutation|handles?)|"
    r"give[-_ ]?item|remove[-_ ]?item|object[-_ ]?identity|uobject[-_ ]?identity|"
    r"object[-_ ]?lookup|resource[-_ ]?handles?|resourcehandle|missions?|"
    r"buff(?:/status|[-_ ]?status)?|buffstatus|buffs?)\s+"
    r"(?:is|are)?\s*(?:included|supported|shipped|exposed|provided|offered|covered|available|public)?\s*"
    r"(?:in|for|part\s+of)\s+v1(?:\.0)?\b",
    r"\b(?:inventory\s+sdk|items\s+sdk)\b.{0,80}"
    r"\b(?:available|complete|full|included|production[- ]?ready|ready|released|shipped|stable|supported|public|promoted)\b",
    r"\b(?:available|complete|full|included|production[- ]?ready|ready|released|shipped|stable|supported|public|promoted)\b"
    r".{0,80}\b(?:inventory\s+sdk|items\s+sdk)\b",
    r"\b(?:resourcehandle|resource[- ]?handle|object[- ]?identity|object[- ]?lookup)\s+"
    r"(?:sdk|api|surface|support)?\b.{0,80}"
    r"\b(?:available|complete|full|included|production[- ]?ready|ready|released|shipped|stable|supported|public|promoted)\b",
    r"\b(?:available|complete|full|included|production[- ]?ready|ready|released|shipped|stable|supported|public|promoted)\b"
    r".{0,80}\b(?:resourcehandle|resource[- ]?handle|object[- ]?identity|object[- ]?lookup)\s+"
    r"(?:sdk|api|surface|support)?\b",
    r"\b(?:plugin\s+hub|pluginhub)\b.{0,80}"
    r"\b(?:available|complete|full|included|opens?|production[- ]?ready|public|publication|published|"
    r"ready|release[- ]?scope|released|shipped|stable|supported)\b",
    r"\b(?:available|complete|full|included|production[- ]?ready|public|publication|published|"
    r"ready|release[- ]?scope|released|shipped|stable|supported|opens?)\b"
    r".{0,80}\b(?:plugin\s+hub|pluginhub)\b",
    r"\b(?:candidate(?:[- ]?only)?|planning(?:[- ]?only)?|orientation(?:[- ]?only)?|"
    r"consume[- ]?only|evidence[- ]?only|preflight|readiness|foundation|package[- ]?shape|"
    r"static[- ]?orientation)\b.{0,100}"
    r"\b(?:available|complete|full|included|production[- ]?ready|public|ready|released|"
    r"shipped|stable|supported|promoted)\b.{0,40}"
    r"\b(?:v1(?:\.0)?|sdk|api|surface|support|claim|release)\b",
    r"\b(?:v1(?:\.0)?|sdk|api|surface|support|claim|release)\b.{0,40}"
    r"\b(?:available|complete|full|included|production[- ]?ready|public|ready|released|"
    r"shipped|stable|supported|promoted)\b.{0,100}"
    r"\b(?:candidate(?:[- ]?only)?|planning(?:[- ]?only)?|orientation(?:[- ]?only)?|"
    r"consume[- ]?only|evidence[- ]?only|preflight|readiness|foundation|package[- ]?shape|"
    r"static[- ]?orientation)\b",
    r"\b(?:candidate(?:[- ]?only)?|planning(?:[- ]?only)?|orientation(?:[- ]?only)?|"
    r"consume[- ]?only|evidence[- ]?only|preflight|readiness|foundation|package[- ]?shape|"
    r"static[- ]?orientation)\b.{0,100}"
    r"\b(?:proves?|validates?|unlocks?|satisf(?:y|ies)|enables?)\b.{0,60}"
    r"\b(?:v1(?:\.0)?\s+stable|complete\s+(?:sdk|api)|full\s+(?:sdk|api)|"
    r"production[- ]?ready\s+(?:sdk|api|support)|production\s+(?:sdk|api|support))\b",
    r"\b(?:package[- ]?shape|installed[- ]?(?:headers?|sdk[- ]?headers?))\b.{0,80}"
    r"\b(?:is|are|declares?|proves?|validates?|unlocks?|satisf(?:y|ies)|enables?)\b.{0,80}"
    r"\b(?:v1(?:\.0)?\s+support|support[- ]?tier|release[- ]?supported|sdk\s+support|"
    r"complete\s+(?:sdk|api)|stable\s+(?:sdk|api|support)|public\s+(?:sdk|api|support)|"
    r"production[- ]?ready\s+(?:sdk|api|support))\b",
    r"\b(?:route[- ]?check|route[- ]?gate|command[- ]?permission[- ]?route(?:[- ]?(?:check|gate))?)\b.{0,80}"
    r"\b(?:accept(?:ed|ance)|pass(?:es|ed)?|green|satisf(?:y|ies|ied)|unlocks?|"
    r"validates?|enables?)\b.{0,80}"
    r"\b(?:complete\s+(?:sdk|api)|full\s+(?:sdk|api)|production[- ]?ready\s+(?:sdk|api|support)|"
    r"stable\s+(?:sdk|api|support)|public\s+sdk|public\s+route|route\s+readiness|"
    r"sdk\s+completion|v1\s+completion|support|status)\b",
    r"\b(?:scoped[- ]?non[- ]?complete(?:[- ]?outcomes?)?|"
    r"scoped[- ]?(?:v1[- ]?)?release[- ]?statements?|release[- ]?statement[- ]?bookkeeping)\b.{0,80}"
    r"\b(?:accept(?:ed|ance)|complete(?:d)?|ready|green|pass(?:es|ed)?|"
    r"satisf(?:y|ies|ied)|unlocks?|counts?|counted|progress)\b",
)
FORBIDDEN_RELEASE_STATEMENT_BROAD_CLAIM_NEGATORS = re.compile(
    r"\b(?:blocked|cannot|does\s+not|do\s+not|excluded|insufficient|limited|"
    r"must\s+not|no|not|post-v1|post v1)\b",
    re.IGNORECASE,
)
FORBIDDEN_RELEASE_STATEMENT_AFFIRMATIVE_NOT_PHRASE = re.compile(
    r"\bnot\s+(?:only|merely|just|simply)\b",
    re.IGNORECASE,
)
FORBIDDEN_RELEASE_STATEMENT_INDEPENDENT_BROAD_CLAIM_HEAD = re.compile(
    r"^\s*(?:the\s+|this\s+|obelisk\s+)?(?:"
    r"(?:complete|full|prod(?:uction)?[- ]?ready|production[- ]?grade|"
    r"release[- ]?grade|production|stable)\s+"
    r"(?:[a-z0-9_/+-]+\s+){0,5}(?:sdk|api|support)\b|"
    r"(?:sdk|api|support)\s+v?1(?:\.0)?\b|"
    r"v1(?:\.0)?\s+(?:stable|(?:sdk|api|support)\b)|"
    r"(?:ga|generally[- ]available)\s+(?:sdk|api|support)\b"
    r")",
    re.IGNORECASE,
)
FORBIDDEN_RELEASE_STATEMENT_BROAD_CLAIM_NEGATED_REMAINDER = re.compile(
    r"^\s*(?:(?:is|are|remains?|stays?)\s+)?"
    r"(?:blocked|cannot|disabled|forbidden|not\s+(?:allowed|approved|authorized|ready)|"
    r"must\s+not|post[- ]?sdk(?:[- ]?complete)?|after\s+sdk\s+completion)\b",
    re.IGNORECASE,
)
FORBIDDEN_RELEASE_STATEMENT_DIRECT_PREFIX_NEGATORS = re.compile(
    r"\b(?:cannot|does\s+not|do\s+not|must\s+not|no|not)\b",
    re.IGNORECASE,
)
FORBIDDEN_RELEASE_STATEMENT_AFFIRMATIVE_TAIL = re.compile(
    r"\b(?:and|but|however|yet)\b.{0,80}"
    r"\b(?:allowed|available|complete|full|included|production[- ]?ready|ready|"
    r"released|shipped|stable|supported|public|promoted|ships?)\b",
    re.IGNORECASE,
)
FORBIDDEN_RELEASE_STATEMENT_NEGATED_GOVERNING_VERB_PREFIX = re.compile(
    r"^(?:"
    r"(?:approves?|allows?|authorizes?|claims?|declares?|enables?|makes?|means?|"
    r"proves?|satisf(?:y|ies|ied)|turns?|unlocks?|validates?)\s+"
    r")?(?:the|a|an)?$|"
    r"^(?:approves?|allows?|authorizes?|claims?|declares?|enables?|makes?|means?|"
    r"proves?|satisf(?:y|ies|ied)|turns?|unlocks?|validates?)$",
    re.IGNORECASE,
)
RELEASE_STATEMENT_OUTCOME_PROGRESS_CLAIM_RE = re.compile(
    r"\b(?:release[-_\s]?statement|scoped[-_\s]?statement|non[-_\s]?p0|"
    r"post[-_\s]?v1|excluded)\b.{0,80}"
    r"\b(?:outcomes?|records?|bookkeeping)\b.{0,80}"
    r"\b(?:ready|complete|completed|pass(?:es|ed)?|green|satisf(?:y|ies|ied)|"
    r"unlocked|counts?|counted|progress)\b|"
    r"\b(?:outcomes?|records?|bookkeeping)\b.{0,80}"
    r"\b(?:ready|complete|completed|pass(?:es|ed)?|green|satisf(?:y|ies|ied)|"
    r"unlocked|counts?|counted|progress)\b.{0,80}"
    r"\b(?:release[-_\s]?statement|scoped[-_\s]?statement|non[-_\s]?p0|"
    r"post[-_\s]?v1|excluded)\b",
    re.IGNORECASE,
)
RELEASE_STATEMENT_OUTCOME_PROGRESS_NEGATORS = re.compile(
    r"\b(?:blocked|cannot|can't|does\s+not|do\s+not|false|insufficient|"
    r"must\s+not|never|no|not|without)\b",
    re.IGNORECASE,
)
PROMOTED_RELEASE_STATEMENT_REVIEWED_EVIDENCE_DETAIL_RE = re.compile(
    r"\b(?:reviewed|validated|verified|accepted|approved)\b.{0,120}"
    r"\b(?:abi|sdk|evidence|tests?|coverage|callbacks?|leaf|leaves|units?)\b|"
    r"\b(?:abi|sdk|evidence|tests?|coverage|callbacks?|leaf|leaves|units?)\b.{0,120}"
    r"\b(?:reviewed|validated|verified|accepted|approved)\b",
    re.IGNORECASE,
)
PROMOTED_RELEASE_STATEMENT_NON_EVIDENCE_DETAIL_RE = re.compile(
    r"\b(?:candidate(?:[-_ ]?only)?|consume[-_ ]?only|core[-_ ]?first|"
    r"copied[-_ ]?logs?[-_ ]?only|"
    r"evidence[-_ ]?only|foundation|package[-_ ]?shape|package[-_ ]?(?:exact|non[-_ ]?exact)|placeholder|"
    r"planning(?:[-_ ]?only)?|plugin[-_ ]?hub|pluginhub|readiness[-_ ]?only|"
    r"release[-_ ]?supported(?:[-_ ]?seeds?)?|support[-_ ]?tiers?|tbd|todo)\b",
    re.IGNORECASE,
)
PROMOTED_RELEASE_STATEMENT_DETAIL_CLAUSE_SPLIT_RE = re.compile(
    r"[.;:\n\r]|(?:\s+\b(?:but|however|yet)\b\s+)",
    re.IGNORECASE,
)
PLUGIN_HUB_DEFERRED_CONTEXT = re.compile(
    r"\b(?:post[- ]?sdk(?:[- ]?complete)?|after\s+sdk\s+completion)\b",
    re.IGNORECASE,
)
PLUGIN_HUB_EXPLICIT_PUBLIC_CLAIM = re.compile(
    r"\b(?:included\s+in\s+v1|public\s+in\s+v1|published\s+for\s+v1|publication\s+is\s+in\s+"
    r"release[- ]?scope|release[- ]?scope|stable\s+sdk\s+includes?)\b",
    re.IGNORECASE,
)
CLAUSE_START_PATTERN = re.compile(r"[.;:\n]|(?:\s+-\s+)")
BROAD_CLAIM_CLAUSE_START_PATTERN = re.compile(
    r"[.;:\n]|(?:\s+-\s+)|(?:\s+\b(?:and|but)\b\s+)",
    re.IGNORECASE,
)
BLOCKED_CONTRACT_HEADER_SYMBOL_PATTERNS = {
    "obelisk.player_identity.v1": (
        re.compile(
            r"(?:PlayerIdentity|PlayerPrincipal|PlayerLookup|PlayerHandle|PlayerId|PlayerID|"
            r"SteamId|SteamID|EOSId|EOSID|PlatformAccountId|PlatformAccountID|"
            r"PlayerName|TribeId|TribeID|NetworkAddress|"
            r"Principal|PrincipalId|PrincipalID|PrincipalHandle|PrincipalGeneration|"
            r"PrincipalScope|ObeliskPrincipal|PlayerSession)"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:PLAYER_IDENTITY|PLAYER_PRINCIPAL|PLAYER_LOOKUP|"
            r"PLAYER_ID|STEAM_ID|EOS_ID|PLATFORM_ACCOUNT_ID|PLAYER_NAME|TRIBE_ID|"
            r"NETWORK_ADDRESS|PRINCIPAL|PRINCIPAL_ID|PRINCIPAL_HANDLE|PRINCIPAL_GENERATION|"
            r"PRINCIPAL_SCOPE|PLAYER_SESSION)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:player_identity|player_principal|player_lookup|principal|principal_id|principal_handle|"
            r"principal_generation|principal_scope|steam_id|eos_id|platform_account_id|"
            r"player_name|tribe_id|network_address|role_id|player_session)(?:_|$)"
        ),
    ),
    "obelisk.permissions_admin.v1": (
        re.compile(
            r"(?:Permission|Permissions|Admin|Authorization|Authorize|Authz|AuthZ|ACL|Acl|"
            r"Moderation|Moderator|BanPlayer|KickPlayer|Grant|Revoke|RoleId|RoleID|"
            r"ReasonFlag|ReasonFlags)"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:PERMISSION|ADMIN|AUTHORIZATION|MODERATION|"
            r"AUTHZ|ACL|BAN|KICK|GRANT|REVOKE|ROLE_ID|REASON_FLAG|REASON_FLAGS)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:permission|permissions|admin|authorization|authority_kind|"
            r"authz|acl|policy_epoch|reason_flag|reason_flags|ban_player|kick_player|grant|revoke|role_id)(?:_|$)"
        ),
    ),
    "obelisk.command_chat_response_path.v1": (
        re.compile(
            r"(?:Command|Reply|Replies|Response|Respond|SendChat|"
            r"ChatSend(?:Api|API|Callback|Handle|Response|Command|Function|WithOwnerTokenHandle)|"
            r"Broadcast|Notice|Moderation)"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:COMMAND|REPLY|RESPONSE|SEND_CHAT|BROADCAST|"
            r"CHAT_SEND_(?:API|CALLBACK|HANDLE|RESPONSE|COMMAND|FUNCTION|WITH_OWNER_TOKEN)|"
            r"NOTICE|MODERATION)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:command|reply|replies|response|response_handle|response_kind|"
            r"send_chat|chat_send_api|chat_send_callback|chat_send_handle|chat_send_response|"
            r"broadcast|notice|moderation|delivery_scope|delivery_flags)(?:_|$)"
        ),
    ),
    "obelisk.commands_replies.v1": (
        re.compile(
            r"(?:Command|Commands|Reply|Replies|CommandRouter|CommandCallback|"
            r"CommandPayload|CommandRegistration|SendChat|"
            r"ChatSend(?:Api|API|Callback|Handle|Response|Command|Function|WithOwnerTokenHandle)|"
            r"Broadcast|Notice|Moderation)"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:COMMAND|COMMANDS|REPLY|REPLIES|SEND_CHAT|"
            r"CHAT_SEND_(?:API|CALLBACK|HANDLE|RESPONSE|COMMAND|FUNCTION|WITH_OWNER_TOKEN)|"
            r"BROADCAST|NOTICE|MODERATION)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:command|commands|command_router|command_callback|command_payload|"
            r"command_registration|reply|replies|send_chat|chat_send_api|chat_send_callback|"
            r"chat_send_handle|chat_send_response|broadcast|notice|moderation)(?:_|$)"
        ),
    ),
    "obelisk.inventory_items_mutation.v1": (
        re.compile(
            r"(?:InventorySdk|ItemsSdk|InventoryLookup|ItemLookup|ItemHandle|GiveItem|"
            r"RemoveItem|GrantItem|InventoryItemsMutation|ItemsMutation|InventoryMutation|"
            r"ItemMutation|Kit|Kits|Reward|Rewards|"
            r"Engram|Progression|ResourceHandle|InventoryComp|InventoryID|InventoryId|"
            r"ItemID|ItemId|ItemNetId|ItemNetID|ItemStack|ItemStackID|ItemStackId|"
            r"CraftBlueprint|AdditionalData|AnActor|anActor)"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:INVENTORY_SDK|ITEMS_SDK|INVENTORY_LOOKUP|"
            r"ITEM_LOOKUP|ITEM_HANDLE|GIVE_ITEM|REMOVE_ITEM|GRANT_ITEM|INVENTORY_MUTATION|"
            r"INVENTORY_ITEMS_MUTATION|ITEMS_MUTATION|ITEM_MUTATION|KIT|KITS|REWARD|REWARDS|ENGRAM|PROGRESSION|"
            r"RESOURCE_HANDLE|INVENTORY_COMP|INVENTORY_ID|ITEM_ID|ITEM_NET_ID|"
            r"ITEM_STACK|ITEM_STACK_ID|CRAFT_BLUEPRINT|ADDITIONAL_DATA|AN_ACTOR)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:inventory_sdk|items_sdk|inventory_lookup|item_lookup|item_handle|"
            r"give_item|remove_item|grant_item|inventory_items_mutation|items_mutation|inventory_mutation|item_mutation|kits?|"
            r"rewards?|engram|progression|resource_handle|inventory_comp|item_net_id|"
            r"inventory_id|item_id|item_stack|item_stack_id|craft_blueprint|additional_data|an_actor)(?:_|$)"
        ),
    ),
    "obelisk.object_identity_resource_handle.v1": (
        re.compile(
            r"(?:ObjectIdentity|UObjectIdentity|ObjectLookup|ResourceHandle|ObjectHandle|"
            r"PostCallbackObject|StructureHandle|ItemHandle|InventoryHandle|DinoHandle|"
            r"TribeHandle|BuffStatusHandle|MissionTransferHandle|AreaPolicyObjectHandle|"
            r"PersistentHandle|SerialHandle|EconomyHandle|MobilityHandle|ObjectID|ObjectId|"
            r"UObjectID|UObjectId|ResourceID|ResourceId)"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:OBJECT_IDENTITY|UOBJECT_IDENTITY|OBJECT_LOOKUP|"
            r"RESOURCE_HANDLE|OBJECT_HANDLE|POST_CALLBACK_OBJECT|STRUCTURE_HANDLE|"
            r"ITEM_HANDLE|INVENTORY_HANDLE|DINO_HANDLE|TRIBE_HANDLE|BUFF_STATUS_HANDLE|"
            r"MISSION_TRANSFER_HANDLE|AREA_POLICY_OBJECT_HANDLE|PERSISTENT_HANDLE|"
            r"SERIAL_HANDLE|ECONOMY_HANDLE|MOBILITY_HANDLE|OBJECT_ID|UOBJECT_ID|"
            r"RESOURCE_ID)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:object_identity|uobject_identity|object_lookup|resource_handle|"
            r"object_handle|post_callback_object|structure_handle|item_handle|"
            r"inventory_handle|dino_handle|tribe_handle|buff_status_handle|"
            r"mission_transfer_handle|area_policy_object_handle|persistent_handle|"
            r"serial_handle|serial_reuse|economy_handle|mobility_handle|object_id|"
            r"uobject_id|resource_id)(?:_|$)"
        ),
    ),
    "obelisk.lifecycle_ops_recovery.v1": (
        re.compile(
            r"(?:PluginWatchdog|CrashRecovery|HotPluginReload|ObeliskHotReload|"
            r"RestartOrchestration|ServerRecovery|OperatorReloadCommand|"
            r"DetachedWorkerIngress|RestartStateRecovery|"
            r"Recovery(?:Api|API|Callback|Handle|Event|State|WithOwnerTokenHandle))"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:PLUGIN_WATCHDOG|CRASH_RECOVERY|HOT_PLUGIN_RELOAD|"
            r"OBELISK_HOT_RELOAD|RESTART_ORCHESTRATION|SERVER_RECOVERY|"
            r"OPERATOR_RELOAD_COMMAND|DETACHED_WORKER_INGRESS|RESTART_STATE_RECOVERY|"
            r"RECOVERY_(?:API|CALLBACK|HANDLE|EVENT|STATE))[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:plugin_watchdog|crash_recovery|hot_plugin_reload|obelisk_hot_reload|"
            r"restart_orchestration|server_recovery|operator_reload_command|"
            r"detached_worker_ingress|restart_state_recovery|recovery_api|recovery_callback|"
            r"recovery_handle|recovery_event|recovery_state)(?:_|$)"
        ),
    ),
    "obelisk.structure_census.v1": (
        re.compile(
            r"(?:StructureEvents|StructureCensus|StructureAggregate|StructureIdentity|"
            r"StructureLookup|StructureHandle|OwnershipLookup|BuildPlacement|"
            r"NoCollision|PinOutcome|Census(?:Api|API|Callback|Handle|Snapshot|WithOwnerTokenHandle))"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:STRUCTURE_EVENTS|STRUCTURE_CENSUS|"
            r"STRUCTURE_AGGREGATE|STRUCTURE_IDENTITY|STRUCTURE_LOOKUP|STRUCTURE_HANDLE|"
            r"OWNERSHIP_LOOKUP|BUILD_PLACEMENT|NO_COLLISION|PIN_OUTCOME|"
            r"CENSUS_(?:API|CALLBACK|HANDLE|SNAPSHOT))[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:structure_events|structure_census|structure_aggregate|"
            r"structure_identity|structure_lookup|structure_handle|ownership_lookup|"
            r"build_placement|no_collision|pin_outcome|census_api|census_callback|"
            r"census_handle|census_snapshot)(?:_|$)"
        ),
    ),
    "obelisk.mission_transfer_dino_tribe.v1": (
        re.compile(
            r"(?:MissionSdk|TransferSdk|DinoSdk|TribeSdk|BuffStatusSdk|BuffSdk|"
            r"Mission|Transfer|Dino|Tribe|BuffStatus|DinoColors|DinoCosmetics|DinoCarryRules|"
            r"TribeMotd|TribeNotice|TribePolicy|TeleportSpawn|CrossMapCorrelation|"
            r"OwnershipLookup|Teleport|Spawn)"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:MISSION_SDK|TRANSFER_SDK|DINO_SDK|TRIBE_SDK|"
            r"BUFF_STATUS_SDK|BUFF_SDK|MISSION|TRANSFER|DINO|BUFF_STATUS|DINO_COLORS|"
            r"DINO_COSMETICS|DINO_CARRY_RULES|(?<!CHAT_SEND_MODE_)TRIBE|TRIBE_MOTD|TRIBE_NOTICE|TRIBE_POLICY|"
            r"TELEPORT_SPAWN|CROSS_MAP_CORRELATION|OWNERSHIP_LOOKUP|TELEPORT|"
            r"SPAWN)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:mission_sdk|transfer_sdk|dino_sdk|tribe_sdk|buff_status_sdk|"
            r"buff_sdk|mission|transfer|dino|tribe|buff_status|dino_colors|dino_cosmetics|"
            r"dino_carry_rules|tribe_motd|tribe_notice|tribe_policy|teleport_spawn|"
            r"cross_map_correlation|ownership_lookup|teleport|spawn)(?:_|$)"
        ),
    ),
    "obelisk.player_services_economy_mobility.v1": (
        re.compile(
            r"(?:PlayerServices|Economy|Shop|Shops|Reward|Rewards|Kit|Kits|Stats|"
            r"Homes|HomeTeleport|Teleport|SafeZone|AreaPolicy|TimedNotice|"
            r"CrossInstancePersistence|Mobility)"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:PLAYER_SERVICES|ECONOMY|SHOP|SHOPS|REWARD|"
            r"REWARDS|KIT|KITS|STATS|HOMES|HOME_TELEPORT|TELEPORT|SAFE_ZONE|"
            r"AREA_POLICY|TIMED_NOTICE|CROSS_INSTANCE_PERSISTENCE|MOBILITY)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:player_services|economy|shops?|rewards?|kits?|stats|homes|"
            r"home_teleport|teleport|safe_zone|area_policy|timed_notice|"
            r"cross_instance_persistence|mobility)(?:_|$)"
        ),
    ),
    "obelisk.operator_ingress_storage.v1": (
        re.compile(
            r"(?:Rcon|RCON|OperatorReload|OperatorCommand|Webhook|Database|StorageSchema|"
            r"StorageMigration|SecretManager|OperatorIngress|ExternalIngress|IngressCallback|"
            r"IngressHandle|CrossInstanceStorage|"
            r"QueueDrain|PoisonMessage|Storage)"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:RCON|OPERATOR_RELOAD|OPERATOR_COMMAND|OPERATOR_INGRESS|WEBHOOK|"
            r"DATABASE|STORAGE_SCHEMA|STORAGE_MIGRATION|SECRET_MANAGER|"
            r"EXTERNAL_INGRESS|INGRESS_CALLBACK|INGRESS_HANDLE|CROSS_INSTANCE_STORAGE|QUEUE_DRAIN|"
            r"POISON_MESSAGE|STORAGE)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:rcon|operator_reload|operator_command|operator_ingress|webhook|database|"
            r"storage_schema|storage_migration|secret_manager|external_ingress|"
            r"ingress_callback|ingress_handle|cross_instance_storage|queue_drain|poison_message|storage)(?:_|$)"
        ),
    ),
    "obelisk.gameplay_tick_callbacks.v1": (
        re.compile(
            r"(?:ServerTick|GameplayTick|ModuleTick|PerFrameHook|FrameHook|"
            r"GameplayTimer|GameplayTimers|TickCallback|TickCallbacks)"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:SERVER_TICK|GAMEPLAY_TICK|MODULE_TICK|"
            r"PER_FRAME_HOOK|FRAME_HOOK|GAMEPLAY_TIMER|GAMEPLAY_TIMERS|"
            r"TICK_CALLBACK|TICK_CALLBACKS)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:server_tick|gameplay_tick|module_tick|per_frame_hook|"
            r"frame_hook|gameplay_timers?|tick_callbacks?)(?:_|$)"
        ),
    ),
}
PUBLIC_CONTRACT_DECISIONS_GLOB = "*_public_contract_decisions.json"
REQUIRED_PUBLIC_CONTRACT_DECISION_MANIFESTS = {
    "obelisk.player_identity.v1": "player_identity_public_contract_decisions.json",
    "obelisk.inventory_item_copied_signals.v1": "inventory_item_copied_signals_public_contract_decisions.json",
    "obelisk.permissions_admin.v1": "permissions_admin_public_contract_decisions.json",
    "obelisk.command_chat_response_path.v1": "command_chat_response_public_contract_decisions.json",
    "obelisk.commands_replies.v1": "commands_replies_public_contract_decisions.json",
}
REQUIRED_ROUTE_GUARDRAIL_DECISION_MANIFESTS = {
    "obelisk.command_principal_authz_response_bridge.v1": "command_principal_authz_response_bridge_decisions.json",
}
REQUIRED_PLANNING_GUARDRAIL_DECISION_MANIFESTS = {
    "obelisk.command_copied_response_intent.planning.v1": "command_copied_response_intent_planning_decisions.json",
    "obelisk.command_copied_response_intent_lifecycle.planning.v1": "command_copied_response_intent_lifecycle_planning_decisions.json",
}
CANONICAL_COMPLETE_SDK_MINIMUM_PROMOTED_DEMAND_FAMILIES = CANONICAL_V1_COMPLETION_BLOCKERS
REVIEWED_V1_COMPLETION_EQUIVALENTS: dict[str, tuple[str, ...]] = {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate that public_sdk_surfaces.json allows a complete v1 SDK claim."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Path to docs/public_sdk_surfaces.json.",
    )
    parser.add_argument(
        "--release-statement",
        type=Path,
        help=(
            "Reviewed v1 SDK release statement that names excluded/post-v1 blockers. "
            "Overrides docs/SCOPED_NON_COMPLETE_V1_RELEASE_STATEMENT.md when that "
            "durable scoped statement exists."
        ),
    )
    parser.add_argument(
        "--public-header",
        type=Path,
        default=DEFAULT_PUBLIC_HEADER,
        help="Public C ABI header checked against blocked public contract decision manifests.",
    )
    parser.add_argument(
        "--contract-decisions-dir",
        type=Path,
        default=DEFAULT_CONTRACT_DECISIONS_DIR,
        help="Directory containing *_public_contract_decisions.json manifests.",
    )
    parser.add_argument("--json", action="store_true", help="Emit the full readiness report as JSON.")
    parser.add_argument(
        "--command-permission-route-gate",
        type=Path,
        default=DEFAULT_COMMAND_PERMISSION_ROUTE_GATE,
        help="Planning-only route gate that guards player identity -> permissions/admin -> command response -> commands/replies.",
    )
    parser.add_argument(
        "--inventory-copied-signals-stability",
        type=Path,
        default=DEFAULT_INVENTORY_COPIED_SIGNALS_STABILITY,
        help=(
            "Offline guardrail that keeps inventory/item copied GameplayPolicyEvent "
            "signals narrow and non-promotional."
        ),
    )
    parser.add_argument(
        "--object-identity-resource-handle-readiness",
        type=Path,
        default=DEFAULT_OBJECT_IDENTITY_RESOURCE_HANDLE_READINESS,
        help=(
            "Offline guardrail that keeps ResourceHandle/object identity lookup "
            "post-v1 and non-promotional."
        ),
    )
    parser.add_argument(
        "--mission-transfer-dino-tribe-outcome-accounting",
        type=Path,
        default=DEFAULT_MISSION_TRANSFER_DINO_TRIBE_OUTCOME_ACCOUNTING,
        help=(
            "Offline guardrail that keeps Mission/Transfer/Dino/Tribe/Buff v1 "
            "umbrella accounting tied to explicit leaf outcomes."
        ),
    )
    parser.add_argument(
        "--structure-census-readiness",
        type=Path,
        default=DEFAULT_STRUCTURE_CENSUS_READINESS,
        help="Offline guardrail that keeps structure census candidate-only and non-promotional.",
    )
    parser.add_argument(
        "--structure-build-policy-offline-intake",
        type=Path,
        default=DEFAULT_STRUCTURE_BUILD_POLICY_OFFLINE_INTAKE,
        help="Offline guardrail that keeps structure build-policy intake planning-only and non-promotional.",
    )
    parser.add_argument(
        "--validate-release-statement-scope",
        action="store_true",
        help=(
            "Validate the supplied release statement's scoped outcome wording without "
            "allowing a complete v1 SDK claim while manifest blockers remain unresolved."
        ),
    )
    parser.add_argument(
        "--allow-scoped-release-statement-extra-records",
        action="store_true",
        help=(
            "Allow explicitly requested extra surface outcome rows during scoped "
            "release-statement validation. Without this, scope validation permits only "
            "non-P0 v1 completion blockers that are already post-v1 or excluded in the manifest."
        ),
    )
    return parser.parse_args()


def resolve_release_statement_for_args(args: argparse.Namespace) -> tuple[Path | None, dict[str, Any]]:
    if args.release_statement is not None:
        return args.release_statement, {
            "release_statement_source": "explicit",
            "default_scoped_release_statement": str(DEFAULT_SCOPED_RELEASE_STATEMENT),
            "default_scoped_release_statement_exists": DEFAULT_SCOPED_RELEASE_STATEMENT.exists(),
            "default_scoped_release_statement_used": False,
            "release_statement_auto_discovery": (
                "not needed because explicit --release-statement was supplied"
            ),
        }
    if DEFAULT_SCOPED_RELEASE_STATEMENT.exists():
        return DEFAULT_SCOPED_RELEASE_STATEMENT, {
            "release_statement_source": "default_scoped_release_statement",
            "default_scoped_release_statement": str(DEFAULT_SCOPED_RELEASE_STATEMENT),
            "default_scoped_release_statement_exists": True,
            "default_scoped_release_statement_used": True,
            "release_statement_auto_discovery": (
                "enabled for fail-closed scoped bookkeeping; pass --release-statement "
                "to override the durable default"
            ),
        }
    auto_discovery = (
        "default scoped release statement missing; pass --release-statement explicitly"
    )
    return None, {
        "release_statement_source": None,
        "default_scoped_release_statement": str(DEFAULT_SCOPED_RELEASE_STATEMENT),
        "default_scoped_release_statement_exists": DEFAULT_SCOPED_RELEASE_STATEMENT.exists(),
        "default_scoped_release_statement_used": False,
        "release_statement_auto_discovery": auto_discovery,
    }


def _helper_subprocess_file_fingerprints(argv: list[str]) -> list[dict[str, Any]]:
    fingerprints: list[dict[str, Any]] = []
    try:
        python_executable = Path(sys.executable).resolve()
    except OSError:
        python_executable = None
    for index, raw_arg in enumerate(argv):
        if not raw_arg or (os.sep not in raw_arg and not Path(raw_arg).is_absolute()):
            continue
        raw_path = Path(raw_arg)
        try:
            path = raw_path.resolve()
        except OSError:
            path = raw_path
        if python_executable is not None and path == python_executable:
            continue
        if not path.is_file():
            fingerprints.append(
                {
                    "index": index,
                    "path": str(path),
                    "exists": False,
                }
            )
            continue
        try:
            data = path.read_bytes()
        except OSError as exc:
            fingerprints.append(
                {
                    "index": index,
                    "path": str(path),
                    "exists": True,
                    "read_error": type(exc).__name__,
                }
            )
            continue
        fingerprints.append(
            {
                "index": index,
                "path": str(path),
                "exists": True,
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return fingerprints


def _helper_subprocess_cache_key(argv: list[str]) -> str:
    env = {
        key: value
        for key, value in os.environ.items()
        if key.startswith("OBELISK_") and key != SUBPROCESS_CACHE_DIR_TEST_ENV
    }
    payload = {
        "schema": "obelisk.public-sdk-v1-completion-helper-subprocess-cache-key.v1",
        "argv": argv,
        "cwd": str(REPO_ROOT),
        "env": env,
        "files": _helper_subprocess_file_fingerprints(argv),
        "python": sys.version,
    }
    data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def helper_subprocess_timeout_seconds() -> float:
    raw = os.environ.get(HELPER_SUBPROCESS_TIMEOUT_ENV)
    if raw is None:
        return HELPER_SUBPROCESS_TIMEOUT_SECONDS
    try:
        parsed = float(raw)
    except ValueError:
        return HELPER_SUBPROCESS_TIMEOUT_SECONDS
    if parsed <= 0:
        return HELPER_SUBPROCESS_TIMEOUT_SECONDS
    return parsed


def timed_out_helper_result(
    argv: list[str],
    exc: subprocess.TimeoutExpired,
) -> subprocess.CompletedProcess[str]:
    stdout = exc.stdout if isinstance(exc.stdout, str) else ""
    stderr = exc.stderr if isinstance(exc.stderr, str) else ""
    timeout = exc.timeout if exc.timeout is not None else helper_subprocess_timeout_seconds()
    message = f"helper subprocess timed out after {timeout:.3g}s: {' '.join(argv)}"
    return subprocess.CompletedProcess(
        argv,
        124,
        stdout,
        f"{stderr}\n{message}\n" if stderr else f"{message}\n",
    )


def run_helper_subprocess(argv: list[str]) -> subprocess.CompletedProcess[str]:
    cache_dir = os.environ.get(SUBPROCESS_CACHE_DIR_TEST_ENV)
    timeout = helper_subprocess_timeout_seconds()
    if not cache_dir:
        try:
            return subprocess.run(
                argv,
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            return timed_out_helper_result(argv, exc)

    cache_path = Path(cache_dir) / f"{_helper_subprocess_cache_key(argv)}.json"
    try:
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        cached = None
    if isinstance(cached, dict) and cached.get("schema") == "obelisk.public-sdk-v1-completion-helper-subprocess-cache.v1":
        return subprocess.CompletedProcess(
            argv,
            int(cached.get("returncode", 1)),
            str(cached.get("stdout", "")),
            str(cached.get("stderr", "")),
        )

    try:
        result = subprocess.run(
            argv,
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        result = timed_out_helper_result(argv, exc)
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = cache_path.with_name(f"{cache_path.name}.{os.getpid()}.tmp")
        tmp_path.write_text(
            json.dumps(
                {
                    "schema": "obelisk.public-sdk-v1-completion-helper-subprocess-cache.v1",
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        os.replace(tmp_path, cache_path)
    except OSError:
        pass
    return result


def run_command_permission_route_gate(
    path: Path,
    public_sdk_surfaces_path: Path,
    public_header_path: Path,
) -> tuple[dict[str, Any], list[str]]:
    blockers: list[str] = []
    resolved_default = DEFAULT_COMMAND_PERMISSION_ROUTE_GATE.resolve()
    try:
        resolved_path = path.resolve()
    except OSError:
        resolved_path = path
    if resolved_path != resolved_default and os.environ.get(ROUTE_GATE_OVERRIDE_TEST_ENV) != "1":
        return (
            {
                "path": str(path),
                "expected_path": str(DEFAULT_COMMAND_PERMISSION_ROUTE_GATE),
                "override_allowed": False,
                "non_claim": "SDK completion uses the canonical route gate; arbitrary route-gate overrides are test-only",
            },
            ["command_permission_route_gate_override_not_allowed"],
        )
    result = run_helper_subprocess(
        [
            sys.executable,
            str(path),
            "--public-sdk-surfaces",
            str(public_sdk_surfaces_path),
            "--public-header",
            str(public_header_path),
            "--json",
        ]
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return (
            {
                "path": str(path),
                "exit_code": result.returncode,
                "parse_error": f"stdout_json_decode_error: {exc}",
                "stderr": result.stderr.strip(),
            },
            ["command_permission_route_gate_output_invalid"],
        )
    if not isinstance(payload, dict):
        return (
            {
                "path": str(path),
                "exit_code": result.returncode,
                "parse_error": "stdout_json_not_object",
                "stderr": result.stderr.strip(),
            },
            ["command_permission_route_gate_output_invalid"],
        )
    public_or_runtime_claims = command_permission_route_gate_public_or_runtime_claims(payload)
    completion_claims_without_blocker = secondary_report_completion_claims_without_blocker(payload)
    post_evidence_p0_lock_simulation_alias_violations = (
        route_gate_post_evidence_p0_lock_simulation_alias_violations(payload)
    )
    if payload.get("schema") != "obelisk.command-permission-route-gate-check.v1":
        blockers.append("command_permission_route_gate_schema_mismatch")
    if result.returncode != 0 or payload.get("valid") is not True:
        blockers.append("command_permission_route_gate_invalid")
    if payload.get("accepted_for_planning") is not True or payload.get("planning_only") is not True:
        blockers.append("command_permission_route_gate_not_planning_only")
    for key in (
        "promotion_ready",
        "public_sdk_ready",
        "public_abi_ready",
        "runtime_ready",
        "public_header_allowed",
        "counts_toward_public_sdk",
        "counts_toward_runtime",
        "counts_toward_v1_completion",
        "public_or_runtime_accounting_allowed",
    ):
        if payload.get(key) is not False:
            blockers.append(f"command_permission_route_gate_{key}_not_false")
    critical_path_phase = payload.get("critical_path_phase") if isinstance(payload.get("critical_path_phase"), dict) else {}
    route_lock = payload.get("route_lock") if isinstance(payload.get("route_lock"), dict) else {}
    current_blocker = critical_path_phase.get("current_blocker")
    current_route_blocker = payload.get("current_route_blocker")
    if not isinstance(current_route_blocker, str) or not current_route_blocker:
        current_route_blocker = current_blocker
    raw_remaining_route_blockers = payload.get("remaining_route_blockers")
    remaining_route_blockers = (
        [
            blocker
            for blocker in raw_remaining_route_blockers
            if isinstance(blocker, str) and blocker
        ]
        if isinstance(raw_remaining_route_blockers, list)
        else []
    )
    if isinstance(current_route_blocker, str) and current_route_blocker:
        remaining_route_blockers = list(
            dict.fromkeys([current_route_blocker, *remaining_route_blockers])
        )
    source_checker_primary_blocker = critical_path_phase.get("source_checker_primary_blocker")
    source_checker_next_blocker = critical_path_phase.get("source_checker_next_blocker")
    source_checker_status = critical_path_phase.get("source_checker_status")
    source_checker_ready = critical_path_phase.get("source_checker_ready")
    source_checker_internal_planning = critical_path_phase.get("source_checker_accepted_for_internal_planning")
    source_ready_aliases = {
        key: critical_path_phase.get(key)
        for key in (
            "ready",
            "source_ready",
            "sources_ready",
            "source_readiness_ready",
            "status_report_ready",
            "runtime_evidence_status_ready",
            "sdk_status_report_ready",
        )
        if key in critical_path_phase
    }
    source_status_aliases = {
        key: critical_path_phase.get(key)
        for key in (
            "source_status",
            "source_state",
            "source_readiness_status",
            "status_report_status",
            "status_report_state",
            "runtime_evidence_status",
        )
        if key in critical_path_phase
    }
    route_blockers = payload.get("blockers", [])
    route_checks = payload.get("checks")
    approved_runtime_evidence_forwarded = False
    if isinstance(route_checks, list):
        for check in route_checks:
            if not isinstance(check, dict) or check.get("name") != "player_identity_public_contract_gap":
                continue
            argv = check.get("argv")
            if isinstance(argv, list) and "--approved-runtime-evidence" in argv:
                approved_runtime_evidence_forwarded = True
                break
    accepted_runtime_evidence_contract = (
        accepted_approved_runtime_principal_lifecycle_bundle_aliases(payload)
    )
    expected_lock_by_blocker = {
        "lifecycle_anchor_first_evidence_provenance_unbound": [
            "bound_lifecycle_anchor_and_principal_policy_sources",
            "reviewed_identity_public_contract",
        ],
        "approved_runtime_evidence_missing": [
            "approved_runtime_principal_lifecycle_evidence",
            "reviewed_identity_public_contract",
        ],
    }
    if accepted_runtime_evidence_contract:
        expected_lock_by_blocker["identity_public_contract_gate_missing"] = [
            "reviewed_identity_public_contract",
        ]
        if current_blocker != "identity_public_contract_gate_missing":
            blockers.append("command_permission_route_gate_accepted_runtime_evidence_blocker_unexpected")
        if current_route_blocker != "identity_public_contract_gate_missing":
            blockers.append("command_permission_route_gate_accepted_runtime_evidence_route_alias_unexpected")
    elif approved_runtime_evidence_forwarded:
        blockers.append("command_permission_route_gate_accepted_runtime_evidence_contract_missing")
    expected_route_lock = expected_lock_by_blocker.get(current_blocker)
    if current_blocker not in expected_lock_by_blocker:
        blockers.append("command_permission_route_gate_default_blocker_mismatch")
    if source_checker_primary_blocker != current_blocker or source_checker_primary_blocker not in expected_lock_by_blocker:
        blockers.append("command_permission_route_gate_default_source_blocker_mismatch")
    if source_checker_next_blocker is not None:
        blockers.append("command_permission_route_gate_default_source_next_blocker_unexpected")
    if source_checker_status != "blocked":
        blockers.append("command_permission_route_gate_source_status_unexpected")
    if source_checker_ready is not False:
        blockers.append("command_permission_route_gate_source_ready_overclaim")
    if any(is_positive_completion_claim_value(value) for value in source_ready_aliases.values()):
        blockers.append("command_permission_route_gate_source_ready_overclaim")
    if any(is_positive_completion_claim_value(value) for value in source_status_aliases.values()):
        blockers.append("command_permission_route_gate_source_status_unexpected")
    if source_checker_internal_planning is not False:
        blockers.append("command_permission_route_gate_source_internal_planning_overclaim")
    if route_blockers:
        blockers.append("command_permission_route_gate_blockers_not_empty")
    if route_lock.get("locked") is not True:
        blockers.append("command_permission_route_gate_lock_unexpected")
    if route_lock.get("blocked_until") != expected_route_lock:
        blockers.append("command_permission_route_gate_default_lock_blocked_until_unexpected")
    if public_or_runtime_claims:
        blockers.append("command_permission_route_gate_public_or_runtime_claims")
    if post_evidence_p0_lock_simulation_alias_violations:
        blockers.append(
            "command_permission_route_gate_post_evidence_p0_lock_simulation_completion_accounting_alias_not_false"
        )
    if completion_claims_without_blocker:
        blockers.append(SECONDARY_REPORT_COMPLETION_CLAIM_WITHOUT_BLOCKER)
    return (
        {
            "path": str(path),
            "exit_code": result.returncode,
            "schema": payload.get("schema"),
            "valid": payload.get("valid"),
            "accepted_for_planning": payload.get("accepted_for_planning"),
            "planning_only": payload.get("planning_only"),
            "promotion_ready": payload.get("promotion_ready"),
            "public_sdk_ready": payload.get("public_sdk_ready"),
            "public_abi_ready": payload.get("public_abi_ready"),
            "runtime_ready": payload.get("runtime_ready"),
            "public_header_allowed": payload.get("public_header_allowed"),
            "counts_toward_public_sdk": payload.get("counts_toward_public_sdk"),
            "counts_toward_runtime": payload.get("counts_toward_runtime"),
            "counts_toward_v1_completion": payload.get("counts_toward_v1_completion"),
            "public_or_runtime_accounting_allowed": payload.get("public_or_runtime_accounting_allowed"),
            "current_route_blocker": current_route_blocker,
            "remaining_route_blockers": remaining_route_blockers,
            "current_blocker": current_blocker,
            "source_checker_primary_blocker": source_checker_primary_blocker,
            "source_checker_next_blocker": source_checker_next_blocker,
            "source_checker_status": source_checker_status,
            "source_checker_ready": source_checker_ready,
            "source_ready_aliases": source_ready_aliases,
            "source_status_aliases": source_status_aliases,
            "source_checker_accepted_for_internal_planning": source_checker_internal_planning,
            "route_lock_blocked_until": route_lock.get("blocked_until"),
            "route_lock_locked": route_lock.get("locked"),
            "approved_runtime_evidence_forwarded": approved_runtime_evidence_forwarded,
            "accepted_runtime_evidence_contract": accepted_runtime_evidence_contract,
            "public_or_runtime_claims": public_or_runtime_claims,
            "completion_claims_without_blocker": completion_claims_without_blocker,
            "post_evidence_p0_lock_simulation_alias_violations": (
                post_evidence_p0_lock_simulation_alias_violations
            ),
            "blockers": route_blockers,
            "completion_gate_accepted": not blockers,
            "completion_gate_blockers": blockers[:],
            "stderr": result.stderr.strip(),
            "non_claim": "planning-only route guard; not v1 completion evidence",
        },
        blockers,
    )


def command_permission_route_gate_public_or_runtime_claims(payload: dict[str, Any]) -> list[str]:
    claims: list[str] = []

    def normalized_key(key: object) -> str:
        separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(key))
        return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")

    def normalized_source(value: object) -> str:
        separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value))
        return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")

    def is_positive_claim_value(value: Any) -> bool:
        if value is True:
            return True
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value != 0
        if isinstance(value, list):
            return any(is_positive_claim_value(item) for item in value)
        if isinstance(value, dict):
            return any(is_positive_claim_value(item) for item in value.values())
        if isinstance(value, str):
            return normalized_key(value) in {
                "accepted",
                "allowed",
                "available",
                "complete",
                "completed",
                "enabled",
                "green",
                "live",
                "operational",
                "passed",
                "promoted",
                "public",
                "published",
                "ready",
                "satisfied",
                "satisfies",
                "stable",
                "supported",
                "true",
                "unlocked",
                "validated",
                "verified",
                "yes",
            }
        return False

    def positive_text_claim(text: str) -> bool:
        patterns = (
            COMMAND_PERMISSION_ROUTE_GATE_POSITIVE_CLAIM_RE,
            COMMAND_PERMISSION_ROUTE_GATE_POSITIVE_CLAIM_REVERSED,
            COMMAND_PERMISSION_ROUTE_GATE_BROAD_REVERSED_CLAIM_RE,
        )
        matches = sorted(
            (match for pattern in patterns for match in pattern.finditer(text)),
            key=lambda match: match.start(),
        )
        if not matches:
            return False
        for match in matches:
            clause_start = 0
            for boundary in CLAUSE_START_PATTERN.finditer(text[: match.start()]):
                clause_start = boundary.end()
            next_boundary = CLAUSE_START_PATTERN.search(text[match.end() :])
            clause_end = match.end() + next_boundary.start() if next_boundary else len(text)
            clause = text[clause_start:clause_end]
            if COMMAND_PERMISSION_ROUTE_GATE_NEGATED_CLAIM_RE.search(clause) and not re.search(
                r"\b(?:claims?|reports?|says|states?)\b[^,.;:\n\r]*$",
                text[max(clause_start, match.start() - 48) : match.start()],
                re.IGNORECASE,
            ):
                continue
            return True
        return False

    def contains_forbidden_claim_source(item: Any) -> bool:
        if isinstance(item, str):
            normalized = normalized_source(item)
            return (
                COMMAND_PERMISSION_ROUTE_GATE_FORBIDDEN_SOURCE_VALUE_RE.search(normalized)
                is not None
                or POST_RUNTIME_P0_CHAIN_SHORTCUT_MARKER_RE.search(normalized)
                is not None
            )
        if isinstance(item, list):
            return any(contains_forbidden_claim_source(child) for child in item)
        if isinstance(item, dict):
            return (
                has_source_overclaim_marker(item)
                or has_post_runtime_p0_chain_shortcut_marker(item)
                or any(contains_forbidden_claim_source(child) for child in item.values())
            )
        return False

    def text_claim_path_is_negative_context(path: str) -> bool:
        return any(
            normalized_key(part.split("[", 1)[0]) in PROMOTION_EVIDENCE_NEGATIVE_CONTEXT_KEYS
            for part in path.split(".")
            if part
        )

    def text_claim_path_is_command_metadata(path: str) -> bool:
        return any(
            normalized_key(part.split("[", 1)[0])
            in {
                "argv",
                "artifact_schema",
                "expected_schema",
                "input_schema",
                "report_schema",
                "schema",
                "schema_id",
                "schema_ids",
                "schemas",
                "source_schema",
            }
            for part in path.split(".")
            if part
        )

    def claim_key_matches_path(key_name: str, path: str) -> bool:
        if (
            key_name in COMMAND_PERMISSION_ROUTE_GATE_FORBIDDEN_CLAIM_KEYS
            or BROAD_ROUTE_GATE_CLAIM_KEY_RE.fullmatch(key_name)
        ):
            return True
        return any(
            suffix in COMMAND_PERMISSION_ROUTE_GATE_FORBIDDEN_CLAIM_KEYS
            or BROAD_ROUTE_GATE_CLAIM_KEY_RE.fullmatch(suffix)
            for suffix in normalized_claim_path_suffixes(path)
        )

    def visit(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                item_path = f"{path}.{key}" if path else str(key)
                key_name = normalized_key(key)
                if claim_key_matches_path(key_name, item_path) and is_positive_claim_value(item):
                    claims.append(item_path)
                if notice_or_bundle_status_alias_claim(key_name, item, item_path):
                    claims.append(item_path)
                if (
                    key_name in COMMAND_PERMISSION_ROUTE_GATE_FORBIDDEN_SOURCE_KEYS
                    and contains_forbidden_claim_source(item)
                ):
                    claims.append(item_path)
                if key == "public_or_runtime_claims" and isinstance(item, list):
                    for claim in item:
                        if isinstance(claim, str) and claim:
                            claims.append(f"{item_path}:{claim}")
                visit(item, item_path)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]")
        elif (
            isinstance(value, str)
            and not text_claim_path_is_negative_context(path)
            and not text_claim_path_is_command_metadata(path)
            and positive_text_claim(value)
        ):
            claims.append(f"{path}:positive_text_claim")

    visit(payload, "")
    return sorted(set(claims))


def secondary_report_completion_claims_without_blocker(payload: dict[str, Any]) -> list[str]:
    claims: list[str] = []
    forbidden_keys = {
        normalized_completion_claim_key(key)
        for key in SECONDARY_REPORT_FORBIDDEN_COMPLETION_CLAIM_KEYS
    }

    def has_local_blockers(value: dict[str, Any]) -> bool:
        blockers = value.get("blockers")
        return isinstance(blockers, list) and bool(blockers)

    def starts_report_context(value: dict[str, Any], path: str) -> bool:
        if path == "" or "schema" in value or "blockers" in value:
            return True
        tail = normalized_claim_path_tail(path)
        return (
            tail in {
                "accounting",
                "certificate",
                "certificates",
                "claim",
                "claims",
                "dependencies",
                "dependency",
                "manifest",
                "manifests",
                "readiness",
                "record",
                "records",
                "release_statement",
                "release_statements",
                "report",
                "reports",
                "result",
                "results",
                "section",
                "sections",
                "summary",
            }
            or tail.endswith("_accounting")
            or tail.endswith("_certificate")
            or tail.endswith("_certificates")
            or tail.endswith("_claims")
            or tail.endswith("_dependencies")
            or tail.endswith("_dependency")
            or tail.endswith("_manifest")
            or tail.endswith("_manifests")
            or tail.endswith("_readiness")
            or tail.endswith("_record")
            or tail.endswith("_records")
            or tail.endswith("_release_statement")
            or tail.endswith("_release_statements")
            or tail.endswith("_report")
            or tail.endswith("_reports")
            or tail.endswith("_result")
            or tail.endswith("_results")
            or tail.endswith("_section")
            or tail.endswith("_sections")
            or tail.endswith("_summary")
        )

    def normalized_claim_text(value: object) -> str:
        separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value))
        return re.sub(r"[^a-z0-9]+", " ", separated.casefold()).strip()

    def claim_search_text(value: object) -> str:
        separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value))
        protected = re.sub(
            r"\b(obelisk[_ -]*(?:api|config|targets))\.(h|cmake)\b",
            r"\1 \2",
            separated,
            flags=re.IGNORECASE,
        )
        return re.sub(r"[_-]+", " ", protected.casefold())

    def is_split_claim_descriptor(value: Any) -> bool:
        if isinstance(value, dict):
            return any(is_split_claim_descriptor(item) for item in value.values())
        if isinstance(value, list):
            return any(is_split_claim_descriptor(item) for item in value)
        return (
            isinstance(value, str)
            and SECONDARY_REPORT_SPLIT_COMPLETION_DESCRIPTOR_RE.search(
                normalized_claim_text(value)
            )
            is not None
        )

    def is_positive_split_claim_status(value: Any) -> bool:
        if isinstance(value, dict):
            return any(is_positive_split_claim_status(item) for item in value.values())
        if isinstance(value, list):
            return any(is_positive_split_claim_status(item) for item in value)
        if is_positive_completion_claim_value(value):
            return True
        if isinstance(value, str):
            return normalized_completion_claim_key(value) in BROAD_RELEASE_SUPPORT_TIER_VALUE_KEYS
        return False

    def path_has_completion_status_context(path: str) -> bool:
        if not path:
            return False
        return (
            SECONDARY_REPORT_STANDALONE_COMPLETION_CONTEXT_RE.search(
                normalized_claim_text(path)
            )
            is not None
        )

    def path_marks_non_counting_completion_context(path: str) -> bool:
        return any(
            (
                NON_COUNTING_COMPLETION_CONTEXT_RE.search(part) is not None
                or POST_RUNTIME_P0_CHAIN_SHORTCUT_MARKER_RE.search(part) is not None
            )
            and not re.fullmatch(
                r"(?:active_)?side_lane(?:_(?:report|review|section|summary))?",
                part,
            )
            for part in normalized_claim_path_parts(path)
        )

    def is_positive_standalone_status_claim(
        key_name: str,
        value: Any,
        path: str,
    ) -> bool:
        if key_name not in SECONDARY_REPORT_SPLIT_CLAIM_STATUS_KEYS:
            return False
        value_name = normalized_completion_claim_key(value) if isinstance(value, str) else ""
        if key_name in {"support_tier", "declared_support_tier", "tier"}:
            if value_name in (
                BROAD_RELEASE_SUPPORT_TIER_VALUE_KEYS
                | SECONDARY_REPORT_STANDALONE_COMPLETION_STATUS_VALUE_KEYS
            ) or value_name.startswith("release_supported"):
                return True
            return (
                isinstance(value, str)
                and SECONDARY_REPORT_STANDALONE_COMPLETION_CONTEXT_RE.search(
                    normalized_claim_text(value)
                )
                is not None
                and is_positive_completion_claim_value(value)
            )
        if (
            value_name in SECONDARY_REPORT_STANDALONE_COMPLETION_STATUS_VALUE_KEYS
            or value_name.startswith("release_supported")
        ):
            return True
        return is_positive_completion_claim_value(value) and path_has_completion_status_context(path)

    def is_positive_completion_progress_claim(key_name: str, value: Any, path: str) -> bool:
        if key_name not in SECONDARY_REPORT_COMPLETION_PROGRESS_VALUE_KEYS:
            return False
        return is_positive_completion_claim_value(value) and path_has_completion_status_context(path)

    def positive_completion_claim_leaf_paths(value: Any, path: str) -> list[str]:
        if isinstance(value, dict):
            paths: list[str] = []
            for key, item in value.items():
                item_path = f"{path}.{key}" if path else str(key)
                paths.extend(positive_completion_claim_leaf_paths(item, item_path))
            return paths
        if isinstance(value, list):
            paths = []
            for index, item in enumerate(value):
                paths.extend(positive_completion_claim_leaf_paths(item, f"{path}[{index}]"))
            return paths
        return [path] if is_positive_completion_claim_value(value) else []

    def path_is_non_claim_container(path: str) -> bool:
        return any(part in {"non_claim", "non_claims"} for part in normalized_claim_path_parts(path))

    def path_is_negative_claim_container(path: str) -> bool:
        return any(
            part in {
                "not_sufficient",
                "not_sufficient_for",
                "required_before_unlocking",
            }
            for part in normalized_claim_path_parts(path)
        )

    def path_is_machine_count_map(path: str) -> bool:
        tail = normalized_claim_path_tail(path)
        return (
            tail in {
                "diagnostic_candidate_target_counts",
                "rejected_drift_target_counts",
                "target_counts",
                "targets_counts",
            }
            or tail.endswith("_target_counts")
            or tail.endswith("_targets_counts")
            or tail.endswith("_counts_by_target")
            or tail.endswith("_counts_by_lifecycle_target")
        )

    def text_claim_path_is_machine_metadata(path: str) -> bool:
        path_parts = normalized_claim_path_parts(path)
        return (
            normalized_claim_path_tail(path) in SECONDARY_REPORT_SPLIT_CLAIM_DESCRIPTOR_KEYS
            or any(
                part
                in {
                    "argv",
                    "artifact_schema",
                    "allowed_remaining_blocker",
                    "allowed_remaining_blockers",
                    "blocker",
                    "blockers",
                    "checker",
                    "command",
                    "commands",
                    "cwd",
                    "digest",
                    "expected_schema",
                    "hash",
                    "input_schema",
                    "output_name",
                    "path",
                    "paths",
                    "producer",
                    "report_schema",
                    "script",
                    "schema",
                    "schema_id",
                    "schema_ids",
                    "schemas",
                    "sha256",
                    "source_schema",
                }
                for part in path_parts
            )
        )

    def has_positive_completion_claim_text(value: str) -> bool:
        for raw_clause in BROAD_CLAIM_TEXT_CLAUSE_SPLIT_RE.split(claim_search_text(value)):
            clause = re.sub(r"\s+", " ", raw_clause).strip()
            if not clause:
                continue
            if SECONDARY_REPORT_POSITIVE_COMPLETION_TEXT_RE.search(
                clause
            ) and not SECONDARY_REPORT_POSITIVE_COMPLETION_TEXT_NEGATORS.search(clause):
                return True
        return False

    def split_completion_claim_paths(value: dict[str, Any], path: str) -> list[str]:
        has_claim_descriptor = False
        positive_status_paths: list[str] = []
        for key, item in value.items():
            key_name = normalized_completion_claim_key(key)
            if key_name in SECONDARY_REPORT_SPLIT_CLAIM_DESCRIPTOR_KEYS and is_split_claim_descriptor(item):
                has_claim_descriptor = True
            if key_name in SECONDARY_REPORT_SPLIT_CLAIM_STATUS_KEYS and is_positive_split_claim_status(item):
                item_path = f"{path}.{key}" if path else str(key)
                positive_status_paths.append(item_path)
            if key_name in SECONDARY_REPORT_COMPLETION_PROGRESS_VALUE_KEYS and is_positive_completion_claim_value(item):
                item_path = f"{path}.{key}" if path else str(key)
                positive_status_paths.append(item_path)
        return positive_status_paths if has_claim_descriptor else []

    def visit(value: Any, path: str, blocked_report_context: bool) -> None:
        if isinstance(value, dict):
            current_blocked_context = (
                has_local_blockers(value)
                if starts_report_context(value, path)
                else blocked_report_context
            )
            if not current_blocked_context:
                claims.extend(split_completion_claim_paths(value, path))
            for key, item in value.items():
                item_path = f"{path}.{key}" if path else str(key)
                key_is_machine_count_entry = path_is_machine_count_map(path)
                if (
                    (
                        normalized_completion_claim_key(key) in forbidden_keys
                        or any(suffix in forbidden_keys for suffix in normalized_claim_path_suffixes(item_path))
                        or BROAD_ROUTE_GATE_CLAIM_KEY_RE.fullmatch(
                            normalized_completion_claim_key(key)
                        )
                        or any(
                            BROAD_ROUTE_GATE_CLAIM_KEY_RE.fullmatch(suffix)
                            for suffix in normalized_claim_path_suffixes(item_path)
                        )
                    )
                    and is_positive_completion_claim_value(item)
                    and not key_is_machine_count_entry
                    and not current_blocked_context
                ):
                    claims.extend(positive_completion_claim_leaf_paths(item, item_path))
                if (
                    is_positive_standalone_status_claim(
                        normalized_completion_claim_key(key),
                        item,
                        item_path,
                    )
                    and not key_is_machine_count_entry
                    and not current_blocked_context
                ):
                    if isinstance(item, (dict, list)):
                        claims.extend(positive_completion_claim_leaf_paths(item, item_path))
                    else:
                        claims.append(item_path)
                if (
                    is_positive_completion_progress_claim(
                        normalized_completion_claim_key(key),
                        item,
                        item_path,
                    )
                    and not key_is_machine_count_entry
                    and not current_blocked_context
                ):
                    claims.append(item_path)
                if (
                    notice_or_bundle_status_alias_claim(
                        normalized_completion_claim_key(key),
                        item,
                        item_path,
                    )
                    and not key_is_machine_count_entry
                    and not current_blocked_context
                ):
                    claims.append(item_path)
                if (
                    path_marks_non_counting_completion_context(item_path)
                    and non_counting_completion_readiness_alias_key(
                        normalized_completion_claim_key(key)
                    )
                    and normalized_completion_claim_key(key) != "accepted_for_contract_review"
                    and is_non_counting_context_positive_status_value(item)
                    and not key_is_machine_count_entry
                    and not current_blocked_context
                ):
                    claims.append(item_path)
                if (
                    path_marks_non_counting_completion_context(item_path)
                    and non_counting_completion_progress_alias_key(
                        normalized_completion_claim_key(key)
                    )
                    and is_positive_completion_claim_value(item)
                    and not key_is_machine_count_entry
                    and not current_blocked_context
                ):
                    claims.append(item_path)
                visit(item, item_path, current_blocked_context)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]", blocked_report_context)
        elif (
            isinstance(value, str)
            and not path_is_negative_claim_container(path)
            and (
                path_is_non_claim_container(path)
                or not text_claim_path_is_machine_metadata(path)
            )
            and has_positive_completion_claim_text(value)
            and not blocked_report_context
        ):
            claims.append(f"{path}:positive_completion_text")

    visit(payload, "", False)
    return sorted(set(claims))


def normalized_completion_claim_key(key: object) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(key))
    return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")


def normalized_claim_path_parts(path: str) -> list[str]:
    return [
        part
        for part in (
            normalized_completion_claim_key(raw_part)
            for raw_part in re.split(r"(?:\.|\[\d+\])", path)
        )
        if part
    ]


def normalized_claim_path_tail(path: str) -> str:
    parts = normalized_claim_path_parts(path)
    return parts[-1] if parts else ""


def is_notice_or_bundle_positive_status_value(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, list):
        return any(is_notice_or_bundle_positive_status_value(item) for item in value)
    if isinstance(value, dict):
        return any(
            is_notice_or_bundle_positive_status_value(item)
            for item in value.values()
        )
    if isinstance(value, str):
        return normalized_completion_claim_key(value) in NOTICE_OR_BUNDLE_POSITIVE_STATUS_VALUES
    return False


def is_non_counting_context_positive_status_value(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, list):
        return any(is_non_counting_context_positive_status_value(item) for item in value)
    if isinstance(value, dict):
        return any(
            is_non_counting_context_positive_status_value(item)
            for item in value.values()
        )
    if isinstance(value, str):
        return normalized_completion_claim_key(value) in NON_COUNTING_COMPLETION_POSITIVE_STATUS_VALUES
    return False


def non_counting_completion_readiness_alias_key(key_name: str) -> bool:
    if key_name in NON_COUNTING_COMPLETION_READINESS_ALIAS_EXEMPT_KEYS:
        return False
    return key_name in NON_COUNTING_COMPLETION_READINESS_ALIAS_KEYS or any(
        key_name.endswith(suffix) for suffix in NON_COUNTING_COMPLETION_READINESS_ALIAS_SUFFIXES
    )


def non_counting_completion_progress_alias_key(key_name: str) -> bool:
    return key_name in SIDE_LANE_COMPLETION_ACCOUNTING_ZERO_ALIAS_KEYS or any(
        key_name.endswith(suffix) for suffix in NON_COUNTING_COMPLETION_PROGRESS_ALIAS_SUFFIXES
    )


def notice_or_bundle_status_alias_claim(key_name: str, value: Any, path: str) -> bool:
    path_parts = normalized_claim_path_parts(path)
    if key_name in NOTICE_OR_BUNDLE_NON_PROGRESS_FALSE_ALIAS_KEYS:
        return is_notice_or_bundle_positive_status_value(value)
    if any(suffix in NOTICE_OR_BUNDLE_NON_PROGRESS_FALSE_ALIAS_KEYS for suffix in normalized_claim_path_suffixes(path)):
        return is_notice_or_bundle_positive_status_value(value)
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
    return is_notice_or_bundle_positive_status_value(value)


def normalized_claim_path_suffixes(path: str) -> list[str]:
    parts = normalized_claim_path_parts(path)
    return ["_".join(parts[index:]) for index in range(len(parts))]


def is_positive_completion_claim_value(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, list):
        return any(is_positive_completion_claim_value(item) for item in value)
    if isinstance(value, dict):
        return any(is_positive_completion_claim_value(item) for item in value.values())
    if isinstance(value, str):
        stripped = value.strip()
        number_match = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)%?", stripped)
        if number_match:
            return float(number_match.group(1)) != 0
        ratio_match = re.fullmatch(
            r"([+-]?\d+(?:\.\d+)?)\s*/\s*([+-]?\d+(?:\.\d+)?)",
            stripped,
        )
        if ratio_match:
            return float(ratio_match.group(1)) != 0
        return normalized_completion_claim_key(value) in {
            "accepted",
            "allowed",
            "approved",
            "available",
            "complete",
            "completed",
            "enabled",
            "green",
            "live",
            "operational",
            "passed",
            "promoted",
            "public",
            "published",
            "ready",
            "counted",
            "counts",
            "satisfied",
            "satisfies",
            "stable",
            "success",
            "succeeded",
            "supported",
            "true",
            "unblocked",
            "unlocked",
            "yes",
        }
    return False


def is_explicit_zero_accounting_alias_value(value: Any) -> bool:
    if value is False:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value == 0
    if isinstance(value, str):
        stripped = value.strip()
        number_match = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)%?", stripped)
        if number_match:
            return float(number_match.group(1)) == 0
        ratio_match = re.fullmatch(
            r"([+-]?\d+(?:\.\d+)?)\s*/\s*([+-]?\d+(?:\.\d+)?)",
            stripped,
        )
        if ratio_match:
            return float(ratio_match.group(1)) == 0
    return False


def has_source_overclaim_marker(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            key_name = normalized_completion_claim_key(key)
            if key_name in SOURCE_OVERCLAIM_MARKER_KEYS:
                return True
            if has_source_overclaim_marker(item):
                return True
        return False
    if isinstance(value, list):
        return any(has_source_overclaim_marker(item) for item in value)
    return False


def has_post_runtime_p0_chain_shortcut_marker(value: Any) -> bool:
    if isinstance(value, str):
        return (
            POST_RUNTIME_P0_CHAIN_SHORTCUT_MARKER_RE.search(
                normalized_completion_claim_key(value)
            )
            is not None
        )
    if isinstance(value, dict):
        for key, item in value.items():
            key_name = normalized_completion_claim_key(key)
            if (
                key_name in SOURCE_OVERCLAIM_MARKER_KEYS
                or POST_RUNTIME_P0_CHAIN_SHORTCUT_MARKER_RE.search(key_name)
                is not None
                or has_post_runtime_p0_chain_shortcut_marker(item)
            ):
                return True
        return False
    if isinstance(value, list):
        return any(has_post_runtime_p0_chain_shortcut_marker(item) for item in value)
    return False


def side_lane_completion_accounting_alias_violations(payload: dict[str, Any]) -> list[str]:
    violations: list[str] = []

    def path_marks_non_counting_context(path: str) -> bool:
        return any(
            NON_COUNTING_COMPLETION_CONTEXT_RE.search(part) is not None
            or POST_RUNTIME_P0_CHAIN_SHORTCUT_MARKER_RE.search(part) is not None
            for part in normalized_claim_path_parts(path)
        )

    def value_marks_non_counting_context(value: Any) -> bool:
        if isinstance(value, str):
            return (
                NON_COUNTING_COMPLETION_CONTEXT_RE.search(
                    normalized_completion_claim_key(value)
                )
                is not None
                or POST_RUNTIME_P0_CHAIN_SHORTCUT_MARKER_RE.search(
                    normalized_completion_claim_key(value)
                )
                is not None
            )
        if isinstance(value, list):
            return any(value_marks_non_counting_context(item) for item in value)
        if isinstance(value, dict):
            if has_source_overclaim_marker(value):
                return True
            return any(
                POST_RUNTIME_P0_CHAIN_SHORTCUT_MARKER_RE.search(
                    normalized_completion_claim_key(key)
                )
                is not None
                or value_marks_non_counting_context(item)
                for key, item in value.items()
                if normalized_completion_claim_key(key)
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
                or normalized_completion_claim_key(key) in SOURCE_OVERCLAIM_MARKER_KEYS
            )
        return False

    def visit(value: Any, path: str, in_non_counting_context: bool) -> None:
        current_context = in_non_counting_context or path_marks_non_counting_context(path)
        if isinstance(value, dict):
            current_context = current_context or value_marks_non_counting_context(value)
            for key, item in value.items():
                item_path = f"{path}.{key}" if path else str(key)
                key_name = normalized_completion_claim_key(key)
                if notice_or_bundle_status_alias_claim(key_name, item, item_path):
                    violations.append(item_path)
                if (
                    key_name in SIDE_LANE_COMPLETION_ACCOUNTING_FALSE_ALIAS_KEYS
                    and is_positive_completion_claim_value(item)
                ):
                    violations.append(item_path)
                if (
                    key_name in SIDE_LANE_COMPLETION_ACCOUNTING_ZERO_ALIAS_KEYS
                    and not is_explicit_zero_accounting_alias_value(item)
                ):
                    violations.append(item_path)
                if (
                    current_context
                    and non_counting_completion_readiness_alias_key(key_name)
                    and is_non_counting_context_positive_status_value(item)
                ):
                    violations.append(item_path)
                if (
                    current_context
                    and non_counting_completion_progress_alias_key(key_name)
                    and is_positive_completion_claim_value(item)
                ):
                    violations.append(item_path)
                visit(item, item_path, current_context)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]", current_context)

    visit(payload, "", False)
    return sorted(set(violations))


def route_gate_post_evidence_p0_lock_simulation_alias_violations(
    payload: dict[str, Any],
) -> list[str]:
    simulation = payload.get("post_evidence_p0_lock_simulation")
    if not isinstance(simulation, dict):
        return []
    return [
        f"post_evidence_p0_lock_simulation.{path}"
        for path in side_lane_completion_accounting_alias_violations(simulation)
    ]


def run_inventory_copied_signals_stability(path: Path) -> tuple[dict[str, Any], list[str]]:
    blockers: list[str] = []
    result = run_helper_subprocess([sys.executable, str(path), "--json"])
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return (
            {
                "path": str(path),
                "exit_code": result.returncode,
                "parse_error": f"stdout_json_decode_error: {exc}",
                "stderr": result.stderr.strip(),
            },
            ["inventory_copied_signals_stability_output_invalid"],
        )
    if not isinstance(payload, dict):
        return (
            {
                "path": str(path),
                "exit_code": result.returncode,
                "parse_error": "stdout_json_not_object",
                "stderr": result.stderr.strip(),
            },
            ["inventory_copied_signals_stability_output_invalid"],
        )

    public_or_runtime_claims = command_permission_route_gate_public_or_runtime_claims(payload)
    completion_claims_without_blocker = secondary_report_completion_claims_without_blocker(payload)
    completion_accounting_alias_violations = side_lane_completion_accounting_alias_violations(payload)
    if result.returncode != 0 or payload.get("ready") is not True:
        blockers.append("inventory_copied_signals_stability_invalid")
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    if summary.get("public_sdk_ready") is not False:
        blockers.append("inventory_copied_signals_public_sdk_ready_not_false")
    if summary.get("v1_completion_ready") is not False:
        blockers.append("inventory_copied_signals_v1_completion_ready_not_false")
    report_blockers = payload.get("blockers", [])
    if report_blockers:
        blockers.append("inventory_copied_signals_stability_blockers_not_empty")
    if public_or_runtime_claims:
        blockers.append("inventory_copied_signals_public_or_runtime_claims")
    if completion_accounting_alias_violations:
        blockers.append("inventory_copied_signals_completion_accounting_alias_not_false")
    if completion_claims_without_blocker:
        blockers.append(SECONDARY_REPORT_COMPLETION_CLAIM_WITHOUT_BLOCKER)

    return (
        {
            "path": str(path),
            "exit_code": result.returncode,
            "schema": payload.get("schema"),
            "ready": payload.get("ready"),
            "surface": payload.get("surface"),
            "allowed_signal_count": summary.get("allowed_signal_count"),
            "resource_kind_contract": summary.get("resource_kind_contract"),
            "public_sdk_ready": summary.get("public_sdk_ready"),
            "v1_completion_ready": summary.get("v1_completion_ready"),
            "counts_toward_complete_sdk_claim": False,
            "counts_toward_p0_dependency_chain_claim": False,
            "progress": 0,
            "stable_claim_allowed": False,
            "public_or_runtime_claims": public_or_runtime_claims,
            "completion_claims_without_blocker": completion_claims_without_blocker,
            "completion_accounting_alias_violations": completion_accounting_alias_violations,
            "blockers": report_blockers,
            "stderr": result.stderr.strip(),
            "non_claim": "copied-signal stability guard; not Inventory SDK, Items SDK, or v1 completion evidence",
        },
        blockers,
    )


def object_identity_resource_handle_public_or_runtime_claims(payload: dict[str, Any]) -> list[str]:
    claims: list[str] = []

    def normalized_key(key: object) -> str:
        separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(key))
        return separated.casefold().replace("-", "_").replace(" ", "_")

    def is_positive_claim_value(value: Any) -> bool:
        if value is True:
            return True
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value != 0
        if isinstance(value, str):
            return normalized_key(value) in {
                "allowed",
            "available",
            "complete",
            "completed",
            "enabled",
            "live",
                "operational",
            "promoted",
            "public",
            "published",
            "ready",
            "satisfied",
            "satisfies",
            "stable",
            "supported",
            "true",
            "unlocked",
            "validated",
            "verified",
            "yes",
        }
        return False

    forbidden_keys = {normalized_key(key) for key in OBJECT_IDENTITY_RESOURCE_HANDLE_FORBIDDEN_READY_KEYS}

    def visit(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                item_path = f"{path}.{key}" if path else str(key)
                if normalized_key(key) in forbidden_keys and is_positive_claim_value(item):
                    claims.append(item_path)
                visit(item, item_path)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]")

    visit(payload, "")
    return sorted(set(claims))


def run_object_identity_resource_handle_readiness(
    path: Path,
    public_sdk_surfaces_path: Path,
    public_header_path: Path,
    contract_decisions_dir: Path,
) -> tuple[dict[str, Any], list[str]]:
    blockers: list[str] = []
    decisions_path = contract_decisions_dir / OBJECT_IDENTITY_RESOURCE_HANDLE_DECISIONS_FILENAME
    result = run_helper_subprocess(
        [
            sys.executable,
            str(path),
            "--decisions",
            str(decisions_path),
            "--surfaces",
            str(public_sdk_surfaces_path),
            "--public-header",
            str(public_header_path),
            "--json",
        ]
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return (
            {
                "path": str(path),
                "decisions": str(decisions_path),
                "exit_code": result.returncode,
                "parse_error": f"stdout_json_decode_error: {exc}",
                "stderr": result.stderr.strip(),
            },
            ["object_identity_resource_handle_readiness_output_invalid"],
        )
    if not isinstance(payload, dict):
        return (
            {
                "path": str(path),
                "decisions": str(decisions_path),
                "exit_code": result.returncode,
                "parse_error": "stdout_json_not_object",
                "stderr": result.stderr.strip(),
            },
            ["object_identity_resource_handle_readiness_output_invalid"],
        )

    public_or_runtime_claims = object_identity_resource_handle_public_or_runtime_claims(payload)
    completion_claims_without_blocker = secondary_report_completion_claims_without_blocker(payload)
    if payload.get("schema") != "obelisk.object-identity-resource-handle-public-contract-readiness-check.v1":
        blockers.append("object_identity_resource_handle_readiness_schema_mismatch")
    if result.returncode != 0 or payload.get("valid") is not True:
        blockers.append("object_identity_resource_handle_readiness_invalid")
    if payload.get("accepted_for_planning") is not True or payload.get("planning_only") is not True:
        blockers.append("object_identity_resource_handle_readiness_not_planning_only")
    for key in OBJECT_IDENTITY_RESOURCE_HANDLE_REQUIRED_FALSE_KEYS:
        if payload.get(key) is not False:
            blockers.append(f"object_identity_resource_handle_{key}_not_false")
    if payload.get("strict_next_blocker") != OBJECT_IDENTITY_RESOURCE_HANDLE_STRICT_NEXT_BLOCKER:
        blockers.append("object_identity_resource_handle_strict_next_blocker_missing")
    if (
        payload.get("offline_serial_post_callback_artifacts")
        != OBJECT_IDENTITY_RESOURCE_HANDLE_OFFLINE_ARTIFACT_POLICY
    ):
        blockers.append("object_identity_resource_handle_offline_artifact_policy_not_candidate_only")
    readiness_blockers = payload.get("blockers", [])
    if readiness_blockers:
        blockers.append("object_identity_resource_handle_readiness_blockers_not_empty")
    if public_or_runtime_claims:
        blockers.append("object_identity_resource_handle_public_or_runtime_claims")
    if completion_claims_without_blocker:
        blockers.append(SECONDARY_REPORT_COMPLETION_CLAIM_WITHOUT_BLOCKER)

    return (
        {
            "path": str(path),
            "decisions": str(decisions_path),
            "exit_code": result.returncode,
            "schema": payload.get("schema"),
            "valid": payload.get("valid"),
            "accepted_for_planning": payload.get("accepted_for_planning"),
            "planning_only": payload.get("planning_only"),
            "promotion_ready": payload.get("promotion_ready"),
            "public_sdk_ready": payload.get("public_sdk_ready"),
            "runtime_ready": payload.get("runtime_ready"),
            "public_resource_handle_ready": payload.get("public_resource_handle_ready"),
            "post_callback_resource_handle_ready": payload.get("post_callback_resource_handle_ready"),
            "serialPolicyReady": payload.get("serialPolicyReady"),
            "resourceLookupReady": payload.get("resourceLookupReady"),
            "postCallbackHandleReady": payload.get("postCallbackHandleReady"),
            "objectIdentityReady": payload.get("objectIdentityReady"),
            "runtimeSampleReady": payload.get("runtimeSampleReady"),
            "strict_next_blocker": payload.get("strict_next_blocker"),
            "offline_serial_post_callback_artifacts": payload.get("offline_serial_post_callback_artifacts"),
            "offline_artifacts_unlock_public_lookup_identity_runtime_sdk": payload.get(
                "offline_artifacts_unlock_public_lookup_identity_runtime_sdk"
            ),
            "next_evidence_contract": {
                "status": "planning-only-not-approval",
                "required_future_evidence": [
                    "runtime object negative samples",
                    "runtime serial reuse/wraparound semantics",
                ],
                "offline_artifacts_policy": OBJECT_IDENTITY_RESOURCE_HANDLE_OFFLINE_ARTIFACT_POLICY,
                "non_claim": (
                    "Next evidence fields document the future ResourceHandle blocker only; "
                    "they do not approve lookup, mutation, cross-event identity, persistent "
                    "object identity, post-callback validity, runtime work, or public SDK readiness."
                ),
            },
            "public_or_runtime_claims": public_or_runtime_claims,
            "completion_claims_without_blocker": completion_claims_without_blocker,
            "blockers": readiness_blockers,
            "stderr": result.stderr.strip(),
            "non_claim": (
                "ResourceHandle/object-identity readiness guard; not public SDK, "
                "runtime, promotion, or v1 completion evidence"
            ),
        },
        blockers,
    )


def mission_transfer_dino_tribe_leaf_outcome_accounting(payload: dict[str, Any]) -> dict[str, Any]:
    candidate_accounting = payload.get("candidate_only_accounting")
    candidate_accounting = candidate_accounting if isinstance(candidate_accounting, dict) else {}
    leaf_gaps = candidate_accounting.get("leaf_family_gaps")
    leaf_gaps = leaf_gaps if isinstance(leaf_gaps, dict) else {}
    leaf_statuses = payload.get("leaf_statuses")
    leaf_statuses = leaf_statuses if isinstance(leaf_statuses, dict) else {}
    missing_leaf_families = payload.get("missing_leaf_families")
    missing_leaf_families = (
        [leaf for leaf in missing_leaf_families if isinstance(leaf, str)]
        if isinstance(missing_leaf_families, list)
        else []
    )

    leaves: list[dict[str, Any]] = []
    for leaf_id in MISSION_TRANSFER_DINO_TRIBE_REQUIRED_LEAVES_ORDER:
        gap = leaf_gaps.get(leaf_id)
        gap = gap if isinstance(gap, dict) else {}
        status = leaf_statuses.get(leaf_id)
        if not isinstance(status, str):
            status = gap.get("status") if isinstance(gap.get("status"), str) else None
        accounted_by = gap.get("accounted_by") if isinstance(gap.get("accounted_by"), str) else None
        manifest_outcome = status if status in {"excluded", "post-v1"} else None
        release_statement_excluded = gap.get("release_statement_excluded") is True
        explicit_non_promoted_outcome = (
            manifest_outcome is not None
            or accounted_by in {
                "manifest_leaf_exclusion",
                "manifest_leaf_exclusion_pending_acceptance",
                "release_statement_leaf_exclusion",
                "release_statement_leaf_exclusion_pending_acceptance",
            }
        )
        leaves.append(
            {
                "leaf": leaf_id,
                "status": status,
                "manifest_outcome": manifest_outcome,
                "v1_accounted": gap.get("v1_accounted") is True,
                "accounted_by": accounted_by,
                "release_statement_excluded": release_statement_excluded,
                "release_statement_promoted": gap.get("release_statement_promoted") is True,
                "explicit_non_promoted_outcome": explicit_non_promoted_outcome,
                "scoped_non_complete_bookkeeping_only": explicit_non_promoted_outcome,
                "allowed_v1_outcome": (
                    gap.get("allowed_v1_outcome")
                    if isinstance(gap.get("allowed_v1_outcome"), str)
                    else None
                ),
                "missing_public_gates": as_string_list(gap.get("missing_public_gates")),
                "counts_toward_complete_sdk_claim": False,
                "counts_toward_p0_dependency_chain_claim": False,
                "counts_toward_public_sdk": False,
                "counts_toward_runtime": False,
                "progress_contribution": 0,
                "fail_closed_requirement": (
                    "release statement must record the umbrella and every leaf as excluded/post-v1"
                    if leaf_id in missing_leaf_families
                    else "non-counting scoped outcome only; promotion remains separately blocked"
                ),
            }
        )

    return {
        "schema": "obelisk.mission-transfer-dino-tribe-v1-leaf-outcomes.v1",
        "surface": "obelisk.mission_transfer_dino_tribe.v1",
        "accounting_route": payload.get("accounting_route"),
        "v1_accounted": payload.get("v1_accounted") is True,
        "all_leaf_outcomes_explicit": not missing_leaf_families,
        "missing_or_unresolved_leaf_outcomes": missing_leaf_families,
        "leaves": leaves,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "non_claim": (
            "Leaf outcomes are scoped non-complete accounting only; they do not add "
            "Mission, Transfer, Dino, Tribe, or Buff SDK coverage."
        ),
    }


def run_mission_transfer_dino_tribe_outcome_accounting(
    path: Path,
    manifest_path: Path,
    release_statement_path: Path | None,
) -> tuple[dict[str, Any], list[str]]:
    blockers: list[str] = []
    argv = [sys.executable, str(path), "--manifest", str(manifest_path), "--json"]
    if release_statement_path is not None:
        argv.extend(["--release-statement", str(release_statement_path)])
    result = run_helper_subprocess(argv)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return (
            {
                "path": str(path),
                "exit_code": result.returncode,
                "parse_error": f"stdout_json_decode_error: {exc}",
                "stderr": result.stderr.strip(),
            },
            ["mission_transfer_dino_tribe_outcome_accounting_output_invalid"],
        )
    if not isinstance(payload, dict):
        return (
            {
                "path": str(path),
                "exit_code": result.returncode,
                "parse_error": "stdout_json_not_object",
                "stderr": result.stderr.strip(),
            },
            ["mission_transfer_dino_tribe_outcome_accounting_output_invalid"],
        )

    accounting_route = payload.get("accounting_route")
    public_or_runtime_claims = command_permission_route_gate_public_or_runtime_claims(payload)
    completion_claims_without_blocker = secondary_report_completion_claims_without_blocker(payload)
    completion_accounting_alias_violations = side_lane_completion_accounting_alias_violations(payload)
    leaf_outcome_accounting = mission_transfer_dino_tribe_leaf_outcome_accounting(payload)
    allowed_per_leaf_promoted_claims = {"promotion_ready", "public_sdk_ready", "runtime_ready"}
    unexpected_public_or_runtime_claims = [
        claim
        for claim in public_or_runtime_claims
        if accounting_route != "per_leaf_promoted" or claim not in allowed_per_leaf_promoted_claims
    ]
    required_leaves_match = (
        set(payload.get("required_leaves", [])) == MISSION_TRANSFER_DINO_TRIBE_REQUIRED_LEAVES
    )
    observed_leaves_match = (
        set(payload.get("observed_leaves", [])) == MISSION_TRANSFER_DINO_TRIBE_REQUIRED_LEAVES
    )
    report_blockers = payload.get("blockers", [])
    non_counting_route = accounting_route in {
        "candidate_only",
        "manifest_umbrella_excluded",
        "release_statement_umbrella_excluded",
    }
    if accounting_route == "release_statement_umbrella_excluded":
        allowed_leaf_exclusion_prefix = "release_statement.leaf_exclusions."
        completion_claims_without_blocker = [
            path
            for path in completion_claims_without_blocker
            if not path.startswith(allowed_leaf_exclusion_prefix)
        ]
        completion_accounting_alias_violations = [
            path
            for path in completion_accounting_alias_violations
            if not path.startswith(allowed_leaf_exclusion_prefix)
        ]
    non_counting_public_runtime_flags_false = all(
        payload.get(key) is False
        for key in ("promotion_ready", "public_sdk_ready", "runtime_ready")
    )
    release_statement_report = (
        payload.get("release_statement") if isinstance(payload.get("release_statement"), dict) else {}
    )
    strict_release_statement_accounting_blocker = (
        release_statement_report.get("umbrella_excluded") is True
        and "release_statement_leaf_exclusions_missing" in report_blockers
    )
    suppress_helper_blocked_status = (
        non_counting_route
        and required_leaves_match
        and observed_leaves_match
        and non_counting_public_runtime_flags_false
        and not unexpected_public_or_runtime_claims
        and not strict_release_statement_accounting_blocker
    )
    normalized_ready = payload.get("ready")
    if (
        accounting_route == "candidate_only"
        and suppress_helper_blocked_status
        and not completion_accounting_alias_violations
        and not completion_claims_without_blocker
    ):
        normalized_ready = True

    if payload.get("schema") != "obelisk.mission-transfer-dino-tribe-v1-outcome-accounting-check.v1":
        blockers.append("mission_transfer_dino_tribe_outcome_accounting_schema_mismatch")
    if (
        result.returncode != 0 or payload.get("ready") is not True
    ) and not suppress_helper_blocked_status:
        blockers.append("mission_transfer_dino_tribe_outcome_accounting_invalid")
    if payload.get("surface") != "obelisk.mission_transfer_dino_tribe.v1":
        blockers.append("mission_transfer_dino_tribe_outcome_accounting_surface_mismatch")
    if not required_leaves_match:
        blockers.append("mission_transfer_dino_tribe_required_leaves_mismatch")
    if not observed_leaves_match:
        blockers.append("mission_transfer_dino_tribe_observed_leaves_mismatch")
    if report_blockers and not suppress_helper_blocked_status:
        blockers.append("mission_transfer_dino_tribe_outcome_accounting_blockers_not_empty")
    if accounting_route == "candidate_only":
        if payload.get("candidate_only") is not True or payload.get("v1_accounted") is not False:
            blockers.append("mission_transfer_dino_tribe_candidate_only_accounting_mismatch")
    elif accounting_route == "release_statement_umbrella_excluded":
        release_statement = payload.get("release_statement") if isinstance(payload.get("release_statement"), dict) else {}
        leaf_exclusions = release_statement.get("leaf_exclusions")
        leaf_exclusions = leaf_exclusions if isinstance(leaf_exclusions, dict) else {}
        missing_leaf_exclusions = sorted(
            leaf_id
            for leaf_id in MISSION_TRANSFER_DINO_TRIBE_REQUIRED_LEAVES
            if leaf_exclusions.get(leaf_id) is not True
        )
        if payload.get("v1_accounted") is not True or missing_leaf_exclusions:
            blockers.append("mission_transfer_dino_tribe_release_statement_leaf_exclusions_incomplete")
    elif accounting_route == "manifest_umbrella_excluded":
        leaf_statuses = payload.get("leaf_statuses")
        leaf_statuses = leaf_statuses if isinstance(leaf_statuses, dict) else {}
        missing_leaf_exclusions = sorted(
            leaf_id
            for leaf_id in MISSION_TRANSFER_DINO_TRIBE_REQUIRED_LEAVES
            if leaf_statuses.get(leaf_id) != "excluded"
        )
        if payload.get("v1_accounted") is not True or missing_leaf_exclusions:
            blockers.append("mission_transfer_dino_tribe_manifest_leaf_exclusions_incomplete")
    elif accounting_route == "per_leaf_promoted":
        if not (
            payload.get("promotion_ready") is True
            and payload.get("public_sdk_ready") is True
            and payload.get("runtime_ready") is True
            and payload.get("v1_accounted") is True
        ):
            blockers.append("mission_transfer_dino_tribe_promoted_leaf_accounting_mismatch")
    else:
        blockers.append("mission_transfer_dino_tribe_outcome_accounting_route_unexpected")
    if accounting_route != "per_leaf_promoted":
        for key in ("promotion_ready", "public_sdk_ready", "runtime_ready"):
            if payload.get(key) is not False:
                blockers.append(f"mission_transfer_dino_tribe_{key}_not_false")
    if unexpected_public_or_runtime_claims:
        blockers.append("mission_transfer_dino_tribe_public_or_runtime_claims")
    if completion_accounting_alias_violations:
        blockers.append("mission_transfer_dino_tribe_completion_accounting_alias_not_false")
    if completion_claims_without_blocker:
        blockers.append(SECONDARY_REPORT_COMPLETION_CLAIM_WITHOUT_BLOCKER)

    return (
        {
            "path": str(path),
            "exit_code": result.returncode,
            "source_ready": payload.get("ready"),
            "schema": payload.get("schema"),
            "surface": payload.get("surface"),
            "ready": normalized_ready,
            "accounting_route": accounting_route,
            "candidate_only": payload.get("candidate_only"),
            "v1_accounted": payload.get("v1_accounted"),
            "promotion_ready": payload.get("promotion_ready"),
            "public_sdk_ready": payload.get("public_sdk_ready"),
            "runtime_ready": payload.get("runtime_ready"),
            "counts_toward_complete_sdk_claim": False,
            "counts_toward_p0_dependency_chain_claim": False,
            "progress": 0,
            "stable_claim_allowed": False,
            "public_or_runtime_claims": public_or_runtime_claims,
            "completion_claims_without_blocker": completion_claims_without_blocker,
            "completion_accounting_alias_violations": completion_accounting_alias_violations,
            "required_leaves": payload.get("required_leaves"),
            "observed_leaves": payload.get("observed_leaves"),
            "missing_leaf_families": payload.get("missing_leaf_families"),
            "leaf_outcome_accounting": leaf_outcome_accounting,
            "release_statement": payload.get("release_statement"),
            "blockers": report_blockers,
            "source_blockers": report_blockers,
            "helper_blocked_status_normalized": (
                suppress_helper_blocked_status
                and (
                    result.returncode != 0
                    or payload.get("ready") is not True
                    or bool(report_blockers)
                )
            ),
            "stderr": result.stderr.strip(),
            "non_claim": (
                "Mission/Transfer/Dino/Tribe/Buff accounting guard; not public SDK, "
                "runtime, promotion, or v1 completion evidence"
            ),
        },
        blockers,
    )


def run_structure_census_readiness(path: Path) -> tuple[dict[str, Any], list[str]]:
    blockers: list[str] = []
    result = run_helper_subprocess([sys.executable, str(path), "--json"])
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return (
            {
                "path": str(path),
                "exit_code": result.returncode,
                "parse_error": f"stdout_json_decode_error: {exc}",
                "stderr": result.stderr.strip(),
            },
            ["structure_census_readiness_output_invalid"],
        )
    if not isinstance(payload, dict):
        return (
            {
                "path": str(path),
                "exit_code": result.returncode,
                "parse_error": "stdout_json_not_object",
                "stderr": result.stderr.strip(),
            },
            ["structure_census_readiness_output_invalid"],
        )

    report_blockers = payload.get("blockers", [])
    public_or_runtime_claims = command_permission_route_gate_public_or_runtime_claims(payload)
    completion_claims_without_blocker = secondary_report_completion_claims_without_blocker(payload)
    if payload.get("schema") != "obelisk.structure-census-readiness-check.v1":
        blockers.append("structure_census_readiness_schema_mismatch")
    if result.returncode != 0 or payload.get("ready") is not True:
        blockers.append("structure_census_readiness_invalid")
    if payload.get("accepted_for_internal_planning") is not True or payload.get("offline_only") is not True:
        blockers.append("structure_census_readiness_not_offline_planning")
    if report_blockers:
        blockers.append("structure_census_readiness_blockers_not_empty")
    for key in ("promotion_ready", "public_sdk_ready", "runtime_ready", "enforcement_ready"):
        if payload.get(key) is not False:
            blockers.append(f"structure_census_{key}_not_false")
    accounting = payload.get("candidate_only_accounting") if isinstance(payload.get("candidate_only_accounting"), dict) else {}
    for key in ("promotion_ready", "public_sdk_ready", "runtime_ready", "build_policy_ready", "public_structure_sdk_ready", "structure_identity_ready"):
        if accounting.get(key) is not False:
            blockers.append(f"structure_census_accounting_{key}_not_false")
    if public_or_runtime_claims:
        blockers.append("structure_census_public_or_runtime_claims")
    if completion_claims_without_blocker:
        blockers.append(SECONDARY_REPORT_COMPLETION_CLAIM_WITHOUT_BLOCKER)

    return (
        {
            "path": str(path),
            "exit_code": result.returncode,
            "schema": payload.get("schema"),
            "ready": payload.get("ready"),
            "status": payload.get("status"),
            "outcome": payload.get("outcome"),
            "accounting_mode": payload.get("accounting_mode"),
            "accepted_for_internal_planning": payload.get("accepted_for_internal_planning"),
            "offline_only": payload.get("offline_only"),
            "promotion_ready": payload.get("promotion_ready"),
            "public_sdk_ready": payload.get("public_sdk_ready"),
            "runtime_ready": payload.get("runtime_ready"),
            "enforcement_ready": payload.get("enforcement_ready"),
            "public_or_runtime_claims": public_or_runtime_claims,
            "completion_claims_without_blocker": completion_claims_without_blocker,
            "second_source_status": (
                payload.get("second_source_readiness", {}).get("status")
                if isinstance(payload.get("second_source_readiness"), dict)
                else None
            ),
            "missing_public_gates": accounting.get("missing_public_gates"),
            "blockers": report_blockers,
            "stderr": result.stderr.strip(),
            "non_claim": "Structure census readiness guard; not Structure SDK, runtime, enforcement, or v1 completion evidence",
        },
        blockers,
    )


def run_structure_build_policy_offline_intake(path: Path) -> tuple[dict[str, Any], list[str]]:
    blockers: list[str] = []
    result = run_helper_subprocess([sys.executable, str(path), "--json"])
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return (
            {
                "path": str(path),
                "exit_code": result.returncode,
                "parse_error": f"stdout_json_decode_error: {exc}",
                "stderr": result.stderr.strip(),
            },
            ["structure_build_policy_offline_intake_output_invalid"],
        )
    if not isinstance(payload, dict):
        return (
            {
                "path": str(path),
                "exit_code": result.returncode,
                "parse_error": "stdout_json_not_object",
                "stderr": result.stderr.strip(),
            },
            ["structure_build_policy_offline_intake_output_invalid"],
        )

    report_blockers = payload.get("blockers", [])
    public_or_runtime_claims = command_permission_route_gate_public_or_runtime_claims(payload)
    completion_claims_without_blocker = secondary_report_completion_claims_without_blocker(payload)
    if payload.get("schema") != "obelisk.structure-build-policy-offline-intake-check.v1":
        blockers.append("structure_build_policy_offline_intake_schema_mismatch")
    if result.returncode != 0 or payload.get("ready") is not True:
        blockers.append("structure_build_policy_offline_intake_invalid")
    if payload.get("planning_only") is not True:
        blockers.append("structure_build_policy_offline_intake_not_planning_only")
    if report_blockers:
        blockers.append("structure_build_policy_offline_intake_blockers_not_empty")
    for key in ("promotion_ready", "public_sdk_ready", "runtime_ready", "enforcement_ready"):
        if payload.get(key) is not False:
            blockers.append(f"structure_build_policy_{key}_not_false")
    readiness_flags = payload.get("readiness_flags") if isinstance(payload.get("readiness_flags"), dict) else {}
    for key in ("promotion_ready", "public_sdk_ready", "runtime_ready", "enforcement_ready"):
        if readiness_flags.get(key) is not False:
            blockers.append(f"structure_build_policy_readiness_flags_{key}_not_false")
    for key in (
        "build_policy_ready",
        "structure_build_policy_ready",
        "route_ready",
        "blocker_resolved",
        "side_lane_promoted",
    ):
        if key in payload and payload.get(key) is not False:
            blockers.append(f"structure_build_policy_{key}_not_false")
        if key in readiness_flags and readiness_flags.get(key) is not False:
            blockers.append(f"structure_build_policy_readiness_flags_{key}_not_false")
    if public_or_runtime_claims:
        blockers.append("structure_build_policy_public_or_runtime_claims")
    if completion_claims_without_blocker:
        blockers.append(SECONDARY_REPORT_COMPLETION_CLAIM_WITHOUT_BLOCKER)

    return (
        {
            "path": str(path),
            "exit_code": result.returncode,
            "schema": payload.get("schema"),
            "ready": payload.get("ready"),
            "status": payload.get("status"),
            "accepted_for_offline_planning": payload.get("accepted_for_offline_planning"),
            "planning_only": payload.get("planning_only"),
            "promotion_ready": payload.get("promotion_ready"),
            "public_sdk_ready": payload.get("public_sdk_ready"),
            "runtime_ready": payload.get("runtime_ready"),
            "enforcement_ready": payload.get("enforcement_ready"),
            "public_or_runtime_claims": public_or_runtime_claims,
            "completion_claims_without_blocker": completion_claims_without_blocker,
            "expected_status": payload.get("expected_status"),
            "target_set": payload.get("target_set"),
            "blockers": [blocker.get("reason") if isinstance(blocker, dict) else blocker for blocker in report_blockers],
            "stderr": result.stderr.strip(),
            "non_claim": "Structure build-policy offline intake guard; not Structure SDK, runtime, enforcement, or v1 completion evidence",
        },
        blockers,
    )


def mission_transfer_dino_tribe_release_statement_path(path: Path | None) -> Path | None:
    if path is None:
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return path
    if not any(
        line.strip().startswith("obelisk.mission_transfer_dino_tribe.v1:")
        for line in text.splitlines()
    ):
        return None
    return path


def load_manifest(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"manifest_load_failed:{exc}"]
    if not isinstance(payload, dict):
        return None, ["manifest_not_object"]
    return payload, []


def as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def as_string_map(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, list[str]] = {}
    for key, raw_values in value.items():
        if not isinstance(key, str):
            continue
        if isinstance(raw_values, str):
            result[key] = [raw_values]
        else:
            result[key] = as_string_list(raw_values)
    return result


def load_release_statement(path: Path | None) -> tuple[str | None, list[str]]:
    if path is None:
        return None, []
    try:
        return path.read_text(encoding="utf-8"), []
    except OSError as exc:
        return None, [f"release_statement_load_failed:{exc}"]


def strip_c_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//.*", "", text)


def load_public_header_symbols(path: Path) -> tuple[set[str], list[str]]:
    try:
        text = strip_c_comments(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return set(), [f"public_header_load_failed:{exc}"]
    symbols: set[str] = set()
    symbols.update(re.findall(r"^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\b", text, flags=re.MULTILINE))
    symbols.update(re.findall(r"\btypedef\s+(?:struct|enum)\s+([A-Za-z_][A-Za-z0-9_]*)\b", text))
    symbols.update(
        re.findall(
            r"\btypedef\s+(?:struct|enum)\s+[A-Za-z_][A-Za-z0-9_]*\s*\*?\s*"
            r"([A-Za-z_][A-Za-z0-9_]*)\s*;",
            text,
        )
    )
    symbols.update(
        re.findall(
            r"\btypedef\s+(?:const\s+)?(?:void|bool|char|u?int(?:8|16|32|64)_t|size_t|"
            r"[A-Za-z_][A-Za-z0-9_]*)\s*\*?\s*([A-Za-z_][A-Za-z0-9_]*)\s*;",
            text,
        )
    )
    symbols.update(re.findall(r"}\s*([A-Za-z_][A-Za-z0-9_]*)\s*;", text))
    symbols.update(re.findall(r"\btypedef\b[^;{]*\(\s*\*\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)", text))
    symbols.update(re.findall(r"\(\s*\*\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)", text))
    symbols.update(re.findall(r"\b(OBELISK_[A-Z0-9_]+)\b", text))
    symbols.update(
        re.findall(
            r"\b(?:uint(?:32|64)_t|int(?:32|64)_t|size_t|bool|char|void|const\s+char\*)\s+"
            r"([A-Za-z_][A-Za-z0-9_]*)(?:\[[^\]]+\])?\s*;",
            text,
        )
    )
    return symbols, []


def contract_decision_paths(decisions_dir: Path) -> list[Path]:
    try:
        paths = set(decisions_dir.glob(PUBLIC_CONTRACT_DECISIONS_GLOB))
        for filename in (
            *REQUIRED_ROUTE_GUARDRAIL_DECISION_MANIFESTS.values(),
            *REQUIRED_PLANNING_GUARDRAIL_DECISION_MANIFESTS.values(),
        ):
            path = decisions_dir / filename
            if path.exists():
                paths.add(path)
        return sorted(paths)
    except OSError:
        return []


def missing_required_contract_decision_manifests(decisions_dir: Path) -> dict[str, str]:
    missing: dict[str, str] = {}
    required_manifests = {
        **REQUIRED_PUBLIC_CONTRACT_DECISION_MANIFESTS,
        **REQUIRED_ROUTE_GUARDRAIL_DECISION_MANIFESTS,
        **REQUIRED_PLANNING_GUARDRAIL_DECISION_MANIFESTS,
    }
    for surface_id, filename in required_manifests.items():
        path = decisions_dir / filename
        payload, blockers = load_manifest(path)
        if blockers or payload is None or payload.get("surface") != surface_id:
            missing[surface_id] = filename
    return missing


def public_header_matches_contract(path: Path, raw_contract_header: Any) -> bool:
    if not isinstance(raw_contract_header, str) or not raw_contract_header:
        return True
    contract_header = Path(raw_contract_header)
    if contract_header.is_absolute():
        try:
            return contract_header.resolve() == path.resolve()
        except OSError:
            return False
    try:
        return (REPO_ROOT / contract_header).resolve() == path.resolve()
    except OSError:
        return False


def contract_symbol_patterns(surface_id: Any) -> tuple[re.Pattern[str], ...]:
    if not isinstance(surface_id, str):
        return ()
    return BLOCKED_CONTRACT_HEADER_SYMBOL_PATTERNS.get(surface_id, ())


def public_contract_decision_surfaces_for_header(
    public_header_path: Path,
    decisions_dir: Path,
) -> set[str]:
    surfaces: set[str] = set()
    for decision_path in contract_decision_paths(decisions_dir):
        payload, load_blockers = load_manifest(decision_path)
        if load_blockers or payload is None:
            continue
        if not public_header_matches_contract(public_header_path, payload.get("public_header")):
            continue
        surface_id = payload.get("surface")
        if isinstance(surface_id, str):
            surfaces.add(surface_id)
    return surfaces


def symbol_matches_blocked_contract(symbol: str, surface_id: str) -> bool:
    return any(pattern.search(symbol) for pattern in contract_symbol_patterns(surface_id))


def symbol_matches_contract_forbidden_tokens(symbol: str, payload: dict[str, Any]) -> bool:
    return symbol in set(as_string_list(payload.get("public_header_forbidden_tokens")))


def blocked_contract_public_header_symbol_drift(
    public_header_path: Path,
    decisions_dir: Path,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    public_symbols, blockers = load_public_header_symbols(public_header_path)
    public_symbols -= native_prototype_header_symbols(public_header_path)
    drift: dict[str, dict[str, Any]] = {}
    for decision_path in contract_decision_paths(decisions_dir):
        payload, load_blockers = load_manifest(decision_path)
        if load_blockers:
            blockers.extend(f"public_contract_decision_load_failed:{decision_path}:{item}" for item in load_blockers)
            continue
        if payload is None:
            continue
        if not public_header_matches_contract(public_header_path, payload.get("public_header")):
            continue
        public_header_allowed = payload.get("public_header_allowed")
        raw_declared_symbols = payload.get("public_header_symbols_now")
        declared_symbols = set(as_string_list(raw_declared_symbols))
        if public_header_allowed is not False and raw_declared_symbols != []:
            continue
        surface_id = payload.get("surface")
        if not isinstance(surface_id, str):
            continue
        matching_symbols = sorted(
            symbol
            for symbol in public_symbols
            if symbol not in declared_symbols
            and (
                symbol_matches_blocked_contract(symbol, surface_id)
                or symbol_matches_contract_forbidden_tokens(symbol, payload)
            )
        )
        if matching_symbols:
            drift[str(decision_path)] = {
                "surface": surface_id,
                "public_header_allowed": public_header_allowed,
                "undeclared_symbols": matching_symbols,
            }
    return drift, blockers


def surface_blocks_public_header_symbols(surface: dict[str, Any]) -> bool:
    surface_id = surface.get("id")
    if not isinstance(surface_id, str) or not contract_symbol_patterns(surface_id):
        return False
    if surface_id not in MANIFEST_BACKED_BLOCKED_HEADER_SURFACE_IDS:
        return False
    if surface.get("status") == "promoted":
        return False
    contract = surface.get("v1_decision_contract")
    return (
        isinstance(contract, dict)
        and contract.get("must_remain_without_public_contract_until_promotion") is True
    )


def manifest_public_header_symbol_drift(
    public_header_path: Path,
    manifest_path: Path,
    surfaces_by_id: dict[str, dict[str, Any]],
    decision_backed_surface_ids: set[str],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    public_symbols, blockers = load_public_header_symbols(public_header_path)
    public_symbols -= native_prototype_header_symbols(public_header_path)
    drift: dict[str, dict[str, Any]] = {}
    if blockers:
        return drift, blockers
    for surface_id, surface in sorted(surfaces_by_id.items()):
        if surface_id in decision_backed_surface_ids:
            continue
        if not surface_blocks_public_header_symbols(surface):
            continue
        matching_symbols = sorted(
            symbol for symbol in public_symbols if symbol_matches_blocked_contract(symbol, surface_id)
        )
        if matching_symbols:
            drift[f"{manifest_path}#{surface_id}"] = {
                "surface": surface_id,
                "public_header_allowed": False,
                "undeclared_symbols": matching_symbols,
            }
    return drift, blockers


def release_statement_names_outcome(text: str, surface_id: str, status: str) -> bool:
    return release_statement_surface_record(text, surface_id, status) is not None


def release_statement_surface_record_candidates(
    text: str,
    surface_id: str,
    status: str | None = None,
) -> list[tuple[str, str, bool]]:
    pattern = re.compile(
        rf"^\s*(?P<surface>{re.escape(surface_id)})\s*"
        rf"(?P<delimiter>{RELEASE_STATEMENT_CANONICAL_ROW_DELIMITER_RE}|{RELEASE_STATEMENT_ALTERNATE_ROW_DELIMITER_RE})\s*"
        rf"(?P<status>promoted|excluded|post-v1)"
        rf"(?:\s+{RELEASE_STATEMENT_DETAIL_SEPARATOR_RE}\s*(?P<details>.+)|\s*)$",
        re.IGNORECASE,
    )
    records: list[tuple[str, str, bool]] = []
    for line in text.splitlines():
        match = pattern.fullmatch(line)
        if not match:
            continue
        found_status = match.group("status").lower()
        if status is None or found_status == status.lower():
            has_reviewed_details = bool((match.group("details") or "").strip())
            canonical_reviewed_record = bool(
                re.fullmatch(
                    RELEASE_STATEMENT_CANONICAL_ROW_DELIMITER_RE,
                    match.group("delimiter"),
                )
            ) and (
                match.group("surface") == surface_id
                and match.group("status") == found_status
                and (found_status != "promoted" or has_reviewed_details)
            )
            records.append((found_status, line.strip(), canonical_reviewed_record))
    return records


def release_statement_all_surface_records(text: str | None) -> list[dict[str, Any]]:
    if text is None:
        return []
    pattern = re.compile(
        rf"(?<![A-Za-z0-9_.-])(?P<surface>obelisk\.[A-Za-z0-9_.-]+\.v1)\s*"
        rf"(?P<delimiter>{RELEASE_STATEMENT_CANONICAL_ROW_DELIMITER_RE}|{RELEASE_STATEMENT_ALTERNATE_ROW_DELIMITER_RE})\s*"
        rf"(?P<status>promoted|excluded|post-v1)"
        rf"(?![A-Za-z0-9_-])",
        re.IGNORECASE,
    )
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for match in pattern.finditer(line):
            status = match.group("status").lower()
            surface_id = match.group("surface")
            detail_match = re.match(
                rf"\s+{RELEASE_STATEMENT_DETAIL_SEPARATOR_RE}\s*(?P<details>.+)",
                line[match.end() :],
            )
            has_reviewed_details = bool(
                detail_match is not None
                and (detail_match.group("details") or "").strip()
            )
            canonical_reviewed_record = bool(
                re.fullmatch(
                    RELEASE_STATEMENT_CANONICAL_ROW_DELIMITER_RE,
                    match.group("delimiter"),
                )
            ) and (
                surface_id == surface_id.casefold()
                and match.group("status") == status
                and (status != "promoted" or has_reviewed_details)
            )
            records.append(
                {
                    "surface": surface_id,
                    "outcome": status,
                    "line": line.strip(),
                    "line_number": str(line_number),
                    "canonical_reviewed_record": canonical_reviewed_record,
                }
            )
    return records


def release_statement_surface_records(text: str, surface_id: str, status: str | None = None) -> list[tuple[str, str]]:
    return [
        (found_status, line)
        for found_status, line, canonical_reviewed_record in release_statement_surface_record_candidates(
            text,
            surface_id,
            status,
        )
        if canonical_reviewed_record
    ]


def release_statement_surface_record(text: str, surface_id: str, status: str) -> str | None:
    records = release_statement_surface_records(text, surface_id, status)
    if len(records) != 1:
        return None
    return records[0][1]


def release_statement_recorded_outcome(text: str | None, surface_id: str) -> str | None:
    if text is None:
        return None
    records = release_statement_surface_records(text, surface_id)
    if len(records) > 1:
        return "duplicate-or-mixed"
    if not records:
        return None
    return records[0][0]


def release_statement_duplicate_or_mixed_records(text: str, surface_id: str) -> bool:
    records = release_statement_surface_record_candidates(text, surface_id)
    if len(records) > 1:
        return True
    embedded_record_pattern = re.compile(
        rf"(?<![A-Za-z0-9_.-]){re.escape(surface_id)}\s*"
        rf"(?:{RELEASE_STATEMENT_CANONICAL_ROW_DELIMITER_RE}|{RELEASE_STATEMENT_ALTERNATE_ROW_DELIMITER_RE})\s*"
        rf"(?:promoted|excluded|post-v1)\b",
        re.IGNORECASE,
    )
    if sum(1 for _ in embedded_record_pattern.finditer(text)) > 1:
        return True
    return False


def required_release_statement_text(requirement: str) -> str | None:
    lowered = requirement.lower()
    marker = "the v1 release statement states that "
    if lowered.startswith(marker):
        return requirement[len(marker) :]
    if lowered.startswith("the v1 release statement names "):
        return None
    if lowered.startswith("a scoped non-complete-sdk release statement may name "):
        return None
    if "v1_completion_required changes only" in lowered:
        return None
    return requirement


def required_release_statement_outcomes(surface: dict[str, Any]) -> set[str]:
    contract = surface.get("v1_decision_contract")
    if not isinstance(contract, dict):
        status = surface.get("status")
        return {status} if status in {"excluded", "post-v1"} else set()
    required = as_string_list(contract.get("exclusion_requires"))
    outcomes: set[str] = set()
    surface_id = surface.get("id")
    if not isinstance(surface_id, str):
        return outcomes
    prefix = f"the v1 release statement names {surface_id} as "
    for requirement in required:
        lowered = requirement.lower()
        if not lowered.startswith(prefix.lower()):
            continue
        suffix = lowered[len(prefix) :]
        if "post-v1" in suffix:
            outcomes.add("post-v1")
        if "excluded" in suffix:
            outcomes.add("excluded")
    if outcomes:
        return outcomes
    status = surface.get("status")
    return {status} if status in {"excluded", "post-v1"} else set()


def scoped_release_statement_required_outcome_records(
    completion_blockers: list[str],
    surfaces_by_id: dict[str, dict[str, Any]],
    post_v1_or_excluded: set[str],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for surface_id in completion_blockers:
        if surface_id in seen:
            continue
        seen.add(surface_id)
        surface = surfaces_by_id.get(surface_id)
        if not surface:
            continue
        if surface_id in CANONICAL_V1_REQUIRED_DEPENDENCY_CHAIN:
            continue
        if surface_id in CANONICAL_EXPERIMENTAL_SURFACE_IDS:
            continue
        status = surface.get("status")
        allowed_outcomes = required_release_statement_outcomes(surface)
        if status in {"excluded", "post-v1"}:
            if surface_id not in post_v1_or_excluded:
                continue
            outcome = status
        elif status == "planning" and allowed_outcomes & {"excluded", "post-v1"}:
            outcome = "excluded" if "excluded" in allowed_outcomes else "post-v1"
        else:
            continue
        records.append(
            {
                "surface": surface_id,
                "outcome": outcome,
                "required_release_statement_outcomes": sorted(allowed_outcomes),
                "blocker": "release_statement_missing_non_promoted_blocker_outcomes",
                "scoped_non_complete_bookkeeping_only": True,
                "counts_toward_complete_sdk_claim": False,
                "claim_progress_contribution": 0,
            }
        )
    return records


def text_has_affirmative_release_claim(text: str) -> bool:
    lowered = text.lower()
    for pattern in AFFIRMATIVE_RELEASE_CLAIM_PATTERNS:
        for match in re.finditer(pattern, lowered):
            prefix = lowered[: match.start()]
            clause_start = 0
            for boundary in CLAUSE_START_PATTERN.finditer(prefix):
                clause_start = boundary.end()
            claim_prefix = lowered[clause_start : match.start()]
            if re.search(r"\b(?:no|not|never|excluded|post-v1|post v1)\b", claim_prefix):
                continue
            claim_clause = lowered[clause_start : match.end()]
            if re.match(r"\s*(?:no|not|never|excluded|post-v1|post v1)\b", claim_clause):
                continue
            claim_match = lowered[match.start() : match.end()]
            if re.match(r"\s*(?:no|not|never|excluded|post-v1|post v1)\b", claim_match):
                continue
            return True
    return False


def release_claim_prefix_negator_governs_claim(claim_prefix: str, matched_claim: str) -> bool:
    negators = list(FORBIDDEN_RELEASE_STATEMENT_BROAD_CLAIM_NEGATORS.finditer(claim_prefix))
    if not negators:
        return False
    direct_negators = [
        negator
        for negator in negators
        if FORBIDDEN_RELEASE_STATEMENT_DIRECT_PREFIX_NEGATORS.fullmatch(negator.group(0))
    ]
    if not direct_negators:
        return False
    trailing_prefix = claim_prefix[direct_negators[-1].end() :]
    if "," in trailing_prefix:
        comma_tail = trailing_prefix.rsplit(",", 1)[1]
        if FORBIDDEN_RELEASE_STATEMENT_INDEPENDENT_BROAD_CLAIM_HEAD.match(
            f"{comma_tail}{matched_claim}"
        ):
            return False
    if "," in matched_claim:
        comma_tail = matched_claim.rsplit(",", 1)[1]
        if FORBIDDEN_RELEASE_STATEMENT_INDEPENDENT_BROAD_CLAIM_HEAD.match(comma_tail):
            return False
    if (
        "," not in trailing_prefix
        and FORBIDDEN_RELEASE_STATEMENT_NEGATED_GOVERNING_VERB_PREFIX.fullmatch(
            trailing_prefix.strip()
        )
    ):
        return True
    return (
        FORBIDDEN_RELEASE_STATEMENT_INDEPENDENT_BROAD_CLAIM_HEAD.match(matched_claim) is None
        or not trailing_prefix.strip(" \t,")
    )


def release_claim_prefix_negator_is_detached(claim_prefix: str, matched_claim: str) -> bool:
    negators = list(FORBIDDEN_RELEASE_STATEMENT_BROAD_CLAIM_NEGATORS.finditer(claim_prefix))
    if not negators:
        return False
    trailing_prefix = claim_prefix[negators[-1].end() :]
    if "," not in trailing_prefix:
        return False
    comma_tail = trailing_prefix.rsplit(",", 1)[1]
    return bool(
        FORBIDDEN_RELEASE_STATEMENT_INDEPENDENT_BROAD_CLAIM_HEAD.match(matched_claim)
        or FORBIDDEN_RELEASE_STATEMENT_INDEPENDENT_BROAD_CLAIM_HEAD.match(
            f"{comma_tail}{matched_claim}"
        )
    )


def release_claim_remainder_is_negated_without_affirmative_tail(claim_remainder: str) -> bool:
    if FORBIDDEN_RELEASE_STATEMENT_BROAD_CLAIM_NEGATED_REMAINDER.search(claim_remainder) is None:
        return False
    return FORBIDDEN_RELEASE_STATEMENT_AFFIRMATIVE_TAIL.search(claim_remainder) is None


def release_statement_forbidden_broad_claims(text: str) -> list[str]:
    offenders: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        lowered = line.lower()
        for match in RELEASE_STATEMENT_OUTCOME_PROGRESS_CLAIM_RE.finditer(lowered):
            prefix = lowered[: match.start()]
            clause_start = 0
            for boundary in BROAD_CLAIM_CLAUSE_START_PATTERN.finditer(prefix):
                clause_start = boundary.end()
            claim_prefix = lowered[clause_start : match.start()]
            full_claim = lowered[clause_start : match.end()]
            if (
                RELEASE_STATEMENT_OUTCOME_PROGRESS_NEGATORS.search(claim_prefix)
                or re.search(
                    r"\b(?:not|never|cannot|can't|must\s+not)\s+"
                    r"(?:be\s+)?(?:ready|complete|completed|passed|green|"
                    r"satisf(?:y|ies|ied)|unlocked|counts?|counted|progress)\b",
                    full_claim,
                )
            ):
                continue
            offenders.append(f"line {line_number}: {line.strip()}")
            break
        if offenders and offenders[-1].startswith(f"line {line_number}:"):
            continue
        for pattern in FORBIDDEN_RELEASE_STATEMENT_BROAD_CLAIM_PATTERNS:
            for match in re.finditer(pattern, lowered, flags=re.IGNORECASE):
                prefix = lowered[: match.start()]
                clause_start = 0
                for boundary in BROAD_CLAIM_CLAUSE_START_PATTERN.finditer(prefix):
                    clause_start = boundary.end()
                clause_end = len(lowered)
                for boundary in BROAD_CLAIM_CLAUSE_START_PATTERN.finditer(lowered, match.end()):
                    clause_end = boundary.start()
                    break
                claim_prefix = lowered[clause_start : match.start()]
                claim_clause = lowered[clause_start : match.end()]
                matched_claim = lowered[match.start() : match.end()]
                claim_remainder = lowered[match.end() : clause_end]
                line_remainder = lowered[match.end() :]
                full_clause = lowered[clause_start:clause_end]
                affirmative_not_phrase = FORBIDDEN_RELEASE_STATEMENT_AFFIRMATIVE_NOT_PHRASE.search(
                    full_clause
                )
                if (
                    FORBIDDEN_RELEASE_STATEMENT_BROAD_CLAIM_NEGATORS.search(claim_prefix)
                    and affirmative_not_phrase is None
                    and release_claim_prefix_negator_governs_claim(claim_prefix, matched_claim)
                ):
                    continue
                if (
                    FORBIDDEN_RELEASE_STATEMENT_BROAD_CLAIM_NEGATORS.search(claim_clause)
                    and affirmative_not_phrase is None
                    and (
                        not FORBIDDEN_RELEASE_STATEMENT_BROAD_CLAIM_NEGATORS.search(claim_prefix)
                        or release_claim_prefix_negator_governs_claim(claim_prefix, matched_claim)
                    )
                ):
                    continue
                if (
                    release_claim_remainder_is_negated_without_affirmative_tail(claim_remainder)
                    and release_claim_remainder_is_negated_without_affirmative_tail(line_remainder)
                ):
                    continue
                if (
                    re.search(r"\b(?:plugin\s+hub|pluginhub)\b", full_clause)
                    and PLUGIN_HUB_DEFERRED_CONTEXT.search(full_clause)
                    and not PLUGIN_HUB_EXPLICIT_PUBLIC_CLAIM.search(full_clause)
                ):
                    continue
                if re.match(
                    r"\s*(?:blocked|cannot|does\s+not|do\s+not|excluded|insufficient|"
                    r"limited|must\s+not|no|not|post-v1|post v1)\b",
                    claim_clause,
                ) and affirmative_not_phrase is None and (
                    not FORBIDDEN_RELEASE_STATEMENT_BROAD_CLAIM_NEGATORS.search(claim_prefix)
                    or release_claim_prefix_negator_governs_claim(claim_prefix, matched_claim)
                ):
                    continue
                offenders.append(f"line {line_number}: {line.strip()}")
                break
            else:
                continue
            break
    return offenders


def release_statement_record_has_contradiction(record: str) -> bool:
    lowered = record.lower()
    if re.search(
        r"\b(?:not true that|false that|it is not the case that|not the case that|"
        r"actually included|included despite|contradict)\b",
        lowered,
    ):
        return True
    if re.search(
        r"\b(?:except|other than|unless|but|however)\b[^.;\n]*"
        r"\b(?:included|available|supported|shipped)\b",
        lowered,
    ):
        return True
    return text_has_affirmative_release_claim(record)


def promoted_release_statement_detail(record: str) -> str:
    match = re.search(
        rf"\bpromoted\b\s+{RELEASE_STATEMENT_DETAIL_SEPARATOR_RE}\s*(?P<details>.+)$",
        record,
        re.IGNORECASE,
    )
    return (match.group("details") if match else "").strip()


def promoted_release_statement_detail_has_reviewed_evidence(detail: str) -> bool:
    for raw_clause in PROMOTED_RELEASE_STATEMENT_DETAIL_CLAUSE_SPLIT_RE.split(detail):
        clause = raw_clause.strip()
        if not clause:
            continue
        if PROMOTED_RELEASE_STATEMENT_REVIEWED_EVIDENCE_DETAIL_RE.search(clause):
            return True
    return False


def release_statement_satisfies_promoted_outcome(
    text: str,
    surface_id: str,
) -> bool:
    record = release_statement_surface_record(text, surface_id, "promoted")
    if record is None or release_statement_record_has_contradiction(record):
        return False
    detail = promoted_release_statement_detail(record)
    if not detail:
        return False
    if PROMOTED_RELEASE_STATEMENT_NON_EVIDENCE_DETAIL_RE.search(detail):
        return False
    return promoted_release_statement_detail_has_reviewed_evidence(detail)


def surface_exclusion_claim_terms(surface: dict[str, Any]) -> set[str]:
    terms = set(as_string_list(surface.get("exclusions")))
    terms.update(as_string_list(surface.get("audit_units")))
    if isinstance(surface.get("public_name"), str):
        terms.add(surface["public_name"])
    contract = surface.get("v1_decision_contract")
    if isinstance(contract, dict):
        for requirement in as_string_list(contract.get("exclusion_requires")):
            required_text = required_release_statement_text(requirement)
            if required_text is None:
                continue
            body = re.sub(r"^\s*no\s+", "", required_text, flags=re.IGNORECASE)
            body = re.sub(r"\s+(?:api\s+)?is included in v1\s*$", "", body, flags=re.IGNORECASE)
            for term in re.split(r"\s*,\s*|\s+\bor\b\s+|\s+\band\b\s+", body):
                term = term.strip(" .")
                if len(term) >= 4:
                    terms.add(term)
    return {term.lower() for term in terms if term}


def release_statement_has_surface_claim_contradiction(text: str, surface: dict[str, Any]) -> bool:
    terms = surface_exclusion_claim_terms(surface)
    if not terms:
        return False
    for line in text.splitlines():
        lowered = line.lower()
        if any(term in lowered for term in terms) and text_has_affirmative_release_claim(line):
            return True
    return False


def release_statement_satisfies_exclusion_contract(text: str, surface: dict[str, Any]) -> bool:
    contract = surface.get("v1_decision_contract")
    if not isinstance(contract, dict):
        return False
    required = as_string_list(contract.get("exclusion_requires"))
    if not required:
        return False
    surface_id = surface.get("id")
    status = surface.get("status")
    if not isinstance(surface_id, str):
        return False
    allowed_outcomes = required_release_statement_outcomes(surface)
    recorded_outcome = release_statement_recorded_outcome(text, surface_id)
    if status in {"excluded", "post-v1"}:
        effective_outcome = status
    elif (
        status == "planning"
        and recorded_outcome in {"excluded", "post-v1"}
        and recorded_outcome in allowed_outcomes
    ):
        effective_outcome = recorded_outcome
    else:
        return False
    if recorded_outcome != effective_outcome:
        return False
    if recorded_outcome not in allowed_outcomes:
        return False
    if release_statement_duplicate_or_mixed_records(text, surface_id):
        return False
    record = release_statement_surface_record(text, surface_id, recorded_outcome)
    if record is None:
        return False
    lowered = record.lower()
    if release_statement_record_has_contradiction(record):
        return False
    if release_statement_has_surface_claim_contradiction(text, surface):
        return False
    required_text = [item for item in (required_release_statement_text(item) for item in required) if item]
    if surface_id == "obelisk.mission_transfer_dino_tribe.v1":
        leaf_units = surface.get("leaf_decision_units")
        if not isinstance(leaf_units, list):
            return False
        leaf_statuses = {
            leaf.get("id"): leaf.get("status")
            for leaf in leaf_units
            if isinstance(leaf, dict) and isinstance(leaf.get("id"), str)
        }
        if set(leaf_statuses) != MISSION_TRANSFER_DINO_TRIBE_REQUIRED_LEAVES:
            return False
        if any(leaf_status not in {status, effective_outcome} for leaf_status in leaf_statuses.values()):
            return False
        leaf_terms = {
            "mission": ("mission excluded", "mission post-v1", "mission post v1"),
            "transfer": ("transfer excluded", "transfer post-v1", "transfer post v1"),
            "dino_policy": ("dino_policy excluded", "dino policy excluded", "dino_policy post-v1", "dino policy post-v1"),
            "tribe_policy": ("tribe_policy excluded", "tribe policy excluded", "tribe_policy post-v1", "tribe policy post-v1"),
            "buff_status": ("buff_status excluded", "buff/status excluded", "buff status excluded", "buff_status post-v1", "buff/status post-v1"),
        }
        if not all(any(term in lowered for term in terms) for terms in leaf_terms.values()):
            return False
    return all(item.lower() in lowered for item in required_text)


def release_statement_satisfies_experimental_outcome(text: str, surface_id: str, status: str) -> bool:
    record = release_statement_surface_record(text, surface_id, status)
    if record is None or release_statement_record_has_contradiction(record):
        return False
    if status == "promoted":
        return release_statement_satisfies_promoted_outcome(text, surface_id)
    required_terms = CANONICAL_EXPERIMENTAL_RELEASE_STATEMENT_TEXT.get(surface_id, ())
    lowered = record.lower()
    return all(term.lower() in lowered for term in required_terms)


def repo_relative_evidence_path(raw_path: str) -> Path | None:
    path = Path(raw_path)
    if path.is_absolute():
        try:
            path.relative_to(REPO_ROOT)
        except ValueError:
            return None
    else:
        path = REPO_ROOT / path
    try:
        return path.resolve().relative_to(REPO_ROOT)
    except (OSError, ValueError):
        return None


def evidence_path_is_specific(raw_path: str, surface_id: str) -> bool:
    relative = repo_relative_evidence_path(raw_path)
    if relative is None:
        return False
    relative_text = relative.as_posix()
    if surface_id in STRICT_PROMOTION_EVIDENCE_SURFACE_IDS and relative_text.startswith("scripts/test_"):
        return False
    if relative_text in GENERIC_SCRIPT_EVIDENCE_DENYLIST:
        return False
    if not relative_text.startswith(PROMOTION_EVIDENCE_ALLOWED_PREFIXES):
        return False
    surface_tokens = [
        token
        for token in surface_id.removeprefix("obelisk.").removesuffix(".v1").replace(".", "_").split("_")
        if token
    ]
    lowered = relative_text.lower()
    return any(token.lower() in lowered for token in surface_tokens)


def evidence_path_has_non_promotional_marker(raw_path: str) -> bool:
    relative = repo_relative_evidence_path(raw_path)
    if relative is None:
        return False

    def normalized_marker_text(text: str) -> str:
        separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", text)
        return re.sub(r"[^a-z0-9]+", "_", separated.lower()).strip("_")

    normalized_parts = [
        normalized_marker_text(part)
        for part in relative.with_suffix("").parts
    ]
    for part in normalized_parts:
        if POST_RUNTIME_P0_CHAIN_SHORTCUT_MARKER_RE.search(part):
            return True
        collapsed_part = part.replace("_", "")
        for marker in STRICT_PROMOTION_EVIDENCE_PATH_DENY_MARKERS:
            normalized_marker = normalized_marker_text(marker)
            collapsed_marker = normalized_marker.replace("_", "")
            if normalized_marker in part or collapsed_marker in collapsed_part:
                return True
    return False


def evidence_path_exists(raw_path: str, *, allow_generic_dirs: bool) -> bool:
    relative = repo_relative_evidence_path(raw_path)
    if relative is None:
        return False
    path = REPO_ROOT / relative
    if not path.exists():
        return False
    if path.is_dir():
        return allow_generic_dirs and relative.as_posix() in ALLOWED_GENERIC_EVIDENCE_DIRS
    return path.is_file()


def evidence_has_non_promotional_schema_marker(
    value: Any,
    *,
    parent_key: str | None = None,
) -> bool:
    normalized_key = None
    if isinstance(parent_key, str):
        separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", parent_key)
        normalized_key = re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")
    if normalized_key in STRICT_PROMOTION_EVIDENCE_SCHEMA_KEYS:
        try:
            text = json.dumps(value, sort_keys=True)
        except TypeError:
            text = str(value)
        normalized_text = normalized_completion_claim_key(text)
        if POST_RUNTIME_P0_CHAIN_SHORTCUT_MARKER_RE.search(normalized_text):
            return True
        if (
            normalized_key in STRICT_PROMOTION_EVIDENCE_SOURCE_MARKER_KEYS
            and STRICT_PROMOTION_EVIDENCE_SOURCE_ONLY_DENY_MARKERS.search(text)
        ):
            return True
        if STRICT_PROMOTION_EVIDENCE_SCHEMA_DENY_MARKERS.search(text):
            return True
    if isinstance(value, dict):
        for key, item in value.items():
            next_key = key if isinstance(key, str) else None
            if evidence_has_non_promotional_schema_marker(item, parent_key=next_key):
                return True
    if isinstance(value, list):
        return any(
            evidence_has_non_promotional_schema_marker(item, parent_key=parent_key)
            for item in value
        )
    return False


def evidence_has_forbidden_ready_scope(value: Any) -> bool:
    def normalized_scope_text(item: object) -> str:
        separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(item))
        return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")

    if isinstance(value, dict):
        for key, item in value.items():
            if (
                isinstance(item, str)
                and normalized_scope_text(key) in PROMOTION_EVIDENCE_SCOPE_KEYS
                and (
                    normalized_scope_text(item) in PROMOTION_EVIDENCE_FORBIDDEN_READY_SCOPES
                    or POST_RUNTIME_P0_CHAIN_SHORTCUT_MARKER_RE.search(
                        normalized_scope_text(item)
                    )
                    is not None
                )
            ):
                return True
            if evidence_has_forbidden_ready_scope(item):
                return True
        return False
    if isinstance(value, list):
        return any(evidence_has_forbidden_ready_scope(item) for item in value)
    return False


def evidence_has_non_promotional_artifact_reference(
    value: Any,
    *,
    parent_key: str | None = None,
    in_artifact_reference: bool = False,
) -> bool:
    def normalized_marker_text(item: object) -> str:
        separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(item))
        return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")

    normalized_key = normalized_marker_text(parent_key) if parent_key is not None else ""
    key_is_structured_promotion_reference = (
        normalized_key in STRUCTURED_PROMOTION_EVIDENCE_REFERENCE_KEYS
        or normalized_key in PROMOTION_CERTIFICATE_HASH_BINDING_REFERENCE_KEYS
    )
    key_is_artifact_reference = (
        not key_is_structured_promotion_reference
        and (
            normalized_key in NON_PROMOTIONAL_ARTIFACT_REFERENCE_KEYS
            or normalized_key.endswith(NON_PROMOTIONAL_ARTIFACT_REFERENCE_KEY_SUFFIXES)
        )
    )
    if (
        normalized_key
        and not key_is_structured_promotion_reference
        and NON_PROMOTIONAL_ARTIFACT_REFERENCE_KEY_MARKERS.search(normalized_key)
    ):
        return True
    if (
        normalized_key
        and not key_is_structured_promotion_reference
        and POST_RUNTIME_P0_CHAIN_SHORTCUT_MARKER_RE.search(normalized_key)
    ):
        return True
    current_reference = in_artifact_reference or key_is_artifact_reference

    if isinstance(value, dict):
        if report_is_limited_to_non_promotional_readiness(value):
            return True
        for key, item in value.items():
            next_key = key if isinstance(key, str) else None
            if evidence_has_non_promotional_artifact_reference(
                item,
                parent_key=next_key,
                in_artifact_reference=current_reference,
            ):
                return True
        return False
    if isinstance(value, list):
        return any(
            evidence_has_non_promotional_artifact_reference(
                item,
                parent_key=parent_key,
                in_artifact_reference=current_reference,
            )
            for item in value
        )
    if isinstance(value, str) and current_reference:
        normalized_value = normalized_marker_text(value)
        return (
            NON_PROMOTIONAL_ARTIFACT_REFERENCE_VALUE_MARKERS.search(normalized_value)
            is not None
            or POST_RUNTIME_P0_CHAIN_SHORTCUT_MARKER_RE.search(normalized_value)
            is not None
        )
    return False


def evidence_has_unscoped_public_contract_review_status_reference(
    value: Any,
    *,
    surface_id: str,
    parent_key: str | None = None,
) -> bool:
    def normalized_marker_text(item: object) -> str:
        separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(item))
        return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")

    normalized_key = normalized_marker_text(parent_key) if parent_key is not None else ""
    if (
        normalized_key in PUBLIC_CONTRACT_REVIEW_STATUS_REFERENCE_KEYS
        and surface_id not in PUBLIC_CONTRACT_REVIEW_STATUS_REFERENCE_ALLOWED_SURFACE_IDS
    ):
        return True
    if isinstance(value, dict):
        for key, item in value.items():
            next_key = key if isinstance(key, str) else None
            if evidence_has_unscoped_public_contract_review_status_reference(
                item,
                surface_id=surface_id,
                parent_key=next_key,
            ):
                return True
        return False
    if isinstance(value, list):
        return any(
            evidence_has_unscoped_public_contract_review_status_reference(
                item,
                surface_id=surface_id,
                parent_key=parent_key,
            )
            for item in value
        )
    return False


def report_is_limited_to_non_promotional_readiness(report: Any) -> bool:
    if not isinstance(report, dict):
        return False
    if has_source_overclaim_marker(report):
        return True
    if any(
        report.get(key) is True
        for key in (
            "planning_only",
            "accepted_for_planning",
            "accepted_for_internal_planning",
            "accepted_for_offline_planning",
            "accepted_for_contract_review",
            "accepted_for_public_contract_review",
            "contract_review_artifact_ready",
            "contract_review_ready",
            "public_contract_allowed",
            "public_contract_artifact_ready",
            "public_contract_ready",
            "public_contract_review_ready",
            "reviewed_public_contract",
            "reviewed_public_contract_ready",
            "accepted_for_runtime_evidence_preconditions",
            "accepted_runtime_evidence_precondition",
            "accepted_runtime_evidence_preconditions",
            "accepted_artifact_class",
            "accepted_artifact_class_report",
            "accepted_artifact_class_ready",
            "activation_preconditions",
            "activation_preconditions_met",
            "offline_pre_activation_consistency",
            "pre_activation_consistency",
            "accepted_runtime_evidence",
            "approved_runtime_evidence_accepted",
            "bundle_accepted",
            "evidence_bundle_accepted",
            "runtime_evidence_preconditions_accepted",
            "beta_notice",
            "beta_notice_send",
            "beta_notice_sent",
            "beta_notice_sent_attestation",
            "bot_notice",
            "bot_notice_sent",
            "confirmed_beta_notice_sent",
            "confirmed_send",
            "confirmed_notice_report",
            "confirmed_notice_sent",
            "discord_beta_bridge",
            "discord_beta_bridge_bot_notice",
            "discord_beta_bridge_config",
            "discord_beta_bridge_event",
            "discord_beta_bot_notice",
            "discord_bot_notice",
            "discord_sent",
            "notice_report",
            "notice_action",
            "notice_action_accepted",
            "notice_action_sent",
            "notice_dry_run",
            "notice_dry_run_accepted",
            "notice_dry_run_sent",
            "notice_sent",
            "player_notice",
            "player_notice_action",
            "player_notice_action_accepted",
            "player_notice_action_required",
            "player_notice_action_sent",
            "player_notice_dry_run_accepted",
            "player_notice_dry_run_sent",
            "player_notice_sent",
            "candidate_only",
            "pre_abi",
            "abi_consumer_guardrail",
            "abi_consumer_guardrails",
            "call_process_event_post_init",
            "post_init_call_process_event",
            "sdk_consumer_guardrail",
            "sdk_consumer_guardrails",
            "copied_log_only",
            "copied_log_only_artifact",
            "copied_log_only_report",
            "copied_bool_fixture_boundary",
            "fixture_boundary",
            "fixture_boundary_only",
            "internal_fixture_boundary",
            "internal_fixture_boundary_only",
            "internal_only",
            "mission_copied_bool",
            "mission_copied_bool_fixture_boundary",
            "readiness_only",
            "report_only",
            "ready_log_evidence_split",
            "ready_log_evidence_split_ready",
            "lifecycle_event_split",
            "lifecycle_event_split_ready",
            "player_principal_lifecycle_event_split_summary",
            "player_principal_lifecycle_event_split_ready",
            "post_runtime_contract_gap",
            "post_runtime_contract_gap_diagnostic",
            "post_runtime_contract_gap_ready",
            "route_sample",
            "route_sample_ready",
            "route_samples",
            "route_samples_ready",
            "closure_report",
            "evidence_closure",
            "evidence_closure_report",
            "scoped_non_complete",
            "scoped_non_complete_only",
            "transfer_scriptstruct_readiness",
            "transfer_scriptstruct_ready",
            "transfer_script_struct_readiness",
            "transfer_script_struct_ready",
            "transfer_baccept_readiness",
            "transfer_baccept_ready",
            "dino_scalar_readiness",
            "dino_scalar_ready",
            "scalar_only_ready",
            "precall_scalar_ready",
            "buff_status_readiness",
            "buff_status_ready",
            "buff_status_candidate_ready",
            "tribe_scalar_boundary_readiness",
            "tribe_scalar_boundary_ready",
            "scalar_boundary_readiness",
            "scalar_boundary_ready",
            "post_evidence_p0_lock_simulation",
            "post_evidence_identity_lock",
            "identity_lock",
            "identity_lock_ready",
            "route_simulation",
            "route_lock_simulation",
            "request_check",
            "request_check_ready",
            "request_pack_ready",
            "package_check",
            "package_install",
            "package_install_succeeded",
            "install_package",
            "install_package_succeeded",
            "find_package",
            "find_package_succeeded",
            "cmake_package_check",
            "component_sdk_check",
            "runtime_window_plan",
            "runtime_window_plan_ready",
            "runtime_window_planner",
            "runtime_window_closure",
            "runtime_window_closure_ready",
            "runtime_window_executor",
            "runtime_window_executor_closure",
            "runtime_window_execution",
            "route_ready",
            "route_gate_post_evidence_p0_lock_simulation",
            "simulation_only",
            "binding_required",
            "binding_required_report",
            "binding_required_ready",
        )
    ):
        return True
    if has_post_runtime_p0_chain_shortcut_marker(
        {
            key: value
            for key, value in report.items()
            if normalized_completion_claim_key(key)
            in {
                "artifact_scope",
                "classification",
                "evidence_kind",
                "path_type",
                "readiness_scope",
                "ready_scope",
                "schema",
                "source_kind",
                "source_schema",
                "source_scope",
                "source_value",
                "status",
                "target_set",
                "type",
            }
            or normalized_completion_claim_key(key) in SOURCE_OVERCLAIM_MARKER_KEYS
        }
    ):
        return True
    ready_scope = report.get("ready_scope")
    if not isinstance(ready_scope, str):
        return False
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", ready_scope)
    normalized_scope = re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")
    return (
        normalized_scope in PROMOTION_EVIDENCE_FORBIDDEN_READY_SCOPES
        or POST_RUNTIME_P0_CHAIN_SHORTCUT_MARKER_RE.search(normalized_scope) is not None
    )


def evidence_has_explicit_no_approved_claim(value: Any) -> bool:
    def normalized_marker_text(item: object) -> str:
        separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(item))
        return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")

    def claim_value_is_none(item: Any) -> bool:
        if item is False or item is None:
            return True
        if isinstance(item, (int, float)) and not isinstance(item, bool):
            return item == 0
        if isinstance(item, str):
            return normalized_marker_text(item) in APPROVED_EVIDENCE_CLAIM_NONE_VALUES
        return False

    if isinstance(value, dict):
        for key, item in value.items():
            key_name = normalized_marker_text(key)
            if key_name in APPROVED_EVIDENCE_CLAIM_KEYS and claim_value_is_none(item):
                return True
            if evidence_has_explicit_no_approved_claim(item):
                return True
        return False
    if isinstance(value, list):
        return any(evidence_has_explicit_no_approved_claim(item) for item in value)
    return False


def normalized_runtime_evidence_marker_text(value: object) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value))
    return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")


def runtime_evidence_positive_marker_value(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value > 0
    if isinstance(value, str):
        normalized = normalized_runtime_evidence_marker_text(value)
        return normalized not in {"", "0", "false", "none", "not_applicable", "absent"}
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def approved_runtime_accepted_lifecycle_count(payload: dict[str, Any]) -> int | None:
    for key in APPROVED_RUNTIME_ACCEPTED_COUNT_KEYS:
        value = payload.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    for key in APPROVED_RUNTIME_ACCEPTED_LIST_KEYS:
        value = payload.get(key)
        if isinstance(value, list):
            return len(value)
    return None


def approved_runtime_diagnostic_material_present(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            key_name = normalized_runtime_evidence_marker_text(key)
            if (
                "diagnostic" in key_name
                or "observer_event_triage" in key_name
                or "fname_mismatch" in key_name
                or "f_name_mismatch" in key_name
                or NON_PUBLIC_CHECKJOIN_REJECTED_OFFLINE_ACCEPTANCE_RE.search(key_name)
                is not None
            ) and runtime_evidence_positive_marker_value(item):
                return True
            if approved_runtime_diagnostic_material_present(item):
                return True
        return False
    if isinstance(value, list):
        return any(approved_runtime_diagnostic_material_present(item) for item in value)
    if isinstance(value, str):
        return APPROVED_RUNTIME_DIAGNOSTIC_MISMATCH_TEXT_RE.search(value) is not None
    return False


def non_public_checkjoin_session_start_rejected_acceptance_present(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if (
                NON_PUBLIC_CHECKJOIN_REJECTED_OFFLINE_ACCEPTANCE_RE.search(
                    normalized_runtime_evidence_marker_text(key)
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
                normalized_runtime_evidence_marker_text(value)
            )
            is not None
        )
    return False


def approved_runtime_evidence_non_approved_artifact_reasons(
    payload: dict[str, Any],
    reason_prefix: str,
) -> list[str]:
    reasons: list[str] = []
    required_event_count = len(
        getattr(
            approved_runtime_principal_lifecycle_evidence,
            "REQUIRED_OBSERVED_EVENT_CASES",
            (),
        )
    )

    def add(reason: str) -> None:
        formatted = f"{reason_prefix}:{reason}"
        if formatted not in reasons:
            reasons.append(formatted)

    def add_shortcut_marker_reasons(marker_text: str, *, positive: bool = True) -> None:
        if not positive:
            return
        for marker, reason in POST_RUNTIME_P0_CHAIN_RUNTIME_FORBIDDEN_MARKERS:
            if marker in marker_text:
                add(reason)

    def visit(value: Any, depth: int = 0) -> None:
        if isinstance(value, dict):
            if non_public_checkjoin_session_start_rejected_acceptance_present(value):
                add(
                    "checkjoininprogress_session_start_rejected_offline_acceptance_not_approved_runtime_evidence"
                )
            if has_source_overclaim_marker(value):
                add("source_overclaim_zero_not_approved_runtime_evidence")
            accepted_count = approved_runtime_accepted_lifecycle_count(value)
            if accepted_count is not None and required_event_count and accepted_count != required_event_count:
                add("partial_lifecycle_events_not_approved_runtime_evidence")
            if approved_runtime_diagnostic_material_present(value) and accepted_count is not None:
                if accepted_count == 0 or (required_event_count and accepted_count != required_event_count):
                    add("diagnostic_only_mismatch_summary_not_approved_runtime_evidence")
            for key, item in value.items():
                key_name = normalized_runtime_evidence_marker_text(key)
                for marker, reason in APPROVED_RUNTIME_EVIDENCE_FORBIDDEN_MARKERS:
                    if marker in key_name and runtime_evidence_positive_marker_value(item):
                        add(reason)
                add_shortcut_marker_reasons(
                    key_name,
                    positive=(
                        runtime_evidence_positive_marker_value(item)
                        or key_name in SOURCE_OVERCLAIM_MARKER_KEYS
                    ),
                )
                if (
                    any(marker in key_name for marker in APPROVED_RUNTIME_PARTIAL_LIFECYCLE_MARKERS)
                    and runtime_evidence_positive_marker_value(item)
                ):
                    add("partial_lifecycle_events_not_approved_runtime_evidence")
                if (
                    depth == 0
                    and key_name in APPROVED_RUNTIME_EVIDENCE_CLASSIFICATION_KEYS
                    and isinstance(item, str)
                ):
                    item_marker = normalized_runtime_evidence_marker_text(item)
                    for marker, reason in APPROVED_RUNTIME_EVIDENCE_FORBIDDEN_MARKERS:
                        if marker in item_marker:
                            add(reason)
                    add_shortcut_marker_reasons(item_marker)
                visit(item, depth + 1)
        elif isinstance(value, list):
            for item in value:
                visit(item, depth)

    visit(payload)
    return reasons


def structured_readiness_report_claim_blockers(report: dict[str, Any], reason_prefix: str) -> list[str]:
    missing: list[str] = []
    if command_permission_route_gate_public_or_runtime_claims(report):
        missing.append(f"{reason_prefix}:public_or_runtime_claim_without_blocker")
    if secondary_report_completion_claims_without_blocker(report):
        missing.append(f"{reason_prefix}:completion_claim_without_blocker")
    return missing


def promotion_evidence_path_is_specific_to_leaf(raw_path: str, leaf_id: str) -> bool:
    relative = repo_relative_evidence_path(raw_path)
    if relative is None:
        return False
    lowered = relative.as_posix().lower()
    leaf_tokens = [token for token in leaf_id.replace("-", "_").split("_") if token]
    return bool(leaf_tokens) and all(token.lower() in lowered for token in leaf_tokens)


def strict_promotion_evidence_value_valid(
    value: Any,
    *,
    surface_id: str,
    evidence_key: str | None = None,
    leaf_id: str | None = None,
) -> bool:
    def item_valid(item: str) -> bool:
        relative = repo_relative_evidence_path(item)
        if relative is None:
            return False
        relative_text = relative.as_posix()
        if evidence_key in {"sdk_consumer_tests", "installed_sdk_consumer_tests"}:
            if (
                relative_text == "tests/sdk_installed_consumer"
                or relative_text.startswith("tests/sdk_installed_consumer/")
            ):
                return False
            if not (
                relative_text == "tests/sdk_consumer"
                or relative_text.startswith("tests/sdk_consumer/")
            ):
                return False
        if evidence_key == "abi_tests":
            if not (relative_text.startswith("tests/abi/") or relative_text.startswith("tests/core/")):
                return False
        if evidence_path_has_non_promotional_marker(item):
            return False
        if not evidence_path_exists(item, allow_generic_dirs=False):
            return False
        if not evidence_path_is_specific(item, surface_id):
            return False
        if leaf_id is not None and not promotion_evidence_path_is_specific_to_leaf(item, leaf_id):
            return False
        return True

    if isinstance(value, list) and value:
        return all(isinstance(item, str) and item_valid(item) for item in value)
    return isinstance(value, str) and item_valid(value)


def strict_promotion_evidence_has_valid_paths(
    evidence: dict[str, Any],
    *,
    surface_id: str,
    leaf_id: str | None = None,
) -> bool:
    return strict_promotion_evidence_value_valid(
        evidence.get("abi_tests"),
        surface_id=surface_id,
        evidence_key="abi_tests",
        leaf_id=leaf_id,
    ) and strict_promotion_evidence_value_valid(
        evidence.get("sdk_consumer_tests"),
        surface_id=surface_id,
        evidence_key="sdk_consumer_tests",
        leaf_id=leaf_id,
    )


def surface_has_promotion_evidence(surface: dict[str, Any]) -> bool:
    if surface.get("status") != "promoted":
        return False
    evidence = surface.get("evidence")
    if not isinstance(evidence, dict) or not evidence:
        return False
    surface_id = surface.get("id")
    if not isinstance(surface_id, str):
        return False
    if evidence_has_forbidden_ready_scope(evidence):
        return False
    if evidence_has_non_promotional_schema_marker(evidence):
        return False
    if evidence_has_non_promotional_artifact_reference(evidence):
        return False
    if evidence_has_unscoped_public_contract_review_status_reference(
        evidence,
        surface_id=surface_id,
    ):
        return False
    if evidence_has_explicit_no_approved_claim(evidence):
        return False
    if evidence_is_generated_promotion_certificate_or_builder_report(evidence):
        return False
    if report_is_limited_to_non_promotional_readiness(evidence):
        return False
    if surface_id == "obelisk.mission_transfer_dino_tribe.v1":
        leaf_units = surface.get("leaf_decision_units")
        if not isinstance(leaf_units, list) or not leaf_units:
            return False
        leaves = {leaf.get("id"): leaf for leaf in leaf_units if isinstance(leaf, dict)}
        observed = {leaf_id: leaf.get("status") for leaf_id, leaf in leaves.items()}
        required = {"mission", "transfer", "dino_policy", "tribe_policy", "buff_status"}
        if set(observed) != required or any(observed.get(leaf_id) != "promoted" for leaf_id in required):
            return False
        per_leaf_evidence = surface.get("promotion_evidence_by_leaf")
        per_leaf_evidence = per_leaf_evidence if isinstance(per_leaf_evidence, dict) else {}
        for leaf_id in required:
            leaf_evidence = leaves[leaf_id].get("evidence")
            if not isinstance(leaf_evidence, dict):
                leaf_evidence = per_leaf_evidence.get(leaf_id)
            if not isinstance(leaf_evidence, dict):
                return False
            if evidence_has_forbidden_ready_scope(leaf_evidence):
                return False
            if evidence_has_non_promotional_schema_marker(leaf_evidence):
                return False
            if evidence_has_non_promotional_artifact_reference(leaf_evidence):
                return False
            if evidence_has_unscoped_public_contract_review_status_reference(
                leaf_evidence,
                surface_id=surface_id,
            ):
                return False
            if evidence_has_explicit_no_approved_claim(leaf_evidence):
                return False
            if evidence_is_generated_promotion_certificate_or_builder_report(leaf_evidence):
                return False
            if report_is_limited_to_non_promotional_readiness(leaf_evidence):
                return False
            if leaf_evidence.get("promotion_status") != "promoted":
                return False
            for flag in ("promotion_ready", "public_sdk_ready", "runtime_ready"):
                if leaf_evidence.get(flag) is not True:
                    return False
            for key in ("abi_tests", "sdk_consumer_tests", "second_source_evidence"):
                value = leaf_evidence.get(key)
                if not isinstance(value, list) or not value:
                    return False
            if not strict_promotion_evidence_has_valid_paths(
                leaf_evidence,
                surface_id=surface_id,
                leaf_id=leaf_id,
            ):
                return False
    allow_generic_dirs = surface_id not in STRICT_PROMOTION_EVIDENCE_SURFACE_IDS
    if not allow_generic_dirs:
        if evidence.get("surface_id") != surface_id:
            return False
        if evidence.get("promotion_status") != "promoted":
            return False
        if evidence.get("public_sdk_ready") is not True:
            return False
        if evidence_has_non_promotional_schema_marker(evidence):
            return False
        if not isinstance(evidence.get("abi_tests"), list) or not evidence["abi_tests"]:
            return False
        if not isinstance(evidence.get("sdk_consumer_tests"), list) or not evidence["sdk_consumer_tests"]:
            return False
    def evidence_value_valid(value: Any, *, evidence_key: str | None = None) -> bool:
        if not allow_generic_dirs:
            return strict_promotion_evidence_value_valid(
                value,
                surface_id=surface_id,
                evidence_key=evidence_key,
            )

        def item_valid(item: str) -> bool:
            relative = repo_relative_evidence_path(item)
            if relative is None:
                return False
            relative_text = relative.as_posix()
            if not allow_generic_dirs and evidence_key in {"sdk_consumer_tests", "installed_sdk_consumer_tests"}:
                if not (
                    relative_text == "tests/sdk_consumer"
                    or relative_text.startswith("tests/sdk_consumer/")
                    or relative_text == "tests/sdk_installed_consumer"
                    or relative_text.startswith("tests/sdk_installed_consumer/")
                ):
                    return False
            if not allow_generic_dirs and evidence_key == "abi_tests":
                if not (relative_text.startswith("tests/abi/") or relative_text.startswith("tests/core/")):
                    return False
            if not allow_generic_dirs and evidence_path_has_non_promotional_marker(item):
                return False
            return evidence_path_exists(item, allow_generic_dirs=allow_generic_dirs) and (
                allow_generic_dirs or evidence_path_is_specific(item, surface_id)
            )

        if isinstance(value, list) and value:
            return all(isinstance(item, str) and item_valid(item) for item in value)
        return isinstance(value, str) and item_valid(value)

    if not allow_generic_dirs and not (
        evidence_value_valid(evidence.get("abi_tests"), evidence_key="abi_tests")
        and evidence_value_valid(evidence.get("sdk_consumer_tests"), evidence_key="sdk_consumer_tests")
    ):
        return False

    machine_keys = (
        "abi_tests",
        "sdk_consumer_tests",
        "tests",
        "install_gate",
    )
    for key in machine_keys:
        if evidence_value_valid(evidence.get(key), evidence_key=key):
            return True
    return False


def surface_declares_completion_equivalent(surface: dict[str, Any], blocker_id: str) -> bool:
    return blocker_id in as_string_list(surface.get("v1_completion_equivalent_for"))


def reviewed_completion_equivalent_allowed(blocker_id: str, equivalent_id: str) -> bool:
    return equivalent_id in REVIEWED_V1_COMPLETION_EQUIVALENTS.get(blocker_id, ())


def explicit_completion_equivalent_satisfies(
    blocker_id: str,
    equivalent_surface_ids: list[str],
    surfaces_by_id: dict[str, dict[str, Any]],
) -> str | None:
    if blocker_id in CANONICAL_V1_REQUIRED_DEPENDENCY_CHAIN:
        return None
    for equivalent_id in equivalent_surface_ids:
        equivalent_surface = surfaces_by_id.get(equivalent_id)
        if not equivalent_surface:
            continue
        if not reviewed_completion_equivalent_allowed(blocker_id, equivalent_id):
            continue
        if equivalent_surface.get("status") != "promoted":
            continue
        if not surface_declares_completion_equivalent(equivalent_surface, blocker_id):
            continue
        if not surface_has_promotion_evidence(equivalent_surface):
            continue
        return equivalent_id
    return None


def complete_sdk_minimum_promoted_demand_family_gaps(
    surfaces_by_id: dict[str, dict[str, Any]],
    stable_contract: dict[str, Any] | None,
) -> tuple[list[str], dict[str, str]]:
    explicit_equivalents = as_string_map(
        stable_contract.get("promoted_demand_family_equivalents") if stable_contract else None
    )
    gaps: list[str] = []
    satisfied_by: dict[str, str] = {}
    for blocker_id in sorted(CANONICAL_COMPLETE_SDK_MINIMUM_PROMOTED_DEMAND_FAMILIES):
        surface = surfaces_by_id.get(blocker_id)
        if surface and surface.get("status") == "promoted" and surface_has_promotion_evidence(surface):
            continue
        equivalent_id = explicit_completion_equivalent_satisfies(
            blocker_id,
            explicit_equivalents.get(blocker_id, []),
            surfaces_by_id,
        )
        if equivalent_id is not None:
            satisfied_by[blocker_id] = equivalent_id
            continue
        gaps.append(blocker_id)
    return gaps, satisfied_by


def installed_sdk_package_shape_guardrail_drift(manifest: dict[str, Any]) -> list[str]:
    installed_shape = manifest.get("installed_sdk_package_shape")
    if not isinstance(installed_shape, dict):
        return ["installed_sdk_package_shape_missing"]

    drift: list[str] = []
    if installed_shape.get("component") != CANONICAL_INSTALLED_SDK_PACKAGE_SHAPE["component"]:
        drift.append("component")
    if installed_shape.get("status") != CANONICAL_INSTALLED_SDK_PACKAGE_SHAPE["status"]:
        drift.append("status")

    installed_files = as_string_list(installed_shape.get("installed_files"))
    expected_installed_files = list(CANONICAL_INSTALLED_SDK_PACKAGE_SHAPE["installed_files"])
    if installed_files != expected_installed_files:
        drift.append("installed_files")

    not_sufficient_for = set(as_string_list(installed_shape.get("not_sufficient_for")))
    for item in CANONICAL_INSTALLED_SDK_PACKAGE_SHAPE["not_sufficient_for"]:
        if item not in not_sufficient_for:
            drift.append(f"not_sufficient_for:{item}")

    non_claim_exports = installed_shape.get("non_claim_exports")
    expected_non_claim_exports = CANONICAL_INSTALLED_SDK_PACKAGE_SHAPE["non_claim_exports"]
    if not isinstance(non_claim_exports, dict):
        drift.append("non_claim_exports")
    else:
        for key, expected_value in expected_non_claim_exports.items():
            if non_claim_exports.get(key) is not expected_value:
                drift.append(f"non_claim_exports:{key}")

    forbidden_positive_keys = {
        normalized_completion_claim_key(key)
        for key in (
            *INSTALLED_SDK_PACKAGE_SHAPE_FORBIDDEN_POSITIVE_CLAIM_KEYS,
            *COMMAND_PERMISSION_ROUTE_GATE_FORBIDDEN_CLAIM_KEYS,
            *SECONDARY_REPORT_FORBIDDEN_COMPLETION_CLAIM_KEYS,
        )
    }
    forbidden_alias_keys = {
        normalized_completion_claim_key(key)
        for key in INSTALLED_SDK_PACKAGE_SHAPE_FORBIDDEN_ALIAS_KEYS
    }

    def positive_installed_claim_value(key_name: str, value: Any) -> bool:
        if key_name in forbidden_alias_keys:
            return bool(value)
        return is_positive_completion_claim_value(value)

    def visit(value: Any, path: str = "") -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                key_path = f"{path}.{key}" if path else str(key)
                key_name = normalized_completion_claim_key(key)
                path_suffixes = normalized_claim_path_suffixes(key_path)
                if (
                    key_name in forbidden_positive_keys
                    or key_name in forbidden_alias_keys
                    or BROAD_ROUTE_GATE_CLAIM_KEY_RE.fullmatch(key_name)
                    or any(suffix in forbidden_positive_keys for suffix in path_suffixes)
                    or any(suffix in forbidden_alias_keys for suffix in path_suffixes)
                    or any(BROAD_ROUTE_GATE_CLAIM_KEY_RE.fullmatch(suffix) for suffix in path_suffixes)
                ) and (
                    positive_installed_claim_value(key_name, item)
                    or any(
                        positive_installed_claim_value(suffix, item)
                        for suffix in path_suffixes
                        if suffix in forbidden_alias_keys
                    )
                ):
                    drift.append(f"positive_claim:{key_path}")
                visit(item, key_path)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]")

    visit(installed_shape)
    for claim_path in secondary_report_completion_claims_without_blocker(
        {
            "schema": "obelisk.installed-sdk-package-shape.v1",
            "blockers": [],
            "installed_sdk_package_shape": installed_shape,
        }
    ):
        if claim_path.startswith("installed_sdk_package_shape."):
            claim_path = claim_path[len("installed_sdk_package_shape.") :]
        drift_item = f"positive_claim:{claim_path}"
        if drift_item not in drift:
            drift.append(drift_item)
    return drift


def promotion_evidence_key_is_negative_context(parent_key: str | None) -> bool:
    if parent_key is None:
        return False
    normalized = parent_key.lower().replace("-", "_")
    return any(marker in normalized for marker in PROMOTION_EVIDENCE_NEGATIVE_CONTEXT_KEYS)


def evidence_value_contains_positive_term(
    value: Any,
    term: str,
    *,
    parent_key: str | None = None,
) -> bool:
    if promotion_evidence_key_is_negative_context(parent_key):
        return False
    if isinstance(value, dict):
        for key, item in value.items():
            next_key = key if isinstance(key, str) else None
            if evidence_value_contains_positive_term(item, term, parent_key=next_key):
                return True
        return False
    if isinstance(value, list):
        return any(
            evidence_value_contains_positive_term(item, term, parent_key=parent_key) for item in value
        )
    if isinstance(value, (str, int, float, bool)) or value is None:
        text = str(value)
    else:
        try:
            text = json.dumps(value, sort_keys=True)
        except TypeError:
            text = str(value)
    normalized_text = text.strip().lower()
    normalized_term = term.strip().lower()
    if normalized_term not in normalized_text:
        return False
    if normalized_text == normalized_term:
        return True
    return PROMOTION_EVIDENCE_NEGATIVE_TERM_CONTEXT.search(text) is None


def surface_missing_required_promotion_evidence(surface: dict[str, Any]) -> list[str]:
    surface_id = surface.get("id")
    if not isinstance(surface_id, str) or surface.get("status") != "promoted":
        return []
    required_terms = PROMOTION_EVIDENCE_REQUIRED_TERMS.get(surface_id, ())
    if not required_terms:
        return []
    evidence = surface.get("evidence", {})
    return [term for term in required_terms if not evidence_value_contains_positive_term(evidence, term)]


def load_repo_relative_json_evidence(raw_path: Any) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(raw_path, str) or not raw_path:
        return None, "missing"
    relative = repo_relative_evidence_path(raw_path)
    if relative is None:
        return None, "path_not_repo_relative"
    path = REPO_ROOT / relative
    if not path.is_file():
        return None, "path_not_file"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "json_unreadable"
    if not isinstance(payload, dict):
        return None, "json_not_object"
    return payload, None


def resolve_report_source_artifact(raw_path: Any, reason_prefix: str) -> tuple[Path | None, list[str]]:
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None, [f"{reason_prefix}:source_artifact_missing"]
    path = Path(raw_path)
    if not path.is_absolute():
        relative = repo_relative_evidence_path(raw_path)
        if relative is None:
            return None, [f"{reason_prefix}:source_artifact_path_not_repo_relative"]
        path = REPO_ROOT / relative
    try:
        resolved = path.resolve()
    except OSError:
        return None, [f"{reason_prefix}:source_artifact_unresolvable"]
    if not resolved.is_file():
        return None, [f"{reason_prefix}:source_artifact_path_not_file"]
    return resolved, []


def source_artifact_hash_bindings_missing(
    report: dict[str, Any],
    resolved: dict[str, Path],
    keys: tuple[str, ...],
    reason_prefix: str,
) -> list[str]:
    if not resolved:
        return []
    bindings = report.get("source_artifact_hashes")
    if not isinstance(bindings, dict):
        return [f"{reason_prefix}:source_artifact_hashes_missing"]
    missing: list[str] = []
    for key in keys:
        path = resolved.get(key)
        if path is None:
            continue
        expected_sha256 = bindings.get(key)
        if not isinstance(expected_sha256, str) or not expected_sha256.strip():
            missing.append(f"{reason_prefix}:{key}:source_artifact_sha256_missing")
            continue
        if SHA256_RE.fullmatch(expected_sha256.strip()) is None:
            missing.append(f"{reason_prefix}:{key}:source_artifact_sha256_invalid")
            continue
        actual_sha256 = sha256_file(path)
        if actual_sha256 is None:
            missing.append(f"{reason_prefix}:{key}:source_artifact_sha256_unavailable")
        elif expected_sha256.lower() != actual_sha256:
            missing.append(f"{reason_prefix}:{key}:source_artifact_sha256_mismatch")
    return missing


def report_path_matches_default(path: Path | None, expected: Path) -> bool:
    if path is None:
        return False
    try:
        return path == expected.resolve()
    except OSError:
        return False


def readiness_json_provenance_missing(readiness_path: Path, readiness_root: Path, reason_prefix: str) -> list[str]:
    missing: list[str] = []
    try:
        readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [f"{reason_prefix}:readiness_json_unreadable"]
    if not isinstance(readiness, dict):
        return [f"{reason_prefix}:readiness_json_not_object"]
    source_root = readiness.get("source_root")
    if not isinstance(source_root, str) or not source_root.strip():
        missing.append(f"{reason_prefix}:readiness_source_root_missing")
    else:
        try:
            if Path(source_root).resolve() != readiness_root:
                missing.append(f"{reason_prefix}:readiness_source_root_mismatch")
        except OSError:
            missing.append(f"{reason_prefix}:readiness_source_root_unresolvable")
    producer = readiness.get("producer")
    if not isinstance(producer, dict):
        missing.append(f"{reason_prefix}:readiness_producer_missing")
        return missing
    if producer.get("script") != COMMAND_RESPONSE_READINESS_PRODUCER_SCRIPT:
        missing.append(f"{reason_prefix}:readiness_producer_script_mismatch")
    if producer.get("output_name") != COMMAND_RESPONSE_READINESS_OUTPUT_NAME:
        missing.append(f"{reason_prefix}:readiness_producer_output_name_mismatch")
    argv = producer.get("argv")
    if not isinstance(argv, list) or not all(isinstance(item, str) and item.strip() for item in argv):
        missing.append(f"{reason_prefix}:readiness_producer_argv_missing")
        return missing
    if COMMAND_RESPONSE_READINESS_PRODUCER_SCRIPT not in argv:
        missing.append(f"{reason_prefix}:readiness_producer_argv_script_missing")
    if "--target-set" not in argv:
        missing.append(f"{reason_prefix}:readiness_producer_argv_target_set_missing")
    else:
        target_set_index = argv.index("--target-set") + 1
        if target_set_index >= len(argv) or argv[target_set_index] != COMMAND_RESPONSE_READINESS_TARGET_SET:
            missing.append(f"{reason_prefix}:readiness_producer_argv_target_set_mismatch")
    if "--readiness-report" not in argv:
        missing.append(f"{reason_prefix}:readiness_producer_argv_readiness_report_missing")
    if "--json" not in argv:
        missing.append(f"{reason_prefix}:readiness_producer_argv_json_missing")
    return missing


def command_response_public_readiness_source_artifacts_missing(
    report: dict[str, Any],
    reason_prefix: str,
    manifest_path: Path = DEFAULT_MANIFEST,
    public_header_path: Path = DEFAULT_PUBLIC_HEADER,
) -> list[str]:
    missing: list[str] = []
    resolved: dict[str, Path] = {}
    for key in COMMAND_RESPONSE_PUBLIC_READINESS_SOURCE_ARTIFACT_KEYS:
        path, errors = resolve_report_source_artifact(report.get(key), f"{reason_prefix}:{key}")
        missing.extend(errors)
        if path is not None:
            resolved[key] = path
    missing.extend(
        source_artifact_hash_bindings_missing(
            report,
            resolved,
            COMMAND_RESPONSE_PUBLIC_READINESS_SOURCE_ARTIFACT_KEYS,
            reason_prefix,
        )
    )
    if not report_path_matches_default(
        resolved.get("decisions_path"),
        DEFAULT_COMMAND_RESPONSE_PUBLIC_CONTRACT_DECISIONS,
    ):
        missing.append(f"{reason_prefix}:decisions_path_mismatch")
    if not report_path_matches_default(resolved.get("surfaces_path"), manifest_path):
        missing.append(f"{reason_prefix}:surfaces_path_mismatch")
    if not report_path_matches_default(resolved.get("public_header_path"), public_header_path):
        missing.append(f"{reason_prefix}:public_header_path_mismatch")
    readiness_path = resolved.get("readiness_path")
    if readiness_path is not None:
        readiness_root = readiness_path.parent
        readiness_root_value = report.get("readiness_root")
        if not isinstance(readiness_root_value, str) or not readiness_root_value.strip():
            missing.append(f"{reason_prefix}:readiness_root_missing")
        else:
            try:
                if Path(readiness_root_value).resolve() != readiness_root:
                    missing.append(f"{reason_prefix}:readiness_root_mismatch")
            except OSError:
                missing.append(f"{reason_prefix}:readiness_root_unresolvable")
        missing.extend(readiness_json_provenance_missing(readiness_path, readiness_root, reason_prefix))
    return missing


def commands_replies_public_readiness_source_artifacts_missing(
    report: dict[str, Any],
    reason_prefix: str,
    manifest_path: Path = DEFAULT_MANIFEST,
    public_header_path: Path = DEFAULT_PUBLIC_HEADER,
) -> list[str]:
    missing: list[str] = []
    resolved: dict[str, Path] = {}
    for key in COMMANDS_REPLIES_PUBLIC_READINESS_SOURCE_ARTIFACT_KEYS:
        path, errors = resolve_report_source_artifact(report.get(key), f"{reason_prefix}:{key}")
        missing.extend(errors)
        if path is not None:
            resolved[key] = path
    if not report_path_matches_default(
        resolved.get("decisions_path"),
        DEFAULT_COMMANDS_REPLIES_PUBLIC_CONTRACT_DECISIONS,
    ):
        missing.append(f"{reason_prefix}:decisions_path_mismatch")
    if not report_path_matches_default(resolved.get("surfaces_path"), manifest_path):
        missing.append(f"{reason_prefix}:surfaces_path_mismatch")
    if not report_path_matches_default(resolved.get("public_header_path"), public_header_path):
        missing.append(f"{reason_prefix}:public_header_path_mismatch")
    response_path_report_path, response_path_report_errors = resolve_report_source_artifact(
        report.get("response_path_report_path"),
        f"{reason_prefix}:response_path_report_path",
    )
    missing.extend(response_path_report_errors)
    if response_path_report_path is not None:
        resolved["response_path_report_path"] = response_path_report_path
    missing.extend(
        source_artifact_hash_bindings_missing(
            report,
            resolved,
            (*COMMANDS_REPLIES_PUBLIC_READINESS_SOURCE_ARTIFACT_KEYS, "response_path_report_path"),
            reason_prefix,
        )
    )
    response_path_report_root_value = report.get("response_path_report_root")
    response_path_report_root: Path | None = None
    if not isinstance(response_path_report_root_value, str) or not response_path_report_root_value.strip():
        missing.append(f"{reason_prefix}:response_path_report_root_missing")
    else:
        try:
            response_path_report_root = Path(response_path_report_root_value).resolve()
        except OSError:
            missing.append(f"{reason_prefix}:response_path_report_root_unresolvable")
    if response_path_report_path is not None and response_path_report_root is not None:
        expected_response_path_report = (
            response_path_report_root / COMMANDS_REPLIES_RESPONSE_PATH_REPORT_NAME
        )
        if response_path_report_path != expected_response_path_report:
            missing.append(f"{reason_prefix}:response_path_report_path_mismatch")
    if response_path_report_path is not None:
        try:
            response_path_report = json.loads(response_path_report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            missing.append(f"{reason_prefix}:response_path_report_path:json_unreadable")
        else:
            if not isinstance(response_path_report, dict):
                missing.append(f"{reason_prefix}:response_path_report_path:json_not_object")
            elif response_path_report.get("schema") != "obelisk.command-chat-response-public-readiness-check.v1":
                missing.append(f"{reason_prefix}:response_path_report:schema_mismatch")
            else:
                for item in command_response_public_readiness_source_artifacts_missing(
                    response_path_report,
                    f"{reason_prefix}:response_path_report",
                    manifest_path,
                    public_header_path,
                ):
                    missing.append(item)
    return missing


def current_repo_head() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    head = result.stdout.strip()
    if not re.fullmatch(r"[0-9a-fA-F]{40}", head):
        return None
    return head


def load_repo_relative_json_artifact(raw_path: Any) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None, "missing"
    if Path(raw_path).is_absolute():
        return None, "path_not_repo_relative"
    relative = repo_relative_evidence_path(raw_path)
    if relative is None:
        return None, "path_not_repo_relative"
    path = REPO_ROOT / relative
    if not path.is_file():
        return None, "path_not_file"
    if path.suffix.lower() != ".json":
        return None, "path_not_json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "json_unreadable"
    if not isinstance(payload, dict):
        return None, "json_not_object"
    return payload, None


def normalized_execution_command_text(value: object) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value))
    return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")


def executed_test_artifact_command_text(report: dict[str, Any]) -> str | None:
    command = report.get("command")
    if isinstance(command, str) and command.strip():
        return command
    argv = report.get("argv")
    if (
        isinstance(argv, list)
        and bool(argv)
        and all(isinstance(item, str) and item.strip() for item in argv)
    ):
        return " ".join(argv)
    return None


def executed_test_artifact_has_command(report: dict[str, Any]) -> bool:
    return executed_test_artifact_command_text(report) is not None


def executed_test_artifact_command_matches_surface(report: dict[str, Any], surface_id: str) -> bool:
    command_text = executed_test_artifact_command_text(report)
    if command_text is None:
        return False
    normalized = normalized_execution_command_text(command_text)
    markers = PROMOTED_SURFACE_TEST_EXECUTION_COMMAND_MARKERS.get(surface_id)
    if markers is None:
        surface_marker = surface_id.removeprefix("obelisk.").removesuffix(".v1")
        markers = (surface_marker.replace(".", "_"),)
    return any(normalized_execution_command_text(marker) in normalized for marker in markers)


def executed_test_artifact_hash_problems(report: dict[str, Any]) -> list[str]:
    observed = False
    invalid: list[str] = []
    for key in PROMOTED_SURFACE_TEST_EXECUTION_HASH_KEYS:
        value = report.get(key)
        if not isinstance(value, str) or not value.strip():
            continue
        observed = True
        if SHA256_RE.fullmatch(value.strip()) is None:
            invalid.append(key)
    for key in ("output", "provenance"):
        value = report.get(key)
        if not isinstance(value, dict):
            continue
        for nested_key in ("hash", "sha256", "digest"):
            nested_value = value.get(nested_key)
            if not isinstance(nested_value, str) or not nested_value.strip():
                continue
            observed = True
            if SHA256_RE.fullmatch(nested_value.strip()) is None:
                invalid.append(f"{key}.{nested_key}")
    if not observed:
        return ["executed_test_report:output_or_provenance_hash_missing"]
    if invalid:
        return [
            f"executed_test_report:output_or_provenance_hash_invalid:{key}"
            for key in sorted(invalid)
        ]
    return []


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def repo_relative_text(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def artifact_input_binding_path_text(path: Path) -> str:
    try:
        return repo_relative_text(path.resolve())
    except ValueError:
        return str(path.resolve())


def executed_test_artifact_missing_provenance(report: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if report.get("producer") != PROMOTED_SURFACE_TEST_EXECUTION_PRODUCER:
        missing.append("executed_test_report:producer_invalid")
    if report.get("checker") != PROMOTED_SURFACE_TEST_EXECUTION_CHECKER:
        missing.append("executed_test_report:checker_invalid")
    produced_at = report.get("produced_at_utc")
    if not isinstance(produced_at, str) or UTC_TIMESTAMP_RE.fullmatch(produced_at.strip()) is None:
        missing.append("executed_test_report:produced_at_utc_invalid")
    return missing


def executed_test_artifact_missing_input_bindings(
    report: dict[str, Any],
    manifest_path: Path = DEFAULT_MANIFEST,
    public_header_path: Path = DEFAULT_PUBLIC_HEADER,
) -> list[str]:
    missing: list[str] = []
    inputs = report.get("inputs")
    if not isinstance(inputs, dict):
        return ["executed_test_report:inputs_missing"]
    expected_bindings = {
        "public_sdk_surfaces": manifest_path,
        "public_header": public_header_path,
    }
    for key, expected_path in expected_bindings.items():
        binding = inputs.get(key)
        if not isinstance(binding, dict):
            missing.append(f"executed_test_report:inputs.{key}_missing")
            continue
        expected_path_text = artifact_input_binding_path_text(expected_path)
        if binding.get("path") != expected_path_text:
            missing.append(f"executed_test_report:inputs.{key}_path_invalid")
        actual_sha256 = sha256_file(expected_path)
        binding_sha256 = binding.get("sha256")
        if not isinstance(binding_sha256, str) or SHA256_RE.fullmatch(binding_sha256.strip()) is None:
            missing.append(f"executed_test_report:inputs.{key}_sha256_invalid")
        elif actual_sha256 is None:
            missing.append(f"executed_test_report:inputs.{key}_sha256_unavailable")
        elif binding_sha256.lower() != actual_sha256:
            missing.append(f"executed_test_report:inputs.{key}_sha256_mismatch")
    return missing


def executed_test_report_missing(
    evidence: dict[str, Any],
    surface_id: str,
    manifest_path: Path = DEFAULT_MANIFEST,
    public_header_path: Path = DEFAULT_PUBLIC_HEADER,
) -> list[str]:
    missing: list[str] = []
    executed, error = load_repo_relative_json_artifact(evidence.get("executed_test_report"))
    if error is not None:
        return [f"executed_test_report:{error}"]
    if executed.get("schema") != PROMOTED_SURFACE_TEST_EXECUTION_ARTIFACT_SCHEMA:
        missing.append("executed_test_report:schema_invalid")
    if executed.get("surface_id") != surface_id:
        missing.append("executed_test_report:surface_id_invalid")
    current_head = current_repo_head()
    if current_head is None:
        missing.append("executed_test_report:current_head_unavailable")
    else:
        commit_values = [
            executed.get(key)
            for key in PROMOTED_SURFACE_TEST_EXECUTION_COMMIT_KEYS
            if isinstance(executed.get(key), str) and executed.get(key).strip()
        ]
        if not commit_values:
            missing.append("executed_test_report:commit_missing")
        elif current_head not in commit_values:
            missing.append("executed_test_report:commit_mismatch")
    if not executed_test_artifact_has_command(executed):
        missing.append("executed_test_report:command_missing")
    elif not executed_test_artifact_command_matches_surface(executed, surface_id):
        missing.append("executed_test_report:command_surface_mismatch")
    if type(executed.get("exit_code")) is not int or executed.get("exit_code") != 0:
        missing.append("executed_test_report:exit_code_not_zero")
    missing.extend(executed_test_artifact_hash_problems(executed))
    missing.extend(executed_test_artifact_missing_provenance(executed))
    missing.extend(
        executed_test_artifact_missing_input_bindings(
            executed,
            manifest_path,
            public_header_path,
        )
    )
    return missing


def player_identity_contract_gate_inputs_invalid(contract_report: dict[str, Any]) -> bool:
    gate_inputs = contract_report.get("contract_gate_inputs")
    if not isinstance(gate_inputs, list):
        return True
    expected_ids = PLAYER_IDENTITY_PUBLIC_CONTRACT_REQUIRED_BLOCKERS
    if len(gate_inputs) != len(expected_ids):
        return True
    seen_ids: set[str] = set()
    for entry in gate_inputs:
        if not isinstance(entry, dict):
            return True
        entry_id = entry.get("id")
        if not isinstance(entry_id, str) or entry_id not in expected_ids or entry_id in seen_ids:
            return True
        seen_ids.add(entry_id)
        review_inputs = entry.get("review_inputs")
        remaining_promotion_inputs = entry.get("remaining_promotion_inputs")
        if (
            entry.get("status") != "unresolved"
            or not isinstance(review_inputs, list)
            or not review_inputs
            or not all(isinstance(item, str) and item for item in review_inputs)
            or not isinstance(remaining_promotion_inputs, list)
            or not all(isinstance(item, str) and item for item in remaining_promotion_inputs)
            or not isinstance(entry.get("non_claim"), str)
            or not entry.get("non_claim")
        ):
            return True
        if any(entry.get(key) is not False for key in PLAYER_IDENTITY_PUBLIC_CONTRACT_GATE_INPUT_REQUIRED_FALSE_KEYS):
            return True
        if entry_id == "runtime.lifecycle_evidence":
            if review_inputs != ["runtime.lifecycle_evidence"] or remaining_promotion_inputs != []:
                return True
        elif not remaining_promotion_inputs:
            return True
    return seen_ids != expected_ids


def player_identity_structured_promotion_evidence_missing(
    evidence: dict[str, Any],
    manifest_path: Path = DEFAULT_MANIFEST,
    public_header_path: Path = DEFAULT_PUBLIC_HEADER,
) -> list[str]:
    missing: list[str] = []
    runtime_manifest, runtime_manifest_errors = load_hash_bound_json_artifact_binding(
        evidence.get("approved_runtime_evidence_manifest"),
        "approved_runtime_evidence_manifest",
    )
    missing.extend(runtime_manifest_errors)
    replayed_runtime_report: dict[str, Any] | None = None
    if runtime_manifest is not None:
        missing.extend(
            structured_readiness_report_claim_blockers(
                runtime_manifest,
                "approved_runtime_evidence_manifest",
            )
        )
        missing.extend(
            approved_runtime_evidence_non_approved_artifact_reasons(
                runtime_manifest,
                "approved_runtime_evidence_manifest",
            )
        )
        validation = approved_runtime_principal_lifecycle_evidence.validate_manifest(
            runtime_manifest,
            check_mode="consume",
        )
        replayed_runtime_report = approved_runtime_principal_lifecycle_evidence.build_report(
            runtime_manifest,
            validation,
            check_mode="consume",
        )
        if validation.blockers:
            missing.append("approved_runtime_evidence_manifest:validation_failed")

    runtime_report, runtime_error = load_repo_relative_json_evidence(evidence.get("approved_runtime_evidence_report"))
    if runtime_error is not None:
        missing.append(f"approved_runtime_evidence_report:{runtime_error}")
    else:
        missing.extend(
            structured_readiness_report_claim_blockers(
                runtime_report,
                "approved_runtime_evidence_report",
            )
        )
        missing.extend(
            approved_runtime_evidence_non_approved_artifact_reasons(
                runtime_report,
                "approved_runtime_evidence_report",
            )
        )
        if not (
            runtime_report.get("schema")
            == "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1"
            and runtime_report.get("ready_scope") == RUNTIME_EVIDENCE_READY_SCOPE
            and runtime_report.get("approved_runtime_evidence_present") is True
            and runtime_report.get("runtime_evidence_ready") is True
            and runtime_report.get("promotion_ready") is False
            and runtime_report.get("public_sdk_ready") is False
            and runtime_report.get("runtime_ready") is False
            and runtime_report.get("next_blocker") == "identity_public_contract_gate_missing"
        ):
            missing.append("approved_runtime_evidence_report:fields_invalid")
        elif replayed_runtime_report is not None:
            for key in (
                "schema",
                "ready_scope",
                "approved_runtime_evidence_present",
                "runtime_evidence_ready",
                "promotion_ready",
                "public_sdk_ready",
                "runtime_ready",
                "next_blocker",
            ):
                if runtime_report.get(key) != replayed_runtime_report.get(key):
                    missing.append(f"approved_runtime_evidence_report:replay_mismatch:{key}")

    contract_report, contract_error = load_repo_relative_json_evidence(evidence.get("public_contract_readiness_report"))
    if contract_error is not None:
        missing.append(f"public_contract_readiness_report:{contract_error}")
    else:
        approved_runtime = contract_report.get("approved_runtime_evidence")
        approved_runtime = approved_runtime if isinstance(approved_runtime, dict) else {}
        missing.extend(
            structured_readiness_report_claim_blockers(
                approved_runtime,
                "public_contract_readiness_report:approved_runtime_evidence",
            )
        )
        missing.extend(
            approved_runtime_evidence_non_approved_artifact_reasons(
                approved_runtime,
                "public_contract_readiness_report:approved_runtime_evidence",
            )
        )
        remaining_blockers = set(contract_report.get("remaining_blockers", []))
        private_candidate_contract = contract_report.get("private_candidate_contract")
        private_candidate_contract = private_candidate_contract if isinstance(private_candidate_contract, dict) else {}
        private_pod_layout_candidate = contract_report.get("private_pod_layout_candidate")
        private_pod_layout_candidate = private_pod_layout_candidate if isinstance(private_pod_layout_candidate, dict) else {}
        contract_gate_inputs_invalid = player_identity_contract_gate_inputs_invalid(contract_report)
        if not (
            contract_report.get("schema") == "obelisk.player-identity-public-contract-readiness-check.v1"
            and contract_report.get("ready") is True
            and contract_report.get("ready_scope") == PUBLIC_CONTRACT_REVIEW_READY_SCOPE
            and contract_report.get("surface") == "obelisk.player_identity.v1"
            and contract_report.get("accepted_for_contract_review") is True
            and contract_report.get("promotion_ready") is False
            and contract_report.get("public_sdk_ready") is False
            and contract_report.get("runtime_ready") is False
            and contract_report.get("public_contract_allowed") is False
            and contract_report.get("public_header_allowed") is False
            and contract_report.get("public_header_symbols_now") == []
            and contract_report.get("public_capability_bits_now") == []
            and contract_report.get("public_callback_abi_now") == []
            and contract_report.get("next_blocker") == "identity_public_contract_gate_missing"
            and set(contract_report.get("remaining_blockers", []))
            == PLAYER_IDENTITY_PUBLIC_CONTRACT_REQUIRED_BLOCKERS
            and contract_report.get("blockers") == []
            and contract_report.get("resolved_inputs") == ["runtime.lifecycle_evidence"]
            and not contract_gate_inputs_invalid
            and approved_runtime.get("approved_runtime_evidence_present") is True
            and approved_runtime.get("runtime_evidence_ready") is True
        ):
            missing.append("public_contract_readiness_report:fields_invalid")
        if contract_gate_inputs_invalid:
            missing.append("public_contract_readiness_report:contract_gate_inputs_invalid")
        if command_permission_route_gate_public_or_runtime_claims(contract_report):
            missing.append("public_contract_readiness_report:public_or_runtime_claim_without_blocker")
        if secondary_report_completion_claims_without_blocker(contract_report):
            missing.append("public_contract_readiness_report:completion_claim_without_blocker")
        if remaining_blockers & {
            "lifetime.generation_scope_invalidation",
            "abi.public_pod_contract",
            "lifecycle.owner_cleanup",
        }:
            missing.append("public_contract_readiness_report:promotion_blockers_remaining")
        if private_candidate_contract.get("candidate_only") is True:
            missing.append("public_contract_readiness_report:private_candidate_contract_candidate_only")
        for key in ("promotion_ready", "public_sdk_ready", "public_header_allowed"):
            if private_candidate_contract.get(key) is False:
                missing.append(f"public_contract_readiness_report:private_candidate_contract_{key}_false")
        if private_pod_layout_candidate.get("candidate_only") is True:
            missing.append("public_contract_readiness_report:private_pod_layout_candidate_candidate_only")
        for key in ("promotion_ready", "public_sdk_ready", "public_header_allowed", "public_abi_ready"):
            if private_pod_layout_candidate.get(key) is False:
                missing.append(f"public_contract_readiness_report:private_pod_layout_candidate_{key}_false")

    missing.extend(
        executed_test_report_missing(
            evidence,
            "obelisk.player_identity.v1",
            manifest_path,
            public_header_path,
        )
    )
    return missing


def load_hash_bound_json_artifact_binding(
    binding: Any,
    reason_prefix: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    if not isinstance(binding, dict):
        return None, [f"{reason_prefix}:missing"]
    if any(key in binding for key in PROMOTION_CERTIFICATE_BINDING_INLINE_SHAPE_KEYS):
        return None, [f"{reason_prefix}:inline_certificate_binding_not_allowed"]
    if set(binding) != {"path", "sha256"}:
        return None, [f"{reason_prefix}:binding_keys_mismatch"]
    raw_path = binding.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None, [f"{reason_prefix}:path_missing"]
    raw_binding_path = Path(raw_path)
    if raw_binding_path.is_absolute():
        return None, [f"{reason_prefix}:path_must_be_canonical_repo_relative"]
    if ".." in raw_binding_path.parts:
        return None, [f"{reason_prefix}:path_must_not_traverse"]
    relative = repo_relative_evidence_path(raw_path)
    if relative is None:
        return None, [f"{reason_prefix}:path_not_repo_relative"]
    if raw_path != relative.as_posix():
        return None, [f"{reason_prefix}:path_must_be_canonical_repo_relative"]
    path = REPO_ROOT / relative
    if not path.is_file():
        return None, [f"{reason_prefix}:path_not_file"]
    if path.suffix.lower() != ".json":
        return None, [f"{reason_prefix}:path_not_json"]
    expected_sha256 = binding.get("sha256")
    if not isinstance(expected_sha256, str) or not expected_sha256.strip():
        return None, [f"{reason_prefix}:sha256_missing"]
    if SHA256_RE.fullmatch(expected_sha256.strip()) is None:
        return None, [f"{reason_prefix}:sha256_invalid"]
    actual_sha256 = sha256_file(path)
    if actual_sha256 is None:
        return None, [f"{reason_prefix}:sha256_unavailable"]
    if actual_sha256 != expected_sha256.lower():
        return None, [f"{reason_prefix}:sha256_mismatch"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, [f"{reason_prefix}:json_unreadable"]
    if not isinstance(payload, dict):
        return None, [f"{reason_prefix}:json_not_object"]
    return payload, []


def hash_bound_artifact_bindings_match(left: Any, right: Any) -> bool:
    if not isinstance(left, dict) or not isinstance(right, dict):
        return False
    if set(left) != {"path", "sha256"} or set(right) != {"path", "sha256"}:
        return False
    return (
        left.get("path") == right.get("path")
        and isinstance(left.get("sha256"), str)
        and isinstance(right.get("sha256"), str)
        and left["sha256"].lower() == right["sha256"].lower()
    )


def active_promoted_surface_certificate_binding(
    manifest_path: Path,
    surface_id: str,
    certificate_key: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, [f"{certificate_key}:manifest_unreadable"]
    if not isinstance(manifest, dict):
        return None, [f"{certificate_key}:manifest_not_object"]
    surfaces = manifest.get("surfaces")
    if not isinstance(surfaces, list):
        return None, [f"{certificate_key}:manifest_surfaces_missing"]
    surface = next(
        (
            item
            for item in surfaces
            if isinstance(item, dict) and item.get("id") == surface_id
        ),
        None,
    )
    if not isinstance(surface, dict) or surface.get("status") != "promoted":
        return None, [f"{certificate_key}:current_surface_record_missing_or_unpromoted"]
    evidence = surface.get("evidence")
    binding = evidence.get(certificate_key) if isinstance(evidence, dict) else None
    if not isinstance(binding, dict):
        return None, [f"{certificate_key}:current_hash_bound_certificate_missing"]
    if set(binding) != {"path", "sha256"}:
        return None, [f"{certificate_key}:current_hash_bound_certificate_binding_keys_mismatch"]
    return binding, []


SURFACE_PROMOTION_CERTIFICATE_EVIDENCE_KEYS = {
    "obelisk.player_identity.v1": "player_identity_promotion_certificate",
    "obelisk.permissions_admin.v1": "permissions_admin_promotion_certificate",
    "obelisk.command_chat_response_path.v1": "command_response_promotion_certificate",
    "obelisk.commands_replies.v1": "commands_replies_promotion_certificate",
}


def promotion_certificate_evidence_key_for_surface(surface_id: str) -> str:
    return SURFACE_PROMOTION_CERTIFICATE_EVIDENCE_KEYS.get(
        surface_id,
        "player_identity_promotion_certificate",
    )


def surface_record_sha256_for_certificate(
    surface: dict[str, Any],
    certificate_key: str = "player_identity_promotion_certificate",
) -> str:
    sanitized = dict(surface)
    evidence = sanitized.get("evidence")
    if isinstance(evidence, dict):
        sanitized["evidence"] = {
            key: value
            for key, value in evidence.items()
            if key != certificate_key
        }
    data = json.dumps(sanitized, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def active_player_identity_surface_record_sha256(manifest_path: Path) -> str | None:
    return active_promoted_surface_record_sha256(manifest_path, "obelisk.player_identity.v1")


def active_promoted_surface_record_sha256(
    manifest_path: Path,
    surface_id: str,
    certificate_key: str | None = None,
) -> str | None:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    surfaces = manifest.get("surfaces") if isinstance(manifest, dict) else None
    if not isinstance(surfaces, list):
        return None
    for surface in surfaces:
        if (
            isinstance(surface, dict)
            and surface.get("id") == surface_id
            and surface.get("status") == "promoted"
        ):
            return surface_record_sha256_for_certificate(
                surface,
                certificate_key or promotion_certificate_evidence_key_for_surface(surface_id),
            )
    return None


def player_identity_promotion_certificate_missing(
    evidence: dict[str, Any],
    manifest_path: Path = DEFAULT_MANIFEST,
    public_header_path: Path = DEFAULT_PUBLIC_HEADER,
) -> list[str]:
    missing: list[str] = []
    certificate, certificate_errors = load_hash_bound_json_artifact_binding(
        evidence.get("player_identity_promotion_certificate"),
        "player_identity_promotion_certificate",
    )
    if certificate_errors:
        return certificate_errors

    assert certificate is not None
    if not (
        certificate.get("schema") == PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA
        and certificate.get("surface_id") == "obelisk.player_identity.v1"
        and certificate.get("promotion_status") == "promoted"
        and certificate.get("v1_dependency_chain") == list(CANONICAL_V1_DEPENDENCY_SEQUENCE)
        and certificate.get("v1_dependency_chain_position") == 1
        and certificate.get("required_by_surface") == "obelisk.permissions_admin.v1"
        and certificate.get("required_by_v1_dependency_chain_position") == 2
    ):
        missing.append("player_identity_promotion_certificate:fields_invalid")

    if (
        certificate.get("required_reviewed_artifact_hash")
        != REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH
    ):
        missing.append("player_identity_promotion_certificate:required_reviewed_artifact_hash_invalid")
    if (
        certificate.get("reviewed_artifact_hash_policy")
        != REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH_POLICY
    ):
        missing.append("player_identity_promotion_certificate:reviewed_artifact_hash_policy_invalid")
    if certificate.get("missing_mismatched_or_stale_certificate_counts") is not False:
        missing.append(
            "player_identity_promotion_certificate:missing_mismatched_or_stale_certificate_counts_not_false"
        )

    identity_evidence = certificate.get("evidence")
    if not isinstance(identity_evidence, dict):
        missing.append("player_identity_promotion_certificate:evidence_missing")
    else:
        active_surface_hash = active_player_identity_surface_record_sha256(manifest_path)
        if active_surface_hash is None:
            missing.append("player_identity_promotion_certificate:surface_record_missing_or_unpromoted")
        else:
            certificate_surface_hash = identity_evidence.get("reviewed_surface_record_sha256")
            if (
                not isinstance(certificate_surface_hash, str)
                or certificate_surface_hash.lower() != active_surface_hash
            ):
                missing.append("player_identity_promotion_certificate:surface_record_sha256_mismatch")
        dependency_missing = player_identity_structured_promotion_evidence_missing(
            identity_evidence,
            manifest_path,
            public_header_path,
        )
        for reason in dependency_missing:
            missing.append(f"player_identity_{reason}")
    return missing


def evidence_is_generated_promotion_certificate_or_builder_report(
    evidence: dict[str, Any],
) -> bool:
    schema = evidence.get("schema")
    if schema in {
        PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
        PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA,
        COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA,
        COMMANDS_REPLIES_PROMOTION_CERTIFICATE_SCHEMA,
        *PROMOTION_CERTIFICATE_BUILD_REPORT_SCHEMAS,
    }:
        return True
    if isinstance(schema, str):
        normalized_schema = schema.lower().replace("-", "_")
        if (
            "promotion_certificate" in normalized_schema
            or "promotion_cert" in normalized_schema
            or "generated_cert" in normalized_schema
            or "generated_certificate" in normalized_schema
        ):
            return True
    if (
        evidence.get("promotion_status") == "promoted"
        and isinstance(evidence.get("v1_dependency_chain"), list)
        and isinstance(evidence.get("v1_dependency_chain_position"), int)
        and isinstance(evidence.get("required_by_surface"), str)
        and isinstance(evidence.get("required_by_v1_dependency_chain_position"), int)
    ):
        return True
    if (
        evidence.get("identity_surface_certificate_binding_valid") is True
        and "player_identity_promotion_certificate" in evidence
        and any(
            key in evidence
            for key in (
                "sdk_progress",
                "counts_toward_v1_completion",
                "output_certificate",
            )
        )
    ):
        return True
    if (
        any(evidence.get(key) is True for key in PROMOTION_CERTIFICATE_BINDING_VALID_KEYS)
        and any(key in evidence for key in SURFACE_PROMOTION_CERTIFICATE_EVIDENCE_KEYS.values())
        and any(key in evidence for key in PROMOTION_CERTIFICATE_REPORT_CONTAINER_KEYS)
    ):
        return True
    if any(key in evidence for key in PROMOTION_CERTIFICATE_REPORT_CONTAINER_KEYS):
        artifact_schema = evidence.get("certificate_artifact_schema")
        if artifact_schema in {
            PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
            PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA,
            COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA,
            COMMANDS_REPLIES_PROMOTION_CERTIFICATE_SCHEMA,
        }:
            return True
        if (
            evidence.get("certificate_written") is True
            and isinstance(evidence.get("certificate_binding"), dict)
            and isinstance(evidence.get("certificate_sha256"), str)
        ):
            return True
    return False


def promoted_dependency_certificate_missing(
    evidence: dict[str, Any],
    *,
    certificate_key: str,
    schema: str,
    surface_id: str,
    v1_dependency_chain_position: int,
    required_by_surface: str,
    required_by_v1_dependency_chain_position: int,
    dependency_reason_prefix: str,
    dependency_validator: Any,
    manifest_path: Path = DEFAULT_MANIFEST,
    public_header_path: Path = DEFAULT_PUBLIC_HEADER,
) -> list[str]:
    missing: list[str] = []
    certificate, certificate_errors = load_hash_bound_json_artifact_binding(
        evidence.get(certificate_key),
        certificate_key,
    )
    if certificate_errors:
        return certificate_errors

    assert certificate is not None
    if not (
        certificate.get("schema") == schema
        and certificate.get("surface_id") == surface_id
        and certificate.get("promotion_status") == "promoted"
        and certificate.get("v1_dependency_chain") == list(CANONICAL_V1_DEPENDENCY_SEQUENCE)
        and certificate.get("v1_dependency_chain_position") == v1_dependency_chain_position
        and certificate.get("required_by_surface") == required_by_surface
        and certificate.get("required_by_v1_dependency_chain_position")
        == required_by_v1_dependency_chain_position
    ):
        missing.append(f"{certificate_key}:fields_invalid")

    dependency_evidence = certificate.get("evidence")
    if not isinstance(dependency_evidence, dict):
        missing.append(f"{certificate_key}:evidence_missing")
        return missing

    if (
        certificate.get("required_reviewed_artifact_hash")
        != REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH
    ):
        missing.append(f"{certificate_key}:required_reviewed_artifact_hash_invalid")
    if (
        certificate.get("reviewed_artifact_hash_policy")
        != REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH_POLICY
    ):
        missing.append(f"{certificate_key}:reviewed_artifact_hash_policy_invalid")
    if certificate.get("missing_mismatched_or_stale_certificate_counts") is not False:
        missing.append(
            f"{certificate_key}:missing_mismatched_or_stale_certificate_counts_not_false"
        )

    active_surface_hash = active_promoted_surface_record_sha256(
        manifest_path,
        surface_id,
        certificate_key,
    )
    if active_surface_hash is None:
        missing.append(f"{certificate_key}:surface_record_missing_or_unpromoted")
    else:
        certificate_surface_hash = dependency_evidence.get("reviewed_surface_record_sha256")
        if (
            not isinstance(certificate_surface_hash, str)
            or certificate_surface_hash.lower() != active_surface_hash
        ):
            missing.append(f"{certificate_key}:surface_record_sha256_mismatch")

    dependency_missing = dependency_validator(
        dependency_evidence,
        manifest_path,
        public_header_path,
    )
    for reason in dependency_missing:
        missing.append(f"{dependency_reason_prefix}_{reason}")
    return missing


def permissions_admin_promotion_certificate_missing(
    evidence: dict[str, Any],
    manifest_path: Path = DEFAULT_MANIFEST,
    public_header_path: Path = DEFAULT_PUBLIC_HEADER,
) -> list[str]:
    return promoted_dependency_certificate_missing(
        evidence,
        certificate_key="permissions_admin_promotion_certificate",
        schema=PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA,
        surface_id="obelisk.permissions_admin.v1",
        v1_dependency_chain_position=2,
        required_by_surface="obelisk.command_chat_response_path.v1",
        required_by_v1_dependency_chain_position=3,
        dependency_reason_prefix="permissions_admin",
        dependency_validator=permissions_admin_structured_promotion_evidence_missing,
        manifest_path=manifest_path,
        public_header_path=public_header_path,
    )


def command_response_promotion_certificate_missing(
    evidence: dict[str, Any],
    manifest_path: Path = DEFAULT_MANIFEST,
    public_header_path: Path = DEFAULT_PUBLIC_HEADER,
) -> list[str]:
    return promoted_dependency_certificate_missing(
        evidence,
        certificate_key="command_response_promotion_certificate",
        schema=COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA,
        surface_id="obelisk.command_chat_response_path.v1",
        v1_dependency_chain_position=3,
        required_by_surface="obelisk.commands_replies.v1",
        required_by_v1_dependency_chain_position=4,
        dependency_reason_prefix="command_response",
        dependency_validator=command_response_structured_promotion_evidence_missing,
        manifest_path=manifest_path,
        public_header_path=public_header_path,
    )


def commands_replies_promotion_certificate_missing(
    evidence: dict[str, Any],
    manifest_path: Path = DEFAULT_MANIFEST,
    public_header_path: Path = DEFAULT_PUBLIC_HEADER,
) -> list[str]:
    del public_header_path
    certificate_key = "commands_replies_promotion_certificate"
    surface_id = "obelisk.commands_replies.v1"
    missing: list[str] = []
    certificate, certificate_errors = load_hash_bound_json_artifact_binding(
        evidence.get(certificate_key),
        certificate_key,
    )
    if certificate_errors:
        return certificate_errors

    assert certificate is not None
    if not (
        certificate.get("schema") == COMMANDS_REPLIES_PROMOTION_CERTIFICATE_SCHEMA
        and certificate.get("surface_id") == surface_id
        and certificate.get("promotion_status") == "promoted"
        and certificate.get("v1_dependency_chain") == list(CANONICAL_V1_DEPENDENCY_SEQUENCE)
        and certificate.get("v1_dependency_chain_position") == 4
    ):
        missing.append(f"{certificate_key}:fields_invalid")
    if (
        certificate.get("certificate_status") == "built"
        or certificate.get("planning_only") is True
        or certificate.get("non_authorizing") is True
        or str(certificate.get("promotion_status", "")).startswith("blocked_")
    ):
        missing.append(f"{certificate_key}:non_authorizing_or_blocked_certificate")
    if (
        certificate.get("required_by_surface") not in (None, "")
        or certificate.get("required_by_v1_dependency_chain_position") not in (None, 0)
    ):
        missing.append(f"{certificate_key}:terminal_scope_invalid")

    if (
        certificate.get("required_reviewed_artifact_hash")
        != REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH
    ):
        missing.append(f"{certificate_key}:required_reviewed_artifact_hash_invalid")
    if (
        certificate.get("reviewed_artifact_hash_policy")
        != REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH_POLICY
    ):
        missing.append(f"{certificate_key}:reviewed_artifact_hash_policy_invalid")
    if certificate.get("missing_mismatched_or_stale_certificate_counts") is not False:
        missing.append(f"{certificate_key}:missing_mismatched_or_stale_certificate_counts_not_false")

    certificate_evidence = certificate.get("evidence")
    if not isinstance(certificate_evidence, dict):
        missing.append(f"{certificate_key}:evidence_missing")
        return missing

    active_surface_hash = active_promoted_surface_record_sha256(
        manifest_path,
        surface_id,
        certificate_key,
    )
    if active_surface_hash is None:
        missing.append(f"{certificate_key}:surface_record_missing_or_unpromoted")
    else:
        for evidence_hash_key in ("reviewed_surface_record_sha256", "reviewed_artifact_hash"):
            observed = certificate_evidence.get(evidence_hash_key)
            if not isinstance(observed, str) or observed.lower() != active_surface_hash:
                missing.append(f"{certificate_key}:{evidence_hash_key}_mismatch")

    current_command_response_binding, current_command_response_errors = (
        active_promoted_surface_certificate_binding(
            manifest_path,
            "obelisk.command_chat_response_path.v1",
            "command_response_promotion_certificate",
        )
    )
    if current_command_response_errors:
        missing.extend(
            f"{certificate_key}:current_{reason}"
            for reason in current_command_response_errors
        )
    else:
        input_bindings = certificate.get("input_bindings")
        declared_command_response_binding = (
            input_bindings.get("command_response_promotion_certificate")
            if isinstance(input_bindings, dict)
            else None
        )
        if declared_command_response_binding is None:
            declared_command_response_binding = certificate_evidence.get(
                "command_response_promotion_certificate"
            )
        if not hash_bound_artifact_bindings_match(
            declared_command_response_binding,
            current_command_response_binding,
        ):
            missing.append(
                f"{certificate_key}:current_command_response_promotion_certificate_binding_missing_or_mismatch"
            )
        else:
            for reason in command_response_promotion_certificate_missing(
                {"command_response_promotion_certificate": current_command_response_binding},
                manifest_path,
            ):
                missing.append(f"{certificate_key}:current_{reason}")
    return missing


def permissions_admin_structured_promotion_evidence_missing(
    evidence: dict[str, Any],
    manifest_path: Path = DEFAULT_MANIFEST,
    public_header_path: Path = DEFAULT_PUBLIC_HEADER,
) -> list[str]:
    missing: list[str] = []
    dependency_missing = player_identity_promotion_certificate_missing(
        evidence,
        manifest_path,
        public_header_path,
    )
    missing.extend(dependency_missing)

    query_report, query_error = load_repo_relative_json_evidence(evidence.get("query_failclosed_report"))
    if query_error is not None:
        missing.append(f"query_failclosed_report:{query_error}")
    elif not (
        query_report.get("schema") == "obelisk.permissions-admin-query-failclosed-contract-check.v1"
        and query_report.get("input_schema") == "obelisk.permissions-admin-query-failclosed-contract.v1"
        and query_report.get("mode") == "consume"
        and query_report.get("ready") is True
        and query_report.get("valid") is True
        and query_report.get("candidate_only") is True
        and query_report.get("pre_abi") is True
        and query_report.get("public_header_allowed") is False
        and query_report.get("public_cache_abi_allowed") is False
        and query_report.get("promotion_ready") is False
        and query_report.get("public_sdk_ready") is False
        and query_report.get("runtime_ready") is False
        and query_report.get("blockers") == []
    ):
        missing.append("query_failclosed_report:fields_invalid")
    else:
        if command_permission_route_gate_public_or_runtime_claims(query_report):
            missing.append("query_failclosed_report:public_or_runtime_claim_without_blocker")
        if secondary_report_completion_claims_without_blocker(query_report):
            missing.append("query_failclosed_report:completion_claim_without_blocker")
        if not dependency_missing and report_is_limited_to_non_promotional_readiness(query_report):
            missing.append("query_failclosed_report:not_promoted_evidence")

    readiness_report, readiness_error = load_repo_relative_json_evidence(evidence.get("public_readiness_report"))
    if readiness_error is not None:
        missing.append(f"public_readiness_report:{readiness_error}")
    elif not (
        readiness_report.get("schema") == "obelisk.permissions-admin-public-readiness-check.v1"
        and readiness_report.get("surface") == "obelisk.permissions_admin.v1"
        and readiness_report.get("valid") is True
        and readiness_report.get("accepted_for_planning") is True
        and readiness_report.get("planning_only") is True
        and readiness_report.get("promotion_ready") is False
        and readiness_report.get("public_header_allowed") is False
        and readiness_report.get("public_abi_ready") is False
        and readiness_report.get("public_sdk_ready") is False
        and readiness_report.get("runtime_ready") is False
        and readiness_report.get("dependency") == "obelisk.player_identity.v1"
        and readiness_report.get("query_failclosed_artifact_schema")
        == "obelisk.permissions-admin-query-failclosed-contract.v1"
        and readiness_report.get("blockers") == []
    ):
        missing.append("public_readiness_report:fields_invalid")
    else:
        if command_permission_route_gate_public_or_runtime_claims(readiness_report):
            missing.append("public_readiness_report:public_or_runtime_claim_without_blocker")
        if secondary_report_completion_claims_without_blocker(readiness_report):
            missing.append("public_readiness_report:completion_claim_without_blocker")
        if not dependency_missing and report_is_limited_to_non_promotional_readiness(readiness_report):
            missing.append("public_readiness_report:not_promoted_evidence")

    missing.extend(
        executed_test_report_missing(
            evidence,
            "obelisk.permissions_admin.v1",
            manifest_path,
            public_header_path,
        )
    )
    return missing


def command_response_structured_promotion_evidence_missing(
    evidence: dict[str, Any],
    manifest_path: Path = DEFAULT_MANIFEST,
    public_header_path: Path = DEFAULT_PUBLIC_HEADER,
) -> list[str]:
    missing: list[str] = []
    dependency_missing = permissions_admin_promotion_certificate_missing(
        evidence,
        manifest_path,
        public_header_path,
    )
    missing.extend(dependency_missing)
    if not isinstance(evidence.get("permissions_admin_promotion_certificate"), dict):
        permissions_admin_evidence = evidence.get("permissions_admin_promotion_evidence")
        if not isinstance(permissions_admin_evidence, dict):
            permissions_admin_evidence = {
                "player_identity_promotion_certificate": evidence.get("player_identity_promotion_certificate"),
                "query_failclosed_report": evidence.get("permissions_admin_query_failclosed_report"),
                "public_readiness_report": evidence.get("permissions_admin_public_readiness_report"),
                "executed_test_report": evidence.get("permissions_admin_executed_test_report"),
            }
        legacy_dependency_missing = permissions_admin_structured_promotion_evidence_missing(
            permissions_admin_evidence,
            manifest_path,
            public_header_path,
        )
        for reason in legacy_dependency_missing:
            missing.append(f"permissions_admin_{reason}")
        dependency_missing = [*dependency_missing, *legacy_dependency_missing]

    readiness_report, readiness_error = load_repo_relative_json_evidence(evidence.get("public_readiness_report"))
    if readiness_error is not None:
        missing.append(f"public_readiness_report:{readiness_error}")
    elif not (
        readiness_report.get("schema") == "obelisk.command-chat-response-public-readiness-check.v1"
        and readiness_report.get("surface") == "obelisk.command_chat_response_path.v1"
        and readiness_report.get("valid") is True
        and readiness_report.get("accepted_for_planning") is True
        and readiness_report.get("planning_only") is True
        and readiness_report.get("public_readiness_ready") is False
        and readiness_report.get("promotion_ready") is False
        and readiness_report.get("public_header_allowed") is False
        and readiness_report.get("public_abi_ready") is False
        and readiness_report.get("public_sdk_ready") is False
        and readiness_report.get("runtime_ready") is False
        and readiness_report.get("target_set") == "command-chat-response-route-planning"
        and readiness_report.get("readiness_status") == "compared"
        and readiness_report.get("decisions_status") == "blocked"
        and readiness_report.get("surfaces_status") in {"planning", "post-v1"}
        and readiness_report.get("blockers") == []
    ):
        missing.append("public_readiness_report:fields_invalid")
    else:
        missing.extend(structured_readiness_report_claim_blockers(readiness_report, "public_readiness_report"))
        if not dependency_missing and report_is_limited_to_non_promotional_readiness(readiness_report):
            missing.append("public_readiness_report:not_promoted_evidence")
        else:
            missing.extend(
                command_response_public_readiness_source_artifacts_missing(
                    readiness_report,
                    "public_readiness_report",
                    manifest_path,
                    public_header_path,
                )
            )

    missing.extend(
        executed_test_report_missing(
            evidence,
            "obelisk.command_chat_response_path.v1",
            manifest_path,
            public_header_path,
        )
    )
    return missing


def commands_replies_structured_promotion_evidence_missing(
    evidence: dict[str, Any],
    manifest_path: Path = DEFAULT_MANIFEST,
    public_header_path: Path = DEFAULT_PUBLIC_HEADER,
) -> list[str]:
    missing: list[str] = []
    dependency_missing = command_response_promotion_certificate_missing(
        evidence,
        manifest_path,
        public_header_path,
    )
    missing.extend(dependency_missing)
    if not isinstance(evidence.get("command_response_promotion_certificate"), dict):
        command_response_evidence = evidence.get("command_response_promotion_evidence")
        if not isinstance(command_response_evidence, dict):
            command_response_evidence = {
                "public_readiness_report": evidence.get("command_response_public_readiness_report"),
                "executed_test_report": evidence.get("command_response_executed_test_report"),
            }
        legacy_dependency_missing = command_response_structured_promotion_evidence_missing(
            command_response_evidence,
            manifest_path,
            public_header_path,
        )
        for reason in legacy_dependency_missing:
            missing.append(f"command_response_{reason}")
        dependency_missing = [*dependency_missing, *legacy_dependency_missing]
    terminal_certificate_missing = commands_replies_promotion_certificate_missing(
        evidence,
        manifest_path,
        public_header_path,
    )
    missing.extend(terminal_certificate_missing)

    readiness_report, readiness_error = load_repo_relative_json_evidence(evidence.get("public_readiness_report"))
    if readiness_error is not None:
        missing.append(f"public_readiness_report:{readiness_error}")
    elif not (
        readiness_report.get("schema") == "obelisk.commands-replies-public-readiness-check.v1"
        and readiness_report.get("surface") == "obelisk.commands_replies.v1"
        and readiness_report.get("valid") is True
        and readiness_report.get("accepted_for_planning") is True
        and readiness_report.get("planning_only") is True
        and readiness_report.get("public_readiness_ready") is False
        and readiness_report.get("public_header_allowed") is False
        and readiness_report.get("public_abi_ready") is False
        and readiness_report.get("runtime_ready") is False
        and readiness_report.get("public_command_router_allowed") is False
        and readiness_report.get("public_reply_or_send_chat_abi_allowed") is False
        and readiness_report.get("public_response_path_allowed") is False
        and readiness_report.get("decisions_status") == "blocked"
        and readiness_report.get("commands_replies_surface_status") in {"planning", "post-v1"}
        and readiness_report.get("dependency_chain")
        == [
            "obelisk.player_identity.v1",
            "obelisk.permissions_admin.v1",
            "obelisk.command_chat_response_path.v1",
        ]
        and readiness_report.get("blockers") == []
    ):
        missing.append("public_readiness_report:fields_invalid")
    else:
        missing.extend(structured_readiness_report_claim_blockers(readiness_report, "public_readiness_report"))
        if not dependency_missing and report_is_limited_to_non_promotional_readiness(readiness_report):
            missing.append("public_readiness_report:not_promoted_evidence")
        else:
            missing.extend(
                commands_replies_public_readiness_source_artifacts_missing(
                    readiness_report,
                    "public_readiness_report",
                    manifest_path,
                    public_header_path,
                )
            )

    missing.extend(
        executed_test_report_missing(
            evidence,
            "obelisk.commands_replies.v1",
            manifest_path,
            public_header_path,
        )
    )
    return missing


def surface_missing_structured_promotion_evidence(
    surface: dict[str, Any],
    manifest_path: Path = DEFAULT_MANIFEST,
    public_header_path: Path = DEFAULT_PUBLIC_HEADER,
) -> list[str]:
    surface_id = surface.get("id")
    if surface.get("status") != "promoted":
        return []
    evidence = surface.get("evidence")
    if not isinstance(evidence, dict):
        return ["evidence:missing"]
    if evidence_is_generated_promotion_certificate_or_builder_report(evidence):
        return ["generated_promotion_certificate_or_builder_report_not_attached"]
    if surface_id == "obelisk.player_identity.v1":
        return player_identity_structured_promotion_evidence_missing(evidence, manifest_path, public_header_path)
    if surface_id == "obelisk.permissions_admin.v1":
        return permissions_admin_structured_promotion_evidence_missing(evidence, manifest_path, public_header_path)
    if surface_id == "obelisk.command_chat_response_path.v1":
        return command_response_structured_promotion_evidence_missing(evidence, manifest_path, public_header_path)
    if surface_id == "obelisk.commands_replies.v1":
        return commands_replies_structured_promotion_evidence_missing(evidence, manifest_path, public_header_path)
    return []



def unresolved_promoted_surface_dependencies(
    surface: dict[str, Any],
    surfaces_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    if surface.get("status") != "promoted" and surface.get("public_abi") is not True:
        return []
    unresolved: list[str] = []
    dependency_ids = as_string_list(surface.get("depends_on"))
    surface_id = surface.get("id")
    if isinstance(surface_id, str):
        for required_dependency_id in REQUIRED_PROMOTED_SURFACE_DEPENDENCIES.get(surface_id, ()):
            if required_dependency_id not in dependency_ids:
                dependency_ids.append(required_dependency_id)
    for dependency_id in dependency_ids:
        dependency = surfaces_by_id.get(dependency_id)
        if not isinstance(dependency, dict) or dependency.get("status") != "promoted":
            unresolved.append(dependency_id)
    return unresolved


def missing_required_dependency_declarations(
    surfaces_by_id: dict[str, dict[str, Any]],
) -> dict[str, list[str]]:
    missing: dict[str, list[str]] = {}
    for surface_id, required_dependency_ids in REQUIRED_PROMOTED_SURFACE_DEPENDENCIES.items():
        surface = surfaces_by_id.get(surface_id)
        if not isinstance(surface, dict):
            continue
        declared_dependency_ids = set(as_string_list(surface.get("depends_on")))
        missing_dependencies = [
            dependency_id
            for dependency_id in required_dependency_ids
            if dependency_id not in declared_dependency_ids
        ]
        if missing_dependencies:
            missing[surface_id] = missing_dependencies
    return missing


def player_identity_request_pack_non_evidence_terms_missing(
    surfaces_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    surface = surfaces_by_id.get("obelisk.player_identity.v1")
    if not isinstance(surface, dict):
        return list(PLAYER_IDENTITY_REQUEST_PACK_NON_EVIDENCE_TERMS)
    text = json.dumps(surface, sort_keys=True).lower()
    return [
        term
        for term in PLAYER_IDENTITY_REQUEST_PACK_NON_EVIDENCE_TERMS
        if term.lower() not in text
    ]


def v1_dependency_sequence_mismatches(
    manifest: dict[str, Any],
    surfaces_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    mismatches: list[str] = []
    declared_sequence = as_string_list(manifest.get("v1_dependency_sequence"))
    chain_surfaces_present = all(surface_id in surfaces_by_id for surface_id in CANONICAL_V1_DEPENDENCY_SEQUENCE)

    if declared_sequence or chain_surfaces_present:
        if declared_sequence != list(CANONICAL_V1_DEPENDENCY_SEQUENCE):
            mismatches.append("v1_dependency_sequence")

    completion_blockers = as_string_list(manifest.get("v1_sdk_completion_blockers"))
    completion_blocker_positions = {
        surface_id: index for index, surface_id in enumerate(completion_blockers)
    }
    if all(surface_id in completion_blocker_positions for surface_id in CANONICAL_V1_DEPENDENCY_SEQUENCE):
        ordered_positions = [
            completion_blocker_positions[surface_id]
            for surface_id in CANONICAL_V1_DEPENDENCY_SEQUENCE
        ]
        if ordered_positions != sorted(ordered_positions):
            mismatches.append("v1_sdk_completion_blockers")

    return mismatches


def blocker_outcome_next_action(
    *,
    surface_id: str,
    status: str,
    manifest_outcome: str | None,
    release_statement_outcome: str | None,
    release_statement_contract_satisfied: bool,
    promotion_evidence_satisfied: bool,
    route_gate_current_blocker: str | None = None,
    route_gate_non_counting_blocker: str | None = None,
) -> str:
    if route_gate_non_counting_blocker is not None:
        if route_gate_non_counting_blocker == "identity_public_contract_gate_missing":
            return (
                "review the identity public contract before counting identity, "
                "permissions, command response, or commands/replies toward complete SDK wording"
            )
        return (
            "resolve the command/permission route gate before counting this P0 row "
            "toward complete SDK wording"
        )
    if status == "promoted":
        if not promotion_evidence_satisfied:
            return "keep blocked; promoted status lacks acceptable ABI and SDK-consumer evidence"
        if release_statement_outcome != "promoted":
            return "add one release-statement promoted record after reviewing evidence"
        if not release_statement_contract_satisfied:
            return "replace the promoted release-statement record with reviewed evidence details"
        return "promoted accounting complete; this still does not allow the stable SDK claim by itself"
    if (
        surface_id in CANONICAL_V1_DEPENDENCY_SEQUENCE
        and manifest_outcome in P0_DEPENDENCY_CHAIN_SCOPED_NON_COMPLETE_ALLOWED_OUTCOMES
    ):
        return (
            "scoped non-complete outcome only; promote with evidence before "
            "complete/full/production SDK wording"
        )
    if manifest_outcome in {"post-v1", "excluded"}:
        if release_statement_contract_satisfied:
            return "release-statement outcome accounted; remaining SDK claim still depends on all blockers"
        expected = manifest_outcome
        return f"add one reviewed {expected} release-statement record satisfying this surface's exclusion contract"
    if status == "missing":
        return "restore the canonical blocker row in docs/public_sdk_surfaces.json"
    if surface_id in CANONICAL_V1_DEPENDENCY_SEQUENCE:
        return "priority dependency-chain blocker: promote with evidence; excluded/post-v1 cannot satisfy complete SDK"
    return "choose a reviewed v1 outcome: promote with evidence or explicitly exclude/post-v1 where the contract allows it"


def approved_runtime_principal_lifecycle_report_contract_satisfied(
    container: dict[str, Any],
) -> bool:
    report_schema = getattr(
        approved_runtime_principal_lifecycle_evidence,
        "REPORT_SCHEMA",
        "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
    )
    input_schema = getattr(
        approved_runtime_principal_lifecycle_evidence,
        "SCHEMA",
        "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
    )
    if (
        container.get("schema") != report_schema
        or container.get("input_schema") != input_schema
        or container.get("ready_scope") != RUNTIME_EVIDENCE_READY_SCOPE
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
    return not approved_runtime_evidence_non_approved_artifact_reasons(
        container,
        "approved_runtime_evidence",
    )


def accepted_approved_runtime_principal_lifecycle_bundle_aliases(
    command_permission_route_gate: dict[str, Any],
) -> bool:
    containers = [
        command_permission_route_gate,
        command_permission_route_gate.get("approved_in_game_evidence"),
        command_permission_route_gate.get("approved_runtime_evidence"),
        command_permission_route_gate.get(APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_BUNDLE),
    ]
    runtime_required_blockers = command_permission_route_gate.get("runtime_required_blockers")
    if isinstance(runtime_required_blockers, dict):
        containers.append(runtime_required_blockers.get("approved_runtime_evidence"))
    critical_path_phase = command_permission_route_gate.get("critical_path_phase")
    if isinstance(critical_path_phase, dict):
        containers.append(
            critical_path_phase.get("source_checker_approved_runtime_evidence_manifest")
        )

    for container in containers:
        if not isinstance(container, dict):
            continue
        if non_public_checkjoin_session_start_rejected_acceptance_present(container):
            continue
        if approved_runtime_evidence_non_approved_artifact_reasons(
            container,
            "approved_runtime_evidence",
        ):
            continue
        if approved_runtime_principal_lifecycle_report_contract_satisfied(container):
            return True
    return False


def command_permission_route_gate_current_blocker(
    command_permission_route_gate: dict[str, Any] | None,
) -> str | None:
    if not isinstance(command_permission_route_gate, dict):
        return None
    current_route_blocker = command_permission_route_gate.get("current_route_blocker")
    if isinstance(current_route_blocker, str) and current_route_blocker:
        return current_route_blocker
    current_blocker = command_permission_route_gate.get("current_blocker")
    if isinstance(current_blocker, str) and current_blocker:
        return current_blocker
    critical_path_phase = command_permission_route_gate.get("critical_path_phase")
    if isinstance(critical_path_phase, dict):
        nested_current_blocker = critical_path_phase.get("current_blocker")
        if isinstance(nested_current_blocker, str) and nested_current_blocker:
            return nested_current_blocker
    if accepted_approved_runtime_principal_lifecycle_bundle_aliases(
        command_permission_route_gate
    ):
        return IDENTITY_PUBLIC_CONTRACT_GATE_MISSING_BLOCKER
    return None


def command_permission_route_gate_remaining_route_blockers(
    command_permission_route_gate: dict[str, Any] | None,
) -> list[str]:
    if not isinstance(command_permission_route_gate, dict):
        return []
    current_route_blocker = command_permission_route_gate_current_blocker(
        command_permission_route_gate
    )
    remaining_route_blockers = command_permission_route_gate.get("remaining_route_blockers")
    normalized = (
        [
            blocker
            for blocker in remaining_route_blockers
            if isinstance(blocker, str) and blocker
        ]
        if isinstance(remaining_route_blockers, list)
        else []
    )
    if current_route_blocker is not None:
        return list(dict.fromkeys([current_route_blocker, *normalized]))
    return normalized


def normalized_completion_summary(
    *,
    status: str,
    ready: bool,
    blockers: list[str],
    current_route_blocker: str | None,
    remaining_route_blockers: list[str],
    stable_claim_allowed: bool,
    manifest_stable_claim_allowed: bool,
    complete_sdk_blocker_claim_accounting: dict[str, Any],
    p0_dependency_chain_claim_accounting: dict[str, Any],
) -> dict[str, Any]:
    def accounting_int(value: Any) -> int:
        return value if isinstance(value, int) and not isinstance(value, bool) else 0

    p0_promoted_count = accounting_int(
        p0_dependency_chain_claim_accounting.get("promoted_for_claim_count")
    )
    p0_total = accounting_int(p0_dependency_chain_claim_accounting.get("total"))
    p0_remaining_count = accounting_int(
        p0_dependency_chain_claim_accounting.get("remaining_for_claim_count")
    )
    normalized_remaining_route_blockers = [
        blocker
        for blocker in remaining_route_blockers
        if isinstance(blocker, str) and blocker
    ]
    normalized_current_route_blocker = (
        current_route_blocker
        if isinstance(current_route_blocker, str) and current_route_blocker
        else None
    )
    route_gate_blocked = (
        normalized_current_route_blocker is not None
        or bool(normalized_remaining_route_blockers)
    )
    p0_ready = (
        p0_total > 0
        and p0_promoted_count == p0_total
        and p0_remaining_count == 0
        and not route_gate_blocked
    )
    return {
        "schema": "obelisk.public-sdk-v1-completion-summary.v1",
        "status": status,
        "ready": ready,
        "blockers": list(blockers),
        "current_route_blocker": normalized_current_route_blocker,
        "remaining_route_blockers": normalized_remaining_route_blockers,
        "route_gate_blocked": route_gate_blocked,
        "stable_claim_allowed": stable_claim_allowed,
        "stable_release_contract_claim_allowed": manifest_stable_claim_allowed,
        "sdk_completion": {
            "status": status,
            "ready": ready,
            "claim_ready": stable_claim_allowed,
            "claim_allowed": stable_claim_allowed,
            "total": accounting_int(complete_sdk_blocker_claim_accounting.get("total")),
            "promoted_for_claim_count": accounting_int(
                complete_sdk_blocker_claim_accounting.get("promoted_for_claim_count")
            ),
            "remaining_for_claim_count": accounting_int(
                complete_sdk_blocker_claim_accounting.get("remaining_for_claim_count")
            ),
            "progress_ratio": complete_sdk_blocker_claim_accounting.get(
                "promoted_for_claim_ratio",
                "0/0",
            ),
            "promoted_for_claim_surfaces": as_string_list(
                complete_sdk_blocker_claim_accounting.get(
                    "promoted_for_claim_surfaces",
                    [],
                )
            ),
            "remaining_for_claim_surfaces": as_string_list(
                complete_sdk_blocker_claim_accounting.get(
                    "remaining_for_claim_surfaces",
                    [],
                )
            ),
        },
        "p0_completion": {
            "status": "ready" if p0_ready else "blocked",
            "ready": p0_ready,
            "total": p0_total,
            "promoted_for_claim_count": p0_promoted_count,
            "remaining_for_claim_count": p0_remaining_count,
            "progress_ratio": p0_dependency_chain_claim_accounting.get(
                "promoted_for_claim_ratio",
                "0/0",
            ),
            "promoted_for_claim_surfaces": as_string_list(
                p0_dependency_chain_claim_accounting.get(
                    "promoted_for_claim_surfaces",
                    [],
                )
            ),
            "remaining_for_claim_surfaces": as_string_list(
                p0_dependency_chain_claim_accounting.get(
                    "remaining_for_claim_surfaces",
                    [],
                )
            ),
            "current_route_blocker": normalized_current_route_blocker,
            "remaining_route_blockers": normalized_remaining_route_blockers,
            "route_gate_blocked": route_gate_blocked,
            "route_gate_current_blockers": as_string_list(
                p0_dependency_chain_claim_accounting.get(
                    "route_gate_current_blockers",
                    [],
                )
            ),
        },
        "non_claim": (
            "Normalized progress summary only; it does not authorize stable, complete, "
            "full, production, runtime, Plugin Hub, or support-tier SDK wording."
        ),
    }


def non_authorizing_action_path_accounting_fields() -> dict[str, bool | int]:
    fields: dict[str, bool | int] = {
        key: False for key in ACTIONABLE_PATH_NON_AUTHORIZING_FALSE_KEYS
    }
    fields.update({key: 0 for key in ACTIONABLE_PATH_ZERO_KEYS})
    return fields


def fastest_next_sdk_unblock(
    *,
    current_route_blocker: str | None,
    remaining_route_blockers: list[str],
    p0_dependency_chain_claim_accounting: dict[str, Any],
) -> dict[str, Any]:
    normalized_route_blockers = [
        blocker
        for blocker in remaining_route_blockers
        if isinstance(blocker, str) and blocker
    ]
    if isinstance(current_route_blocker, str) and current_route_blocker:
        normalized_route_blockers = list(
            dict.fromkeys([current_route_blocker, *normalized_route_blockers])
        )

    remaining_p0 = as_string_list(
        p0_dependency_chain_claim_accounting.get("remaining_for_claim_surfaces", [])
    )
    current_p0_surface = remaining_p0[0] if remaining_p0 else None
    current_blocker = normalized_route_blockers[0] if normalized_route_blockers else None
    actionable_paths: dict[str, Any] = {}

    if current_blocker == "approved_runtime_evidence_missing":
        unblock_kind = "approved_copied_runtime_principal_lifecycle_evidence"
        required_artifacts = [
            APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_BUNDLE,
            "copied_Obelisk.log_with_PlayerPrincipalLifecycleObserver_event_triplet",
        ]
        required_actions = ["player_notice_action"]
        required_event_roles = list(REQUIRED_PRINCIPAL_LIFECYCLE_EVENT_ROLES)
        required_closure_artifacts = [
            "window-manifest.env",
            "preflight-post.json",
            "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
        ]
        actionable_paths = {
            "historical_theisland_candidate_missing_sidecars": {
                "path_type": "candidate_closure_request_helper",
                "authorization": "non-authorizing",
                "non_authorizing": True,
                **non_authorizing_action_path_accounting_fields(),
                "authorizes_runtime_work": False,
                "authorizes_server_operations": False,
                "authorizes_workspace_writes": False,
                "reads_live_logs": False,
                "counts_toward_complete_sdk_claim_now": False,
                "counts_toward_p0_dependency_chain_claim_now": False,
                "complete_sdk_claim_progress_contribution": 0,
                "p0_dependency_chain_claim_progress_contribution": 0,
                "target": {"instance": "arkserver2", "map": "TheIsland"},
                "helper_path": (
                    "scripts/prepare_player_principal_lifecycle_evidence_closure_request.py"
                ),
                "command_template": [
                    "python3",
                    "scripts/prepare_player_principal_lifecycle_evidence_closure_request.py",
                    "--evidence-dir",
                    "<copied-historical-TheIsland-evidence-dir>",
                    "--instance",
                    "arkserver2",
                    "--map",
                    "TheIsland",
                    "--the-island-off",
                    "--two-server-cap-preserved",
                    "--format",
                    "json",
                ],
                "paths": [
                    "scripts/prepare_player_principal_lifecycle_evidence_closure_request.py",
                    "<copied-historical-TheIsland-evidence-dir>/window-manifest.env",
                    "<copied-historical-TheIsland-evidence-dir>/preflight-post.json",
                    (
                        "<copied-historical-TheIsland-evidence-dir>/approved-bundle/"
                        "approved-runtime-principal-lifecycle-evidence.json"
                    ),
                ],
                "requirements": [
                    "use copied/offline candidate artifacts only; do not read live logs",
                    (
                        "close the historical TheIsland candidate's missing sidecars with "
                        "fresh current-turn operator approval before any file write"
                    ),
                    (
                        "the helper report is a closure request only and does not create "
                        "sidecars or approved evidence"
                    ),
                    "preserve TheIsland-off and two-server-cap constraints when supplied",
                    (
                        "required event roles remain session_start, session_start_rejected, "
                        "and session_end"
                    ),
                ],
                "required_closure_artifacts": required_closure_artifacts,
                "required_event_roles": required_event_roles,
                "evidence_status": "non_evidence_until_approved_bundle_acceptance",
                "path_status": "historical_theisland_sidecar_closure",
                "missing_artifact_key": "historical_theisland_candidate_missing_sidecars",
            },
            "active_genesis2_passive_missing_roles": {
                "path_type": "passive_observation_missing_role_triplet",
                "source_scope": "historical_documented_passive_context",
                "freshness": "not_current_runtime_evidence",
                "current_live_capture": False,
                "current_posture_input": False,
                "active_path_label_is_historical_compatibility_alias": True,
                "path_label_note": (
                    "The active_genesis2 path id is retained for compatibility with "
                    "older reports; current one-server posture must not treat it as "
                    "an active live capture or current role source."
                ),
                "authorization": "non-authorizing",
                "non_authorizing": True,
                **non_authorizing_action_path_accounting_fields(),
                "authorizes_runtime_work": False,
                "authorizes_server_operations": False,
                "authorizes_workspace_writes": False,
                "reads_live_logs": False,
                "counts_toward_complete_sdk_claim_now": False,
                "counts_toward_p0_dependency_chain_claim_now": False,
                "complete_sdk_claim_progress_contribution": 0,
                "p0_dependency_chain_claim_progress_contribution": 0,
                "target": {"instance": "arkserver3", "map": "Genesis2"},
                "paths": [
                    "current-docs passive Genesis2 observation scope",
                    "missing_role_triplet:session_end",
                ],
                "requirements": [
                    (
                        "treat the Genesis2 passive observation as historical "
                        "diagnostic context until a checked current copied/runtime "
                        "log artifact explicitly supplies fresh roles"
                    ),
                    (
                        "a complete role triplet still remains diagnostic until copied, "
                        "reviewed approved runtime evidence is produced"
                    ),
                    (
                        "passive snapshots, latest summaries, and activity triage do not "
                        "satisfy approved runtime principal lifecycle evidence"
                    ),
                    (
                        "required event roles remain session_start, session_start_rejected, "
                        "and session_end"
                    ),
                ],
                "required_event_roles": required_event_roles,
                "missing_event_roles": ["session_end"],
                "evidence_status": "diagnostic_passive_non_evidence",
                "path_status": "active_genesis2_missing_session_end",
                "required_next_role": "session_end",
                "missing_requirement_key": "active_genesis2_passive_missing_roles",
            },
            "active_ragnarok_passive_complete_triplet_non_evidence_needs_bundle": {
                "path_type": "passive_observation_complete_role_triplet_non_evidence",
                "source_scope": "historical_documented_passive_context",
                "freshness": "not_current_runtime_evidence",
                "current_live_capture": False,
                "current_posture_input": False,
                "approved_offline_bundle_candidate": False,
                "authorization": "non-authorizing",
                "non_authorizing": True,
                **non_authorizing_action_path_accounting_fields(),
                "authorizes_runtime_work": False,
                "authorizes_server_work": False,
                "authorizes_workspace_work": False,
                "authorizes_server_operations": False,
                "authorizes_workspace_writes": False,
                "reads_live_logs": False,
                "counts_as_approved_runtime_evidence": False,
                "passive_snapshot_evidence_allowed": False,
                "counts_toward_complete_sdk_claim_now": False,
                "counts_toward_p0_dependency_chain_claim_now": False,
                "claim_progress_contribution": 0,
                "complete_sdk_claim_progress_contribution": 0,
                "p0_dependency_chain_claim_progress_contribution": 0,
                "target": {"instance": "arkserver", "map": "Ragnarok"},
                "paths": [
                    "historical/current-docs passive Ragnarok observation scope",
                    "passive_role_triplet:session_start",
                    "passive_role_triplet:session_start_rejected",
                    "passive_role_triplet:session_end",
                    "approved_bundle_missing",
                ],
                "requirements": [
                    (
                        "treat the documented complete passive Ragnarok triplet as "
                        "historical diagnostic/non-evidence context only, not as a "
                        "fresh live capture"
                    ),
                    (
                        "do not read live logs or perform server/runtime work from this "
                        "actionable path"
                    ),
                    (
                        "produce a copied, reviewed approved runtime principal lifecycle "
                        "evidence bundle before it can unblock the route gate"
                    ),
                    (
                        "passive snapshots, latest summaries, and activity triage do not "
                        "satisfy approved runtime principal lifecycle evidence"
                    ),
                    (
                        "required event roles remain session_start, session_start_rejected, "
                        "and session_end"
                    ),
                ],
                "required_event_roles": required_event_roles,
                "present_event_roles": required_event_roles,
                "missing_event_roles": [],
                "evidence_status": "diagnostic_passive_non_evidence",
                "path_status": "active_ragnarok_complete_passive_triplet_needs_approved_bundle",
                "required_next_artifact": APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_BUNDLE,
                "approved_bundle_required": True,
                "missing_requirement_key": (
                    "active_ragnarok_passive_complete_triplet_non_evidence_needs_bundle"
                ),
            },
            "player_notice_action": {
                "path_type": "player_notice_action",
                "authorization": "non-authorizing",
                "non_authorizing": True,
                **non_authorizing_action_path_accounting_fields(),
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
                    "player_notice_action",
                    "standing-authorized or current-turn approved player notice path required before activation",
                ],
                "requirements": [
                    (
                        "player-backed evidence windows require a standing-authorized "
                        "or current-turn approved player_notice_action before activation"
                    ),
                    (
                        "this status report does not authorize Discord, beta tester "
                        "notices, runtime work, server operations, live-log reads, or "
                        "workspace writes"
                    ),
                    (
                        "notice sent, notice dry-run accepted, and bundle accepted "
                        "statuses do not satisfy approved runtime evidence or count "
                        "toward SDK/P0 progress"
                    ),
                ],
                "required_event_roles": required_event_roles,
                "evidence_status": "player_notice_action_required_non_evidence",
                "path_status": "player_notice_action_required",
                "missing_requirement_key": "player_notice_action",
            },
            "multi_surface_beta_capture_candidate_queue": {
                "path_type": "multi_surface_beta_capture_plan_queue",
                "authorization": "non-authorizing",
                "non_authorizing": True,
                **non_authorizing_action_path_accounting_fields(),
                "visible_as_next_action": True,
                "candidate_presence_visible": True,
                "approved_runtime_evidence_missing_cleared": False,
                "approved_runtime_evidence_missing_resolved": False,
                "clears_approved_runtime_evidence_missing": False,
                "resolves_approved_runtime_evidence_missing": False,
                "plugin_hub_ready": False,
                "plugin_hub_readiness_claim_allowed": False,
                "plugin_hub_readiness_ready": False,
                "public_sdk_readiness_ready": False,
                "runtime_readiness_ready": False,
                "sdk_accounting_counts_as_completed_surface": False,
                "p0_accounting_counts_as_promoted_surface": False,
                "candidate_presence_counts_toward_sdk": False,
                "candidate_presence_counts_toward_p0_dependency_chain": False,
                "safe_candidate_surfaces": list(MULTI_SURFACE_BETA_CAPTURE_TARGETS),
                "recognized_candidate_queue_artifact_schemas": list(
                    MULTI_SURFACE_BETA_CAPTURE_CANDIDATE_QUEUE_ARTIFACT_SCHEMAS
                ),
                "recognized_candidate_queue_artifact_names": list(
                    MULTI_SURFACE_BETA_CAPTURE_CANDIDATE_QUEUE_ARTIFACT_NAMES
                ),
                "required_event_roles": required_event_roles,
                "candidate_queue_artifact_family_status": (
                    "visible_non_counting_candidate_queue_material"
                ),
                "candidate_queue_artifact_family_counts_as_approved_runtime_evidence": False,
                "candidate_queue_artifact_family_counts_toward_sdk": False,
                "candidate_queue_artifact_family_counts_toward_p0_dependency_chain": False,
                "prior_blocker": APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER,
                "required_first_artifact": APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_BUNDLE,
                "queue_status": "candidate_plan_visible_non_counting",
                "evidence_status": "multi_surface_beta_capture_plan_queue_non_evidence",
                "path_status": (
                    "queue_safe_beta_candidate_surfaces_after_player_principal_"
                    "evidence_blocker"
                ),
                "requirements": [
                    (
                        "keep the approved player-principal runtime evidence blocker "
                        "first before any downstream promotion checker can count surfaces"
                    ),
                    (
                        "beta sessions may collect safe candidate observations across "
                        "player-principal, admin, command, dino, tribe, buff, "
                        "inventory, transfer, and mission surfaces"
                    ),
                    (
                        "candidate presence, plans, beta notices, passive logs, and "
                        "multi-surface queues are visible planning inputs only"
                    ),
                    (
                        "generated pack manifests, checker-command matrices, "
                        "non-claim manifests, operator runbooks, and manifest/readme "
                        "files remain candidate queue material only"
                    ),
                    (
                        "this queue does not clear approved_runtime_evidence_missing, "
                        "runtime readiness, public SDK readiness, Plugin Hub readiness, "
                        "or SDK/P0 progress"
                    ),
                ],
                "missing_requirement_key": (
                    "multi_surface_beta_capture_candidate_queue_non_counting"
                ),
            },
        }
        next_route_blocker_after_acceptance = "identity_public_contract_gate_missing"
        active_runtime_window_requires_current_turn_scope = False
        active_runtime_window_requires_standing_or_current_scope = True
        recommended_next_action = (
            "produce approved copied runtime principal lifecycle evidence for "
            "obelisk.player_identity.v1 before reviewing public identity, permissions/admin, "
            "command response, or commands/replies ABI"
        )
    elif current_blocker == "identity_public_contract_gate_missing":
        unblock_kind = "reviewed_identity_public_contract"
        required_artifacts = ["reviewed_player_identity_public_contract_decision"]
        required_actions = []
        required_event_roles = []
        next_route_blocker_after_acceptance = None
        active_runtime_window_requires_current_turn_scope = False
        active_runtime_window_requires_standing_or_current_scope = False
        recommended_next_action = (
            "review the player identity public contract before permissions/admin, "
            "command response, or commands/replies ABI"
        )
    elif current_p0_surface:
        unblock_kind = "p0_dependency_chain_promotion"
        required_artifacts = ["promoted_surface_evidence_and_matching_sdk_consumer_tests"]
        required_actions = []
        required_event_roles = []
        next_route_blocker_after_acceptance = None
        active_runtime_window_requires_current_turn_scope = False
        active_runtime_window_requires_standing_or_current_scope = False
        recommended_next_action = (
            f"promote {current_p0_surface} with reviewed evidence before later P0 surfaces"
        )
    else:
        unblock_kind = "remaining_complete_sdk_demand_family_promotion"
        required_artifacts = ["promoted_surface_evidence_or_reviewed_v1_outcome"]
        required_actions = []
        required_event_roles = []
        next_route_blocker_after_acceptance = None
        active_runtime_window_requires_current_turn_scope = False
        active_runtime_window_requires_standing_or_current_scope = False
        recommended_next_action = (
            "resolve remaining complete-SDK demand family blockers with promoted evidence "
            "or reviewed scoped outcomes"
        )

    return {
        "schema": "obelisk.public-sdk-v1-fastest-next-unblock.v1",
        "surface": current_p0_surface,
        "current_route_blocker": current_blocker,
        "remaining_route_blockers": normalized_route_blockers,
        "unblock_kind": unblock_kind,
        "required_artifacts": required_artifacts,
        "required_actions": required_actions,
        "required_event_roles": required_event_roles,
        "next_route_blocker_after_acceptance": next_route_blocker_after_acceptance,
        "active_runtime_window_requires_current_turn_scope": (
            active_runtime_window_requires_current_turn_scope
        ),
        "active_runtime_window_requires_standing_or_current_scope": (
            active_runtime_window_requires_standing_or_current_scope
        ),
        "standing_launch_authority_recorded": STANDING_LAUNCH_AUTHORITY_RECORDED,
        "standing_launch_authority_source": STANDING_LAUNCH_AUTHORITY_SOURCE,
        "standing_launch_authority_satisfies_runtime_window_scope": (
            active_runtime_window_requires_standing_or_current_scope
            and STANDING_LAUNCH_AUTHORITY_RECORDED
        ),
        "current_turn_scope_requirement": STANDING_OR_CURRENT_SCOPE_REQUIREMENT,
        "runtime_window_scope_requirement": STANDING_OR_CURRENT_SCOPE_REQUIREMENT,
        "runtime_window_can_be_prepared_under_standing_authority": (
            active_runtime_window_requires_standing_or_current_scope
            and STANDING_LAUNCH_AUTHORITY_RECORDED
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
        **non_authorizing_action_path_accounting_fields(),
        "counts_toward_complete_sdk_claim_now": False,
        "counts_toward_p0_dependency_chain_claim_now": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "prioritization_only": True,
        "player_notice_action_required": "player_notice_action" in required_actions,
        "notice_action_authorized": False,
        "player_notice_action_authorized": False,
        "authorizes_discord": False,
        "discord_authorized": False,
        "notice_sent": False,
        "player_notice_sent": False,
        "notice_dry_run_sent": False,
        "notice_dry_run_accepted": False,
        "notice_bundle_accepted": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "stable_claim_allowed": False,
        "actionable_paths": actionable_paths,
        "recommended_next_action": recommended_next_action,
        "non_claim": (
            "Prioritization only; this object does not approve runtime work, public ABI, "
            "public SDK readiness, or complete/full/production/stable SDK wording."
        ),
    }


def approved_in_game_evidence_completion_status(
    *,
    current_route_blocker: str | None,
    fastest_next_unblock: dict[str, Any],
) -> dict[str, Any]:
    action_paths = fastest_next_unblock.get("actionable_paths")
    if not isinstance(action_paths, dict):
        action_paths = {}
    required_roles = list(REQUIRED_PRINCIPAL_LIFECYCLE_EVENT_ROLES)
    required_role_set = set(required_roles)
    diagnostic_complete_triplet_path_ids: list[str] = []
    missing_role_path_ids: list[str] = []
    path_summaries: dict[str, dict[str, Any]] = {}

    for path_id, payload in action_paths.items():
        if not isinstance(path_id, str) or not isinstance(payload, dict):
            continue
        present_roles = as_string_list(payload.get("present_event_roles"))
        missing_roles = as_string_list(payload.get("missing_event_roles"))
        complete_triplet = required_role_set.issubset(set(present_roles)) and not missing_roles
        evidence_status = payload.get("evidence_status")
        if complete_triplet and evidence_status == "diagnostic_passive_non_evidence":
            diagnostic_complete_triplet_path_ids.append(path_id)
        if missing_roles:
            missing_role_path_ids.append(path_id)
        path_summaries[path_id] = {
            "target": payload.get("target"),
            "path_status": payload.get("path_status"),
            "path_type": payload.get("path_type"),
            "source_scope": payload.get("source_scope"),
            "freshness": payload.get("freshness"),
            "current_live_capture": bool(payload.get("current_live_capture")),
            "current_posture_input": bool(payload.get("current_posture_input")),
            "approved_offline_bundle_candidate": bool(
                payload.get("approved_offline_bundle_candidate")
            ),
            "evidence_status": evidence_status,
            "authorization": "non-authorizing",
            "candidate_presence_visible": bool(payload.get("candidate_presence_visible")),
            "candidate_queue_artifact_family_status": payload.get(
                "candidate_queue_artifact_family_status"
            ),
            "recognized_candidate_queue_artifact_schemas": as_string_list(
                payload.get("recognized_candidate_queue_artifact_schemas")
            ),
            "recognized_candidate_queue_artifact_names": as_string_list(
                payload.get("recognized_candidate_queue_artifact_names")
            ),
            "present_event_roles": present_roles,
            "missing_event_roles": missing_roles,
            "complete_required_role_triplet": complete_triplet,
            "approved_runtime_evidence": False,
            "approved_runtime_evidence_accepted": False,
            "evidence_bundle_accepted": False,
            "counts_as_approved_runtime_evidence": False,
            "candidate_queue_artifact_family_counts_as_approved_runtime_evidence": False,
            "counts_toward_complete_sdk_claim_now": False,
            "counts_toward_p0_dependency_chain_claim_now": False,
            "candidate_queue_artifact_family_counts_toward_sdk": False,
            "candidate_queue_artifact_family_counts_toward_p0_dependency_chain": False,
            "live_ops_authorized": False,
            "server_operations_authorized": False,
            "workspace_writes_authorized": False,
            "runtime_capture_authorized": False,
            "reads_live_logs": False,
            "read_live_logs": False,
            "required_next_artifact": payload.get("required_next_artifact"),
        }

    next_required_artifact = None
    for artifact in as_string_list(fastest_next_unblock.get("required_artifacts")):
        if artifact == APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_BUNDLE:
            next_required_artifact = artifact
            break
    if next_required_artifact is None:
        source_next_required_artifact = fastest_next_unblock.get("next_required_artifact")
        if isinstance(source_next_required_artifact, str) and source_next_required_artifact:
            next_required_artifact = source_next_required_artifact
    if (
        next_required_artifact is None
        and current_route_blocker == "approved_runtime_evidence_missing"
    ):
        next_required_artifact = APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_BUNDLE
    return {
        "schema": "obelisk.public-sdk-v1-approved-in-game-evidence-status.v1",
        "completion_gate_status_only": True,
        "current_route_blocker": current_route_blocker,
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
        "current_turn_scope_required": bool(
            fastest_next_unblock.get("active_runtime_window_requires_current_turn_scope")
        ),
        "active_runtime_window_requires_standing_or_current_scope": bool(
            fastest_next_unblock.get("active_runtime_window_requires_standing_or_current_scope")
        ),
        "standing_launch_authority_recorded": bool(
            fastest_next_unblock.get("standing_launch_authority_recorded")
        ),
        "standing_launch_authority_source": fastest_next_unblock.get(
            "standing_launch_authority_source"
        ),
        "standing_launch_authority_satisfies_runtime_window_scope": bool(
            fastest_next_unblock.get("standing_launch_authority_satisfies_runtime_window_scope")
        ),
        "runtime_window_scope_requirement": fastest_next_unblock.get(
            "runtime_window_scope_requirement"
        ),
        "runtime_window_can_be_prepared_under_standing_authority": bool(
            fastest_next_unblock.get("runtime_window_can_be_prepared_under_standing_authority")
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
            fastest_next_unblock.get("player_notice_action_required")
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
            "Completion-gate status only: approved in-game evidence stays false unless "
            "an approved copied runtime principal lifecycle evidence bundle is accepted; "
            "passive triplets, player notices, public reachability, and closure requests "
            "do not count toward SDK or P0 progress."
        ),
    }


def progress_normalization_trace(
    *,
    status: str,
    ready: bool,
    current_route_blocker: str | None,
    remaining_route_blockers: list[str],
    approved_in_game_evidence: dict[str, Any],
    complete_sdk_blocker_claim_accounting: dict[str, Any],
    p0_dependency_chain_claim_accounting: dict[str, Any],
    stable_claim_allowed: bool,
) -> dict[str, Any]:
    next_required_artifact = approved_in_game_evidence.get("next_required_artifact")
    missing_required_artifact = approved_in_game_evidence.get("missing_required_artifact")
    complete_sdk_progress_ratio = complete_sdk_blocker_claim_accounting.get(
        "promoted_for_claim_ratio"
    )
    p0_chain_progress_ratio = p0_dependency_chain_claim_accounting.get(
        "promoted_for_claim_ratio"
    )
    normalization_reasons = list(dict.fromkeys(
        [
            reason
            for reason in [
                current_route_blocker,
                (
                    f"missing_required_artifact:{missing_required_artifact}"
                    if missing_required_artifact
                    else None
                ),
                (
                    "complete_sdk_blockers_remaining_for_claim"
                    if complete_sdk_blocker_claim_accounting.get("remaining_for_claim_count")
                    else None
                ),
                (
                    "p0_dependency_chain_remaining_for_claim"
                    if p0_dependency_chain_claim_accounting.get("remaining_for_claim_count")
                    else None
                ),
            ]
            if isinstance(reason, str) and reason
        ]
    ))

    return {
        "schema": "obelisk.public-sdk-v1-progress-normalization-trace.v1",
        "status_report_only": True,
        "status": status,
        "ready": ready,
        "current_route_blocker": current_route_blocker,
        "remaining_route_blockers": remaining_route_blockers,
        "route_gate_blocked": bool(current_route_blocker or remaining_route_blockers),
        "next_required_artifact": next_required_artifact,
        "missing_required_artifact": missing_required_artifact,
        "approved_runtime_evidence_ready": bool(
            approved_in_game_evidence.get("approved_runtime_evidence_ready")
        ),
        "approved_in_game_evidence_ready": bool(
            approved_in_game_evidence.get("approved_in_game_evidence_ready")
        ),
        "evidence_bundle_accepted": bool(
            approved_in_game_evidence.get("evidence_bundle_accepted")
        ),
        "complete_sdk_progress_ratio": complete_sdk_progress_ratio,
        "p0_chain_progress_ratio": p0_chain_progress_ratio,
        "complete_sdk_promoted_for_claim_count": (
            complete_sdk_blocker_claim_accounting.get("promoted_for_claim_count")
        ),
        "complete_sdk_remaining_for_claim_count": (
            complete_sdk_blocker_claim_accounting.get("remaining_for_claim_count")
        ),
        "p0_dependency_chain_promoted_for_claim_count": (
            p0_dependency_chain_claim_accounting.get("promoted_for_claim_count")
        ),
        "p0_dependency_chain_remaining_for_claim_count": (
            p0_dependency_chain_claim_accounting.get("remaining_for_claim_count")
        ),
        "runtime_ready": False,
        "public_sdk_ready": stable_claim_allowed,
        "stable_claim_allowed": stable_claim_allowed,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "normalization_reasons": normalization_reasons,
        "non_claim": (
            "Diagnostic trace only: it explains why claim progress remains normalized; "
            "it does not approve runtime evidence, public SDK readiness, or stable SDK claims."
        ),
    }


def stable_sdk_remaining_blockers_report(
    *,
    status: str,
    ready: bool,
    current_route_blocker: str | None,
    remaining_route_blockers: list[str],
    complete_sdk_blocker_claim_accounting: dict[str, Any],
    p0_dependency_chain_claim_accounting: dict[str, Any],
    fastest_next_unblock: dict[str, Any],
    approved_in_game_evidence: dict[str, Any],
    stable_claim_allowed: bool,
) -> dict[str, Any]:
    sdk_remaining_surfaces = as_string_list(
        complete_sdk_blocker_claim_accounting.get("remaining_for_claim_surfaces", [])
    )
    p0_remaining_surfaces = as_string_list(
        p0_dependency_chain_claim_accounting.get("remaining_for_claim_surfaces", [])
    )
    normalized_route_blockers = [
        blocker
        for blocker in remaining_route_blockers
        if isinstance(blocker, str) and blocker
    ]
    if isinstance(current_route_blocker, str) and current_route_blocker:
        normalized_route_blockers = list(
            dict.fromkeys([current_route_blocker, *normalized_route_blockers])
        )
    next_required_artifact = approved_in_game_evidence.get("next_required_artifact")
    if not isinstance(next_required_artifact, str) or not next_required_artifact:
        next_required_artifact = fastest_next_unblock.get("next_required_artifact")
    missing_required_artifact = approved_in_game_evidence.get("missing_required_artifact")

    return {
        "schema": "obelisk.public-sdk-v1-stable-sdk-remaining-blockers.v1",
        "status_report_only": True,
        "status": status,
        "ready": ready,
        "complete_sdk_ready": ready,
        "stable_claim_allowed": stable_claim_allowed,
        "stable_sdk_ready": stable_claim_allowed,
        "public_sdk_ready": stable_claim_allowed,
        "runtime_ready": False,
        "current_route_blocker": current_route_blocker,
        "remaining_route_blockers": normalized_route_blockers,
        "route_gate_blocked": bool(normalized_route_blockers),
        "next_required_artifact": next_required_artifact,
        "missing_required_artifact": missing_required_artifact,
        "after_runtime_evidence": fastest_next_unblock.get("next_route_blocker_after_acceptance"),
        "complete_sdk_progress_ratio": complete_sdk_blocker_claim_accounting.get(
            "promoted_for_claim_ratio"
        ),
        "complete_sdk_promoted_for_claim_count": complete_sdk_blocker_claim_accounting.get(
            "promoted_for_claim_count"
        ),
        "complete_sdk_remaining_for_claim_count": complete_sdk_blocker_claim_accounting.get(
            "remaining_for_claim_count"
        ),
        "complete_sdk_total": complete_sdk_blocker_claim_accounting.get("total"),
        "remaining_sdk_blocker_surfaces": sdk_remaining_surfaces,
        "remaining_sdk_blocker_surface_count": len(sdk_remaining_surfaces),
        "p0_dependency_chain": list(CANONICAL_V1_REQUIRED_DEPENDENCY_CHAIN),
        "p0_dependency_chain_progress_ratio": p0_dependency_chain_claim_accounting.get(
            "promoted_for_claim_ratio"
        ),
        "p0_dependency_chain_promoted_for_claim_count": (
            p0_dependency_chain_claim_accounting.get("promoted_for_claim_count")
        ),
        "p0_dependency_chain_remaining_for_claim_count": (
            p0_dependency_chain_claim_accounting.get("remaining_for_claim_count")
        ),
        "p0_dependency_chain_total": p0_dependency_chain_claim_accounting.get("total"),
        "remaining_p0_dependency_chain_surfaces": p0_remaining_surfaces,
        "remaining_p0_dependency_chain_surface_count": len(p0_remaining_surfaces),
        "current_p0_surface": p0_remaining_surfaces[0] if p0_remaining_surfaces else None,
        "package_shape_counts_toward_complete_sdk_claim": False,
        "scoped_non_complete_release_statement_counts_toward_complete_sdk_claim": False,
        "monitor_context_counts_toward_complete_sdk_claim": False,
        "passive_status_counts_toward_complete_sdk_claim": False,
        "beta_notice_counts_toward_complete_sdk_claim": False,
        "copied_log_only_counts_toward_complete_sdk_claim": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "non_claim": (
            "Stable SDK remaining-blocker report only: package-shape installs, scoped "
            "non-complete release statements, monitor/passive status context, beta notices, "
            "and copied-log-only artifacts do not satisfy runtime evidence, SDK/P0 progress, "
            "runtime readiness, public SDK readiness, release readiness, or stable SDK wording."
        ),
    }


def completion_blocker_outcome_rows(
    completion_blockers: list[str],
    surfaces_by_id: dict[str, dict[str, Any]],
    post_v1_or_excluded: set[str],
    release_statement_text: str | None,
    command_permission_route_gate: dict[str, Any] | None = None,
    manifest_path: Path = DEFAULT_MANIFEST,
    public_header_path: Path = DEFAULT_PUBLIC_HEADER,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    counts_by_surface: dict[str, bool] = {}
    route_gate_current_blocker = command_permission_route_gate_current_blocker(
        command_permission_route_gate
    )
    for index, surface_id in enumerate(completion_blockers, start=1):
        surface = surfaces_by_id.get(surface_id, {})
        status = surface.get("status", "missing")
        status = status if isinstance(status, str) else "invalid"
        manifest_outcome = status if status in {"promoted", "post-v1", "excluded"} else None
        release_statement_outcome = release_statement_recorded_outcome(release_statement_text, surface_id)
        evidence = surface.get("evidence") if surface else None
        evidence_is_dict = isinstance(evidence, dict)
        promotion_evidence_forbidden_ready_scope = (
            evidence_is_dict and evidence_has_forbidden_ready_scope(evidence)
        )
        promotion_evidence_non_promotional_schema_marker = (
            evidence_is_dict and evidence_has_non_promotional_schema_marker(evidence)
        )
        promotion_evidence_non_promotional_artifact_reference = (
            evidence_is_dict and evidence_has_non_promotional_artifact_reference(evidence)
        )
        promotion_evidence_public_contract_review_status_reference = (
            evidence_is_dict
            and evidence_has_unscoped_public_contract_review_status_reference(
                evidence,
                surface_id=surface_id,
            )
        )
        promotion_evidence_explicit_no_approved_claim = (
            evidence_is_dict and evidence_has_explicit_no_approved_claim(evidence)
        )
        promotion_evidence_limited_to_non_promotional_readiness = (
            evidence_is_dict and report_is_limited_to_non_promotional_readiness(evidence)
        )
        promotion_evidence_satisfied = bool(surface) and status == "promoted" and surface_has_promotion_evidence(surface)
        missing_required_terms = surface_missing_required_promotion_evidence(surface)
        missing_structured_evidence = surface_missing_structured_promotion_evidence(
            surface,
            manifest_path,
            public_header_path,
        )
        required_outcomes = sorted(required_release_statement_outcomes(surface)) if surface else []
        release_statement_contract_satisfied = False
        release_statement_outcome_matches_manifest = release_statement_outcome == manifest_outcome
        if status == "promoted":
            release_statement_contract_satisfied = (
                release_statement_text is not None
                and release_statement_satisfies_promoted_outcome(
                    release_statement_text,
                    surface_id,
                )
            )
        elif status in {"post-v1", "excluded"} and surface_id in post_v1_or_excluded:
            release_statement_contract_satisfied = (
                release_statement_text is not None
                and release_statement_outcome_matches_manifest
                and release_statement_outcome in required_outcomes
                and release_statement_satisfies_exclusion_contract(release_statement_text, surface)
            )
        elif status == "planning" and release_statement_outcome in required_outcomes:
            release_statement_outcome_matches_manifest = True
            release_statement_contract_satisfied = (
                release_statement_text is not None
                and release_statement_outcome in {"post-v1", "excluded"}
                and release_statement_satisfies_exclusion_contract(release_statement_text, surface)
            )
        is_p0_dependency_chain = surface_id in CANONICAL_V1_REQUIRED_DEPENDENCY_CHAIN
        scoped_non_complete_outcome_only = (
            is_p0_dependency_chain
            and manifest_outcome in P0_DEPENDENCY_CHAIN_SCOPED_NON_COMPLETE_ALLOWED_OUTCOMES
        )
        route_gate_claim_satisfied = not is_p0_dependency_chain
        dependency_claims_satisfied = True
        dependency_ids = as_string_list(surface.get("depends_on")) if surface else []
        for required_dependency_id in REQUIRED_PROMOTED_SURFACE_DEPENDENCIES.get(surface_id, ()):
            if required_dependency_id not in dependency_ids:
                dependency_ids.append(required_dependency_id)
        for dependency_id in dependency_ids:
            if dependency_id in completion_blockers and counts_by_surface.get(dependency_id) is not True:
                dependency_claims_satisfied = False
                break
        route_gate_non_counting_active = (
            is_p0_dependency_chain
            and manifest_outcome == "promoted"
            and promotion_evidence_satisfied
            and not missing_required_terms
            and not missing_structured_evidence
            and release_statement_contract_satisfied
            and route_gate_claim_satisfied is not True
        )
        route_gate_non_counting_blocker = (
            route_gate_current_blocker
            if route_gate_non_counting_active and isinstance(route_gate_current_blocker, str)
            else None
        )
        non_counting_reasons: list[str] = []
        if not promotion_evidence_satisfied:
            non_counting_reasons.append("promotion_evidence_missing")
        if promotion_evidence_forbidden_ready_scope:
            non_counting_reasons.append("non_promotional_ready_scope")
        if promotion_evidence_non_promotional_schema_marker:
            non_counting_reasons.append("non_promotional_schema_marker")
        if promotion_evidence_non_promotional_artifact_reference:
            non_counting_reasons.append("non_promotional_artifact_reference")
        if promotion_evidence_public_contract_review_status_reference:
            non_counting_reasons.append(
                "public_contract_review_status_artifact_without_identity_gate"
            )
        if promotion_evidence_explicit_no_approved_claim:
            non_counting_reasons.append("approved_evidence_claim_none")
        if promotion_evidence_limited_to_non_promotional_readiness:
            non_counting_reasons.append("non_promotional_readiness_only")
        if missing_required_terms:
            non_counting_reasons.append("required_promotion_evidence_terms_missing")
        if missing_structured_evidence:
            non_counting_reasons.append("structured_promotion_evidence_missing")
        if release_statement_contract_satisfied is not True:
            non_counting_reasons.append("release_statement_outcome_or_contract_missing")
        if manifest_outcome != "promoted":
            if scoped_non_complete_outcome_only:
                non_counting_reasons.append("p0_scoped_non_complete_outcome")
            elif manifest_outcome in {"post-v1", "excluded"}:
                non_counting_reasons.append("scoped_non_complete_outcome")
            elif (
                status == "planning"
                and release_statement_contract_satisfied
                and release_statement_outcome in {"post-v1", "excluded"}
            ):
                non_counting_reasons.append("scoped_non_complete_outcome")
            else:
                non_counting_reasons.append("manifest_promoted_outcome_missing")
        if route_gate_non_counting_blocker is not None:
            non_counting_reasons.append(f"route_gate_blocker:{route_gate_non_counting_blocker}")
        if not dependency_claims_satisfied:
            non_counting_reasons.append("dependency_claims_not_satisfied")
        counts_toward_complete_sdk_claim = (
            promotion_evidence_satisfied
            and not missing_required_terms
            and not missing_structured_evidence
            and release_statement_contract_satisfied
            and manifest_outcome == "promoted"
            and route_gate_claim_satisfied
            and dependency_claims_satisfied
        )
        manifest_promoted_but_non_counting = (
            manifest_outcome == "promoted"
            and not counts_toward_complete_sdk_claim
        )
        release_statement_scoped_non_complete_bookkeeping = (
            (
                manifest_outcome in P0_DEPENDENCY_CHAIN_SCOPED_NON_COMPLETE_ALLOWED_OUTCOMES
                or (
                    status == "planning"
                    and release_statement_outcome in {"post-v1", "excluded"}
                )
            )
            and release_statement_contract_satisfied
            and not counts_toward_complete_sdk_claim
        )
        non_counting_reasons = [] if counts_toward_complete_sdk_claim else non_counting_reasons
        counts_by_surface[surface_id] = counts_toward_complete_sdk_claim
        rows.append(
            {
                "surface": surface_id,
                "position": index,
                "status": status,
                "support_tier": surface.get("support_tier") if surface else None,
                "is_p0_dependency_chain": is_p0_dependency_chain,
                "manifest_outcome": manifest_outcome,
                "release_statement_outcome": release_statement_outcome,
                "release_statement_outcome_matches_manifest": release_statement_outcome_matches_manifest,
                "release_statement_contract_satisfied": release_statement_contract_satisfied,
                "required_release_statement_outcomes": required_outcomes,
                "promotion_evidence_satisfied": promotion_evidence_satisfied,
                "promotion_evidence_forbidden_ready_scope": promotion_evidence_forbidden_ready_scope,
                "promotion_evidence_non_promotional_schema_marker": (
                    promotion_evidence_non_promotional_schema_marker
                ),
                "promotion_evidence_non_promotional_artifact_reference": (
                    promotion_evidence_non_promotional_artifact_reference
                ),
                "promotion_evidence_public_contract_review_status_reference": (
                    promotion_evidence_public_contract_review_status_reference
                ),
                "promotion_evidence_explicit_no_approved_claim": (
                    promotion_evidence_explicit_no_approved_claim
                ),
                "promotion_evidence_limited_to_non_promotional_readiness": (
                    promotion_evidence_limited_to_non_promotional_readiness
                ),
                "required_promotion_evidence_terms_satisfied": not missing_required_terms,
                "missing_required_promotion_evidence_terms": missing_required_terms,
                "structured_promotion_evidence_satisfied": not missing_structured_evidence,
                "missing_structured_promotion_evidence": missing_structured_evidence,
                "dependency_claims_satisfied": dependency_claims_satisfied,
                "route_gate_claim_satisfied": route_gate_claim_satisfied,
                "route_gate_current_blocker": route_gate_current_blocker,
                "scoped_non_complete_outcome_only": scoped_non_complete_outcome_only,
                "non_counting_reasons": non_counting_reasons,
                "manifest_promoted_but_non_counting": manifest_promoted_but_non_counting,
                "release_statement_scoped_non_complete_bookkeeping": (
                    release_statement_scoped_non_complete_bookkeeping
                ),
                "route_gate_non_counting_blocker": route_gate_non_counting_blocker,
                "scoped_release_statement_counts_toward_complete_sdk_claim": False,
                "scoped_release_statement_claim_progress_contribution": 0,
                "counts_toward_complete_sdk_claim": counts_toward_complete_sdk_claim,
                "unresolved_for_complete_sdk_claim": not counts_toward_complete_sdk_claim,
                "next_action": blocker_outcome_next_action(
                    surface_id=surface_id,
                    status=status,
                    manifest_outcome=manifest_outcome,
                    release_statement_outcome=release_statement_outcome,
                    release_statement_contract_satisfied=release_statement_contract_satisfied,
                    promotion_evidence_satisfied=promotion_evidence_satisfied,
                    route_gate_current_blocker=(
                        route_gate_current_blocker if isinstance(route_gate_current_blocker, str) else None
                    ),
                    route_gate_non_counting_blocker=route_gate_non_counting_blocker,
                ),
                "non_claim": "Accounting row only; it does not authorize complete/full/production/stable SDK wording.",
            }
        )
    return rows


def completion_blocker_outcome_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    completion_blockers_promoted_for_claim = [
        row["surface"]
        for row in rows
        if row.get("counts_toward_complete_sdk_claim") is True
    ]
    completion_blockers_remaining_for_claim = [
        row["surface"]
        for row in rows
        if row.get("unresolved_for_complete_sdk_claim") is True
    ]
    p0_dependency_chain_surfaces = [
        row["surface"]
        for row in rows
        if row.get("is_p0_dependency_chain") is True
    ]
    p0_dependency_chain_promoted_for_claim = [
        row["surface"]
        for row in rows
        if row.get("is_p0_dependency_chain") is True
        and row.get("counts_toward_complete_sdk_claim") is True
    ]
    manifest_outcome_missing = [
        row["surface"] for row in rows if row.get("manifest_outcome") is None
    ]
    release_statement_outcome_missing = [
        row["surface"]
        for row in rows
        if row.get("manifest_outcome") in {"promoted", "post-v1", "excluded"}
        and row.get("release_statement_contract_satisfied") is not True
    ]
    dependency_chain_remaining = [
        row["surface"]
        for row in rows
        if row["surface"] in CANONICAL_V1_DEPENDENCY_SEQUENCE
        and row.get("unresolved_for_complete_sdk_claim") is True
    ]
    p0_scoped_non_complete_outcomes = [
        row["surface"]
        for row in rows
        if row.get("is_p0_dependency_chain") is True
        and row.get("scoped_non_complete_outcome_only") is True
    ]
    manifest_promoted_but_non_counting = [
        row["surface"]
        for row in rows
        if row.get("manifest_promoted_but_non_counting") is True
    ]
    release_statement_scoped_non_complete_bookkeeping = [
        row["surface"]
        for row in rows
        if row.get("release_statement_scoped_non_complete_bookkeeping") is True
    ]
    route_gate_non_counting_surfaces = [
        row["surface"]
        for row in rows
        if row.get("route_gate_non_counting_blocker") is not None
    ]
    route_gate_non_counting_blockers = sorted(
        {
            row["route_gate_non_counting_blocker"]
            for row in rows
            if isinstance(row.get("route_gate_non_counting_blocker"), str)
        }
    )
    route_gate_current_blockers = sorted(
        {
            row["route_gate_current_blocker"]
            for row in rows
            if isinstance(row.get("route_gate_current_blocker"), str)
        }
    )
    p0_manifest_promoted_non_counting = [
        row["surface"]
        for row in rows
        if row.get("is_p0_dependency_chain") is True
        and row.get("manifest_promoted_but_non_counting") is True
    ]
    p0_release_statement_scoped_non_complete_outcomes = [
        row["surface"]
        for row in rows
        if row.get("is_p0_dependency_chain") is True
        and row.get("release_statement_scoped_non_complete_bookkeeping") is True
    ]
    non_p0_manifest_post_v1_or_excluded_outcomes = [
        row["surface"]
        for row in rows
        if row.get("is_p0_dependency_chain") is not True
        and row.get("manifest_outcome") in {"post-v1", "excluded"}
    ]
    non_p0_release_statement_post_v1_or_excluded_outcomes = [
        row["surface"]
        for row in rows
        if row.get("is_p0_dependency_chain") is not True
        and row.get("release_statement_scoped_non_complete_bookkeeping") is True
    ]
    active_side_lane_review_blockers = [
        row["surface"]
        for row in rows
        if row["surface"] in CANONICAL_ACTIVE_SIDE_LANE_REVIEW_BLOCKERS
    ]
    active_side_lane_review_manifest_post_v1_or_excluded = [
        row["surface"]
        for row in rows
        if row["surface"] in CANONICAL_ACTIVE_SIDE_LANE_REVIEW_BLOCKERS
        and row.get("manifest_outcome") in {"post-v1", "excluded"}
    ]
    active_side_lane_review_release_statement_post_v1_or_excluded = [
        row["surface"]
        for row in rows
        if row["surface"] in CANONICAL_ACTIVE_SIDE_LANE_REVIEW_BLOCKERS
        and row.get("release_statement_scoped_non_complete_bookkeeping") is True
    ]
    active_side_lane_review_promoted_for_claim = [
        row["surface"]
        for row in rows
        if row["surface"] in CANONICAL_ACTIVE_SIDE_LANE_REVIEW_BLOCKERS
        and row.get("counts_toward_complete_sdk_claim") is True
    ]
    active_side_lane_review_remaining_for_claim = [
        row["surface"]
        for row in rows
        if row["surface"] in CANONICAL_ACTIVE_SIDE_LANE_REVIEW_BLOCKERS
        and row.get("unresolved_for_complete_sdk_claim") is True
    ]
    return {
        "total": len(rows),
        "complete_sdk_blocker_total": len(rows),
        "complete_sdk_blockers_promoted_for_claim_count": len(
            completion_blockers_promoted_for_claim
        ),
        "complete_sdk_blockers_remaining_for_claim_count": len(
            completion_blockers_remaining_for_claim
        ),
        "p0_dependency_chain_total": len(p0_dependency_chain_surfaces),
        "p0_dependency_chain_promoted_for_claim_count": len(
            p0_dependency_chain_promoted_for_claim
        ),
        "p0_dependency_chain_remaining_for_claim_count": len(dependency_chain_remaining),
        "manifest_outcome_missing_count": len(manifest_outcome_missing),
        "release_statement_outcome_missing_count": len(release_statement_outcome_missing),
        "p0_scoped_non_complete_outcome_count": len(p0_scoped_non_complete_outcomes),
        "manifest_promoted_but_non_counting_count": len(manifest_promoted_but_non_counting),
        "p0_manifest_promoted_non_counting_count": len(p0_manifest_promoted_non_counting),
        "release_statement_scoped_non_complete_bookkeeping_count": len(
            release_statement_scoped_non_complete_bookkeeping
        ),
        "release_statement_scoped_non_complete_claim_progress_contribution": 0,
        "p0_release_statement_scoped_non_complete_outcome_count": (
            len(p0_release_statement_scoped_non_complete_outcomes)
        ),
        "non_p0_manifest_post_v1_or_excluded_outcome_count": (
            len(non_p0_manifest_post_v1_or_excluded_outcomes)
        ),
        "non_p0_release_statement_post_v1_or_excluded_outcome_count": (
            len(non_p0_release_statement_post_v1_or_excluded_outcomes)
        ),
        "active_side_lane_review_blocker_count": len(active_side_lane_review_blockers),
        "active_side_lane_review_promoted_for_claim_count": len(
            active_side_lane_review_promoted_for_claim
        ),
        "active_side_lane_review_remaining_for_claim_count": len(
            active_side_lane_review_remaining_for_claim
        ),
        "active_side_lane_review_manifest_post_v1_or_excluded_count": len(
            active_side_lane_review_manifest_post_v1_or_excluded
        ),
        "active_side_lane_review_release_statement_post_v1_or_excluded_count": len(
            active_side_lane_review_release_statement_post_v1_or_excluded
        ),
        "route_gate_non_counting_surface_count": len(route_gate_non_counting_surfaces),
        "route_gate_non_counting_blocker_count": len(route_gate_non_counting_blockers),
        "complete_sdk_blockers_promoted_for_claim": completion_blockers_promoted_for_claim,
        "complete_sdk_blockers_remaining_for_claim": completion_blockers_remaining_for_claim,
        "p0_dependency_chain_surfaces": p0_dependency_chain_surfaces,
        "p0_dependency_chain_promoted_for_claim": p0_dependency_chain_promoted_for_claim,
        "manifest_outcome_missing": manifest_outcome_missing,
        "release_statement_outcome_missing": release_statement_outcome_missing,
        "p0_scoped_non_complete_outcomes": p0_scoped_non_complete_outcomes,
        "manifest_promoted_but_non_counting": manifest_promoted_but_non_counting,
        "completion_blockers_with_manifest_promoted_non_counting": manifest_promoted_but_non_counting,
        "p0_manifest_promoted_non_counting": p0_manifest_promoted_non_counting,
        "release_statement_scoped_non_complete_bookkeeping": (
            release_statement_scoped_non_complete_bookkeeping
        ),
        "release_statement_scoped_non_complete_counts_toward_complete_sdk_claim": False,
        "release_statement_scoped_non_complete_claim_progress_contribution": 0,
        "p0_release_statement_scoped_non_complete_outcomes": (
            p0_release_statement_scoped_non_complete_outcomes
        ),
        "non_p0_manifest_post_v1_or_excluded_outcomes": (
            non_p0_manifest_post_v1_or_excluded_outcomes
        ),
        "non_p0_release_statement_post_v1_or_excluded_outcomes": (
            non_p0_release_statement_post_v1_or_excluded_outcomes
        ),
        "active_side_lane_review_blockers": active_side_lane_review_blockers,
        "active_side_lane_review_manifest_post_v1_or_excluded": (
            active_side_lane_review_manifest_post_v1_or_excluded
        ),
        "active_side_lane_review_release_statement_post_v1_or_excluded": (
            active_side_lane_review_release_statement_post_v1_or_excluded
        ),
        "active_side_lane_review_promoted_for_claim": active_side_lane_review_promoted_for_claim,
        "active_side_lane_review_remaining_for_claim": active_side_lane_review_remaining_for_claim,
        "active_side_lane_review_non_claim": (
            "Active side-lane review bookkeeping is non-claim accounting; post-v1/excluded "
            "or release-statement records do not promote lifecycle ops, player services, "
            "operator ingress/storage, or gameplay tick callbacks into the complete SDK."
        ),
        "route_gate_non_counting_surfaces": route_gate_non_counting_surfaces,
        "route_gate_non_counting_blockers": route_gate_non_counting_blockers,
        "route_gate_current_blockers": route_gate_current_blockers,
        "p0_scoped_non_complete_note": (
            "P0 dependency-chain excluded/post-v1 outcomes are scoped non-complete "
            "bookkeeping only; they do not satisfy complete/full/production SDK claims."
        ),
        "dependency_chain_remaining": dependency_chain_remaining,
        "dependency_chain_remaining_count": len(dependency_chain_remaining),
        "non_claim": "This summary ranks accounting gaps only; stable SDK claim approval still requires the full checker to pass.",
    }


def categorized_v1_report_sections(
    *,
    manifest: dict[str, Any],
    blockers: list[str],
    promoted_surfaces: set[str],
    experimental_surfaces: set[str],
    release_statement_text: str | None,
    release_statement_missing_blockers: list[str],
    release_statement_missing_contracts: list[str],
    release_statement_missing_experimental_outcomes: list[str],
    release_statement_duplicate_records: list[str],
    release_statement_forbidden_claims: list[str],
    completion_blockers_with_post_v1_or_excluded_outcome: list[str],
    completion_blockers_with_release_statement_post_v1_or_excluded_outcome: list[str],
    minimum_promoted_demand_family_gaps: list[str],
    minimum_promoted_demand_family_equivalents: dict[str, str],
    blocker_outcome_summary: dict[str, Any],
    unresolved_completion_blockers: list[str],
    unresolved_experimental: list[str],
    unresolved_planning_surfaces: list[str],
    promoted_without_evidence: list[str],
    promoted_missing_required_evidence_terms: dict[str, list[str]],
    promoted_dependency_failures: dict[str, list[str]],
    blocked_contract_header_symbols: dict[str, Any],
    stable_claim_allowed: bool,
    manifest_stable_claim_allowed: bool,
) -> dict[str, Any]:
    """Group the JSON report by release-accounting concern without changing gates."""

    installed_shape = manifest.get("installed_sdk_package_shape")
    package_shape_status = None
    if isinstance(installed_shape, dict):
        package_shape_status = installed_shape.get("status")

    manifest_outcome_missing = blocker_outcome_summary.get("manifest_outcome_missing", [])
    dependency_chain_remaining = blocker_outcome_summary.get("dependency_chain_remaining", [])
    route_gate_current_blockers = blocker_outcome_summary.get("route_gate_current_blockers", [])
    if (
        dependency_chain_remaining
        and isinstance(route_gate_current_blockers, list)
        and "identity_public_contract_gate_missing" in route_gate_current_blockers
    ):
        recommended_next_action = (
            "review the player identity public contract before any public identity, "
            "permissions/admin, command response, or commands/replies ABI; approved copied "
            "runtime principal lifecycle evidence is only a contract-review input"
        )
    elif dependency_chain_remaining:
        recommended_next_action = (
            "resolve the player identity/principal critical path first: produce approved "
            "copied runtime principal lifecycle evidence before any public identity, "
            "permissions/admin, command response, or commands/replies ABI"
        )
    elif manifest_outcome_missing:
        recommended_next_action = (
            "choose reviewed v1 outcomes for planning blockers before counting them "
            "toward a complete SDK release statement"
        )
    elif release_statement_missing_blockers:
        recommended_next_action = (
            "add reviewed scoped release-statement records for manifest post-v1 or "
            "excluded blockers without treating bookkeeping as promoted SDK support"
        )
    else:
        recommended_next_action = (
            "promote remaining demand-family surfaces with evidence or explicitly keep "
            "them out of the complete SDK claim"
        )

    runtime_blocker_codes = [
        blocker
        for blocker in blockers
        if blocker
        in {
            "blocked_public_contract_header_symbols_detected",
            "canonical_surface_id_missing",
            "canonical_v1_completion_blocker_missing",
            "debug_only_surface_promoted",
            "non_promoted_surface_has_public_abi",
            "non_promoted_surface_has_public_contract",
            "planning_surfaces_unresolved_for_v1_claim",
            "promoted_experimental_surfaces_unresolved",
            "promoted_surface_dependency_unresolved",
            "promoted_surface_evidence_missing",
            "promoted_surface_required_evidence_terms_missing",
            "required_surface_dependency_declaration_missing",
            "surface_id_missing",
            "top_level_planning_surfaces_unresolved_for_v1_claim",
            "v1_dependency_sequence_mismatch",
            "v1_required_dependency_chain_missing_from_completion_blockers",
            "v1_sdk_completion_blockers_unresolved",
        }
    ]

    return {
        "no_live_progress": {
            "live_server_required_for_this_report": False,
            "promoted_foundation_surfaces": sorted(promoted_surfaces),
            "experimental_copied_data_seeds": sorted(experimental_surfaces),
            "package_shape_evidence_status": package_shape_status,
            "stable_claim_allowed": stable_claim_allowed,
            "stable_release_contract_claim_allowed": manifest_stable_claim_allowed,
            "non_claim": (
                "These are no-live inventory/package-shape progress signals only; they do not "
                "satisfy runtime gameplay promotion evidence or authorize complete/full/"
                "production/stable SDK wording."
            ),
        },
        "release_statement_bookkeeping": {
            "release_statement_present": release_statement_text is not None,
            "manifest_post_v1_or_excluded_outcomes": (
                completion_blockers_with_post_v1_or_excluded_outcome
            ),
            "release_statement_post_v1_or_excluded_outcomes": (
                completion_blockers_with_release_statement_post_v1_or_excluded_outcome
            ),
            "p0_scoped_non_complete_outcomes": blocker_outcome_summary.get(
                "p0_scoped_non_complete_outcomes",
                [],
            ),
            "p0_scoped_non_complete_outcome_count": blocker_outcome_summary.get(
                "p0_scoped_non_complete_outcome_count",
                0,
            ),
            "release_statement_scoped_non_complete_bookkeeping": blocker_outcome_summary.get(
                "release_statement_scoped_non_complete_bookkeeping",
                [],
            ),
            "release_statement_scoped_non_complete_bookkeeping_count": blocker_outcome_summary.get(
                "release_statement_scoped_non_complete_bookkeeping_count",
                0,
            ),
            "p0_release_statement_scoped_non_complete_outcomes": blocker_outcome_summary.get(
                "p0_release_statement_scoped_non_complete_outcomes",
                [],
            ),
            "p0_release_statement_scoped_non_complete_outcome_count": blocker_outcome_summary.get(
                "p0_release_statement_scoped_non_complete_outcome_count",
                0,
            ),
            "non_p0_release_statement_post_v1_or_excluded_outcomes": blocker_outcome_summary.get(
                "non_p0_release_statement_post_v1_or_excluded_outcomes",
                [],
            ),
            "non_p0_release_statement_post_v1_or_excluded_outcome_count": blocker_outcome_summary.get(
                "non_p0_release_statement_post_v1_or_excluded_outcome_count",
                0,
            ),
            "active_side_lane_review_manifest_post_v1_or_excluded": blocker_outcome_summary.get(
                "active_side_lane_review_manifest_post_v1_or_excluded",
                [],
            ),
            "active_side_lane_review_release_statement_post_v1_or_excluded": blocker_outcome_summary.get(
                "active_side_lane_review_release_statement_post_v1_or_excluded",
                [],
            ),
            "active_side_lane_review_non_claim": blocker_outcome_summary.get(
                "active_side_lane_review_non_claim",
            ),
            "missing_blocker_outcomes": sorted(set(release_statement_missing_blockers)),
            "missing_exclusion_contracts": sorted(set(release_statement_missing_contracts)),
            "missing_experimental_outcomes": sorted(
                set(release_statement_missing_experimental_outcomes)
            ),
            "duplicate_or_mixed_records": sorted(set(release_statement_duplicate_records)),
            "forbidden_broad_claims": release_statement_forbidden_claims,
            "non_claim": (
                "Release-statement rows record reviewed promoted/excluded/post-v1 outcomes; "
                "bookkeeping alone never approves the stable SDK claim."
            ),
        },
        "promoted_demand_gaps": {
            "minimum_promoted_demand_family_count": len(
                CANONICAL_COMPLETE_SDK_MINIMUM_PROMOTED_DEMAND_FAMILIES
            ),
            "minimum_promoted_demand_family_gaps": minimum_promoted_demand_family_gaps,
            "minimum_promoted_demand_family_equivalents": (
                minimum_promoted_demand_family_equivalents
            ),
            "all_minimum_demand_families_promoted_or_equivalent": not minimum_promoted_demand_family_gaps,
            "claim_blocker_active": "complete_sdk_claim_requires_promoted_demand_families"
            in blockers,
            "non_claim": (
                "Excluded/post-v1 outcomes do not satisfy promoted-demand requirements; "
                "demand families need promoted surfaces or explicit promoted equivalents."
            ),
        },
        "active_side_lane_review": {
            "blockers": blocker_outcome_summary.get("active_side_lane_review_blockers", []),
            "promoted_for_claim": blocker_outcome_summary.get(
                "active_side_lane_review_promoted_for_claim",
                [],
            ),
            "promoted_for_claim_count": blocker_outcome_summary.get(
                "active_side_lane_review_promoted_for_claim_count",
                0,
            ),
            "remaining_for_claim": blocker_outcome_summary.get(
                "active_side_lane_review_remaining_for_claim",
                [],
            ),
            "remaining_for_claim_count": blocker_outcome_summary.get(
                "active_side_lane_review_remaining_for_claim_count",
                0,
            ),
            "manifest_post_v1_or_excluded": blocker_outcome_summary.get(
                "active_side_lane_review_manifest_post_v1_or_excluded",
                [],
            ),
            "release_statement_post_v1_or_excluded": blocker_outcome_summary.get(
                "active_side_lane_review_release_statement_post_v1_or_excluded",
                [],
            ),
            "stable_claim_allowed": stable_claim_allowed,
            "non_claim": blocker_outcome_summary.get("active_side_lane_review_non_claim"),
        },
        "runtime_required_blockers": {
            "blocker_codes": sorted(set(runtime_blocker_codes)),
            "route_gate_current_blockers": blocker_outcome_summary.get(
                "route_gate_current_blockers",
                [],
            ),
            "dependency_chain_remaining": blocker_outcome_summary.get(
                "dependency_chain_remaining",
                [],
            ),
            "p0_scoped_non_complete_outcomes": blocker_outcome_summary.get(
                "p0_scoped_non_complete_outcomes",
                [],
            ),
            "p0_scoped_non_complete_outcome_count": blocker_outcome_summary.get(
                "p0_scoped_non_complete_outcome_count",
                0,
            ),
            "manifest_promoted_but_non_counting": blocker_outcome_summary.get(
                "manifest_promoted_but_non_counting",
                [],
            ),
            "manifest_promoted_but_non_counting_count": blocker_outcome_summary.get(
                "manifest_promoted_but_non_counting_count",
                0,
            ),
            "p0_manifest_promoted_non_counting": blocker_outcome_summary.get(
                "p0_manifest_promoted_non_counting",
                [],
            ),
            "p0_manifest_promoted_non_counting_count": blocker_outcome_summary.get(
                "p0_manifest_promoted_non_counting_count",
                0,
            ),
            "route_gate_non_counting_surfaces": blocker_outcome_summary.get(
                "route_gate_non_counting_surfaces",
                [],
            ),
            "route_gate_non_counting_surface_count": blocker_outcome_summary.get(
                "route_gate_non_counting_surface_count",
                0,
            ),
            "route_gate_non_counting_blockers": blocker_outcome_summary.get(
                "route_gate_non_counting_blockers",
                [],
            ),
            "route_gate_non_counting_blocker_count": blocker_outcome_summary.get(
                "route_gate_non_counting_blocker_count",
                0,
            ),
            "manifest_outcome_missing": blocker_outcome_summary.get(
                "manifest_outcome_missing",
                [],
            ),
            "unresolved_completion_blockers": sorted(set(unresolved_completion_blockers)),
            "unresolved_experimental_surfaces": sorted(set(unresolved_experimental)),
            "unresolved_planning_surfaces": sorted(set(unresolved_planning_surfaces)),
            "promoted_surfaces_without_evidence": sorted(set(promoted_without_evidence)),
            "promoted_surfaces_missing_required_evidence_terms": {
                surface_id: sorted(set(terms))
                for surface_id, terms in sorted(promoted_missing_required_evidence_terms.items())
            },
            "promoted_surfaces_with_unresolved_dependencies": {
                surface_id: sorted(set(dependencies))
                for surface_id, dependencies in sorted(promoted_dependency_failures.items())
            },
            "blocked_public_contract_header_symbol_surfaces": sorted(
                {
                    drift.get("surface")
                    for drift in blocked_contract_header_symbols.values()
                    if isinstance(drift, dict) and isinstance(drift.get("surface"), str)
                }
            ),
            "non_claim": (
                "These are SDK/runtime promotion blockers and header-drift guardrails; they "
                "do not allow stable SDK wording before promotion evidence or reviewed "
                "non-promoted outcomes."
            ),
        },
        "next_v1_work": {
            "critical_path": list(dependency_chain_remaining),
            "route_gate_current_blockers": blocker_outcome_summary.get(
                "route_gate_current_blockers",
                [],
            ),
            "release_statement_bookkeeping_required": sorted(set(release_statement_missing_blockers)),
            "manifest_promoted_but_non_counting": blocker_outcome_summary.get(
                "manifest_promoted_but_non_counting",
                [],
            ),
            "p0_manifest_promoted_non_counting": blocker_outcome_summary.get(
                "p0_manifest_promoted_non_counting",
                [],
            ),
            "release_statement_scoped_non_complete_bookkeeping": blocker_outcome_summary.get(
                "release_statement_scoped_non_complete_bookkeeping",
                [],
            ),
            "p0_release_statement_scoped_non_complete_outcomes": blocker_outcome_summary.get(
                "p0_release_statement_scoped_non_complete_outcomes",
                [],
            ),
            "route_gate_non_counting_surfaces": blocker_outcome_summary.get(
                "route_gate_non_counting_surfaces",
                [],
            ),
            "route_gate_non_counting_blockers": blocker_outcome_summary.get(
                "route_gate_non_counting_blockers",
                [],
            ),
            "product_decision_required": list(manifest_outcome_missing),
            "runtime_or_promotion_required": sorted(
                set(unresolved_completion_blockers)
                | set(dependency_chain_remaining)
                | set(minimum_promoted_demand_family_gaps)
            ),
            "experimental_outcome_required": sorted(set(unresolved_experimental)),
            "recommended_next_action": recommended_next_action,
            "non_claim": (
                "This section prioritizes work only; it does not change readiness, "
                "promote ABI, or authorize complete/full/production/stable SDK wording."
            ),
        },
    }


def build_report(
    manifest_path: Path,
    release_statement_path: Path | None = None,
    public_header_path: Path = DEFAULT_PUBLIC_HEADER,
    contract_decisions_dir: Path = DEFAULT_CONTRACT_DECISIONS_DIR,
    command_permission_route_gate_path: Path = DEFAULT_COMMAND_PERMISSION_ROUTE_GATE,
    inventory_copied_signals_stability_path: Path = DEFAULT_INVENTORY_COPIED_SIGNALS_STABILITY,
    object_identity_resource_handle_readiness_path: Path = DEFAULT_OBJECT_IDENTITY_RESOURCE_HANDLE_READINESS,
    mission_transfer_dino_tribe_outcome_accounting_path: Path = DEFAULT_MISSION_TRANSFER_DINO_TRIBE_OUTCOME_ACCOUNTING,
    structure_census_readiness_path: Path = DEFAULT_STRUCTURE_CENSUS_READINESS,
    structure_build_policy_offline_intake_path: Path = DEFAULT_STRUCTURE_BUILD_POLICY_OFFLINE_INTAKE,
) -> dict[str, Any]:
    manifest, blockers = load_manifest(manifest_path)
    command_permission_route_gate, route_gate_blockers = run_command_permission_route_gate(
        command_permission_route_gate_path,
        manifest_path,
        public_header_path,
    )
    blockers.extend(route_gate_blockers)
    inventory_copied_signals_stability, inventory_stability_blockers = (
        run_inventory_copied_signals_stability(inventory_copied_signals_stability_path)
    )
    blockers.extend(inventory_stability_blockers)
    object_identity_resource_handle_readiness, resource_handle_readiness_blockers = (
        run_object_identity_resource_handle_readiness(
            object_identity_resource_handle_readiness_path,
            manifest_path,
            public_header_path,
            contract_decisions_dir,
        )
    )
    blockers.extend(resource_handle_readiness_blockers)
    mission_transfer_dino_tribe_outcome_accounting, mission_transfer_blockers = (
        run_mission_transfer_dino_tribe_outcome_accounting(
            mission_transfer_dino_tribe_outcome_accounting_path,
            manifest_path,
            mission_transfer_dino_tribe_release_statement_path(release_statement_path),
        )
    )
    blockers.extend(mission_transfer_blockers)
    structure_census_readiness, structure_census_blockers = run_structure_census_readiness(
        structure_census_readiness_path
    )
    blockers.extend(structure_census_blockers)
    structure_build_policy_offline_intake, structure_build_policy_blockers = (
        run_structure_build_policy_offline_intake(structure_build_policy_offline_intake_path)
    )
    blockers.extend(structure_build_policy_blockers)
    release_statement_text, release_statement_blockers = load_release_statement(release_statement_path)
    blockers.extend(release_statement_blockers)
    blocked_contract_header_symbols, contract_symbol_blockers = blocked_contract_public_header_symbol_drift(
        public_header_path,
        contract_decisions_dir,
    )
    blockers.extend(contract_symbol_blockers)
    missing_required_contract_decisions = missing_required_contract_decision_manifests(contract_decisions_dir)
    if missing_required_contract_decisions:
        blockers.append("required_public_contract_decision_manifest_missing")
    if manifest is None:
        return {
            "schema": "obelisk.public-sdk-v1-completion-check.v1",
            "status": "blocked",
            "ready": False,
            "manifest": str(manifest_path),
            "release_statement": str(release_statement_path) if release_statement_path else None,
            "public_header": str(public_header_path),
            "contract_decisions_dir": str(contract_decisions_dir),
            "command_permission_route_gate": command_permission_route_gate,
            "inventory_copied_signals_stability": inventory_copied_signals_stability,
            "object_identity_resource_handle_readiness": object_identity_resource_handle_readiness,
            "mission_transfer_dino_tribe_outcome_accounting": mission_transfer_dino_tribe_outcome_accounting,
            "structure_census_readiness": structure_census_readiness,
            "structure_build_policy_offline_intake": structure_build_policy_offline_intake,
            "blocked_public_contract_header_symbols": blocked_contract_header_symbols,
            "missing_required_public_contract_decision_manifests": missing_required_contract_decisions,
            "blockers": blockers,
        }

    surfaces = manifest.get("surfaces")
    surface_rows = surfaces if isinstance(surfaces, list) else []
    seen_surface_ids: set[str] = set()
    duplicate_surface_ids: list[str] = []
    for surface in surface_rows:
        if not isinstance(surface, dict) or not isinstance(surface.get("id"), str):
            continue
        surface_id = surface["id"]
        if surface_id in seen_surface_ids:
            duplicate_surface_ids.append(surface_id)
        seen_surface_ids.add(surface_id)
    surfaces_by_id = {
        surface.get("id"): surface
        for surface in surface_rows
        if isinstance(surface, dict) and isinstance(surface.get("id"), str)
    }
    if mission_transfer_dino_tribe_outcome_accounting.get("accounting_route") == "per_leaf_promoted":
        mission_surface = surfaces_by_id.get("obelisk.mission_transfer_dino_tribe.v1")
        mission_manifest_leaf_evidence_verified = (
            isinstance(mission_surface, dict)
            and surface_has_promotion_evidence(mission_surface)
        )
        mission_transfer_dino_tribe_outcome_accounting[
            "manifest_leaf_promotion_evidence_verified"
        ] = mission_manifest_leaf_evidence_verified
        if not mission_manifest_leaf_evidence_verified:
            blockers.append("mission_transfer_dino_tribe_per_leaf_promotion_evidence_unverified")
    decision_backed_surface_ids = public_contract_decision_surfaces_for_header(
        public_header_path,
        contract_decisions_dir,
    )
    manifest_contract_header_symbols, manifest_symbol_blockers = manifest_public_header_symbol_drift(
        public_header_path,
        manifest_path,
        surfaces_by_id,
        decision_backed_surface_ids,
    )
    blocked_contract_header_symbols.update(manifest_contract_header_symbols)
    blockers.extend(manifest_symbol_blockers)

    if manifest.get("schema") != "obelisk.public-sdk-surfaces.v1":
        blockers.append("schema_mismatch")
    if manifest.get("sdk_version") != "v1.0":
        blockers.append("sdk_version_not_v1")
    if manifest.get("release_claim") != CANONICAL_MANIFEST_RELEASE_CLAIM:
        blockers.append("release_claim_scope_drift")

    stable_contract = manifest.get("stable_release_contract")
    if not isinstance(stable_contract, dict):
        blockers.append("stable_release_contract_missing")
        manifest_stable_claim_allowed = False
        missing_stable_claim_requires = list(CANONICAL_STABLE_RELEASE_CLAIM_REQUIRES)
        missing_stable_not_sufficient = list(CANONICAL_STABLE_RELEASE_NOT_SUFFICIENT)
    else:
        manifest_stable_claim_allowed = stable_contract.get("claim_allowed") is True
        if not manifest_stable_claim_allowed:
            blockers.append("stable_release_contract_claim_not_allowed")
        stable_claim_requires = set(as_string_list(stable_contract.get("claim_requires")))
        missing_stable_claim_requires = [
            requirement
            for requirement in CANONICAL_STABLE_RELEASE_CLAIM_REQUIRES
            if requirement not in stable_claim_requires
        ]
        stable_not_sufficient = set(as_string_list(stable_contract.get("not_sufficient")))
        missing_stable_not_sufficient = [
            item
            for item in CANONICAL_STABLE_RELEASE_NOT_SUFFICIENT
            if item not in stable_not_sufficient
        ]
    if missing_stable_claim_requires:
        blockers.append("stable_release_contract_claim_requires_incomplete")
    if missing_stable_not_sufficient:
        blockers.append("stable_release_contract_not_sufficient_incomplete")

    if manifest.get("v1_completion_required") is not True:
        blockers.append("v1_completion_required_false")

    installed_sdk_package_shape_drift = installed_sdk_package_shape_guardrail_drift(manifest)
    if installed_sdk_package_shape_drift:
        blockers.append("installed_sdk_package_shape_guardrail_incomplete")

    minimum_promoted_demand_family_gaps, minimum_promoted_demand_family_equivalents = (
        complete_sdk_minimum_promoted_demand_family_gaps(
            surfaces_by_id,
            stable_contract if isinstance(stable_contract, dict) else None,
        )
    )
    missing_dependency_declarations = missing_required_dependency_declarations(surfaces_by_id)
    dependency_sequence_mismatches = v1_dependency_sequence_mismatches(manifest, surfaces_by_id)
    required_dependency_chain = as_string_list(manifest.get("v1_required_dependency_chain"))

    promoted_surfaces = set(as_string_list(manifest.get("promoted_surfaces")))
    experimental_surfaces = set(as_string_list(manifest.get("experimental_surfaces")))
    planning_surfaces = set(as_string_list(manifest.get("planning_surfaces")))
    status_experimental_surfaces = {
        surface_id
        for surface_id, surface in surfaces_by_id.items()
        if surface.get("status") == "promoted-experimental-only"
    }
    status_planning_surfaces = {
        surface_id
        for surface_id, surface in surfaces_by_id.items()
        if surface.get("status") == "planning"
    }
    completion_blockers = as_string_list(manifest.get("v1_sdk_completion_blockers"))
    duplicate_completion_blockers = sorted(
        surface_id
        for surface_id, count in Counter(completion_blockers).items()
        if count > 1
    )
    unique_completion_blockers = list(dict.fromkeys(completion_blockers))
    completion_blocker_set = set(unique_completion_blockers)
    post_v1_or_excluded = set(as_string_list(manifest.get("post_v1_or_excluded_surfaces")))
    status_post_v1_or_excluded_surfaces = {
        surface_id
        for surface_id, surface in surfaces_by_id.items()
        if surface.get("status") in {"post-v1", "excluded"}
    }
    debug_only_surfaces = set(as_string_list(manifest.get("debug_only_surfaces")))
    canonical_debug_only_present = CANONICAL_DEBUG_ONLY_SURFACE_IDS & set(surfaces_by_id)

    unresolved_experimental: list[str] = []
    unresolved_completion_blockers: list[str] = []
    unresolved_planning_surfaces: list[str] = []
    missing_surfaces: list[str] = []
    missing_canonical_surfaces = sorted(CANONICAL_SURFACE_IDS - set(surfaces_by_id))
    missing_canonical_completion_blockers = sorted(CANONICAL_V1_COMPLETION_BLOCKERS - completion_blocker_set)
    missing_dependency_chain_completion_blockers = [
        surface_id
        for surface_id in CANONICAL_V1_REQUIRED_DEPENDENCY_CHAIN
        if surface_id not in completion_blocker_set
    ]
    promoted_without_contract: list[str] = []
    promoted_without_evidence: list[str] = []
    non_promoted_with_contract: list[str] = []
    promoted_list_mismatches: list[str] = []
    experimental_list_mismatches: list[str] = []
    planning_list_mismatches: list[str] = []
    post_v1_or_excluded_list_mismatches: list[str] = []
    release_statement_missing_blockers: list[str] = []
    release_statement_missing_contracts: list[str] = []
    release_statement_missing_experimental_outcomes: list[str] = []
    release_statement_duplicate_records: list[str] = []
    release_statement_forbidden_claims: list[str] = []
    missing_completion_blocker_exclusion_contracts: list[str] = []
    debug_only_promoted: list[str] = []
    promoted_dependency_failures: dict[str, list[str]] = {}
    promoted_missing_required_evidence_terms: dict[str, list[str]] = {}
    promoted_missing_structured_evidence: dict[str, list[str]] = {}
    non_promoted_with_public_abi: list[str] = []
    player_identity_request_pack_non_evidence_missing = (
        player_identity_request_pack_non_evidence_terms_missing(surfaces_by_id)
    )
    unpromoted_required_dependency_chain = [
        surface_id
        for surface_id in CANONICAL_V1_REQUIRED_DEPENDENCY_CHAIN
        if surfaces_by_id.get(surface_id, {}).get("status") != "promoted"
    ]

    if manifest_stable_claim_allowed and manifest.get("v1_completion_required") is True and release_statement_text is None:
        blockers.append("release_statement_required_for_v1_completion")

    if not canonical_debug_only_present.issubset(debug_only_surfaces):
        blockers.append("debug_only_surface_list_missing_canonical_ids")

    if experimental_surfaces != status_experimental_surfaces:
        experimental_list_mismatches = sorted(experimental_surfaces ^ status_experimental_surfaces)
    if planning_surfaces != status_planning_surfaces:
        planning_list_mismatches = sorted(planning_surfaces ^ status_planning_surfaces)
    if post_v1_or_excluded != status_post_v1_or_excluded_surfaces:
        post_v1_or_excluded_list_mismatches = sorted(
            post_v1_or_excluded ^ status_post_v1_or_excluded_surfaces
        )

    experimental_outcome_surface_ids = (
        experimental_surfaces
        | status_experimental_surfaces
        | (CANONICAL_EXPERIMENTAL_SURFACE_IDS & set(surfaces_by_id))
    )
    for surface_id in sorted(experimental_outcome_surface_ids):
        surface = surfaces_by_id.get(surface_id)
        if not surface:
            missing_surfaces.append(surface_id)
            unresolved_experimental.append(surface_id)
            continue
        status = surface.get("status")
        if status == "promoted":
            if release_statement_text is None:
                release_statement_missing_experimental_outcomes.append(surface_id)
            elif release_statement_duplicate_or_mixed_records(release_statement_text, surface_id):
                release_statement_duplicate_records.append(surface_id)
            elif not release_statement_satisfies_experimental_outcome(release_statement_text, surface_id, status):
                release_statement_missing_experimental_outcomes.append(surface_id)
            continue
        if status in {"post-v1", "excluded"} and surface_id in post_v1_or_excluded:
            if release_statement_text is None:
                release_statement_missing_experimental_outcomes.append(surface_id)
            elif release_statement_duplicate_or_mixed_records(release_statement_text, surface_id):
                release_statement_duplicate_records.append(surface_id)
            elif not release_statement_satisfies_experimental_outcome(release_statement_text, surface_id, status):
                release_statement_missing_experimental_outcomes.append(surface_id)
            continue
        unresolved_experimental.append(surface_id)

    for surface_id in completion_blockers:
        surface = surfaces_by_id.get(surface_id)
        if not surface:
            missing_surfaces.append(surface_id)
            unresolved_completion_blockers.append(surface_id)
            continue
        status = surface.get("status")
        if status == "promoted":
            if not surface_has_promotion_evidence(surface):
                promoted_without_evidence.append(surface_id)
            if release_statement_text is None:
                release_statement_missing_blockers.append(surface_id)
            elif release_statement_duplicate_or_mixed_records(release_statement_text, surface_id):
                release_statement_duplicate_records.append(surface_id)
            elif not release_statement_satisfies_promoted_outcome(
                release_statement_text,
                surface_id,
            ):
                release_statement_missing_blockers.append(surface_id)
            continue
        if status in {"post-v1", "excluded"} and surface_id in post_v1_or_excluded:
            allowed_outcomes = required_release_statement_outcomes(surface)
            if surface_id in CANONICAL_V1_COMPLETION_BLOCKERS:
                contract = surface.get("v1_decision_contract")
                if not isinstance(contract, dict) or not as_string_list(contract.get("exclusion_requires")):
                    missing_completion_blocker_exclusion_contracts.append(surface_id)
                    continue
                if status not in allowed_outcomes:
                    release_statement_missing_contracts.append(surface_id)
                    continue
            if release_statement_text is None:
                release_statement_missing_blockers.append(surface_id)
            elif release_statement_duplicate_or_mixed_records(release_statement_text, surface_id):
                release_statement_duplicate_records.append(surface_id)
            elif release_statement_recorded_outcome(release_statement_text, surface_id) != status:
                release_statement_missing_blockers.append(surface_id)
            elif release_statement_recorded_outcome(release_statement_text, surface_id) not in allowed_outcomes:
                release_statement_missing_blockers.append(surface_id)
            elif not release_statement_satisfies_exclusion_contract(release_statement_text, surface):
                release_statement_missing_contracts.append(surface_id)
            continue
        if surface_id in CANONICAL_V1_COMPLETION_BLOCKERS:
            contract = surface.get("v1_decision_contract")
            if not isinstance(contract, dict) or not as_string_list(contract.get("exclusion_requires")):
                missing_completion_blocker_exclusion_contracts.append(surface_id)
        unresolved_completion_blockers.append(surface_id)

    for surface_id, surface in surfaces_by_id.items():
        status = surface.get("status")
        contract = surface.get("public_contract")
        contract_items = contract if isinstance(contract, list) else []
        if surface_id in debug_only_surfaces or surface_id in CANONICAL_DEBUG_ONLY_SURFACE_IDS:
            if status == "promoted" or surface_id in promoted_surfaces:
                debug_only_promoted.append(surface_id)
        if status == "promoted":
            if surface_id not in promoted_surfaces:
                promoted_list_mismatches.append(surface_id)
            if not contract_items:
                promoted_without_contract.append(surface_id)
            if not surface_has_promotion_evidence(surface):
                promoted_without_evidence.append(surface_id)
            missing_required_terms = surface_missing_required_promotion_evidence(surface)
            if missing_required_terms:
                promoted_missing_required_evidence_terms[surface_id] = missing_required_terms
            missing_structured_evidence = surface_missing_structured_promotion_evidence(
                surface,
                manifest_path,
                public_header_path,
            )
            if missing_structured_evidence:
                promoted_missing_structured_evidence[surface_id] = missing_structured_evidence
        elif status == "planning":
            unresolved_planning_surfaces.append(surface_id)
        elif status != "promoted-experimental-only" and contract_items:
            non_promoted_with_contract.append(surface_id)
        if status != "promoted" and surface.get("public_abi") is True:
            non_promoted_with_public_abi.append(surface_id)
        unresolved_dependencies = unresolved_promoted_surface_dependencies(surface, surfaces_by_id)
        if unresolved_dependencies:
            promoted_dependency_failures[surface_id] = unresolved_dependencies

    for surface_id in sorted(promoted_surfaces):
        surface = surfaces_by_id.get(surface_id)
        if not surface:
            missing_surfaces.append(surface_id)
        elif surface.get("status") != "promoted":
            promoted_list_mismatches.append(surface_id)

    missing_surfaces.extend(missing_canonical_surfaces)
    unresolved_completion_blockers.extend(missing_canonical_completion_blockers)

    if missing_surfaces:
        blockers.append("surface_id_missing")
    if duplicate_surface_ids:
        blockers.append("duplicate_surface_id")
    if duplicate_completion_blockers:
        blockers.append("duplicate_v1_sdk_completion_blocker")
    if missing_canonical_surfaces:
        blockers.append("canonical_surface_id_missing")
    if missing_canonical_completion_blockers:
        blockers.append("canonical_v1_completion_blocker_missing")
    if missing_dependency_chain_completion_blockers:
        blockers.append("v1_required_dependency_chain_missing_from_completion_blockers")
    if minimum_promoted_demand_family_gaps:
        blockers.append("complete_sdk_claim_requires_promoted_demand_families")
    if unresolved_experimental:
        blockers.append("promoted_experimental_surfaces_unresolved")
    if unresolved_completion_blockers:
        blockers.append("v1_sdk_completion_blockers_unresolved")
    if unresolved_planning_surfaces:
        blockers.append("planning_surfaces_unresolved_for_v1_claim")
    if planning_surfaces:
        blockers.append("top_level_planning_surfaces_unresolved_for_v1_claim")
    if missing_completion_blocker_exclusion_contracts:
        blockers.append("completion_blocker_exclusion_contract_missing")
    if debug_only_promoted:
        blockers.append("debug_only_surface_promoted")
    if promoted_without_contract:
        blockers.append("promoted_surface_public_contract_missing")
    if promoted_without_evidence:
        blockers.append("promoted_surface_evidence_missing")
    if promoted_missing_required_evidence_terms:
        blockers.append("promoted_surface_required_evidence_terms_missing")
    if promoted_missing_structured_evidence:
        blockers.append("promoted_surface_structured_evidence_missing")
    if promoted_dependency_failures:
        blockers.append("promoted_surface_dependency_unresolved")
    if missing_dependency_declarations:
        blockers.append("required_surface_dependency_declaration_missing")
    if player_identity_request_pack_non_evidence_missing:
        blockers.append("player_identity_request_pack_non_evidence_manifest_terms_missing")
    if dependency_sequence_mismatches:
        blockers.append("v1_dependency_sequence_mismatch")
    if required_dependency_chain != list(CANONICAL_V1_REQUIRED_DEPENDENCY_CHAIN):
        blockers.append("v1_required_dependency_chain_mismatch")
    if unpromoted_required_dependency_chain:
        blockers.append("v1_required_dependency_chain_unpromoted")
    if non_promoted_with_contract:
        blockers.append("non_promoted_surface_has_public_contract")
    if non_promoted_with_public_abi:
        blockers.append("non_promoted_surface_has_public_abi")
    if promoted_list_mismatches:
        blockers.append("promoted_surface_list_mismatch")
    if experimental_list_mismatches:
        blockers.append("experimental_surface_list_mismatch")
    if planning_list_mismatches:
        blockers.append("planning_surface_list_mismatch")
    if post_v1_or_excluded_list_mismatches:
        blockers.append("post_v1_or_excluded_surface_list_mismatch")
    if release_statement_missing_blockers:
        blockers.append("release_statement_missing_non_promoted_blocker_outcomes")
    if release_statement_missing_contracts:
        blockers.append("release_statement_missing_exclusion_contract")
    if release_statement_missing_experimental_outcomes:
        blockers.append("release_statement_missing_experimental_outcomes")
    if release_statement_duplicate_records:
        blockers.append("release_statement_duplicate_or_mixed_surface_records")
    if release_statement_text is not None:
        release_statement_forbidden_claims = release_statement_forbidden_broad_claims(
            release_statement_text
        )
        if release_statement_forbidden_claims:
            blockers.append("release_statement_forbidden_broad_claims")
        if "docs/sdk_v1_compatibility.md" not in release_statement_text.lower():
            blockers.append("release_statement_missing_sdk_compatibility_reference")
        if "docs/public_sdk_surfaces.json" not in release_statement_text.lower():
            blockers.append("release_statement_missing_public_sdk_surfaces_reference")
    if blocked_contract_header_symbols:
        blockers.append("blocked_public_contract_header_symbols_detected")

    completion_blocker_statuses = {
        surface_id: surfaces_by_id.get(surface_id, {}).get("status", "missing")
        for surface_id in unique_completion_blockers
    }
    completion_blockers_with_promoted_outcome = sorted(
        surface_id
        for surface_id, status in completion_blocker_statuses.items()
        if status == "promoted"
    )
    completion_blockers_with_post_v1_or_excluded_outcome = sorted(
        surface_id
        for surface_id, status in completion_blocker_statuses.items()
        if status in {"post-v1", "excluded"}
    )
    completion_blockers_with_release_statement_post_v1_or_excluded_outcome = sorted(
        surface_id
        for surface_id in unique_completion_blockers
        if release_statement_text is not None
        and not release_statement_duplicate_or_mixed_records(release_statement_text, surface_id)
        and release_statement_recorded_outcome(release_statement_text, surface_id)
        in {"post-v1", "excluded"}
        and release_statement_satisfies_exclusion_contract(
            release_statement_text,
            surfaces_by_id.get(surface_id, {}),
        )
    )
    completion_blockers_without_manifest_outcome = sorted(
        surface_id
        for surface_id, status in completion_blocker_statuses.items()
        if status not in {"promoted", "post-v1", "excluded"}
    )
    canonical_completion_blockers = [
        surface_id
        for surface_id in CANONICAL_V1_COMPLETION_BLOCKER_ORDER
        if surface_id in CANONICAL_V1_COMPLETION_BLOCKERS
    ]
    completion_blockers_for_accounting = list(
        dict.fromkeys([*unique_completion_blockers, *canonical_completion_blockers])
    )
    completion_blocker_total = len(completion_blockers_for_accounting)
    blocker_outcome_rows = completion_blocker_outcome_rows(
        completion_blockers_for_accounting,
        surfaces_by_id,
        post_v1_or_excluded,
        release_statement_text,
        command_permission_route_gate,
        manifest_path,
        public_header_path,
    )
    blocker_outcome_summary = completion_blocker_outcome_summary(blocker_outcome_rows)
    release_statement_surface_records_all = release_statement_all_surface_records(
        release_statement_text
    )
    required_scoped_release_statement_outcome_records = (
        scoped_release_statement_required_outcome_records(
            completion_blockers_for_accounting,
            surfaces_by_id,
            post_v1_or_excluded,
        )
    )
    scoped_release_statement_allowed_surface_records = [
        record["surface"] for record in required_scoped_release_statement_outcome_records
    ]
    scoped_release_statement_allowed_surface_record_set = set(
        scoped_release_statement_allowed_surface_records
    )
    scoped_release_statement_unexpected_surface_records = [
        record
        for record in release_statement_surface_records_all
        if record["surface"] not in scoped_release_statement_allowed_surface_record_set
    ]
    p0_scoped_non_complete_outcomes = blocker_outcome_summary["p0_scoped_non_complete_outcomes"]
    manifest_promoted_but_non_counting = blocker_outcome_summary[
        "manifest_promoted_but_non_counting"
    ]
    release_statement_scoped_non_complete_bookkeeping = blocker_outcome_summary[
        "release_statement_scoped_non_complete_bookkeeping"
    ]
    scoped_release_statement_satisfied_outcome_surfaces = [
        surface_id
        for surface_id in scoped_release_statement_allowed_surface_records
        if surface_id in set(release_statement_scoped_non_complete_bookkeeping)
    ]
    scoped_release_statement_missing_required_outcome_surfaces = [
        surface_id
        for surface_id in scoped_release_statement_allowed_surface_records
        if surface_id not in set(release_statement_scoped_non_complete_bookkeeping)
    ]
    route_gate_non_counting_blockers = blocker_outcome_summary[
        "route_gate_non_counting_blockers"
    ]
    completion_blockers_counting_toward_claim = sorted(
        row["surface"]
        for row in blocker_outcome_rows
        if row.get("counts_toward_complete_sdk_claim") is True
    )
    p0_chain_counting_toward_claim = sorted(
        row["surface"]
        for row in blocker_outcome_rows
        if row.get("is_p0_dependency_chain") is True
        and row.get("counts_toward_complete_sdk_claim") is True
    )
    p0_route_gate_locked_promoted_surfaces = sorted(
        row["surface"]
        for row in blocker_outcome_rows
        if row.get("is_p0_dependency_chain") is True
        and row.get("manifest_outcome") == "promoted"
        and row.get("promotion_evidence_satisfied") is True
        and row.get("structured_promotion_evidence_satisfied") is True
        and row.get("route_gate_claim_satisfied") is not True
    )
    required_dependency_chain_unresolved_for_claim = blocker_outcome_summary[
        "dependency_chain_remaining"
    ]
    if p0_scoped_non_complete_outcomes:
        blockers.append("p0_dependency_chain_outcomes_scoped_non_complete_only")
    if p0_route_gate_locked_promoted_surfaces:
        blockers.append("p0_dependency_chain_route_gate_locked")
    ready = not blockers
    stable_claim_allowed = manifest_stable_claim_allowed and ready
    completion_blockers_remaining_for_claim = blocker_outcome_summary[
        "complete_sdk_blockers_remaining_for_claim"
    ]
    p0_chain_remaining_for_claim = blocker_outcome_summary["dependency_chain_remaining"]
    complete_sdk_blocker_claim_accounting = {
        "total": completion_blocker_total,
        "promoted_for_claim_count": len(completion_blockers_counting_toward_claim),
        "remaining_for_claim_count": len(completion_blockers_remaining_for_claim),
        "promoted_for_claim_ratio": (
            f"{len(completion_blockers_counting_toward_claim)}/{completion_blocker_total}"
        ),
        "promoted_for_claim_surfaces": completion_blockers_counting_toward_claim,
        "remaining_for_claim_surfaces": completion_blockers_remaining_for_claim,
        "stable_claim_allowed": stable_claim_allowed,
        "non_claim": (
            "Rows do not count here unless promoted-for-claim evidence is present; "
            "accepted runtime evidence, manifest post-v1/excluded outcomes, and "
            "release-statement bookkeeping never increment this total."
        ),
    }
    p0_dependency_chain_claim_accounting = {
        "total": len(CANONICAL_V1_REQUIRED_DEPENDENCY_CHAIN),
        "promoted_for_claim_count": len(p0_chain_counting_toward_claim),
        "remaining_for_claim_count": len(p0_chain_remaining_for_claim),
        "promoted_for_claim_ratio": (
            f"{len(p0_chain_counting_toward_claim)}/{len(CANONICAL_V1_REQUIRED_DEPENDENCY_CHAIN)}"
        ),
        "promoted_for_claim_surfaces": p0_chain_counting_toward_claim,
        "remaining_for_claim_surfaces": p0_chain_remaining_for_claim,
        "route_gate_current_blockers": blocker_outcome_summary["route_gate_current_blockers"],
        "stable_claim_allowed": stable_claim_allowed,
        "non_claim": (
            "P0 dependency-chain rows must be promoted with evidence and pass the route gate; "
            "accepted runtime evidence only advances the route blocker to identity public "
            "contract review, and excluded/post-v1 outcomes are scoped non-complete "
            "bookkeeping only."
        ),
    }
    current_route_blocker = command_permission_route_gate_current_blocker(
        command_permission_route_gate
    )
    remaining_route_blockers = command_permission_route_gate_remaining_route_blockers(
        command_permission_route_gate
    )
    complete_sdk_claim_progress_ratio = complete_sdk_blocker_claim_accounting[
        "promoted_for_claim_ratio"
    ]
    p0_dependency_chain_claim_progress_ratio = p0_dependency_chain_claim_accounting[
        "promoted_for_claim_ratio"
    ]
    status = "ready" if ready else "blocked"
    summary = normalized_completion_summary(
        status=status,
        ready=ready,
        blockers=blockers,
        current_route_blocker=current_route_blocker,
        remaining_route_blockers=remaining_route_blockers,
        stable_claim_allowed=stable_claim_allowed,
        manifest_stable_claim_allowed=manifest_stable_claim_allowed,
        complete_sdk_blocker_claim_accounting=complete_sdk_blocker_claim_accounting,
        p0_dependency_chain_claim_accounting=p0_dependency_chain_claim_accounting,
    )
    report_sections = categorized_v1_report_sections(
        manifest=manifest,
        blockers=blockers,
        promoted_surfaces=promoted_surfaces,
        experimental_surfaces=experimental_surfaces,
        release_statement_text=release_statement_text,
        release_statement_missing_blockers=release_statement_missing_blockers,
        release_statement_missing_contracts=release_statement_missing_contracts,
        release_statement_missing_experimental_outcomes=release_statement_missing_experimental_outcomes,
        release_statement_duplicate_records=release_statement_duplicate_records,
        release_statement_forbidden_claims=release_statement_forbidden_claims,
        completion_blockers_with_post_v1_or_excluded_outcome=(
            completion_blockers_with_post_v1_or_excluded_outcome
        ),
        completion_blockers_with_release_statement_post_v1_or_excluded_outcome=(
            completion_blockers_with_release_statement_post_v1_or_excluded_outcome
        ),
        minimum_promoted_demand_family_gaps=minimum_promoted_demand_family_gaps,
        minimum_promoted_demand_family_equivalents=minimum_promoted_demand_family_equivalents,
        blocker_outcome_summary=blocker_outcome_summary,
        unresolved_completion_blockers=unresolved_completion_blockers,
        unresolved_experimental=unresolved_experimental,
        unresolved_planning_surfaces=unresolved_planning_surfaces,
        promoted_without_evidence=promoted_without_evidence,
        promoted_missing_required_evidence_terms=promoted_missing_required_evidence_terms,
        promoted_dependency_failures=promoted_dependency_failures,
        blocked_contract_header_symbols=blocked_contract_header_symbols,
        stable_claim_allowed=stable_claim_allowed,
        manifest_stable_claim_allowed=manifest_stable_claim_allowed,
    )
    fastest_next_unblock = fastest_next_sdk_unblock(
        current_route_blocker=current_route_blocker,
        remaining_route_blockers=remaining_route_blockers,
        p0_dependency_chain_claim_accounting=p0_dependency_chain_claim_accounting,
    )
    approved_in_game_evidence = approved_in_game_evidence_completion_status(
        current_route_blocker=current_route_blocker,
        fastest_next_unblock=fastest_next_unblock,
    )
    progress_trace = progress_normalization_trace(
        status=status,
        ready=ready,
        current_route_blocker=current_route_blocker,
        remaining_route_blockers=remaining_route_blockers,
        approved_in_game_evidence=approved_in_game_evidence,
        complete_sdk_blocker_claim_accounting=complete_sdk_blocker_claim_accounting,
        p0_dependency_chain_claim_accounting=p0_dependency_chain_claim_accounting,
        stable_claim_allowed=stable_claim_allowed,
    )
    stable_sdk_remaining_blockers = stable_sdk_remaining_blockers_report(
        status=status,
        ready=ready,
        current_route_blocker=current_route_blocker,
        remaining_route_blockers=remaining_route_blockers,
        complete_sdk_blocker_claim_accounting=complete_sdk_blocker_claim_accounting,
        p0_dependency_chain_claim_accounting=p0_dependency_chain_claim_accounting,
        fastest_next_unblock=fastest_next_unblock,
        approved_in_game_evidence=approved_in_game_evidence,
        stable_claim_allowed=stable_claim_allowed,
    )

    return {
        "schema": "obelisk.public-sdk-v1-completion-check.v1",
        "status": status,
        "ready": ready,
        "summary": summary,
        "progress_normalization_trace": progress_trace,
        "stable_sdk_remaining_blockers": stable_sdk_remaining_blockers,
        "fastest_next_sdk_unblock": fastest_next_unblock,
        "approved_in_game_evidence_ready": approved_in_game_evidence[
            "approved_in_game_evidence_ready"
        ],
        "approved_runtime_evidence_ready": approved_in_game_evidence[
            "approved_runtime_evidence_ready"
        ],
        "next_required_artifact": approved_in_game_evidence["next_required_artifact"],
        "missing_required_artifact": approved_in_game_evidence[
            "missing_required_artifact"
        ],
        "approved_in_game_evidence": approved_in_game_evidence,
        "manifest": str(manifest_path),
        "release_statement": str(release_statement_path) if release_statement_path else None,
        "public_header": str(public_header_path),
        "contract_decisions_dir": str(contract_decisions_dir),
        "command_permission_route_gate": command_permission_route_gate,
        "current_route_blocker": current_route_blocker,
        "remaining_route_blockers": remaining_route_blockers,
        "route_gate_blocked": summary["route_gate_blocked"],
        "promotion_ready": stable_claim_allowed,
        "public_sdk_ready": stable_claim_allowed,
        "public_abi_ready": stable_claim_allowed,
        "runtime_ready": False,
        "complete_sdk_ready": ready,
        "v1_completion_ready": ready,
        "complete_sdk_blockers_promoted_for_claim_count": (
            complete_sdk_blocker_claim_accounting["promoted_for_claim_count"]
        ),
        "complete_sdk_blockers_remaining_for_claim_count": (
            complete_sdk_blocker_claim_accounting["remaining_for_claim_count"]
        ),
        "complete_sdk_blockers_promoted_for_claim_ratio": complete_sdk_claim_progress_ratio,
        "complete_sdk_claim_progress_ratio": complete_sdk_claim_progress_ratio,
        "complete_sdk_progress_ratio": complete_sdk_claim_progress_ratio,
        "p0_chain_promoted_count": p0_dependency_chain_claim_accounting[
            "promoted_for_claim_count"
        ],
        "p0_chain_progress_ratio": p0_dependency_chain_claim_progress_ratio,
        "p0_chain_promoted_ratio": p0_dependency_chain_claim_progress_ratio,
        "p0_dependency_chain_promoted_for_claim_count": (
            p0_dependency_chain_claim_accounting["promoted_for_claim_count"]
        ),
        "p0_dependency_chain_remaining_for_claim_count": (
            p0_dependency_chain_claim_accounting["remaining_for_claim_count"]
        ),
        "p0_dependency_chain_promoted_for_claim_ratio": (
            p0_dependency_chain_claim_progress_ratio
        ),
        "p0_dependency_chain_claim_progress_ratio": (
            p0_dependency_chain_claim_progress_ratio
        ),
        "p0_dependency_chain_progress_ratio": p0_dependency_chain_claim_progress_ratio,
        "inventory_copied_signals_stability": inventory_copied_signals_stability,
        "object_identity_resource_handle_readiness": object_identity_resource_handle_readiness,
        "mission_transfer_dino_tribe_outcome_accounting": mission_transfer_dino_tribe_outcome_accounting,
        "structure_census_readiness": structure_census_readiness,
        "structure_build_policy_offline_intake": structure_build_policy_offline_intake,
        "missing_required_public_contract_decision_manifests": missing_required_contract_decisions,
        "sdk_version": manifest.get("sdk_version"),
        "release_claim": manifest.get("release_claim"),
        "expected_release_claim": CANONICAL_MANIFEST_RELEASE_CLAIM,
        "v1_completion_required": manifest.get("v1_completion_required"),
        "stable_claim_allowed": stable_claim_allowed,
        "stable_release_contract_claim_allowed": manifest_stable_claim_allowed,
        "stable_release_contract_missing_claim_requires": missing_stable_claim_requires,
        "stable_release_contract_missing_not_sufficient": missing_stable_not_sufficient,
        "installed_sdk_package_shape_guardrail_drift": installed_sdk_package_shape_drift,
        "minimum_promoted_demand_families": sorted(CANONICAL_COMPLETE_SDK_MINIMUM_PROMOTED_DEMAND_FAMILIES),
        "minimum_promoted_demand_family_gaps": minimum_promoted_demand_family_gaps,
        "minimum_promoted_demand_family_equivalents": minimum_promoted_demand_family_equivalents,
        "blockers": blockers,
        "unresolved_experimental_surfaces": sorted(set(unresolved_experimental)),
        "unresolved_completion_blockers": sorted(set(unresolved_completion_blockers)),
        "unresolved_planning_surfaces": sorted(set(unresolved_planning_surfaces)),
        "top_level_planning_surfaces": sorted(planning_surfaces),
        "planning_list_mismatches": planning_list_mismatches,
        "post_v1_or_excluded_list_mismatches": post_v1_or_excluded_list_mismatches,
        "debug_only_promoted_surfaces": sorted(set(debug_only_promoted)),
        "missing_completion_blocker_exclusion_contracts": sorted(
            set(missing_completion_blocker_exclusion_contracts)
        ),
        "missing_surfaces": sorted(set(missing_surfaces)),
        "duplicate_surface_ids": sorted(set(duplicate_surface_ids)),
        "duplicate_v1_sdk_completion_blockers": duplicate_completion_blockers,
        "promoted_without_public_contract": sorted(set(promoted_without_contract)),
        "missing_canonical_surfaces": missing_canonical_surfaces,
        "missing_canonical_completion_blockers": missing_canonical_completion_blockers,
        "missing_v1_required_dependency_chain_completion_blockers": (
            missing_dependency_chain_completion_blockers
        ),
        "promoted_surfaces_without_evidence": sorted(set(promoted_without_evidence)),
        "promoted_surfaces_missing_required_evidence_terms": {
            surface_id: sorted(set(terms))
            for surface_id, terms in sorted(promoted_missing_required_evidence_terms.items())
        },
        "promoted_surfaces_missing_structured_evidence": {
            surface_id: sorted(set(items))
            for surface_id, items in sorted(promoted_missing_structured_evidence.items())
        },
        "promoted_surfaces_with_unresolved_dependencies": {
            surface_id: sorted(set(dependencies))
            for surface_id, dependencies in sorted(promoted_dependency_failures.items())
        },
        "surfaces_missing_required_dependency_declarations": {
            surface_id: sorted(set(dependencies))
            for surface_id, dependencies in sorted(missing_dependency_declarations.items())
        },
        "player_identity_request_pack_non_evidence_terms_missing": (
            player_identity_request_pack_non_evidence_missing
        ),
        "v1_dependency_sequence": as_string_list(manifest.get("v1_dependency_sequence")),
        "v1_dependency_sequence_expected": list(CANONICAL_V1_DEPENDENCY_SEQUENCE),
        "v1_dependency_sequence_mismatches": sorted(set(dependency_sequence_mismatches)),
        "v1_required_dependency_chain": required_dependency_chain,
        "v1_required_dependency_chain_expected": list(CANONICAL_V1_REQUIRED_DEPENDENCY_CHAIN),
        "p0_dependency_chain_scoped_non_complete_outcomes": p0_scoped_non_complete_outcomes,
        "p0_dependency_chain_scoped_non_complete_outcome_count": len(p0_scoped_non_complete_outcomes),
        "manifest_promoted_but_non_counting_completion_blockers": manifest_promoted_but_non_counting,
        "manifest_promoted_but_non_counting_completion_blocker_count": len(
            manifest_promoted_but_non_counting
        ),
        "release_statement_scoped_non_complete_bookkeeping_blockers": (
            release_statement_scoped_non_complete_bookkeeping
        ),
        "release_statement_scoped_non_complete_bookkeeping_blocker_count": len(
            release_statement_scoped_non_complete_bookkeeping
        ),
        "route_gate_non_counting_blockers": route_gate_non_counting_blockers,
        "route_gate_non_counting_blocker_count": len(route_gate_non_counting_blockers),
        "p0_dependency_chain_route_gate_locked_surfaces": p0_route_gate_locked_promoted_surfaces,
        "unpromoted_required_dependency_chain": required_dependency_chain_unresolved_for_claim,
        "complete_sdk_blocker_claim_accounting": complete_sdk_blocker_claim_accounting,
        "p0_dependency_chain_claim_accounting": p0_dependency_chain_claim_accounting,
        "promoted_blockers_without_evidence": sorted(set(promoted_without_evidence) & completion_blocker_set),
        "non_promoted_with_public_contract": sorted(set(non_promoted_with_contract)),
        "non_promoted_with_public_abi": sorted(set(non_promoted_with_public_abi)),
        "promoted_list_mismatches": sorted(set(promoted_list_mismatches)),
        "experimental_list_mismatches": sorted(set(experimental_list_mismatches)),
        "release_statement_missing_blocker_outcomes": sorted(set(release_statement_missing_blockers)),
        "release_statement_missing_exclusion_contracts": sorted(set(release_statement_missing_contracts)),
        "release_statement_missing_experimental_outcomes": sorted(set(release_statement_missing_experimental_outcomes)),
        "release_statement_duplicate_or_mixed_records": sorted(set(release_statement_duplicate_records)),
        "release_statement_forbidden_broad_claims": release_statement_forbidden_claims,
        "release_statement_surface_records": release_statement_surface_records_all,
        "scoped_release_statement_required_outcome_records": (
            required_scoped_release_statement_outcome_records
        ),
        "scoped_release_statement_required_outcome_surfaces": (
            scoped_release_statement_allowed_surface_records
        ),
        "scoped_release_statement_required_outcome_count": len(
            scoped_release_statement_allowed_surface_records
        ),
        "scoped_release_statement_satisfied_outcome_surfaces": (
            scoped_release_statement_satisfied_outcome_surfaces
        ),
        "scoped_release_statement_satisfied_outcome_count": len(
            scoped_release_statement_satisfied_outcome_surfaces
        ),
        "scoped_release_statement_missing_required_outcome_surfaces": (
            scoped_release_statement_missing_required_outcome_surfaces
        ),
        "scoped_release_statement_missing_required_outcome_count": len(
            scoped_release_statement_missing_required_outcome_surfaces
        ),
        "scoped_release_statement_counts_toward_complete_sdk_claim": False,
        "scoped_release_statement_claim_progress_contribution": 0,
        "scoped_release_statement_allowed_surface_records": (
            scoped_release_statement_allowed_surface_records
        ),
        "scoped_release_statement_unexpected_surface_records": (
            scoped_release_statement_unexpected_surface_records
        ),
        "blocked_public_contract_header_symbols": blocked_contract_header_symbols,
        "v1_sdk_blocker_outcomes": blocker_outcome_rows,
        "v1_sdk_blocker_outcome_summary": blocker_outcome_summary,
        "v1_sdk_report_sections": report_sections,
        "v1_sdk_progress": {
            "completion_blocker_total": completion_blocker_total,
            "completion_blockers_promoted_count": len(completion_blockers_counting_toward_claim),
            "complete_sdk_blocker_total": completion_blocker_total,
            "complete_sdk_blockers_promoted_for_claim_count": len(
                completion_blockers_counting_toward_claim
            ),
            "complete_sdk_blockers_remaining_for_claim_count": len(
                completion_blockers_remaining_for_claim
            ),
            "complete_sdk_blockers_promoted_for_claim": completion_blockers_counting_toward_claim,
            "complete_sdk_blockers_remaining_for_claim": completion_blockers_remaining_for_claim,
            "complete_sdk_blocker_claim_accounting": complete_sdk_blocker_claim_accounting,
            "complete_sdk_blockers_promoted_for_claim_ratio": complete_sdk_claim_progress_ratio,
            "complete_sdk_claim_progress_ratio": complete_sdk_claim_progress_ratio,
            "complete_sdk_progress_ratio": complete_sdk_claim_progress_ratio,
            "p0_chain_total": len(CANONICAL_V1_REQUIRED_DEPENDENCY_CHAIN),
            "p0_chain_promoted_count": len(p0_chain_counting_toward_claim),
            "p0_chain_progress_ratio": p0_dependency_chain_claim_progress_ratio,
            "p0_chain_promoted_ratio": p0_dependency_chain_claim_progress_ratio,
            "p0_dependency_chain_total": len(CANONICAL_V1_REQUIRED_DEPENDENCY_CHAIN),
            "p0_dependency_chain_promoted_for_claim_count": len(p0_chain_counting_toward_claim),
            "p0_dependency_chain_remaining_for_claim_count": len(p0_chain_remaining_for_claim),
            "p0_dependency_chain_promoted_for_claim": p0_chain_counting_toward_claim,
            "p0_dependency_chain_remaining_for_claim": p0_chain_remaining_for_claim,
            "p0_dependency_chain_claim_accounting": p0_dependency_chain_claim_accounting,
            "p0_dependency_chain_promoted_for_claim_ratio": (
                p0_dependency_chain_claim_progress_ratio
            ),
            "p0_dependency_chain_claim_progress_ratio": (
                p0_dependency_chain_claim_progress_ratio
            ),
            "p0_dependency_chain_progress_ratio": p0_dependency_chain_claim_progress_ratio,
            "p0_chain_scoped_non_complete_outcomes": p0_scoped_non_complete_outcomes,
            "p0_chain_scoped_non_complete_outcome_count": len(p0_scoped_non_complete_outcomes),
            "p0_chain_route_gate_locked_surfaces": p0_route_gate_locked_promoted_surfaces,
            "manifest_promoted_but_non_counting_completion_blockers": (
                manifest_promoted_but_non_counting
            ),
            "manifest_promoted_but_non_counting_completion_blocker_count": len(
                manifest_promoted_but_non_counting
            ),
            "p0_manifest_promoted_non_counting": blocker_outcome_summary[
                "p0_manifest_promoted_non_counting"
            ],
            "p0_manifest_promoted_non_counting_count": blocker_outcome_summary[
                "p0_manifest_promoted_non_counting_count"
            ],
            "release_statement_scoped_non_complete_bookkeeping_blockers": (
                release_statement_scoped_non_complete_bookkeeping
            ),
            "release_statement_scoped_non_complete_bookkeeping_blocker_count": len(
                release_statement_scoped_non_complete_bookkeeping
            ),
            "scoped_release_statement_required_outcome_surfaces": (
                scoped_release_statement_allowed_surface_records
            ),
            "scoped_release_statement_required_outcome_count": len(
                scoped_release_statement_allowed_surface_records
            ),
            "scoped_release_statement_satisfied_outcome_surfaces": (
                scoped_release_statement_satisfied_outcome_surfaces
            ),
            "scoped_release_statement_satisfied_outcome_count": len(
                scoped_release_statement_satisfied_outcome_surfaces
            ),
            "scoped_release_statement_missing_required_outcome_surfaces": (
                scoped_release_statement_missing_required_outcome_surfaces
            ),
            "scoped_release_statement_missing_required_outcome_count": len(
                scoped_release_statement_missing_required_outcome_surfaces
            ),
            "scoped_release_statement_counts_toward_complete_sdk_claim": False,
            "scoped_release_statement_claim_progress_contribution": 0,
            "p0_release_statement_scoped_non_complete_outcomes": blocker_outcome_summary[
                "p0_release_statement_scoped_non_complete_outcomes"
            ],
            "p0_release_statement_scoped_non_complete_outcome_count": blocker_outcome_summary[
                "p0_release_statement_scoped_non_complete_outcome_count"
            ],
            "non_p0_release_statement_post_v1_or_excluded_outcomes": blocker_outcome_summary[
                "non_p0_release_statement_post_v1_or_excluded_outcomes"
            ],
            "non_p0_release_statement_post_v1_or_excluded_outcome_count": blocker_outcome_summary[
                "non_p0_release_statement_post_v1_or_excluded_outcome_count"
            ],
            "non_p0_manifest_post_v1_or_excluded_outcomes": blocker_outcome_summary[
                "non_p0_manifest_post_v1_or_excluded_outcomes"
            ],
            "non_p0_manifest_post_v1_or_excluded_outcome_count": blocker_outcome_summary[
                "non_p0_manifest_post_v1_or_excluded_outcome_count"
            ],
            "active_side_lane_review_blockers": blocker_outcome_summary[
                "active_side_lane_review_blockers"
            ],
            "active_side_lane_review_blocker_count": blocker_outcome_summary[
                "active_side_lane_review_blocker_count"
            ],
            "active_side_lane_review_promoted_for_claim": blocker_outcome_summary[
                "active_side_lane_review_promoted_for_claim"
            ],
            "active_side_lane_review_promoted_for_claim_count": blocker_outcome_summary[
                "active_side_lane_review_promoted_for_claim_count"
            ],
            "active_side_lane_review_remaining_for_claim": blocker_outcome_summary[
                "active_side_lane_review_remaining_for_claim"
            ],
            "active_side_lane_review_remaining_for_claim_count": blocker_outcome_summary[
                "active_side_lane_review_remaining_for_claim_count"
            ],
            "active_side_lane_review_manifest_post_v1_or_excluded": blocker_outcome_summary[
                "active_side_lane_review_manifest_post_v1_or_excluded"
            ],
            "active_side_lane_review_manifest_post_v1_or_excluded_count": blocker_outcome_summary[
                "active_side_lane_review_manifest_post_v1_or_excluded_count"
            ],
            "active_side_lane_review_release_statement_post_v1_or_excluded": blocker_outcome_summary[
                "active_side_lane_review_release_statement_post_v1_or_excluded"
            ],
            "active_side_lane_review_release_statement_post_v1_or_excluded_count": blocker_outcome_summary[
                "active_side_lane_review_release_statement_post_v1_or_excluded_count"
            ],
            "active_side_lane_review_non_claim": blocker_outcome_summary[
                "active_side_lane_review_non_claim"
            ],
            "route_gate_non_counting_surfaces": blocker_outcome_summary[
                "route_gate_non_counting_surfaces"
            ],
            "route_gate_non_counting_surface_count": blocker_outcome_summary[
                "route_gate_non_counting_surface_count"
            ],
            "route_gate_non_counting_blockers": route_gate_non_counting_blockers,
            "route_gate_non_counting_blocker_count": len(route_gate_non_counting_blockers),
            "p0_chain_scoped_non_complete_note": (
                "P0 excluded/post-v1 outcomes are scoped release-statement accounting only and do not "
                "increase p0_chain_promoted_count or complete_sdk_claim_progress_percent."
            ),
            "progress_normalization_trace": progress_trace,
            "stable_sdk_remaining_blockers": stable_sdk_remaining_blockers,
            "complete_sdk_claim_progress_percent": (
                int((len(completion_blockers_counting_toward_claim) / completion_blocker_total) * 100)
                if completion_blocker_total
                else 0
            ),
            "completion_blockers_with_promoted_outcome": completion_blockers_counting_toward_claim,
            "completion_blockers_with_manifest_promoted_status": completion_blockers_with_promoted_outcome,
            "completion_blockers_with_promoted_outcome_note": (
                "Only promoted blockers with acceptable evidence and a matching promoted "
                "release-statement record count toward complete SDK claim progress."
            ),
            "completion_blockers_with_post_v1_or_excluded_outcome": (
                completion_blockers_with_post_v1_or_excluded_outcome
            ),
            "completion_blockers_with_post_v1_or_excluded_outcome_note": (
                "bookkeeping only; excluded/post-v1 outcomes do not contribute to complete SDK "
                "claim progress or promoted demand-family coverage"
            ),
            "completion_blockers_with_manifest_post_v1_or_excluded_outcome": (
                completion_blockers_with_post_v1_or_excluded_outcome
            ),
            "completion_blockers_with_release_statement_post_v1_or_excluded_outcome": (
                completion_blockers_with_release_statement_post_v1_or_excluded_outcome
            ),
            "completion_blockers_with_release_statement_post_v1_or_excluded_outcome_count": len(
                completion_blockers_with_release_statement_post_v1_or_excluded_outcome
            ),
            "completion_blockers_without_manifest_outcome": completion_blockers_without_manifest_outcome,
            "completion_blockers_without_manifest_outcome_count": len(
                completion_blockers_without_manifest_outcome
            ),
            "unresolved_completion_blocker_count": len(set(unresolved_completion_blockers)),
            "unresolved_experimental_surface_count": len(set(unresolved_experimental)),
            "minimum_promoted_demand_family_gap_count": len(minimum_promoted_demand_family_gaps),
            "manifest_outcome_missing_count": blocker_outcome_summary["manifest_outcome_missing_count"],
            "release_statement_outcome_missing_count": (
                blocker_outcome_summary["release_statement_outcome_missing_count"]
            ),
            "dependency_chain_remaining_count": blocker_outcome_summary[
                "dependency_chain_remaining_count"
            ],
            "release_statement_required_for_completion_claim": release_statement_text is None,
            "stable_claim_allowed": stable_claim_allowed,
            "stable_release_contract_claim_allowed": manifest_stable_claim_allowed,
            "outcome_accounting_note": (
                "Manifest post-v1/excluded outcomes are only status accounting; release statement "
                "outcomes are counted separately after exact statement wording and exclusion-contract "
                "validation. They never contribute percentage toward complete/full/production SDK."
            ),
            "non_claim": (
                "This is accounting only; it does not authorize broad stable SDK release wording."
            ),
        },
        "non_claims": [
            "core-first release readiness, install layout, and package-shape checks do not satisfy this v1 SDK completion gate",
            "post-v1 or excluded surfaces must be named in the manifest and release statement before a stable v1 SDK claim",
        ],
    }


def add_scoped_release_statement_result(
    report: dict[str, Any],
    *,
    allow_extra_records: bool = False,
) -> dict[str, Any]:
    blocking_report_blockers = [
        blocker
        for blocker in report.get("blockers", [])
        if blocker not in SCOPED_RELEASE_STATEMENT_ALLOWED_BLOCKERS
    ]
    if report.get("release_statement") is None:
        blocking_report_blockers.append("scoped_release_statement_path_required")
    unexpected_records = report.get("scoped_release_statement_unexpected_surface_records")
    if unexpected_records and not allow_extra_records:
        blocking_report_blockers.append("scoped_release_statement_unexpected_surface_records")
    scoped_ready = not blocking_report_blockers
    report["scoped_release_statement"] = {
        "ready": scoped_ready,
        "stable_claim_allowed": False,
        "stable_sdk_claim_allowed": False,
        "stable_v1_sdk_claim_allowed": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "complete_sdk_claim_allowed": False,
        "complete_sdk_ready": False,
        "v1_completion_ready": False,
        "current_route_blocker": report.get("current_route_blocker"),
        "remaining_route_blockers": report.get("remaining_route_blockers", []),
        "next_required_artifact": report.get("next_required_artifact"),
        "missing_required_artifact": report.get("missing_required_artifact"),
        "approved_runtime_evidence": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "approved_runtime_evidence_accepted": False,
        "approved_runtime_principal_lifecycle_evidence_bundle_accepted": False,
        "evidence_bundle_accepted": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "counts_toward_v1_completion": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "p0_dependency_chain_progress_contribution": 0,
        "v1_completion_contribution": 0,
        "scoped_non_complete_bookkeeping_only": True,
        "release_statement": report.get("release_statement"),
        "release_statement_source": report.get("release_statement_source"),
        "default_scoped_release_statement_used": report.get(
            "default_scoped_release_statement_used",
            False,
        ),
        "blocking_report_blockers": sorted(set(blocking_report_blockers)),
        "allowed_remaining_blockers": sorted(
            set(report.get("blockers", [])) & SCOPED_RELEASE_STATEMENT_ALLOWED_BLOCKERS
        ),
        "allowed_surface_records": report.get(
            "scoped_release_statement_allowed_surface_records",
            [],
        ),
        "required_outcome_records": report.get(
            "scoped_release_statement_required_outcome_records",
            [],
        ),
        "required_outcome_surfaces": report.get(
            "scoped_release_statement_required_outcome_surfaces",
            [],
        ),
        "required_outcome_count": report.get(
            "scoped_release_statement_required_outcome_count",
            0,
        ),
        "satisfied_outcome_surfaces": report.get(
            "scoped_release_statement_satisfied_outcome_surfaces",
            [],
        ),
        "satisfied_outcome_count": report.get(
            "scoped_release_statement_satisfied_outcome_count",
            0,
        ),
        "missing_required_outcome_surfaces": report.get(
            "scoped_release_statement_missing_required_outcome_surfaces",
            [],
        ),
        "missing_required_outcome_count": report.get(
            "scoped_release_statement_missing_required_outcome_count",
            0,
        ),
        "unexpected_surface_records": unexpected_records or [],
        "extra_records_explicitly_allowed": allow_extra_records,
        "non_claim": (
            "A scoped release statement records reviewed exclusions/post-v1 outcomes only; "
            "it does not authorize v1.0 stable, stable SDK, complete SDK, full SDK, or production SDK wording."
        ),
    }
    return report


def format_human_list(items: Any, *, limit: int = 12) -> str:
    if not isinstance(items, list) or not items:
        return "none"
    rendered = [str(item) for item in items[:limit]]
    if len(items) > limit:
        rendered.append(f"... {len(items) - limit} more")
    return ", ".join(rendered)


def release_statement_missing_outcomes_guidance(report: dict[str, Any]) -> list[str]:
    guidance = [
        "The release statement is missing required outcome records for non-promoted blockers.",
        f"Surfaces: {format_human_list(report.get('release_statement_missing_blocker_outcomes'))}.",
    ]
    if report.get("release_statement") is None:
        default_statement = report.get("default_scoped_release_statement")
        if report.get("default_scoped_release_statement_exists") is True and default_statement:
            guidance.append(
                f"Default scoped statement exists at {default_statement}, but this report did not "
                "load it."
            )
            guidance.append(
                "Action: rerun the default checker or pass --release-statement with that file "
                "for fail-closed full-gate accounting."
            )
        else:
            guidance.append(
                "Action: pass --release-statement with a reviewed v1 SDK compatibility statement."
            )
        return guidance
    guidance.append(
        "Action: add one exact record per surface: '<surface-id>: excluded - ...' or '<surface-id>: post-v1 - ...'."
    )
    return guidance


def blocker_guidance(report: dict[str, Any], blocker: str) -> list[str]:
    guidance: dict[str, list[str]] = {
        "stable_release_contract_claim_not_allowed": [
            "stable_release_contract.claim_allowed is not true; keep stable SDK release wording blocked.",
            "Action: leave the claim off until the manifest, blocker outcomes, and release statement all pass.",
        ],
        "v1_completion_required_false": [
            "v1_completion_required is not true.",
            "Action: do not describe this tree as a complete v1.0 SDK; finish or explicitly exclude blockers first.",
        ],
        "release_claim_scope_drift": [
            "public_sdk_surfaces.json release_claim must remain an explicit no-v1-stable claim.",
            f"Expected: {CANONICAL_MANIFEST_RELEASE_CLAIM}.",
            f"Actual: {report.get('release_claim')}.",
        ],
        "stable_release_contract_claim_requires_incomplete": [
            "stable_release_contract.claim_requires is missing required guardrail text.",
            f"Missing: {format_human_list(report.get('stable_release_contract_missing_claim_requires'))}.",
        ],
        "stable_release_contract_not_sufficient_incomplete": [
            "stable_release_contract.not_sufficient is missing non-claim boundaries.",
            f"Missing: {format_human_list(report.get('stable_release_contract_missing_not_sufficient'))}.",
        ],
        "installed_sdk_package_shape_guardrail_incomplete": [
            "installed_sdk_package_shape must remain package-shape evidence only.",
            f"Drift: {format_human_list(report.get('installed_sdk_package_shape_guardrail_drift'))}.",
            "Action: do not use installed SDK/package-shape evidence for runtime readiness, live-op approval, Plugin Hub readiness/publication, support-tier activation, v1 completion, or stable SDK wording.",
        ],
        "promoted_experimental_surfaces_unresolved": [
            "Experimental copied-data seeds still need an explicit v1 outcome.",
            f"Surfaces: {format_human_list(report.get('unresolved_experimental_surfaces'))}.",
            "Action: promote with evidence, exclude, or mark post-v1 and name each in the release statement.",
        ],
        "v1_sdk_completion_blockers_unresolved": [
            "High-demand v1 completion blockers are still unresolved.",
            f"Surfaces: {format_human_list(report.get('unresolved_completion_blockers'))}.",
            "Action: promote P0 dependency-chain surfaces with evidence; non-chain blockers may be promoted or scoped excluded/post-v1 where the contract allows it.",
        ],
        "v1_required_dependency_chain_unpromoted": [
            "The P0 dependency chain is not fully promoted.",
            f"Surfaces: {format_human_list(report.get('unpromoted_required_dependency_chain'))}.",
            "Action: promote player identity, permissions/admin, command/chat response path, and commands/replies with evidence before complete/full/production SDK wording.",
        ],
        "p0_dependency_chain_outcomes_scoped_non_complete_only": [
            "A P0 dependency-chain surface is recorded as excluded/post-v1.",
            f"Surfaces: {format_human_list(report.get('p0_dependency_chain_scoped_non_complete_outcomes'))}.",
            "Action: treat this only as scoped non-complete release-statement accounting; promote the P0 chain with evidence before complete/full/production SDK wording.",
        ],
        "p0_dependency_chain_route_gate_locked": [
            "A P0 dependency-chain surface has promoted-looking evidence while the command/permission route gate remains identity-locked.",
            f"Surfaces: {format_human_list(report.get('p0_dependency_chain_route_gate_locked_surfaces'))}.",
            "Action: resolve the current route-lock blocker first: produce approved runtime principal lifecycle evidence, then complete the reviewed identity public contract before counting identity, permissions, command response, or commands/replies toward complete SDK wording.",
        ],
        "complete_sdk_claim_requires_promoted_demand_families": [
            "The complete/full/production SDK claim requires promoted demand families, not only excluded or post-v1 outcomes.",
            f"Gaps: {format_human_list(report.get('minimum_promoted_demand_family_gaps'))}.",
            "Action: use scoped/foundation wording, or promote these families with evidence or explicit promoted equivalents.",
        ],
        "planning_surfaces_unresolved_for_v1_claim": [
            "Planning surfaces remain in the surface table.",
            f"Surfaces: {format_human_list(report.get('unresolved_planning_surfaces'))}.",
            "Action: convert each to promoted, excluded, or post-v1 before any complete SDK claim.",
        ],
        "top_level_planning_surfaces_unresolved_for_v1_claim": [
            "The top-level planning_surfaces list is not empty.",
            f"Surfaces: {format_human_list(report.get('top_level_planning_surfaces'))}.",
            "Action: keep v1 blocked until those entries have reviewed outcomes.",
        ],
        "completion_blocker_exclusion_contract_missing": [
            "A non-promoted completion blocker lacks a v1_decision_contract.exclusion_requires checklist.",
            f"Surfaces: {format_human_list(report.get('missing_completion_blocker_exclusion_contracts'))}.",
        ],
        "promoted_surface_public_contract_missing": [
            "Promoted surfaces are missing public_contract entries.",
            f"Surfaces: {format_human_list(report.get('promoted_without_public_contract'))}.",
        ],
        "promoted_surface_evidence_missing": [
            "Promoted surfaces lack acceptable ABI and SDK-consumer promotion evidence.",
            f"Surfaces: {format_human_list(report.get('promoted_surfaces_without_evidence'))}.",
            f"Completion blockers: {format_human_list(report.get('promoted_blockers_without_evidence'))}.",
        ],
        "promoted_surface_required_evidence_terms_missing": [
            "Promoted surfaces are missing required named evidence terms.",
            "Action: add the required terms to the manifest evidence or keep the surface non-promoted.",
        ],
        "player_identity_request_pack_non_evidence_manifest_terms_missing": [
            "The player identity surface is missing the request-pack non-evidence boundary.",
            f"Missing terms: {format_human_list(report.get('player_identity_request_pack_non_evidence_terms_missing'))}.",
            "Action: restore wording that freshness-bound request packs, preflight, manifests, env sidecars, and approval receipts do not satisfy approved runtime principal lifecycle evidence.",
        ],
        "promoted_surface_structured_evidence_missing": [
            "Promoted dependency-chain surfaces lack structured runtime, readiness, or executed-test evidence.",
            "Action: bind promotion accounting to checker reports and passed ABI/SDK test execution, or keep the surface non-promoted.",
        ],
        "promoted_surface_dependency_unresolved": [
            "A public ABI surface is promoted while required dependency surfaces are not promoted.",
            "Action: promote the dependencies first, or keep the dependent surface non-promoted.",
        ],
        "required_surface_dependency_declaration_missing": [
            "A permissions/admin or command surface row is missing a required depends_on declaration.",
            f"Surfaces: {format_human_list(sorted(report.get('surfaces_missing_required_dependency_declarations', {}).keys()))}.",
            "Action: keep identity/principal before permissions/admin, and keep command/chat response before commands/replies.",
        ],
        "v1_dependency_sequence_mismatch": [
            "The manifest v1 dependency sequence no longer matches identity -> permissions -> command/chat response -> commands/replies.",
            f"Mismatches: {format_human_list(report.get('v1_dependency_sequence_mismatches'))}.",
            "Action: restore v1_dependency_sequence and v1_sdk_completion_blockers to the canonical dependency order.",
        ],
        "non_promoted_surface_has_public_contract": [
            "A non-promoted surface still lists public_contract entries.",
            f"Surfaces: {format_human_list(report.get('non_promoted_with_public_contract'))}.",
            "Action: remove the public contract entries or promote the surface with evidence.",
        ],
        "non_promoted_surface_has_public_abi": [
            "A non-promoted surface is marked public_abi=true.",
            f"Surfaces: {format_human_list(report.get('non_promoted_with_public_abi'))}.",
            "Action: remove public_abi or promote the surface with dependencies and evidence.",
        ],
        "release_statement_required_for_v1_completion": [
            "The manifest is trying to allow a v1 completion claim without a reviewed release statement.",
            "Action: pass --release-statement with the reviewed v1 SDK compatibility statement.",
        ],
        "release_statement_missing_non_promoted_blocker_outcomes": (
            release_statement_missing_outcomes_guidance(report)
        ),
        "release_statement_missing_exclusion_contract": [
            "The release statement outcome text does not satisfy the surface exclusion contract.",
            f"Surfaces: {format_human_list(report.get('release_statement_missing_exclusion_contracts'))}.",
            "Action: include the required exclusion wording from each surface v1_decision_contract.",
        ],
        "release_statement_missing_experimental_outcomes": [
            "The release statement is missing required outcome records for experimental copied-data seeds.",
            f"Surfaces: {format_human_list(report.get('release_statement_missing_experimental_outcomes'))}.",
            "Action: name the seed and state whether it is promoted, excluded, or post-v1.",
        ],
        "release_statement_duplicate_or_mixed_surface_records": [
            "The release statement has duplicate or mixed outcome records for a surface.",
            f"Surfaces: {format_human_list(report.get('release_statement_duplicate_or_mixed_records'))}.",
            "Action: keep exactly one promoted/excluded/post-v1 record per surface.",
        ],
        "release_statement_forbidden_broad_claims": [
            "The release statement contains broad SDK/support claims that conflict with blocked surfaces.",
            f"Claims: {format_human_list(report.get('release_statement_forbidden_broad_claims'), limit=4)}.",
        ],
        "release_statement_missing_sdk_compatibility_reference": [
            "The release statement does not reference docs/SDK_V1_COMPATIBILITY.md.",
        ],
        "release_statement_missing_public_sdk_surfaces_reference": [
            "The release statement does not reference docs/public_sdk_surfaces.json.",
        ],
        "scoped_release_statement_unexpected_surface_records": [
            "The scoped release statement contains surface rows outside the default scoped builder set.",
            f"Rows: {format_human_list([record.get('line') for record in report.get('scoped_release_statement_unexpected_surface_records', [])], limit=4)}.",
            "Action: remove P0, promoted, experimental, and non-blocker rows, or rerun scope validation with --allow-scoped-release-statement-extra-records when the extra rows are intentional.",
        ],
        "blocked_public_contract_header_symbols_detected": [
            "The public header contains symbols that look like blocked public contract surface drift.",
            "Action: remove those symbols or update the reviewed public contract decisions before claiming v1.",
        ],
        "command_permission_route_gate_public_or_runtime_claims": [
            "The command/permission route gate reported a public, runtime, or v1-completion claim.",
            "Action: keep the route gate planning-only; identity, permissions, command response, and replies need separate promotion evidence.",
        ],
        "command_permission_route_gate_override_not_allowed": [
            "SDK completion was asked to use a non-canonical command/permission route gate.",
            "Action: use scripts/check_command_permission_route_gate.py for release/accounting checks; route-gate overrides are test-only.",
        ],
        "inventory_copied_signals_stability_output_invalid": [
            "The inventory/item copied-signal stability checker did not emit valid JSON.",
            "Action: fix scripts/check_inventory_item_copied_signals_stability.py before relying on copied inventory signals in release accounting.",
        ],
        "inventory_copied_signals_stability_invalid": [
            "The inventory/item copied-signal stability checker failed.",
            "Action: keep inventory copied signals as non-promotional until the exact five copied signal contract, category-only resource kind, and no Inventory/Items SDK boundaries are restored.",
        ],
        "inventory_copied_signals_public_sdk_ready_not_false": [
            "Inventory copied-signal stability attempted to mark public SDK readiness.",
            "Action: keep this checker as a copied-signal guardrail only; Inventory SDK and Items SDK need separate promotion gates.",
        ],
        "inventory_copied_signals_v1_completion_ready_not_false": [
            "Inventory copied-signal stability attempted to mark v1 completion readiness.",
            "Action: copied inventory signals cannot count toward complete/full/production SDK progress.",
        ],
        "inventory_copied_signals_completion_accounting_alias_not_false": [
            "Inventory copied-signal stability attempted to expose positive complete-SDK accounting aliases.",
            "Action: keep counts_toward_complete_sdk_claim=false, counts_toward_p0_dependency_chain_claim=false, progress=0, and stable_claim_allowed=false for copied-signal stability reports.",
        ],
        "object_identity_resource_handle_readiness_output_invalid": [
            "The ResourceHandle/object-identity public-contract readiness checker did not emit valid JSON.",
            "Action: fix scripts/check_object_identity_resource_handle_public_contract_readiness.py before relying on ResourceHandle/object-identity accounting.",
        ],
        "object_identity_resource_handle_readiness_schema_mismatch": [
            "The ResourceHandle/object-identity readiness checker emitted an unexpected schema.",
            "Action: keep the dedicated checker on obelisk.object-identity-resource-handle-public-contract-readiness-check.v1.",
        ],
        "object_identity_resource_handle_readiness_invalid": [
            "The ResourceHandle/object-identity readiness checker failed.",
            "Action: keep ResourceHandle, object identity, object lookup, and post-callback object correlation blocked from public SDK accounting.",
        ],
        "object_identity_resource_handle_readiness_not_planning_only": [
            "The ResourceHandle/object-identity readiness checker stopped reporting planning-only status.",
            "Action: this guardrail must remain planning-only until a separate promotion gate exists.",
        ],
        "object_identity_resource_handle_readiness_blockers_not_empty": [
            "The ResourceHandle/object-identity readiness checker reported blockers.",
            "Action: resolve the dedicated checker blockers before any SDK completion claim.",
        ],
        "object_identity_resource_handle_strict_next_blocker_missing": [
            "The ResourceHandle/object-identity readiness checker did not preserve the precise next-evidence contract.",
            "Action: keep the next blocker scoped to runtime object negative samples plus serial reuse/wraparound semantics under a future approved live-ops brief.",
        ],
        "object_identity_resource_handle_offline_artifact_policy_not_candidate_only": [
            "The ResourceHandle/object-identity readiness checker stopped treating offline serial/post-callback artifacts as candidate-only.",
            "Action: offline artifacts may plan the blocker but must not approve lookup, mutation, persistent identity, post-callback validity, runtime readiness, or public SDK readiness.",
        ],
        "object_identity_resource_handle_public_or_runtime_claims": [
            "The ResourceHandle/object-identity readiness checker reported a public, runtime, or promotion claim.",
            "Action: keep ResourceHandle/object identity post-v1; copied events and category-only resource_kind metadata do not imply lookup or identity.",
        ],
        "object_identity_resource_handle_promotion_ready_not_false": [
            "ResourceHandle/object identity attempted to mark promotion readiness.",
            "Action: promotion readiness must remain false until a reviewed public ResourceHandle/object-identity gate exists.",
        ],
        "object_identity_resource_handle_public_sdk_ready_not_false": [
            "ResourceHandle/object identity attempted to mark public SDK readiness.",
            "Action: keep ResourceHandle/object identity out of public SDK readiness accounting.",
        ],
        "object_identity_resource_handle_runtime_ready_not_false": [
            "ResourceHandle/object identity attempted to mark runtime readiness.",
            "Action: runtime readiness for ResourceHandle/object identity needs separate promotion evidence.",
        ],
        "object_identity_resource_handle_public_resource_handle_ready_not_false": [
            "ResourceHandle readiness was reported as true.",
            "Action: no public ResourceHandle ABI is part of the v1 SDK completion claim.",
        ],
        "object_identity_resource_handle_post_callback_resource_handle_ready_not_false": [
            "Post-callback ResourceHandle readiness was reported as true.",
            "Action: no post-callback object correlation or handle API is part of the v1 SDK completion claim.",
        ],
        SECONDARY_REPORT_COMPLETION_CLAIM_WITHOUT_BLOCKER: [
            "A secondary offline report emitted a positive public/runtime/completion readiness claim without its own blockers.",
            "Action: keep secondary reports non-promotional, or include a blocker that prevents the claim from being counted.",
        ],
        "structure_census_readiness_output_invalid": [
            "The Structure census readiness checker did not emit valid JSON.",
            "Action: fix scripts/check_structure_census_readiness.py before relying on Structure census accounting.",
        ],
        "structure_census_readiness_schema_mismatch": [
            "The Structure census readiness checker emitted an unexpected schema.",
            "Action: keep the dedicated checker on obelisk.structure-census-readiness-check.v1.",
        ],
        "structure_census_readiness_invalid": [
            "The Structure census readiness checker failed.",
            "Action: keep Structure census candidate-only until second-source/readiness evidence remains accepted and non-promotional.",
        ],
        "structure_census_readiness_not_offline_planning": [
            "The Structure census readiness checker stopped reporting offline internal-planning status.",
            "Action: Structure census accounting must not become a public SDK, runtime, promotion, or enforcement gate here.",
        ],
        "structure_census_readiness_blockers_not_empty": [
            "The Structure census readiness checker reported blockers.",
            "Action: resolve the dedicated checker blockers before any SDK completion claim.",
        ],
        "structure_census_promotion_ready_not_false": [
            "Structure census attempted to mark promotion readiness.",
            "Action: promotion readiness must remain false until a reviewed public Structure SDK gate exists.",
        ],
        "structure_census_public_sdk_ready_not_false": [
            "Structure census attempted to mark public SDK readiness.",
            "Action: keep Structure census out of public SDK readiness accounting.",
        ],
        "structure_census_runtime_ready_not_false": [
            "Structure census attempted to mark runtime readiness.",
            "Action: runtime readiness for Structure APIs needs separate promotion evidence.",
        ],
        "structure_census_enforcement_ready_not_false": [
            "Structure census attempted to mark enforcement readiness.",
            "Action: enforcement/build-policy readiness is a separate Structure side-lane and cannot be inferred from census.",
        ],
        "structure_census_accounting_public_structure_sdk_ready_not_false": [
            "Structure census candidate-only accounting attempted to mark public Structure SDK readiness.",
            "Action: candidate-only accounting must keep public Structure SDK readiness false.",
        ],
        "structure_build_policy_offline_intake_output_invalid": [
            "The Structure build-policy offline intake checker did not emit valid JSON.",
            "Action: fix scripts/check_structure_build_policy_offline_intake.py before relying on build-policy accounting.",
        ],
        "structure_build_policy_offline_intake_schema_mismatch": [
            "The Structure build-policy offline intake checker emitted an unexpected schema.",
            "Action: keep the dedicated checker on obelisk.structure-build-policy-offline-intake-check.v1.",
        ],
        "structure_build_policy_offline_intake_invalid": [
            "The Structure build-policy offline intake checker failed.",
            "Action: keep build-policy intake planning-only and resolve its blockers before any SDK completion claim.",
        ],
        "structure_build_policy_offline_intake_not_planning_only": [
            "The Structure build-policy offline intake checker stopped reporting planning-only status.",
            "Action: this guardrail cannot authorize public SDK, runtime, promotion, or enforcement readiness.",
        ],
        "structure_build_policy_offline_intake_blockers_not_empty": [
            "The Structure build-policy offline intake checker reported blockers.",
            "Action: resolve dedicated build-policy blockers before relying on Structure build-policy accounting.",
        ],
        "structure_build_policy_promotion_ready_not_false": [
            "Structure build-policy intake attempted to mark promotion readiness.",
            "Action: promotion readiness needs a separate reviewed public gate.",
        ],
        "structure_build_policy_public_sdk_ready_not_false": [
            "Structure build-policy intake attempted to mark public SDK readiness.",
            "Action: keep build-policy intake out of public SDK readiness accounting.",
        ],
        "structure_build_policy_runtime_ready_not_false": [
            "Structure build-policy intake attempted to mark runtime readiness.",
            "Action: runtime readiness needs separate approved evidence.",
        ],
        "structure_build_policy_enforcement_ready_not_false": [
            "Structure build-policy intake attempted to mark enforcement readiness.",
            "Action: enforcement readiness must stay false until a reviewed enforcement gate exists.",
        ],
        "structure_build_policy_readiness_flags_public_sdk_ready_not_false": [
            "Structure build-policy readiness_flags attempted to mark public SDK readiness.",
            "Action: nested readiness flags must remain false in offline intake accounting.",
        ],
        "mission_transfer_dino_tribe_completion_accounting_alias_not_false": [
            "Mission/Transfer/Dino/Tribe/Buff outcome accounting attempted to expose positive complete-SDK accounting aliases.",
            "Action: keep counts_toward_complete_sdk_claim=false, counts_toward_p0_dependency_chain_claim=false, progress=0, and stable_claim_allowed=false for candidate and umbrella accounting reports.",
        ],
        "schema_mismatch": [
            "The manifest schema is not obelisk.public-sdk-surfaces.v1.",
        ],
        "sdk_version_not_v1": [
            "The manifest sdk_version is not v1.0.",
        ],
        "stable_release_contract_missing": [
            "The manifest is missing stable_release_contract.",
        ],
        "surface_id_missing": [
            f"Missing surfaces: {format_human_list(report.get('missing_surfaces'))}.",
        ],
        "canonical_surface_id_missing": [
            f"Missing canonical surfaces: {format_human_list(report.get('missing_canonical_surfaces'))}.",
        ],
        "canonical_v1_completion_blocker_missing": [
            f"Missing canonical blockers: {format_human_list(report.get('missing_canonical_completion_blockers'))}.",
        ],
        "v1_required_dependency_chain_missing_from_completion_blockers": [
            "A P0 dependency-chain surface is missing from v1_sdk_completion_blockers.",
            f"Surfaces: {format_human_list(report.get('missing_v1_required_dependency_chain_completion_blockers'))}.",
            "Action: keep the canonical P0 chain in v1_sdk_completion_blockers; exclusions/post-v1 accounting cannot satisfy these surfaces.",
        ],
        "duplicate_surface_id": [
            f"Duplicate surface IDs: {format_human_list(report.get('duplicate_surface_ids'))}.",
        ],
        "duplicate_v1_sdk_completion_blocker": [
            "v1_sdk_completion_blockers must be a unique canonical blocker list.",
            f"Duplicate blockers: {format_human_list(report.get('duplicate_v1_sdk_completion_blockers'))}.",
            "Action: remove duplicates before using SDK progress counters.",
        ],
        "debug_only_surface_promoted": [
            "Debug-only surfaces cannot count as promoted public SDK surfaces.",
            f"Surfaces: {format_human_list(report.get('debug_only_promoted_surfaces'))}.",
        ],
        "promoted_surface_list_mismatch": [
            f"Promoted surface list mismatches: {format_human_list(report.get('promoted_list_mismatches'))}.",
        ],
        "experimental_surface_list_mismatch": [
            f"Experimental surface list mismatches: {format_human_list(report.get('experimental_list_mismatches'))}.",
        ],
        "planning_surface_list_mismatch": [
            f"Planning surface list mismatches: {format_human_list(report.get('planning_list_mismatches'))}.",
        ],
        "post_v1_or_excluded_surface_list_mismatch": [
            "post_v1_or_excluded_surfaces does not match surface statuses.",
            f"Surfaces: {format_human_list(report.get('post_v1_or_excluded_list_mismatches'))}.",
        ],
    }
    return guidance.get(blocker, ["Action: inspect the JSON report for this blocker with --json."])


def print_human_report(report: dict[str, Any]) -> None:
    if report["ready"]:
        print("Public SDK v1 completion gate passed.")
        return
    print("Public SDK v1 completion gate blocked.")
    print("The stable v1 SDK claim remains disabled; this is not a v1.0 complete SDK approval.")
    print(
        "Installed SDK/package-shape evidence is package-shape evidence only; it does not "
        "authorize runtime readiness, live-op approval, Plugin Hub readiness/publication, "
        "support-tier activation, v1 completion, or stable SDK wording."
    )
    outcome_summary = report.get("v1_sdk_blocker_outcome_summary", {})
    if isinstance(outcome_summary, dict):
        print(
            "12-blocker outcome accounting: "
            f"{outcome_summary.get('manifest_outcome_missing_count', 0)} need manifest outcomes; "
            f"{outcome_summary.get('release_statement_outcome_missing_count', 0)} need release-statement outcomes; "
            f"{outcome_summary.get('dependency_chain_remaining_count', 0)} dependency-chain blockers remain."
        )
    complete_sdk_progress = report.get("complete_sdk_progress_ratio")
    p0_dependency_chain_progress = report.get("p0_dependency_chain_claim_progress_ratio")
    if isinstance(complete_sdk_progress, str) and isinstance(p0_dependency_chain_progress, str):
        print(
            "Complete SDK progress: "
            f"{complete_sdk_progress}; P0 dependency-chain progress: {p0_dependency_chain_progress}."
        )
    route_gate = report.get("command_permission_route_gate")
    if isinstance(route_gate, dict):
        current_blocker = route_gate.get("current_blocker")
        blocked_until = route_gate.get("route_lock_blocked_until")
        if current_blocker:
            print(
                "P0 route gate: "
                f"{current_blocker}; blocked until {format_human_list(blocked_until)}."
            )
            if current_blocker == "approved_runtime_evidence_missing":
                print(
                    "Request-pack and preflight readiness are non-counting preparation; "
                    "they do not satisfy approved runtime principal lifecycle evidence."
                )
    approved_in_game = report.get("approved_in_game_evidence")
    if isinstance(approved_in_game, dict):
        print(
            "Approved in-game evidence: "
            f"ready={str(bool(approved_in_game.get('approved_in_game_evidence_ready'))).lower()}; "
            f"approved_runtime_evidence={str(bool(approved_in_game.get('approved_runtime_evidence'))).lower()}; "
            f"diagnostic_complete_triplet={str(bool(approved_in_game.get('complete_lifecycle_event_triplet_observed_diagnostic_only'))).lower()}; "
            f"next_required_artifact={approved_in_game.get('next_required_artifact')}."
        )
        diagnostic_paths = as_string_list(approved_in_game.get("diagnostic_complete_triplet_path_ids"))
        missing_role_paths = as_string_list(approved_in_game.get("missing_role_path_ids"))
        if diagnostic_paths:
            print(
                "Diagnostic complete-triplet paths are non-evidence: "
                f"{format_human_list(diagnostic_paths)}."
            )
        if missing_role_paths:
            print(
                "Player-backed paths still missing lifecycle roles: "
                f"{format_human_list(missing_role_paths)}."
            )
    fastest_unblock = report.get("fastest_next_sdk_unblock")
    if isinstance(fastest_unblock, dict):
        actionable_paths = fastest_unblock.get("actionable_paths")
        if isinstance(actionable_paths, dict) and actionable_paths:
            path_labels = []
            for path_id, path_payload in actionable_paths.items():
                authorization = "non-authorizing"
                if isinstance(path_payload, dict) and isinstance(
                    path_payload.get("authorization"),
                    str,
                ):
                    authorization = path_payload["authorization"]
                path_labels.append(f"{path_id} ({authorization})")
            print(
                "Fastest next SDK unblock paths: "
                f"{format_human_list(path_labels)}."
            )
    print("Blockers:")
    for blocker in report["blockers"]:
        print(f"- {blocker}")
        for detail in blocker_guidance(report, blocker):
            print(f"  {detail}")
    print("Use --json for the full machine-readable report.")


def print_scoped_release_statement_report(report: dict[str, Any]) -> None:
    scoped = report["scoped_release_statement"]
    if scoped["ready"]:
        print("Scoped v1 SDK release statement check passed.")
        print("This does not allow a v1.0 stable or complete-SDK claim.")
        print(f"Remaining full-gate blockers: {format_human_list(scoped['allowed_remaining_blockers'])}.")
        return
    print("Scoped v1 SDK release statement check blocked.")
    print("Blocking statement-scope issues:")
    for blocker in scoped["blocking_report_blockers"]:
        print(f"- {blocker}")
        for detail in blocker_guidance(report, blocker):
            print(f"  {detail}")


def main() -> int:
    args = parse_args()
    release_statement_path, release_statement_resolution = resolve_release_statement_for_args(args)
    report = build_report(
        args.manifest,
        release_statement_path,
        args.public_header,
        args.contract_decisions_dir,
        args.command_permission_route_gate,
        args.inventory_copied_signals_stability,
        args.object_identity_resource_handle_readiness,
        args.mission_transfer_dino_tribe_outcome_accounting,
        args.structure_census_readiness,
        args.structure_build_policy_offline_intake,
    )
    report.update(release_statement_resolution)
    if args.validate_release_statement_scope:
        report = add_scoped_release_statement_result(
            report,
            allow_extra_records=args.allow_scoped_release_statement_extra_records,
        )
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print_scoped_release_statement_report(report)
        return 0 if report["scoped_release_statement"]["ready"] else 1
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_human_report(report)
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
