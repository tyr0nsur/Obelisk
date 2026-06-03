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


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
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
OBJECT_IDENTITY_RESOURCE_HANDLE_DECISIONS_FILENAME = (
    "object_identity_resource_handle_public_contract_decisions.json"
)
MISSION_TRANSFER_DINO_TRIBE_REQUIRED_LEAVES = {
    "mission",
    "transfer",
    "dino_policy",
    "tribe_policy",
    "buff_status",
}
PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA = (
    "obelisk.player-identity-promotion-certificate.v1"
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
        "Obelisk_PLUGIN_HUB_PUBLICATION_ALLOWED": False,
        "Obelisk_V1_COMPLETION_CLAIM_ALLOWED": False,
        "Obelisk_PUBLIC_MODULE_SDK_COVERAGE_CLAIM_ALLOWED": False,
        "Obelisk_PRODUCTION_STABLE_SDK_CLAIM_ALLOWED": False,
    },
}
INSTALLED_SDK_PACKAGE_SHAPE_FORBIDDEN_POSITIVE_CLAIM_KEYS = (
    "Obelisk_PLUGIN_HUB_PUBLICATION_ALLOWED",
    "Obelisk_PRODUCTION_STABLE_SDK_CLAIM_ALLOWED",
    "Obelisk_PUBLIC_MODULE_SDK_COVERAGE_CLAIM_ALLOWED",
    "Obelisk_V1_COMPLETION_CLAIM_ALLOWED",
    "counts_toward_complete_sdk_claim",
    "installed_sdk_package_ready",
    "installed_sdk_release_ready",
    "package_available",
    "package_publication_allowed",
    "package_publication_ready",
    "package_published",
    "package_shape_counts_toward_release",
    "package_shape_release_ready",
    "public_package_available",
    "public_package_published",
    "public_package_ready",
    "plugin_hub_publication_allowed",
    "plugin_hub_seed_package_publication",
    "promoted_for_claim_count",
    "promotion_ready",
    "public_module_sdk_coverage_claim_allowed",
    "public_sdk_ready",
    "release_package_allowed",
    "release_package_available",
    "release_package_published",
    "release_package_ready",
    "release_packaged",
    "sdk_package_available",
    "sdk_package_published",
    "sdk_package_ready",
    "stable_claim_allowed",
    "stable_release_contract_claim_allowed",
    "v1_completion_claim_allowed",
    "v1_completion_ready",
    "v1_completion_required",
)
INSTALLED_SDK_PACKAGE_SHAPE_FORBIDDEN_ALIAS_KEYS = (
    "promoted_demand_family_equivalents",
    "v1_completion_equivalent_for",
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
    "promotion_ready",
    "public_sdk_ready",
    "public_sdk",
    "public_abi_ready",
    "public_abi_allowed",
    "public_reply_abi_ready",
    "public_response_path_ready",
    "runtime_ready",
    "send_chat_ready",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "public_or_runtime_accounting_allowed",
    "public_header_allowed",
    "public_header_ready",
    "public_readiness_ready",
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
    "permissions_ready",
    "permission_ready",
    "command_router_allowed",
    "runtime_delivery_allowed",
    "runtime_readiness_allowed",
    "public_response_path_allowed",
    "v1_completion_evidence",
    "v1_completion_ready",
    "stable_claim_allowed",
    "operator_approval_granted",
    "runtime_approval",
    "runtime_approval_granted",
    "runtime_work_authorized",
    "server_operations_authorized",
)
COMMAND_PERMISSION_ROUTE_GATE_FORBIDDEN_SOURCE_KEYS = {
    "approved_runtime_evidence_source",
    "authority_claim_source",
    "authz_principal_source",
    "command_principal_source",
    "evidence_source",
    "identity_claim_source",
    "permission_principal_source",
    "principal_claim_source",
    "principal_source",
    "public_identity_source",
    "runtime_evidence_source",
    "runtime_identity_source",
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
    r"request_?pack|"
    r"preflight(?:_?sidecar)?|"
    r"operator_?(?:approval_?)?receipts?|"
    r"(?:live_?)?(?:validation|ops)_?sidecars?|"
    r"window_?manifests?|"
    r"placeholder_?(?:runtime_?)?evidence|"
    r"public_identity"
    r")"
)
SECONDARY_REPORT_FORBIDDEN_COMPLETION_CLAIM_KEYS = (
    *INSTALLED_SDK_PACKAGE_SHAPE_FORBIDDEN_POSITIVE_CLAIM_KEYS,
    "complete_sdk_blockers_promoted_count",
    "complete_sdk_blockers_promoted_for_claim_count",
    "complete_sdk_blockers_promoted_for_claim_ratio",
    "complete_sdk_claim_progress_percent",
    "complete_sdk_claim_progress_ratio",
    "complete_sdk_progress_percent",
    "complete_sdk_progress_ratio",
    "p0_chain_promoted_count",
    "p0_chain_promoted_ratio",
    "p0_dependency_chain_promoted_for_claim_count",
    "p0_dependency_chain_promoted_for_claim_ratio",
    "promoted_for_claim_ratio",
    "public_abi_ready",
    "rc_ready",
    "rc_readiness_ready",
    "release_candidate_ready",
    "release_candidate_readiness_ready",
    "release_ready",
    "release_readiness_ready",
    "v1_completion_ready",
    "stable_claim_allowed",
    "public_sdk_ready",
    "promotion_ready",
    "runtime_ready",
    "sdk_completion_progress_percent",
    "sdk_completion_progress_ratio",
    "v1_completion_progress_percent",
    "v1_completion_progress_ratio",
)
BROAD_ROUTE_GATE_CLAIM_KEY_RE = re.compile(
    r"^(?:"
    r"(?:complete|full|stable|production(?:_ready|_grade)?)_(?:sdk|api|support)"
    r"(?:_(?:ready|allowed|supported|enabled|public))?|"
    r"(?:sdk|api|support)_(?:complete|full|stable|production(?:_ready|_grade)?)"
    r"(?:_(?:ready|allowed|supported|enabled|public))?|"
    r"public_api(?:_(?:ready|allowed|supported|enabled|public))?"
    r")$"
)
ROUTE_GATE_OVERRIDE_TEST_ENV = "OBELISK_SDK_COMPLETION_ALLOW_ROUTE_GATE_OVERRIDE_FOR_TESTS"
SECONDARY_REPORT_COMPLETION_CLAIM_WITHOUT_BLOCKER = (
    "secondary_report_completion_claim_without_blocker"
)
OBJECT_IDENTITY_RESOURCE_HANDLE_REQUIRED_FALSE_KEYS = (
    "promotion_ready",
    "public_sdk_ready",
    "runtime_ready",
    "public_resource_handle_ready",
    "post_callback_resource_handle_ready",
)
OBJECT_IDENTITY_RESOURCE_HANDLE_FORBIDDEN_READY_KEYS = (
    *OBJECT_IDENTITY_RESOURCE_HANDLE_REQUIRED_FALSE_KEYS,
    "object_identity_ready",
    "object_lookup_ready",
    "public_abi_ready",
    "public_contract_allowed",
    "public_header_allowed",
    "public_object_identity_ready",
    "public_object_lookup_ready",
    "release_ready",
    "resource_handle_ready",
    "v1_completion_ready",
)
COMMAND_PERMISSION_ROUTE_GATE_POSITIVE_CLAIM_RE = re.compile(
    r"\b(?:"
    r"reply\s+api|reply\s+abi|send[-\s]?chat\s+api|command\s+router|"
    r"send[-\s]?chat\s+abi|reply\s+endpoint|command\s+routing|permissions/admin|replies\s+api|"
    r"response\s+path|runtime\s+delivery|runtime\s+readiness|runtime\s+work|"
    r"server\s+operations?|operator\s+approval|runtime\s+approval|"
    r"public\s+abi|public\s+sdk|public\s+header|v1\s+completion|"
    r"(?:complete|full|stable|production(?:[-\s]?(?:ready|grade))?)\s+(?:sdk|api|support)"
    r")\b.{0,80}\b(?:is|are|now|becomes?|became)?\s*"
    r"\b(?:authorized|granted|public|ready|available|allowed|enabled|promoted|supported|unlocked|live|operational)\b",
    re.IGNORECASE,
)
COMMAND_PERMISSION_ROUTE_GATE_POSITIVE_CLAIM_REVERSED = re.compile(
    r"\b(?:authorized|granted|public|ready|available|allowed|enabled|promoted|supported|unlocked|live|operational)\b"
    r".{0,80}\b(?:"
    r"reply\s+api|reply\s+abi|reply\s+endpoint|send[-\s]?chat\s+api|command\s+router|"
    r"response\s+path|runtime\s+delivery|runtime\s+readiness|runtime\s+work|"
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
    "approved_bundle",
    BUNDLE_BUILDER_INPUTS_READY_SCOPE,
    "lifecycle_anchor",
    "lifecycle_anchor_candidates",
    "lifecycle_anchor_candidates_only",
    "lifecycle_anchor_only",
    "live_ops_sidecar",
    "live_validation_sidecar",
    "operator_approval_receipt",
    "operator_approval_receipt_only",
    "operator_receipt",
    "operator_receipt_only",
    "placeholder_provenance",
    "preflight",
    "preflight_only",
    "post_window_replay",
    "post_window_replay_only",
    "request_pack",
    "request_pack_only",
    "runtime_replay",
    "runtime_replay_fixture",
    "runtime_replay_fixture_only",
    "runtime_replay_only",
    "runtime_window",
    "live_ops_sidecar_only",
    "live_validation_sidecar_only",
    "window_manifest",
    "window_manifest_only",
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
    "approved_runtime_bundle",
    "approved-runtime-bundle",
    "candidate",
    "admin_thunk",
    "admin_thunks",
    "chat_message_event_seed",
    "chat_seed",
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
    "package_shape",
    "placeholder",
    "placeholder_provenance",
    "planning",
    "plugin_hub",
    "pluginhub",
    "plugin_hub_seed",
    "orientation",
    "preflight",
    "preflight-pre",
    "preflight-post",
    "post_window_replay",
    "post-window-replay",
    "readiness",
    "request_pack",
    "request-pack",
    "runtime_replay",
    "runtime-replay",
    "runtime_replay_fixture",
    "runtime-replay-fixture",
    "operator_approval_receipt",
    "operator-approval-receipt",
    "operator_receipt",
    "operator-receipt",
    "window_manifest",
    "window-manifest",
    "runtime_window",
    "runtime-window",
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
    "descriptor_preflight",
    "evidence_kind",
    "evidence_kinds",
    "evidence_terms",
    "input_target_set",
    "output_target_set",
    "pack",
    "packs",
    "promotion_terms",
    "release_readiness_target_sets",
    "contract_kind",
    "schema",
    "schemas",
    "source_kind",
    "source_kinds",
    "status",
    "source_target_sets",
    "target_set",
    "target_sets",
    "terms",
}
STRICT_PROMOTION_EVIDENCE_SCHEMA_DENY_MARKERS = re.compile(
    r"(?:candidate|placeholder(?:[-_ ]?provenance)?|planning|approved[-_ ]?(?:runtime[-_ ]?)?bundle|plugin[-_ ]?hub|package[-_ ]?shape|core[-_ ]?first|"
    r"players?[-_ ]?identity[-_ ]?principal[-_ ]?invalidation[-_ ]?policy|"
    r"players?[-_ ]?identity[-_ ]?runtime[-_ ]?principal[-_ ]?lifecycle[-_ ]?evidence|"
    r"players?[-_ ]?identity[-_ ]?lifecycle[-_ ]?anchor[-_ ]?candidates?|"
    r"principal[-_ ]?invalidation[-_ ]?policy|"
    r"lifecycle[-_ ]?anchor[-_ ]?candidates?|"
    r"player[-_ ]?principal[-_ ]?lifecycle[-_ ]?window[-_ ]?request|"
    r"operator[-_ ]?(?:approval[-_ ]?)?receipts?|window[-_ ]?manifests?|"
    r"(?:(?:post[-_ ]?window[-_ ]?)?runtime[-_ ]?replay(?:[-_ ]?fixtures?)?|"
    r"post[-_ ]?window[-_ ]?replay(?:[-_ ]?fixtures?)?)|"
    r"live[-_ ]?(?:validation|ops)(?:[-_ ]?sidecars?)?|"
    r"copied[-_ ]?data|(?:chat[-_ ]?message|gameplay[-_ ]?policy[-_ ]?event|event|chat)[-_ ]?seeds?|"
    r"static[-_ ]?(?:orientation|candidate|target|discovery)|native[-_ ]?ufunction[-_ ]?registration[-_ ]?static[-_ ]?discovery|"
    r"admin[-_ ]?thunks?|orientation|preflight|readiness|"
    r"item[-_ ]?return[-_ ]?only|return[-_ ]?only|descriptor[-_ ]?preflight|"
    r"descriptor[-_ ]?catalog|consume[-_ ]?only|evidence[-_ ]?only)",
    re.IGNORECASE,
)
CANONICAL_DEBUG_ONLY_SURFACE_IDS = {
    "obelisk.debug_raw_process_event.v1",
}
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
SHA256_RE = re.compile(r"[0-9a-fA-F]{64}")
UTC_TIMESTAMP_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})"
)
AFFIRMATIVE_RELEASE_CLAIM_PATTERNS = (
    r"\b(?:complete|full|production|stable)\s+(?:[a-z0-9_/+-]+\s+){0,5}(?:sdk|api|support)\b",
    r"\b(?:sdk|api|surface|capability|support)\s+"
    r"(?:is|are|remains?|stays?)\s+"
    r"(?:complete|full|production|stable|available|ready|supported|included|shipped|"
    r"public|promoted)\b",
    r"\b[a-z0-9_ /+-]{2,80}\s+(?:is|are)\s+"
    r"(?:available|ready|supported|included|shipped|public|promoted)\s+in\s+v1\b",
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
    r"(?:complete|full|production[- ]?ready|production[- ]?grade|stable|ready|supported|public)\b",
    r"\b(?:ga|generally[- ]available)\s+(?:sdk|api|support)\b.{0,80}"
    r"\b(?:available|published|ready|released|shipped)\b",
    r"\b(?:sdk|api|support)\b.{0,40}\b(?:ga|generally[- ]available)\b",
    r"\b1\.0\s+stable\s+(?:sdk|api|support)\b",
    r"\b(?:complete|full|prod(?:uction)?[- ]?ready|production[- ]?grade|"
    r"release[- ]?grade|production|stable)\s+"
    r"(?:[a-z0-9_/+-]+\s+){1,5}(?:sdk|api|support)\b.{0,80}"
    r"\b(?:allowed|available|complete|full|included|production[- ]?ready|ready|released|"
    r"shipped|stable|supported|public|promoted)\b",
    r"\b(?:complete|full|prod(?:uction)?[- ]?ready|production[- ]?grade|release[- ]?grade|production|stable)[- ]+"
    r"(?:sdk|api|support)\b.{0,80}"
    r"\b(?:allowed|available|complete|full|included|production[- ]?ready|ready|released|"
    r"shipped|stable|supported|public|promoted)\b",
    r"\b(?:public\s+|obelisk\s+)?(?:sdk|api|support)\s+v1(?:\.0)?\s+"
    r"(?:is|are|remains?|stays?)\s+"
    r"\b(?:allowed|available|complete|full|included|production[- ]?ready|ready|released|"
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
            r"PrincipalHandle|PrincipalGeneration|PrincipalScope|ObeliskPrincipal|"
            r"PlayerSession)"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:PLAYER_IDENTITY|PLAYER_PRINCIPAL|PLAYER_LOOKUP|"
            r"PLAYER_ID|STEAM_ID|EOS_ID|PLATFORM_ACCOUNT_ID|PLAYER_NAME|TRIBE_ID|"
            r"NETWORK_ADDRESS|PRINCIPAL_HANDLE|PRINCIPAL_GENERATION|"
            r"PRINCIPAL_SCOPE|PLAYER_SESSION)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:player_identity|player_principal|player_lookup|principal_handle|"
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
            r"(?:Command|Reply|Replies|Response|Respond|SendChat|Broadcast|Notice|Moderation)"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:COMMAND|REPLY|RESPONSE|SEND_CHAT|BROADCAST|"
            r"NOTICE|MODERATION)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:command|reply|replies|response|response_handle|response_kind|"
            r"send_chat|broadcast|notice|moderation|delivery_scope|delivery_flags)(?:_|$)"
        ),
    ),
    "obelisk.commands_replies.v1": (
        re.compile(
            r"(?:Command|Commands|Reply|Replies|CommandRouter|CommandCallback|"
            r"CommandPayload|CommandRegistration|SendChat|Broadcast|Notice|Moderation)"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:COMMAND|COMMANDS|REPLY|REPLIES|SEND_CHAT|"
            r"BROADCAST|NOTICE|MODERATION)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:command|commands|command_router|command_callback|command_payload|"
            r"command_registration|reply|replies|send_chat|broadcast|notice|moderation)(?:_|$)"
        ),
    ),
    "obelisk.inventory_items_mutation.v1": (
        re.compile(
            r"(?:InventorySdk|ItemsSdk|InventoryLookup|ItemLookup|ItemHandle|GiveItem|"
            r"RemoveItem|GrantItem|InventoryMutation|ItemMutation|Kit|Kits|Reward|Rewards|"
            r"Engram|Progression|ResourceHandle|InventoryComp|InventoryID|InventoryId|"
            r"ItemID|ItemId|ItemNetId|ItemNetID|ItemStack|ItemStackID|ItemStackId|"
            r"CraftBlueprint|AdditionalData|AnActor|anActor)"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:INVENTORY_SDK|ITEMS_SDK|INVENTORY_LOOKUP|"
            r"ITEM_LOOKUP|ITEM_HANDLE|GIVE_ITEM|REMOVE_ITEM|GRANT_ITEM|INVENTORY_MUTATION|"
            r"ITEM_MUTATION|KIT|KITS|REWARD|REWARDS|ENGRAM|PROGRESSION|"
            r"RESOURCE_HANDLE|INVENTORY_COMP|INVENTORY_ID|ITEM_ID|ITEM_NET_ID|"
            r"ITEM_STACK|ITEM_STACK_ID|CRAFT_BLUEPRINT|ADDITIONAL_DATA|AN_ACTOR)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:inventory_sdk|items_sdk|inventory_lookup|item_lookup|item_handle|"
            r"give_item|remove_item|grant_item|inventory_mutation|item_mutation|kits?|"
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
            r"DetachedWorkerIngress|RestartStateRecovery)"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:PLUGIN_WATCHDOG|CRASH_RECOVERY|HOT_PLUGIN_RELOAD|"
            r"OBELISK_HOT_RELOAD|RESTART_ORCHESTRATION|SERVER_RECOVERY|"
            r"OPERATOR_RELOAD_COMMAND|DETACHED_WORKER_INGRESS|RESTART_STATE_RECOVERY)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:plugin_watchdog|crash_recovery|hot_plugin_reload|obelisk_hot_reload|"
            r"restart_orchestration|server_recovery|operator_reload_command|"
            r"detached_worker_ingress|restart_state_recovery)(?:_|$)"
        ),
    ),
    "obelisk.structure_census.v1": (
        re.compile(
            r"(?:StructureEvents|StructureCensus|StructureAggregate|StructureIdentity|"
            r"StructureLookup|StructureHandle|OwnershipLookup|BuildPlacement|"
            r"NoCollision|PinOutcome)"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:STRUCTURE_EVENTS|STRUCTURE_CENSUS|"
            r"STRUCTURE_AGGREGATE|STRUCTURE_IDENTITY|STRUCTURE_LOOKUP|STRUCTURE_HANDLE|"
            r"OWNERSHIP_LOOKUP|BUILD_PLACEMENT|NO_COLLISION|PIN_OUTCOME)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:structure_events|structure_census|structure_aggregate|"
            r"structure_identity|structure_lookup|structure_handle|ownership_lookup|"
            r"build_placement|no_collision|pin_outcome)(?:_|$)"
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
            r"DINO_COSMETICS|DINO_CARRY_RULES|TRIBE_MOTD|TRIBE_NOTICE|TRIBE_POLICY|"
            r"TELEPORT_SPAWN|CROSS_MAP_CORRELATION|OWNERSHIP_LOOKUP|TELEPORT|"
            r"SPAWN)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:mission_sdk|transfer_sdk|dino_sdk|tribe_sdk|buff_status_sdk|"
            r"buff_sdk|mission|transfer|dino|buff_status|dino_colors|dino_cosmetics|"
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
            r"StorageMigration|SecretManager|ExternalIngress|CrossInstanceStorage|"
            r"QueueDrain|PoisonMessage|Storage)"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:RCON|OPERATOR_RELOAD|OPERATOR_COMMAND|WEBHOOK|"
            r"DATABASE|STORAGE_SCHEMA|STORAGE_MIGRATION|SECRET_MANAGER|"
            r"EXTERNAL_INGRESS|CROSS_INSTANCE_STORAGE|QUEUE_DRAIN|"
            r"POISON_MESSAGE|STORAGE)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:rcon|operator_reload|operator_command|webhook|database|"
            r"storage_schema|storage_migration|secret_manager|external_ingress|"
            r"cross_instance_storage|queue_drain|poison_message|storage)(?:_|$)"
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
        help="Reviewed v1 SDK release statement that names excluded/post-v1 blockers.",
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
    return parser.parse_args()


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
    result = subprocess.run(
        [
            sys.executable,
            str(path),
            "--public-sdk-surfaces",
            str(public_sdk_surfaces_path),
            "--public-header",
            str(public_header_path),
            "--json",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
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
    source_checker_primary_blocker = critical_path_phase.get("source_checker_primary_blocker")
    source_checker_next_blocker = critical_path_phase.get("source_checker_next_blocker")
    source_checker_status = critical_path_phase.get("source_checker_status")
    source_checker_ready = critical_path_phase.get("source_checker_ready")
    source_checker_internal_planning = critical_path_phase.get("source_checker_accepted_for_internal_planning")
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
    if approved_runtime_evidence_forwarded:
        expected_lock_by_blocker["identity_public_contract_gate_missing"] = [
            "reviewed_identity_public_contract",
        ]
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
            "current_blocker": current_blocker,
            "source_checker_primary_blocker": source_checker_primary_blocker,
            "source_checker_next_blocker": source_checker_next_blocker,
            "source_checker_status": source_checker_status,
            "source_checker_ready": source_checker_ready,
            "source_checker_accepted_for_internal_planning": source_checker_internal_planning,
            "route_lock_blocked_until": route_lock.get("blocked_until"),
            "route_lock_locked": route_lock.get("locked"),
            "public_or_runtime_claims": public_or_runtime_claims,
            "completion_claims_without_blocker": completion_claims_without_blocker,
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
        if isinstance(value, str):
            return normalized_key(value) in {
                "allowed",
                "available",
                "enabled",
                "live",
                "operational",
                "promoted",
                "public",
                "ready",
                "supported",
                "true",
                "unlocked",
                "yes",
            }
        return False

    def positive_text_claim(text: str) -> bool:
        if not (
            COMMAND_PERMISSION_ROUTE_GATE_POSITIVE_CLAIM_RE.search(text)
            or COMMAND_PERMISSION_ROUTE_GATE_POSITIVE_CLAIM_REVERSED.search(text)
            or COMMAND_PERMISSION_ROUTE_GATE_BROAD_REVERSED_CLAIM_RE.search(text)
        ):
            return False
        claim_start = min(
            [
                match.start()
                for pattern in (
                    COMMAND_PERMISSION_ROUTE_GATE_POSITIVE_CLAIM_RE,
                    COMMAND_PERMISSION_ROUTE_GATE_POSITIVE_CLAIM_REVERSED,
                    COMMAND_PERMISSION_ROUTE_GATE_BROAD_REVERSED_CLAIM_RE,
                )
                for match in pattern.finditer(text)
            ]
            or [0]
        )
        context = text[max(0, claim_start - 48) : min(len(text), claim_start + 128)]
        if COMMAND_PERMISSION_ROUTE_GATE_NEGATED_CLAIM_RE.search(context) and not re.search(
            r"\b(?:claims?|reports?|says|states?)\b[^,.;:\n\r]*$",
            text[max(0, claim_start - 48) : claim_start],
            re.IGNORECASE,
        ):
            return False
        return True

    def contains_forbidden_claim_source(item: Any) -> bool:
        if isinstance(item, str):
            return COMMAND_PERMISSION_ROUTE_GATE_FORBIDDEN_SOURCE_VALUE_RE.search(normalized_source(item)) is not None
        if isinstance(item, list):
            return any(contains_forbidden_claim_source(child) for child in item)
        if isinstance(item, dict):
            return any(contains_forbidden_claim_source(child) for child in item.values())
        return False

    def text_claim_path_is_negative_context(path: str) -> bool:
        return any(
            normalized_key(part.split("[", 1)[0]) in PROMOTION_EVIDENCE_NEGATIVE_CONTEXT_KEYS
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
            tail in {"accounting", "claim", "claims", "readiness", "report", "reports", "result", "results", "summary"}
            or tail.endswith("_accounting")
            or tail.endswith("_claims")
            or tail.endswith("_readiness")
            or tail.endswith("_report")
            or tail.endswith("_reports")
            or tail.endswith("_result")
            or tail.endswith("_results")
            or tail.endswith("_summary")
        )

    def visit(value: Any, path: str, blocked_report_context: bool) -> None:
        if isinstance(value, dict):
            current_blocked_context = (
                has_local_blockers(value)
                if starts_report_context(value, path)
                else blocked_report_context
            )
            for key, item in value.items():
                item_path = f"{path}.{key}" if path else str(key)
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
                    and not current_blocked_context
                ):
                    claims.append(item_path)
                visit(item, item_path, current_blocked_context)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]", blocked_report_context)

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


def normalized_claim_path_suffixes(path: str) -> list[str]:
    parts = normalized_claim_path_parts(path)
    return ["_".join(parts[index:]) for index in range(len(parts))]


def is_positive_completion_claim_value(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
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
            "allowed",
            "available",
            "enabled",
            "live",
            "operational",
            "promoted",
            "public",
            "published",
            "ready",
            "supported",
            "true",
            "unlocked",
            "yes",
        }
    return False


def run_inventory_copied_signals_stability(path: Path) -> tuple[dict[str, Any], list[str]]:
    blockers: list[str] = []
    result = subprocess.run(
        [sys.executable, str(path), "--json"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
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
            "public_or_runtime_claims": public_or_runtime_claims,
            "completion_claims_without_blocker": completion_claims_without_blocker,
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
                "enabled",
                "live",
                "operational",
                "promoted",
                "public",
                "ready",
                "supported",
                "true",
                "unlocked",
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
    result = subprocess.run(
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
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
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


def run_mission_transfer_dino_tribe_outcome_accounting(
    path: Path,
    manifest_path: Path,
    release_statement_path: Path | None,
) -> tuple[dict[str, Any], list[str]]:
    blockers: list[str] = []
    argv = [sys.executable, str(path), "--manifest", str(manifest_path), "--json"]
    if release_statement_path is not None:
        argv.extend(["--release-statement", str(release_statement_path)])
    result = subprocess.run(
        argv,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
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
    if payload.get("schema") != "obelisk.mission-transfer-dino-tribe-v1-outcome-accounting-check.v1":
        blockers.append("mission_transfer_dino_tribe_outcome_accounting_schema_mismatch")
    if result.returncode != 0 or payload.get("ready") is not True:
        blockers.append("mission_transfer_dino_tribe_outcome_accounting_invalid")
    if payload.get("surface") != "obelisk.mission_transfer_dino_tribe.v1":
        blockers.append("mission_transfer_dino_tribe_outcome_accounting_surface_mismatch")
    if set(payload.get("required_leaves", [])) != MISSION_TRANSFER_DINO_TRIBE_REQUIRED_LEAVES:
        blockers.append("mission_transfer_dino_tribe_required_leaves_mismatch")
    if set(payload.get("observed_leaves", [])) != MISSION_TRANSFER_DINO_TRIBE_REQUIRED_LEAVES:
        blockers.append("mission_transfer_dino_tribe_observed_leaves_mismatch")
    report_blockers = payload.get("blockers", [])
    if report_blockers:
        blockers.append("mission_transfer_dino_tribe_outcome_accounting_blockers_not_empty")
    allowed_per_leaf_promoted_claims = {"promotion_ready", "public_sdk_ready", "runtime_ready"}
    unexpected_public_or_runtime_claims = [
        claim
        for claim in public_or_runtime_claims
        if accounting_route != "per_leaf_promoted" or claim not in allowed_per_leaf_promoted_claims
    ]
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
    if completion_claims_without_blocker:
        blockers.append(SECONDARY_REPORT_COMPLETION_CLAIM_WITHOUT_BLOCKER)

    return (
        {
            "path": str(path),
            "exit_code": result.returncode,
            "schema": payload.get("schema"),
            "surface": payload.get("surface"),
            "ready": payload.get("ready"),
            "accounting_route": accounting_route,
            "candidate_only": payload.get("candidate_only"),
            "v1_accounted": payload.get("v1_accounted"),
            "promotion_ready": payload.get("promotion_ready"),
            "public_sdk_ready": payload.get("public_sdk_ready"),
            "runtime_ready": payload.get("runtime_ready"),
            "public_or_runtime_claims": public_or_runtime_claims,
            "completion_claims_without_blocker": completion_claims_without_blocker,
            "required_leaves": payload.get("required_leaves"),
            "observed_leaves": payload.get("observed_leaves"),
            "missing_leaf_families": payload.get("missing_leaf_families"),
            "release_statement": payload.get("release_statement"),
            "blockers": report_blockers,
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
    result = subprocess.run(
        [sys.executable, str(path), "--json"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
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
    result = subprocess.run(
        [sys.executable, str(path), "--json"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
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
        rf"^\s*{re.escape(surface_id)}\s*(?P<delimiter>:|\s+-\s+)\s*"
        rf"(?P<status>promoted|excluded|post-v1)(?:\s+-\s*(?P<details>.+)|\s*)$",
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
            canonical_reviewed_record = match.group("delimiter") == ":" and (
                found_status != "promoted" or has_reviewed_details
            )
            records.append((found_status, line.strip(), canonical_reviewed_record))
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


def release_statement_forbidden_broad_claims(text: str) -> list[str]:
    offenders: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        lowered = line.lower()
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
                full_clause = lowered[clause_start:clause_end]
                affirmative_not_phrase = FORBIDDEN_RELEASE_STATEMENT_AFFIRMATIVE_NOT_PHRASE.search(
                    full_clause
                )
                if (
                    FORBIDDEN_RELEASE_STATEMENT_BROAD_CLAIM_NEGATORS.search(claim_prefix)
                    and affirmative_not_phrase is None
                    and not release_claim_prefix_negator_is_detached(claim_prefix, matched_claim)
                ):
                    continue
                if (
                    FORBIDDEN_RELEASE_STATEMENT_BROAD_CLAIM_NEGATORS.search(claim_clause)
                    and affirmative_not_phrase is None
                    and (
                        not FORBIDDEN_RELEASE_STATEMENT_BROAD_CLAIM_NEGATORS.search(claim_prefix)
                        or not release_claim_prefix_negator_is_detached(claim_prefix, matched_claim)
                    )
                ):
                    continue
                if FORBIDDEN_RELEASE_STATEMENT_BROAD_CLAIM_NEGATED_REMAINDER.search(claim_remainder):
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
                ) and affirmative_not_phrase is None and not release_claim_prefix_negator_is_detached(
                    claim_prefix,
                    matched_claim,
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
    if not isinstance(surface_id, str) or status not in {"excluded", "post-v1"}:
        return False
    allowed_outcomes = required_release_statement_outcomes(surface)
    recorded_outcome = release_statement_recorded_outcome(text, surface_id)
    if recorded_outcome not in allowed_outcomes:
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
        return True
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
    normalized_key = parent_key.lower().replace("-", "_") if isinstance(parent_key, str) else None
    if normalized_key in STRICT_PROMOTION_EVIDENCE_SCHEMA_KEYS:
        try:
            text = json.dumps(value, sort_keys=True)
        except TypeError:
            text = str(value)
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
                and normalized_scope_text(item) in PROMOTION_EVIDENCE_FORBIDDEN_READY_SCOPES
            ):
                return True
            if evidence_has_forbidden_ready_scope(item):
                return True
        return False
    if isinstance(value, list):
        return any(evidence_has_forbidden_ready_scope(item) for item in value)
    return False


def report_is_limited_to_non_promotional_readiness(report: Any) -> bool:
    if not isinstance(report, dict):
        return False
    if report.get("planning_only") is True:
        return True
    if report.get("accepted_for_planning") is True:
        return True
    if report.get("candidate_only") is True:
        return True
    if report.get("pre_abi") is True:
        return True
    ready_scope = report.get("ready_scope")
    return isinstance(ready_scope, str) and ready_scope in {
        RUNTIME_EVIDENCE_READY_SCOPE,
        PUBLIC_CONTRACT_REVIEW_READY_SCOPE,
        BUNDLE_BUILDER_INPUTS_READY_SCOPE,
    }


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
            if not (
                relative_text == "tests/sdk_consumer"
                or relative_text.startswith("tests/sdk_consumer/")
                or relative_text == "tests/sdk_installed_consumer"
                or relative_text.startswith("tests/sdk_installed_consumer/")
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
        "installed_sdk_consumer_tests",
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
        if surface and surface.get("status") == "promoted":
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
                if (
                    key_name in forbidden_positive_keys
                    or key_name in forbidden_alias_keys
                    or BROAD_ROUTE_GATE_CLAIM_KEY_RE.fullmatch(key_name)
                ) and positive_installed_claim_value(key_name, item):
                    drift.append(f"positive_claim:{key_path}")
                visit(item, key_path)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]")

    visit(installed_shape)
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


def executed_test_artifact_has_command(report: dict[str, Any]) -> bool:
    command = report.get("command")
    if isinstance(command, str) and command.strip():
        return True
    argv = report.get("argv")
    return (
        isinstance(argv, list)
        and bool(argv)
        and all(isinstance(item, str) and item.strip() for item in argv)
    )


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
    elif not (
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
    raw_path = binding.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None, [f"{reason_prefix}:path_missing"]
    relative = repo_relative_evidence_path(raw_path)
    if relative is None:
        return None, [f"{reason_prefix}:path_not_repo_relative"]
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


def surface_record_sha256_for_certificate(surface: dict[str, Any]) -> str:
    sanitized = dict(surface)
    evidence = sanitized.get("evidence")
    if isinstance(evidence, dict):
        sanitized["evidence"] = {
            key: value
            for key, value in evidence.items()
            if key != "player_identity_promotion_certificate"
        }
    data = json.dumps(sanitized, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def active_player_identity_surface_record_sha256(manifest_path: Path) -> str | None:
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
            and surface.get("id") == "obelisk.player_identity.v1"
            and surface.get("status") == "promoted"
        ):
            return surface_record_sha256_for_certificate(surface)
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

    identity_evidence = certificate.get("evidence")
    if not isinstance(identity_evidence, dict):
        missing.append("player_identity_promotion_certificate:evidence_missing")
    else:
        active_surface_hash = active_player_identity_surface_record_sha256(manifest_path)
        if active_surface_hash is not None:
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
    permissions_admin_evidence = evidence.get("permissions_admin_promotion_evidence")
    if not isinstance(permissions_admin_evidence, dict):
        permissions_admin_evidence = {
            "player_identity_promotion_certificate": evidence.get("player_identity_promotion_certificate"),
            "query_failclosed_report": evidence.get("permissions_admin_query_failclosed_report"),
            "public_readiness_report": evidence.get("permissions_admin_public_readiness_report"),
            "executed_test_report": evidence.get("permissions_admin_executed_test_report"),
        }
    dependency_missing = permissions_admin_structured_promotion_evidence_missing(
        permissions_admin_evidence,
        manifest_path,
        public_header_path,
    )
    for reason in dependency_missing:
        missing.append(f"permissions_admin_{reason}")

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
    elif not dependency_missing and report_is_limited_to_non_promotional_readiness(readiness_report):
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
    command_response_evidence = evidence.get("command_response_promotion_evidence")
    if not isinstance(command_response_evidence, dict):
        command_response_evidence = {
            "public_readiness_report": evidence.get("command_response_public_readiness_report"),
            "executed_test_report": evidence.get("command_response_executed_test_report"),
        }
    dependency_missing = command_response_structured_promotion_evidence_missing(
        command_response_evidence,
        manifest_path,
        public_header_path,
    )
    for reason in dependency_missing:
        missing.append(f"command_response_{reason}")

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
    elif not dependency_missing and report_is_limited_to_non_promotional_readiness(readiness_report):
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
        expected = "post-v1 or excluded"
        return f"add one reviewed {expected} release-statement record satisfying this surface's exclusion contract"
    if status == "missing":
        return "restore the canonical blocker row in docs/public_sdk_surfaces.json"
    if surface_id in CANONICAL_V1_DEPENDENCY_SEQUENCE:
        return "priority dependency-chain blocker: promote with evidence; excluded/post-v1 cannot satisfy complete SDK"
    return "choose a reviewed v1 outcome: promote with evidence or explicitly exclude/post-v1 where the contract allows it"


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
    return None


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
        promotion_evidence_satisfied = bool(surface) and status == "promoted" and surface_has_promotion_evidence(surface)
        missing_required_terms = surface_missing_required_promotion_evidence(surface)
        missing_structured_evidence = surface_missing_structured_promotion_evidence(
            surface,
            manifest_path,
            public_header_path,
        )
        release_statement_contract_satisfied = False
        if status == "promoted":
            release_statement_contract_satisfied = release_statement_outcome == "promoted"
        elif status in {"post-v1", "excluded"} and surface_id in post_v1_or_excluded:
            allowed_outcomes = required_release_statement_outcomes(surface)
            release_statement_contract_satisfied = (
                release_statement_text is not None
                and release_statement_outcome in allowed_outcomes
                and release_statement_satisfies_exclusion_contract(release_statement_text, surface)
            )
        required_outcomes = sorted(required_release_statement_outcomes(surface)) if surface else []
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
            manifest_outcome in P0_DEPENDENCY_CHAIN_SCOPED_NON_COMPLETE_ALLOWED_OUTCOMES
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
                "release_statement_contract_satisfied": release_statement_contract_satisfied,
                "required_release_statement_outcomes": required_outcomes,
                "promotion_evidence_satisfied": promotion_evidence_satisfied,
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
    non_p0_release_statement_post_v1_or_excluded_outcomes = [
        row["surface"]
        for row in rows
        if row.get("is_p0_dependency_chain") is not True
        and row.get("release_statement_scoped_non_complete_bookkeeping") is True
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
        "p0_release_statement_scoped_non_complete_outcome_count": (
            len(p0_release_statement_scoped_non_complete_outcomes)
        ),
        "non_p0_release_statement_post_v1_or_excluded_outcome_count": (
            len(non_p0_release_statement_post_v1_or_excluded_outcomes)
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
        "p0_release_statement_scoped_non_complete_outcomes": (
            p0_release_statement_scoped_non_complete_outcomes
        ),
        "non_p0_release_statement_post_v1_or_excluded_outcomes": (
            non_p0_release_statement_post_v1_or_excluded_outcomes
        ),
        "route_gate_non_counting_surfaces": route_gate_non_counting_surfaces,
        "route_gate_non_counting_blockers": route_gate_non_counting_blockers,
        "route_gate_current_blockers": route_gate_current_blockers,
        "p0_scoped_non_complete_note": (
            "P0 dependency-chain excluded/post-v1 outcomes are scoped non-complete "
            "bookkeeping only; they remain unresolved for complete/full/production SDK claims."
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
                "must be resolved by promotion evidence or reviewed non-promoted outcomes "
                "before stable SDK wording is possible."
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
            elif not release_statement_names_outcome(release_statement_text, surface_id, status):
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
        for surface_id in completion_blockers_with_post_v1_or_excluded_outcome
        if release_statement_text is not None
        and surface_id in post_v1_or_excluded
        and not release_statement_duplicate_or_mixed_records(release_statement_text, surface_id)
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
    p0_scoped_non_complete_outcomes = blocker_outcome_summary["p0_scoped_non_complete_outcomes"]
    manifest_promoted_but_non_counting = blocker_outcome_summary[
        "manifest_promoted_but_non_counting"
    ]
    release_statement_scoped_non_complete_bookkeeping = blocker_outcome_summary[
        "release_statement_scoped_non_complete_bookkeeping"
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
            "Only rows with counts_toward_complete_sdk_claim=true count here; "
            "manifest or release-statement post-v1/excluded bookkeeping never increments this total."
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
            "excluded/post-v1 outcomes are scoped non-complete bookkeeping only."
        ),
    }
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

    return {
        "schema": "obelisk.public-sdk-v1-completion-check.v1",
        "status": "ready" if ready else "blocked",
        "ready": ready,
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
            "p0_chain_total": len(CANONICAL_V1_REQUIRED_DEPENDENCY_CHAIN),
            "p0_chain_promoted_count": len(p0_chain_counting_toward_claim),
            "p0_dependency_chain_total": len(CANONICAL_V1_REQUIRED_DEPENDENCY_CHAIN),
            "p0_dependency_chain_promoted_for_claim_count": len(p0_chain_counting_toward_claim),
            "p0_dependency_chain_remaining_for_claim_count": len(p0_chain_remaining_for_claim),
            "p0_dependency_chain_promoted_for_claim": p0_chain_counting_toward_claim,
            "p0_dependency_chain_remaining_for_claim": p0_chain_remaining_for_claim,
            "p0_dependency_chain_claim_accounting": p0_dependency_chain_claim_accounting,
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


def add_scoped_release_statement_result(report: dict[str, Any]) -> dict[str, Any]:
    blocking_report_blockers = [
        blocker
        for blocker in report.get("blockers", [])
        if blocker not in SCOPED_RELEASE_STATEMENT_ALLOWED_BLOCKERS
    ]
    if report.get("release_statement") is None:
        blocking_report_blockers.append("scoped_release_statement_path_required")
    scoped_ready = not blocking_report_blockers
    report["scoped_release_statement"] = {
        "ready": scoped_ready,
        "stable_v1_sdk_claim_allowed": False,
        "blocking_report_blockers": sorted(set(blocking_report_blockers)),
        "allowed_remaining_blockers": sorted(
            set(report.get("blockers", [])) & SCOPED_RELEASE_STATEMENT_ALLOWED_BLOCKERS
        ),
        "non_claim": (
            "A scoped release statement records reviewed exclusions/post-v1 outcomes only; "
            "it does not authorize v1.0 stable, complete SDK, full SDK, or production SDK wording."
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
            "Action: do not use installed SDK/package-shape evidence for Plugin Hub publication, v1 completion, or stable SDK wording.",
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
        "release_statement_missing_non_promoted_blocker_outcomes": [
            "The release statement is missing required outcome records for non-promoted blockers.",
            f"Surfaces: {format_human_list(report.get('release_statement_missing_blocker_outcomes'))}.",
            "Action: add one exact record per surface: '<surface-id>: excluded - ...' or '<surface-id>: post-v1 - ...'.",
        ],
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
        "authorize Plugin Hub publication, v1 completion, or stable SDK wording."
    )
    outcome_summary = report.get("v1_sdk_blocker_outcome_summary", {})
    if isinstance(outcome_summary, dict):
        print(
            "12-blocker outcome accounting: "
            f"{outcome_summary.get('manifest_outcome_missing_count', 0)} need manifest outcomes; "
            f"{outcome_summary.get('release_statement_outcome_missing_count', 0)} need release-statement outcomes; "
            f"{outcome_summary.get('dependency_chain_remaining_count', 0)} dependency-chain blockers remain."
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
    report = build_report(
        args.manifest,
        args.release_statement,
        args.public_header,
        args.contract_decisions_dir,
        args.command_permission_route_gate,
        args.inventory_copied_signals_stability,
        args.object_identity_resource_handle_readiness,
        args.mission_transfer_dino_tribe_outcome_accounting,
        args.structure_census_readiness,
        args.structure_build_policy_offline_intake,
    )
    if args.validate_release_statement_scope:
        report = add_scoped_release_statement_result(report)
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
