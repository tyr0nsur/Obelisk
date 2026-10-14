#!/usr/bin/env python3
"""Validate commands/replies public-readiness stays candidate/planning-only."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import check_command_chat_response_public_readiness as response_path_readiness
from native_prototype_guardrails import without_native_prototype_symbols
from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_DECISIONS = REPO_ROOT / "docs" / "commands_replies_public_contract_decisions.json"
DEFAULT_SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
DEFAULT_PUBLIC_HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"
DEFAULT_PUBLIC_HEADER_DECL = "include/obelisk/ObeliskApi.h"
DEFAULT_RESPONSE_PATH_REPORT_NAME = "command-chat-response-public-readiness.json"

REPORT_SCHEMA = "obelisk.commands-replies-public-readiness-check.v1"
DECISIONS_SCHEMA = "obelisk.commands-replies-public-contract-decisions.v1"
SURFACES_SCHEMA = "obelisk.public-sdk-surfaces.v1"
RESPONSE_PATH_REPORT_SCHEMA = "obelisk.command-chat-response-public-readiness-check.v1"
RESPONSE_PATH_READINESS_SCHEMA = "obelisk.reflection-snapshot-readiness.v1"
SURFACE = "obelisk.commands_replies.v1"
RESPONSE_PATH_SURFACE = "obelisk.command_chat_response_path.v1"
RESPONSE_PATH_SOURCE_ARTIFACT_KEYS = (
    "readiness_path",
    "decisions_path",
    "surfaces_path",
    "public_header_path",
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RESPONSE_PATH_REPORT_HANDOFF_REQUIREMENT_SCHEMA = (
    "obelisk.commands-replies-response-path-report-handoff-requirement.v1"
)
DEPENDENCY_CHAIN = (
    "obelisk.player_identity.v1",
    "obelisk.permissions_admin.v1",
    RESPONSE_PATH_SURFACE,
    SURFACE,
)
BLOCKED_BEHIND_SURFACES = list(DEPENDENCY_CHAIN[:-1])
PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA = "obelisk.player-identity-promotion-certificate.v1"
PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA = "obelisk.permissions-admin-promotion-certificate.v1"
COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA = "obelisk.command-chat-response-path-promotion-certificate.v1"
REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH = "evidence.reviewed_surface_record_sha256"
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
COMMANDS_REPLIES_PROMOTION_CERTIFICATE_SCHEMA = (
    "obelisk.commands-replies-promotion-certificate.v1"
)
COMMANDS_REPLIES_PROMOTION_CERTIFICATE_BUILD_REPORT_SCHEMA = (
    "obelisk.commands-replies-promotion-certificate-build-report.v1"
)
CURRENT_ROUTE_BLOCKER = "approved_runtime_evidence_missing"
ALLOWED_ROUTE_BLOCKERS = (
    "approved_runtime_evidence_missing",
    "identity_public_contract_gate_missing",
)
RUNTIME_EVIDENCE_ROUTE_BLOCKER = "approved_runtime_evidence_missing"
IDENTITY_CONTRACT_ROUTE_BLOCKER = "identity_public_contract_gate_missing"
ROUTE_BLOCKER_NEXT_ACTIONS = {
    RUNTIME_EVIDENCE_ROUTE_BLOCKER: {
        "next_action": "produce_approved_runtime_principal_lifecycle_evidence",
        "blocked_until": "approved_runtime_principal_lifecycle_evidence",
    },
    IDENTITY_CONTRACT_ROUTE_BLOCKER: {
        "next_action": "review_identity_public_contract_gate",
        "blocked_until": "reviewed_identity_public_contract",
    },
}
REQUIRED_DEPENDS_ON = list(DEPENDENCY_CHAIN[:-1])
MANIFEST_PROMOTION_STATUSES = frozenset(("promoted", "promoted-experimental-only"))
REQUIRED_DECISION_IDS = frozenset(
    (
        "dependency.promoted_player_identity",
        "dependency.promoted_permissions_admin",
        "dependency.promoted_command_chat_response_path",
        "abi.future_copied_command_payload",
        "abi.no_public_symbols_now",
        "auth.identity_permission_provenance",
        "lifecycle.owner_scoped_registration_cleanup",
        "parser.no_arkapi_copy",
        "abuse.rate_limit_audit_moderation_boundary",
        "separation.no_response_send_reply_moderation",
        "evidence.runtime_sdk_coverage",
        "release.not_sufficient_for_v1",
    )
)
REQUIRED_MIGRATION_ALLOWED_TERMS = frozenset(
    (
        "chat command",
        "console command",
        "admin-like command",
        "reply request",
        "permission action",
    )
)
REQUIRED_MIGRATION_SOURCE_KINDS = frozenset(("chat", "server_console", "rcon"))
REQUIRED_MIGRATION_REGISTRATION_SEMANTICS = frozenset(
    (
        "future command registration must be owner-token scoped",
        "future command names must be normalized by an Obelisk-owned contract before duplicate detection",
        "duplicate normalized command names must have deterministic owner-token scoped conflict handling",
        "unsupported or unknown source_kind fails closed",
        "permission denial or unknown result never dispatches a command",
        "missing permission policy provenance fails closed",
        "reply/send-chat/router planning must consume only runtime-owned principal and permissions provenance after separate promotion",
        "reply request is copied request data only and never implies response delivery until command_chat_response_path is separately promoted",
        "activation preconditions, beta notice sends, public reachability, request checks, and identity_public_contract_gate_missing aliases cannot unlock command replies, chat/send/broadcast APIs, command dispatch, or admin-like behavior before permissions/admin promotion",
    )
)
REQUIRED_MIGRATION_NON_COMPATIBILITY = frozenset(
    (
        "no ArkApi parser compatibility",
        "no AseApi parser compatibility",
        "no ArkApi or AseApi dispatch ordering compatibility",
        "no ArkApi or AseApi return semantics compatibility",
        "no direct plugin portability claim",
        "no copied command parser, control flow, offsets, layouts, vtables, native-call wrappers, or ABI semantics",
    )
)
REQUIRED_DECISION_PREFIX = (
    "dependency.promoted_player_identity",
    "dependency.promoted_permissions_admin",
    "dependency.promoted_command_chat_response_path",
)
REQUIRED_FORBIDDEN_PUBLIC_CONTRACT = frozenset(
    (
        "public command SDK/router",
        "public command parser",
        "command parser copied from ArkApi or AseApi",
        "activation preconditions, beta notice sends, public reachability, request checks, and identity_public_contract_gate_missing aliases cannot be used as command/reply unlocks",
        "public CallProcessEvent command or reply path",
        "raw ProcessEvent or legacy CallProcessEvent fallback",
        "public command_chat_response_path ABI",
        "reply ABI",
        "send-chat ABI",
        "principal or permission claims from command text",
        "principal or permission claims from operator config",
        "principal or permission claims from reply request",
        "principal or permission claims from router metadata",
        "runtime-owned principal or permission bypass",
        "raw UE pointers",
        "raw ProcessEvent params",
        "raw FString storage",
        "UObject pointers",
        "UFunction pointers",
        "FName/GObjects indices",
        "player lookup",
        "mutation",
        "return override",
    )
)
REQUIRED_AUTH_BEHAVIORS = frozenset(
    (
        "principal tuple source must be runtime-owned player identity observation before any command payload can consume player identity",
        "principal_handle, principal_generation, and principal_scope_flags must appear together in any future command payload that consumes player identity",
        "activation preconditions, beta notice sends, public reachability, request checks, and identity_public_contract_gate_missing aliases cannot unlock command replies, chat/send/broadcast APIs, command dispatch, or admin-like behavior before permissions/admin promotion",
        "principal_handle alone never authorizes command dispatch",
        "missing principal fails closed",
        "missing principal provenance fails closed",
        "missing principal_handle fails closed",
        "missing principal_generation fails closed",
        "missing principal_scope_flags fails closed",
        "plugin-supplied principal tuple fails closed",
        "command-supplied principal tuple fails closed",
        "operator-supplied principal tuple fails closed",
        "stale principal fails closed",
        "server process epoch mismatch fails closed",
        "unsupported principal_scope_flags fails closed",
        "missing permission policy provenance fails closed",
        "permission allow cannot be consumed without policy provenance",
        "permission allow must come from runtime-owned permissions/admin evaluation for the same principal_handle, principal_generation, and principal_scope_flags tuple",
        "permission denial or unknown result never dispatches a command",
        "reply requests, send-chat requests, and router metadata cannot establish principal identity, permission authority, or policy provenance",
        "reply/send-chat/router planning cannot consume permission allow until promoted permissions/admin returns allow with runtime-owned policy provenance",
        "command text remains copied request data only and cannot establish identity, permission authority, or policy provenance",
        "operator config remains policy input only and cannot establish command identity, principal identity, permission authority, or policy provenance",
        "command callbacks cannot self-attest permission authority",
    )
)
REQUIRED_IDENTITY_DEPENDENCY_BEHAVIORS = frozenset(
    (
        "accepted runtime evidence, reviewed identity contract aliases, and player-identity promotion certificate status text cannot replace a matching player-identity promotion certificate with current artifact hash and first chain position",
        "commands/replies planning cannot bypass identity promotion",
        "missing, mismatched, stale, hash-unbound, or wrong-position player-identity promotion certificates keep commands/replies non-counting",
    )
)
REQUIRED_PERMISSIONS_DEPENDENCY_BEHAVIORS = frozenset(
    (
        "permissions/admin shortcut aliases, command planning records, and response bridge records cannot stand in for the promoted permissions/admin certificate or the upstream player-identity promotion certificate",
        "commands/replies planning cannot bypass permissions/admin promotion",
        "permissions/admin must be promoted before commands can authorize execution, reply delivery, send-chat, broadcast, moderation, or admin-like behavior",
    )
)
REQUIRED_LIFECYCLE_BEHAVIORS = frozenset(
    (
        "command registrations are owner-token scoped",
        "duplicate command names have deterministic owner-scoped conflict handling",
        "plugin init failure removes all command registrations before dlclose",
        "plugin unload unregisters commands and waits for in-flight callbacks or fails closed without dlclose",
        "future command router, reply/send path, and response shortcuts require owner-scoped lifecycle and unregister cleanup before public ABI",
        "raw ProcessEvent and legacy CallProcessEvent fallback do not satisfy command lifecycle cleanup or dispatch drain",
        "self-unregister from a command callback is safe",
        "command callbacks cannot outlive copied payload storage",
        "server shutdown does not call into unmapped plugin code",
    )
)
REQUIRED_ABUSE_BEHAVIORS = frozenset(
    (
        "command dispatch attempts are rate-limited per plugin owner token and source scope",
        "command router, reply request, send-chat request, raw ProcessEvent, and legacy CallProcessEvent paths cannot bypass rate-limit, abuse, or sanitized audit gates",
        "malformed UTF-8, oversize commands, and unsupported source kinds fail closed",
        "audit records are sanitized and do not expose raw UE internals, platform IDs, raw player names, or secret policy contents",
        "operator controls can disable command dispatch without disabling passive chat intake",
        "moderation, ban, kick, mute, broadcast, scheduled notice, and admin mutation APIs remain separate promotions",
    )
)
REQUIRED_RUNTIME_OWNED_GATE_INPUTS = frozenset(
    (
        "principal_handle",
        "principal_generation",
        "principal_scope_flags",
        "server_process_epoch",
        "permission_decision",
        "permission_policy_epoch",
        "policy_source_id",
        "policy_source_generation",
        "authority_kind",
        "authority_generation",
    )
)
REQUIRED_RUNTIME_OWNED_FORBIDDEN_SOURCES = frozenset(
    (
        "activation preconditions",
        "beta notice send",
        "copied response intent planning",
        "identity_public_contract_gate_missing alias",
        "local chat seed",
        "local routing seed",
        "next-action metadata",
        "no-users passive runtime",
        "notice or bundle artifact",
        "passive evidence",
        "post-runtime planning metadata",
        "plugin input",
        "command text",
        "operator config",
        "public reachability",
        "request check",
        "response bridge",
        "reply request",
        "send-chat request",
        "chat/RCON/broadcast/send source alias",
        "side-lane evidence",
        "status report",
        "status metadata",
        "router metadata",
        "passive ChatMessageEvent",
        "raw ProcessEvent",
        "legacy CallProcessEvent",
    )
)
REQUIRED_NOT_SUFFICIENT = frozenset(
    (
        "activation preconditions met are not sufficient",
        "beta notice sent is not sufficient",
        "copied response intent planning is not sufficient",
        "identity_public_contract_gate_missing route blocker is not sufficient",
        "local routing or chat seeds are not sufficient",
        "next-action metadata is not sufficient",
        "no-users/passive runtime is not sufficient",
        "notice or status shortcut aliases are not sufficient",
        "passive evidence is not sufficient",
        "public reachability is not sufficient",
        "request checks are not sufficient",
        "response bridge planning is not sufficient",
        "route-ready aliases are not sufficient",
        "side-lane evidence is not sufficient",
        "passive ChatMessageEvent parsing",
        "plugin-local command parser scaffold",
        "static thunk orientation",
        "candidate vtable slots",
        "raw ProcessEvent callbacks",
        "legacy CallProcessEvent debug gate",
        "ArkApi or AseApi compatibility names",
        "command_chat_response_path planning status",
    )
)
REQUIRED_SURFACE_NOT_SUFFICIENT = frozenset(
    (
        "passive ChatMessageEvent parsing",
        "plugin-local command parser scaffold",
        "static thunk orientation",
        "candidate vtable slots",
        "raw ProcessEvent callbacks",
        "legacy CallProcessEvent debug access",
        "command_chat_response_path planning status",
    )
)
FUTURE_PUBLIC_ABI_REQUIRES = (
    {
        "surface": DEPENDENCY_CHAIN[0],
        "required_artifact": "approved_runtime_principal_lifecycle_evidence",
        "certificate_schema": PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
    },
    {
        "surface": DEPENDENCY_CHAIN[1],
        "certificate_schema": PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA,
        "requires_certificate_schema": PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
        "required_by_surface": RESPONSE_PATH_SURFACE,
    },
    {
        "surface": RESPONSE_PATH_SURFACE,
        "certificate_schema": COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA,
        "requires_certificate_schema": PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA,
        "required_by_surface": SURFACE,
    },
    {
        "surface": SURFACE,
        "required_evidence": [
            "copied_command_abi_layout_tests",
            "owner_token_lifecycle_tests",
            "permission_fail_closed_tests",
            "sdk_consumer_tests",
            "isolated_runtime_command_dispatch_evidence",
            "second_source_or_independently_reviewed_command_source_evidence",
        ],
    },
)
COMMAND_RESPONSE_PROMOTION_REQUIRED_ARTIFACT = {
    "surface": RESPONSE_PATH_SURFACE,
    "schema": COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA,
    "promotion_status": "promoted",
    "v1_dependency_chain_position": 3,
    "required_by_surface": SURFACE,
    "required_by_v1_dependency_chain_position": 4,
    "required_after": DEPENDENCY_CHAIN[1],
    "non_counting_until_present": True,
}
COMMANDS_REPLIES_PROMOTION_REQUIRED_ARTIFACT = {
    "surface": SURFACE,
    "schema": COMMANDS_REPLIES_PROMOTION_CERTIFICATE_SCHEMA,
    "certificate_key": "commands_replies_promotion_certificate",
    "promotion_status": "promoted",
    "v1_dependency_chain_position": 4,
    "required_after": RESPONSE_PATH_SURFACE,
    "required_prior_certificate_schema": COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA,
    "required_prior_certificate_key": "command_response_promotion_certificate",
    "required_prior_certificate_binding": "current hash-bound path+sha256 binding from docs/public_sdk_surfaces.json",
    "required_evidence": [
        "copied_command_abi_layout_tests",
        "owner_token_lifecycle_tests",
        "permission_fail_closed_tests",
        "sdk_consumer_tests",
        "isolated_runtime_command_dispatch_evidence",
        "second_source_or_independently_reviewed_command_source_evidence",
    ],
    "non_counting_until_present": True,
    "package_shape_status_beta_offline_shortcuts_count": False,
}
POST_RESPONSE_ABI_EVIDENCE_GUARDRAIL_SCHEMA = (
    "obelisk.commands-replies-post-response-abi-evidence-guardrail.v1"
)
POST_RESPONSE_FAIL_CLOSED_GUARDRAILS = (
    "append-only copied POD command ABI with abi_version and struct_size is required before promotion",
    "nonzero plugin_owner_token and an advertised commands/replies capability are required before dispatch",
    "runtime-owned principal tuple and permissions/admin provenance are required for the same server process epoch",
    "permission allow for the same principal tuple is required before command dispatch or reply/send-chat delivery",
    "owner-scoped command unregister must remove registrations and drain in-flight callbacks before unload",
    "malformed UTF-8, oversize commands, unsupported source_kind, and stale principals fail closed",
    "current command_chat_response_path promotion certificate must be path-and-sha-bound to the current upstream surface record; stale/current surface-record mismatches fail closed",
    "commands/replies standalone readiness requires a caller-supplied command/chat response public-readiness report with source-artifact paths that revalidate to the exact report payload",
    "commands/replies cannot infer, synthesize, summarize, or inline a command/chat response-path report from planning metadata",
    "command_chat_response_path planning summaries do not advance commands/replies; the current command_chat_response_path promotion certificate binding stays mandatory",
    "response/send/broadcast readiness aliases cannot count without valid upstream promotion certificates",
    "post-runtime planning metadata and chat/RCON/broadcast/send-source aliases cannot count without valid upstream promotion certificates",
    "source-kind/status metadata aliases for chat, RCON, broadcast, send-chat, replies, or response bridge cannot count without valid upstream promotion certificates",
    "certificate-looking metadata cannot replace path-and-sha-bound promotion certificates in docs/public_sdk_surfaces.json",
    "final/terminal, authz-ready, response-path-complete, reply-ready, public/stable SDK, P0 progress, beta/Discord ack, scoped release statement, and package-shape aliases cannot count without exact ordered predecessor certificates and current source hashes",
)
POST_RESPONSE_ABI_EVIDENCE_GUARDRAIL = {
    "schema": POST_RESPONSE_ABI_EVIDENCE_GUARDRAIL_SCHEMA,
    "surface": SURFACE,
    "planning_only": True,
    "trigger": "after_valid_player_identity_permissions_admin_and_command_response_promotion_certificates",
    "requires_valid_upstream_promotion_certificates": [
        PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
        PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA,
        COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA,
    ],
    "required_before_commands_replies_promotion_certificate": list(
        COMMANDS_REPLIES_PROMOTION_REQUIRED_ARTIFACT["required_evidence"]
    ),
    "required_fail_closed_guardrails": list(POST_RESPONSE_FAIL_CLOSED_GUARDRAILS),
    "certificate_metadata_counts_as_promotion": False,
    "response_send_broadcast_aliases_count_as_promotion": False,
    "counts_toward_public_sdk": False,
    "counts_toward_runtime": False,
    "counts_toward_v1_completion": False,
    "public_or_runtime_accounting_allowed": False,
    "public_readiness_ready": False,
    "promotion_ready": False,
    "public_abi_ready": False,
    "runtime_ready": False,
}
RESPONSE_PATH_REPORT_HANDOFF_REQUIREMENT = {
    "schema": RESPONSE_PATH_REPORT_HANDOFF_REQUIREMENT_SCHEMA,
    "surface": SURFACE,
    "required_prior_surface": RESPONSE_PATH_SURFACE,
    "required_source_artifact_keys": list(RESPONSE_PATH_SOURCE_ARTIFACT_KEYS),
    "caller_supplied_report_required": True,
    "source_artifact_revalidation_required": True,
    "exact_rebuilt_report_identity_required": True,
    "summary_report_allowed": False,
    "implicit_report_synthesis_allowed": False,
    "planning_summary_counts_as_response_path_report": False,
    "commands_replies_can_advance_before_command_response_promotion": False,
    "required_prior_certificate_schema": COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA,
    "required_prior_certificate_binding": (
        COMMANDS_REPLIES_PROMOTION_REQUIRED_ARTIFACT["required_prior_certificate_binding"]
    ),
    "planning_only": True,
    "counts_toward_public_sdk": False,
    "counts_toward_runtime": False,
    "counts_toward_v1_completion": False,
    "public_or_runtime_accounting_allowed": False,
    "public_readiness_ready": False,
    "promotion_ready": False,
    "public_abi_ready": False,
    "runtime_ready": False,
    "non_claim": (
        "This requirement describes a mandatory handoff input only; it is not response-path "
        "evidence, command-response promotion, commands/replies readiness, SDK/P0 progress, "
        "runtime delivery, or public ABI approval."
    ),
}
POST_COMMAND_RESPONSE_BLOCKER_DIAGNOSTIC_SCHEMA = (
    "obelisk.commands-replies-post-command-response-blocker-diagnostic.v1"
)
POST_COMMAND_RESPONSE_BLOCKER = "copied_command_payload_public_abi_contract"
POST_COMMAND_RESPONSE_NEXT_ACTION = "define_copied_command_payload_public_abi_contract"
POST_COMMAND_RESPONSE_REQUIRED_ACTIONS = (
    "define append-only copied POD command ABI with abi_version and struct_size",
    "prove owner-token scoped registration, unregister, init-failure cleanup, and unload drain",
    "prove runtime-owned principal and permissions/admin provenance for the same server process epoch",
    "prove malformed UTF-8, oversize commands, unsupported source_kind, and stale principals fail closed",
    "add SDK consumer tests that observe no public symbol or capability until promotion",
)
POST_COMMAND_RESPONSE_FORBIDDEN_UNLOCKS = (
    "replies/send-chat delivery",
    "broadcast/notices",
    "public CallProcessEvent",
    "runtime delivery",
    "public SDK readiness",
    "stable SDK readiness",
    "SDK/P0 progress",
)
DOWNSTREAM_CHAIN_GATE_SCHEMA = "obelisk.commands-replies-downstream-chain-gate.v1"
DOWNSTREAM_NON_COUNTING_ARTIFACT_CLASSES = frozenset(
    (
        "activation_preconditions",
        "beta_notice",
        "chat_rcon_broadcast_send_source_alias",
        "copied_response_intent_planning",
        "diagnostic_candidate",
        "local_chat_seed",
        "local_routing_seed",
        "machine_next_action",
        "next_action_metadata",
        "no_users_passive_runtime",
        "notice_bundle",
        "package_shape",
        "passive_chat_evidence",
        "passive_evidence",
        "passive_status",
        "post_runtime_planning_metadata",
        "public_reachability",
        "request_check",
        "request_pack",
        "response_bridge",
        "route_bundle",
        "route_snapshot",
        "scoped_release_statement",
        "side_lane_evidence",
        "status_report",
        "status_snapshot",
        "status_update",
        "support_tier_package_shape",
    )
)
CANDIDATE_CAPTURE_CLASSIFICATION = "candidate_only_non_counting"
CANDIDATE_CAPTURE_NON_COUNTING_SOURCES = (
    "beta notice drafts/actions",
    "beta capture plans",
    "beta capture packs",
    "chat/RCON/broadcast/send source alias probes",
    "command/chat-response candidate reports",
    "commands/replies command candidates",
    "commands/replies candidate captures",
    "debug capture artifacts",
    "multi-surface beta capture packs",
    "multi-surface beta capture plans",
    "passive logs",
    "passive monitor ticks/output",
    "post-runtime planning metadata",
    "response bridge candidates",
        "runtime window artifacts",
)
DOWNSTREAM_BLOCKER_SPECS = (
    {
        "id": "promote_command_chat_response_path_first",
        "surface": RESPONSE_PATH_SURFACE,
        "blocked_until": "command_chat_response_path_promotion_certificate",
        "required_after": DEPENDENCY_CHAIN[1],
        "required_certificate_schema": COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA,
    },
    {
        "id": "define_commands_replies_public_abi_after_response_path",
        "surface": SURFACE,
        "blocked_until": "copied_command_payload_public_abi_contract",
        "required_after": RESPONSE_PATH_SURFACE,
        "required_evidence": [
            "copied_command_abi_layout_tests",
            "owner_token_lifecycle_tests",
            "permission_fail_closed_tests",
            "sdk_consumer_tests",
        ],
    },
    {
        "id": "prove_commands_replies_runtime_dispatch_after_abi_contract",
        "surface": SURFACE,
        "blocked_until": "isolated_runtime_command_dispatch_evidence",
        "required_after": "copied_command_payload_public_abi_contract",
        "required_evidence": [
            "isolated_runtime_command_dispatch_evidence",
            "second_source_or_independently_reviewed_command_source_evidence",
        ],
    },
    {
        "id": "issue_commands_replies_promotion_certificate",
        "surface": SURFACE,
        "blocked_until": "commands_replies_promotion_certificate",
        "required_after": "isolated_runtime_command_dispatch_evidence",
        "required_prior_certificate_schema": COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA,
        "required_evidence": list(COMMANDS_REPLIES_PROMOTION_REQUIRED_ARTIFACT["required_evidence"]),
    },
)
DOWNSTREAM_BLOCKER_FALSE_FIELDS = (
    "satisfied",
    "counts_as_downstream_progress",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "public_or_runtime_accounting_allowed",
)
DOWNSTREAM_BLOCKER_ZERO_FIELDS = (
    "downstream_progress_contribution",
    "v1_completion_progress_contribution",
)
P0_METADATA_FALSE_FLAGS = {
    "accepted_for_evidence": False,
    "accepted_for_readiness": False,
    "command_response_unlocked": False,
    "commands_replies_unlocked": False,
    "counts_as_evidence": False,
    "counts_as_runtime_evidence": False,
    "counts_as_sdk_evidence": False,
    "counts_toward_complete_sdk_claim": False,
    "counts_toward_p0_dependency_chain_claim": False,
    "counts_toward_public_sdk": False,
    "counts_toward_runtime": False,
    "counts_toward_v1_completion": False,
    "evidence_ready": False,
    "p0_progress_ready": False,
    "public_abi_ready": False,
    "public_header_allowed": False,
    "public_or_runtime_accounting_allowed": False,
    "public_readiness_ready": False,
    "public_sdk_ready": False,
    "runtime_ready": False,
}
P0_METADATA_ZERO_FIELDS = {
    "claim_progress_contribution": 0,
    "complete_sdk_claim_progress_contribution": 0,
    "p0_dependency_chain_claim_progress_contribution": 0,
    "p0_dependency_chain_progress_contribution": 0,
    "progress": 0,
}
REQUIRED_HEADER_ABSENT_TOKENS = frozenset(
    (
        "OBELISK_API_CAPABILITY_COMMANDS",
        "OBELISK_API_CAPABILITY_CHAT_COMMANDS",
        "OBELISK_API_CAPABILITY_COMMAND_CHAT_RESPONSE_PATH",
        "OBELISK_API_CAPABILITY_COMMAND_RESPONSE",
        "OBELISK_API_CAPABILITY_CHAT_RESPONSE",
        "OBELISK_API_CAPABILITY_CHAT_REPLY",
        "OBELISK_API_CAPABILITY_COMMANDS_REPLIES",
        "OBELISK_API_CAPABILITY_COMMAND_REPLY",
        "OBELISK_API_CAPABILITY_COMMAND_REPLIES",
        "OBELISK_API_CAPABILITY_COMMAND_ROUTER",
        "OBELISK_API_CAPABILITY_CHAT_REPLIES",
        "OBELISK_API_CAPABILITY_CHAT_ROUTING",
        "OBELISK_API_CAPABILITY_CHAT_LOCAL_ROUTING",
        "OBELISK_API_CAPABILITY_SEND_CHAT",
        "OBELISK_API_CAPABILITY_BROADCAST",
        "OBELISK_API_CAPABILITY_NOTICES",
        "OBELISK_API_CAPABILITY_MODERATION",
        "OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT_RESPONSE",
        "OBELISK_COMMAND_ABI_VERSION",
        "OBELISK_COMMANDS_ABI_VERSION",
        "OBELISK_CHAT_COMMAND_ABI_VERSION",
        "OBELISK_CHAT_COMMANDS_ABI_VERSION",
        "OBELISK_COMMAND_CHAT_RESPONSE_ABI_VERSION",
        "OBELISK_COMMAND_RESPONSE_ABI_VERSION",
        "OBELISK_CHAT_RESPONSE_ABI_VERSION",
        "OBELISK_COMMAND_REPLY_ABI_VERSION",
        "OBELISK_CHAT_REPLY_ABI_VERSION",
        "OBELISK_COMMANDS_REPLIES_ABI_VERSION",
        "OBELISK_COMMAND_ROUTER_ABI_VERSION",
        "ObeliskCommandChatResponse",
        "ObeliskCommandResponse",
        "ObeliskChatResponse",
        "ObeliskCommandRegistration",
        "ObeliskCommandCallback",
        "ObeliskCommandPayload",
        "ObeliskCommandParser",
        "ObeliskArkApiCommandParser",
        "ObeliskAseApiCommandParser",
        "ObeliskCommandReply",
        "ObeliskChatReply",
        "ObeliskChatRoute",
        "ObeliskChatRouter",
        "ObeliskSendChat",
        "ObeliskBroadcast",
        "ObeliskNotice",
        "ObeliskModeration",
        "ObeliskRawFStringResponse",
        "ObeliskRawFStringCommand",
        "ObeliskRawFStringReply",
        "ObeliskProcessEventResponseShortcut",
        "ObeliskProcessEventCommandShortcut",
        "ObeliskCallProcessEventResponseShortcut",
        "ObeliskCallProcessEventCommandShortcut",
        "RegisterCommandChatResponse",
        "RegisterCommandResponse",
        "RegisterChatResponse",
        "RegisterChatRoute",
        "RegisterChatRouter",
        "RegisterCommandReply",
        "UnregisterCommandChatResponse",
        "UnregisterCommandResponse",
        "UnregisterChatResponse",
        "UnregisterCommandReply",
        "RegisterCommandWithOwnerToken",
        "UnregisterCommandWithOwnerToken",
        "ReplyToCommand",
        "ReplyToCommandWithOwnerToken",
        "RouteChat",
        "RouteChatWithOwnerToken",
        "SendChat",
        "SendChatWithOwnerToken",
        "BroadcastChat",
        "BroadcastNotice",
        "SendNotice",
        "ModerateChat",
        "RawFStringChatResponse",
        "RawFStringCommandResponse",
        "RawFStringCommandReply",
        "RawProcessEventChatResponse",
        "RawProcessEventCommandResponse",
        "RawProcessEventCommandReply",
        "ProcessEventChatResponse",
        "ProcessEventCommandResponse",
        "ProcessEventCommandReply",
        "ProcessEventReply",
        "CallProcessEventShortcut",
        "CallProcessEventResponseShortcut",
        "CallProcessEventCommandResponse",
        "CallProcessEventChatResponse",
        "CallProcessEventReply",
    )
)
FALSE_ONLY_KEYS = frozenset(
    (
        "activation_allowed",
        "activation_authorized",
        "activation_preconditions",
        "activation_preconditions_met",
        "activation_preconditions_ready",
        "activation_preconditions_unlock_allowed",
        "activation_ready",
        "arkapi_parser_copy_allowed",
        "aseapi_parser_copy_allowed",
        "beta_notice",
        "beta_capture_pack_ready",
        "beta_capture_plan_ready",
        "beta_notice_ready",
        "beta_notice_send_unlock_allowed",
        "beta_notice_sent",
        "beta_plan_ready",
        "broadcast_abi_allowed",
        "broadcast_allowed",
        "broadcast_api",
        "broadcast_api_allowed",
        "broadcast_ready",
        "broadcast_notice_api",
        "broadcast_notice_api_allowed",
        "broadcast_notice_ready",
        "call_process_event_response_allowed",
        "chat_api",
        "chat_api_allowed",
        "chat_send_api",
        "chat_send_api_allowed",
        "chat_send_ready",
        "candidate_capture_ready",
        "candidate_plan_ready",
        "command_route_ready",
        "command_candidate_ready",
        "command_parser_allowed",
        "command_router_allowed",
        "command_support_ready",
        "commands_replies_candidate_ready",
        "commands_replies_final_gate_ready",
        "commands_replies_final_ready",
        "commands_replies_ready",
        "commands_unlocked",
        "active_player_presence_ready",
        "active_players_ready",
        "debug_capture_ready",
        "diagnostic_drift_ready",
        "drift_ready",
        "observer_enabled",
        "observer_enabled_ready",
        "observer_enablement_ready",
        "player_presence_ready",
        "complete_sdk_claim_allowed",
        "complete_sdk_ready",
        "counts_toward_public_sdk",
        "counts_toward_runtime",
        "counts_toward_v1_completion",
        "accepted_runtime_evidence_only",
        "accepted_runtime_evidence_only_allowed",
        "accepted_runtime_evidence_only_ready",
        "accepted_runtime_evidence_sufficient",
        "accepted_runtime_evidence_sufficient_for_promotion",
        "accepted_runtime_evidence_ready",
        "admin_authority_ready",
        "authz_bridge_ready",
        "authz_ready",
        "authz_response_ready",
        "authorization_ready",
        "capability_advertised",
        "capability_allowed",
        "capability_ready",
        "full_sdk_claim_allowed",
        "full_sdk_ready",
        "command_chat_response_path_complete",
        "command_chat_response_path_completed",
        "command_chat_response_path_ready",
        "command_response_path_complete",
        "command_response_path_completed",
        "identity_contract_reviewed",
        "identity_public_contract_gate_missing",
        "identity_public_contract_gate_missing_allows_broadcast",
        "identity_public_contract_gate_missing_allows_command_replies",
        "identity_public_contract_gate_missing_allows_replies",
        "identity_public_contract_gate_missing_allows_send_chat",
        "identity_public_contract_gate_missing_unlock_allowed",
        "identity_public_contract_gate_accepted",
        "identity_public_contract_gate_passed",
        "identity_public_contract_gate_resolved",
        "identity_public_contract_allowed",
        "identity_public_contract_ready",
        "identity_public_contract_reviewed",
        "identity_public_contract_decision_record_contract_review_only",
        "identity_public_contract_decision_record_hash_current",
        "identity_public_contract_decision_record_reviewed",
        "reviewed_hash_current_contract_review_only",
        "reviewed_identity_contract_complete",
        "reviewed_identity_public_contract",
        "reviewed_identity_public_contract_ready",
        "reviewed_player_identity_public_contract",
        "reviewed_player_identity_public_contract_ready",
        "identity_evidence_accepted",
        "identity_review_complete",
        "identity_contract_review_complete",
        "final_artifact_accepted",
        "final_artifact_ready",
        "final_certificate_accepted",
        "final_certificate_metadata_ready",
        "final_certificate_ready",
        "final_certificate_status_ready",
        "final_gate_accepted",
        "final_gate_ready",
        "final_gate_unlocked",
        "operator_approval_granted",
        "parser_allowed",
        "permission_header_allowed",
        "permission_ready",
        "permissions_admin_ready",
        "permissions_admin_route_ready",
        "permissions_query_ready",
        "permissions_ready",
        "permissions_unlocked",
        "planning_layout_accepted",
        "planning_layout_gate_accepted",
        "planning_layout_gate_ready",
        "planning_layout_public_abi_ready",
        "planning_layout_public_reply_abi_ready",
        "planning_layout_public_reply_or_send_chat_abi_ready",
        "planning_layout_public_send_chat_abi_ready",
        "planning_layout_reply_abi_ready",
        "planning_layout_reply_or_send_chat_abi_ready",
        "planning_layout_send_chat_abi_ready",
        "player_identity_evidence_accepted",
        "player_identity_public_contract_ready",
        "player_identity_promotion_certificate_ready",
        "principal_ready",
        "production_sdk_claim_allowed",
        "production_sdk_ready",
        "promotion_certificate_ready",
        "promotion_ready",
        "public_abi_allowed",
        "public_abi_ready",
        "public_abi_unlocked",
        "public_broadcast_abi_allowed",
        "public_broadcast_api",
        "public_broadcast_api_allowed",
        "public_broadcast_notice_api",
        "public_broadcast_notice_api_allowed",
        "public_bridge_abi_allowed",
        "public_chat_api",
        "public_chat_api_allowed",
        "public_chat_send_api",
        "public_chat_send_api_allowed",
        "public_chat_send_ready",
        "public_capability_advertised",
        "public_capability_allowed",
        "public_capability_ready",
        "public_or_runtime_accounting_allowed",
        "public_command_parser_allowed",
        "public_command_router_allowed",
        "public_contract_allowed",
        "public_contract_ready",
        "public_contract_reviewed",
        "public_reachability",
        "public_reachability_counts_as_approved_runtime_evidence",
        "public_reachability_ready",
        "public_reachability_satisfies_runtime_evidence",
        "public_reachability_status",
        "public_reachability_unlock_allowed",
        "public_header_allowed",
        "public_header_ready",
        "public_moderation_api",
        "public_moderation_api_allowed",
        "public_moderation_ready",
        "public_notice_abi_allowed",
        "public_notice_api",
        "public_notice_api_allowed",
        "public_notice_scheduler_api",
        "public_notice_scheduler_api_allowed",
        "public_notices_abi_allowed",
        "public_notices_api",
        "public_notices_api_allowed",
        "public_route_gate_ready",
        "public_route_ready",
        "public_reply_api",
        "public_reply_api_unlocked",
        "public_reply_send_broadcast_ready",
        "public_readiness_ready",
        "public_reply_abi_ready",
        "public_reply_abi_allowed",
        "public_reply_abi_unlocked",
        "public_reply_or_send_chat_abi_allowed",
        "public_reply_or_send_chat_abi_unlocked",
        "public_response_abi_allowed",
        "public_response_path_allowed",
        "public_response_path_ready",
        "public_sdk",
        "public_sdk_ready",
        "public_send_chat_api",
        "public_send_chat_api_unlocked",
        "release_readiness_ready",
        "response_complete",
        "response_completed",
        "raw_fstring_response_allowed",
        "raw_fstring_shortcut",
        "raw_fstring_shortcut_allowed",
        "raw_fstring_shortcut_ready",
        "raw_process_event_shortcut",
        "raw_process_event_shortcut_allowed",
        "raw_process_event_shortcut_ready",
        "reply_send_chat_router_claims_allowed",
        "reply_send_broadcast_alias_ready",
        "reply_send_broadcast_ready",
        "reply_ready",
        "reply_abi_allowed",
        "reply_abi_unlocked",
        "reply_api_allowed",
        "reply_api_unlocked",
        "public_send_chat_abi_allowed",
        "public_send_chat_abi_unlocked",
        "reply_allowed",
        "reply_unlocked",
        "reply_path_ready",
        "route_ready",
        "route_accepted",
        "route_accepted_as_public_abi",
        "route_accepted_as_public_reply_abi",
        "route_accepted_as_public_reply_or_send_chat_abi",
        "route_accepted_as_public_send_chat_abi",
        "route_accepted_for_public_abi",
        "route_accepted_for_public_reply_abi",
        "route_accepted_for_public_reply_or_send_chat_abi",
        "route_accepted_for_public_send_chat_abi",
        "route_accepted_for_reply_send_chat_abi",
        "route_acceptance_ready",
        "route_blocker_bypass",
        "route_blocker_bypass_allowed",
        "route_blocker_bypass_ready",
        "route_blocker_bypassed",
        "current_route_blocker_bypassed",
        "remaining_route_blockers_bypassed",
        "dependency_gate_bypass_allowed",
        "dependency_route_bypass_allowed",
        "route_gate_ready",
        "route_gate_unlocked",
        "route_readiness_ready",
        "response_header_allowed",
        "moderation_allowed",
        "moderation_api",
        "moderation_api_allowed",
        "moderation_ready",
        "multi_surface_beta_capture_pack_ready",
        "multi_surface_beta_capture_plan_ready",
        "multi_surface_beta_plan_ready",
        "notice_allowed",
        "notice_api",
        "notice_api_allowed",
        "notice_ready",
        "notices_allowed",
        "notices_api",
        "notices_api_allowed",
        "notices_ready",
        "runtime_approval",
        "runtime_approval_granted",
        "runtime_delivery_allowed",
        "runtime_readiness_allowed",
        "runtime_ready",
        "runtime_work_authorized",
        "discord_sent",
        "live_ops_authorization_granted",
        "live_ops_approval_granted",
        "live_ops_authorized",
        "live_ops_ready",
        "live_operations_authorized",
        "live_server_authorized",
        "live_posture_ready",
        "live_server_posture_ready",
        "runtime_posture_ready",
        "server_posture_ready",
        "runtime_window_ready",
        "runtime_window_status_ready",
        "runtime_window_manifest_ready",
        "runtime_window_report_ready",
        "production_server_authorized",
        "response_send_broadcast_ready",
        "send_chat_api_allowed",
        "send_chat_api_unlocked",
        "send_chat_allowed",
        "send_chat_abi_unlocked",
        "send_chat_ready",
        "send_chat_unlocked",
        "send_ready",
        "send_route_ready",
        "send_source_ready",
        "send_source_status_ready",
        "send_status",
        "send_status_ready",
        "source_ready",
        "source_status_ready",
        "request_check",
        "request_check_ready",
        "request_check_unlock_allowed",
        "request_json_check_ready",
        "request_pack",
        "request_pack_ready",
        "request_pack_unlock_allowed",
        "rcon_command_ready",
        "rcon_command_status",
        "rcon_ready",
        "rcon_route_ready",
        "rcon_route_status",
        "rcon_status",
        "p0_completion_ready",
        "p0_dependency_ready",
        "p0_dependency_satisfied",
        "p0_progress_claim_allowed",
        "p0_progress_ready",
        "p0_release_ready",
        "p0_surface_ready",
        "sdk_p0_progress_claim_allowed",
        "sdk_p0_progress_ready",
        "process_event_shortcut_allowed",
        "process_event_shortcut_ready",
        "plugin_hub_package_shape_ready",
        "plugin_hub_ready",
        "plugin_hub_support_ready",
        "call_process_event_shortcut_allowed",
        "call_process_event_shortcut_ready",
        "call_process_event_response_shortcut_allowed",
        "call_process_event_reply_shortcut_allowed",
        "chat_seed_ready",
        "command_principal_authz_response_bridge_ready",
        "command_principal_authz_response_bridge_unlocked",
        "copied_response_intent_planning_ready",
        "copied_response_intent_ready",
        "copied_response_planning_ready",
        "server_operations_authorized",
        "stable_claim_allowed",
        "stable_sdk_claim_allowed",
        "stable_sdk_ready",
        "local_chat_seed_ready",
        "local_route_seed_ready",
        "local_routing_seed_ready",
        "machine_next_action_accepted",
        "machine_next_action_completed",
        "machine_next_action_progress_ready",
        "machine_next_action_ready",
        "next_action_accepted",
        "next_action_completed",
        "next_action_counts_toward_p0",
        "next_action_counts_toward_p0_dependency_chain",
        "next_action_progress_ready",
        "next_action_ready",
        "next_action_sequence_accepted",
        "next_action_sequence_completed",
        "next_action_sequence_counts_toward_p0",
        "next_action_sequence_progress_ready",
        "next_action_sequence_ready",
        "notice_status_ready",
        "passive_status_ready",
        "passive_chat_evidence_ready",
        "passive_evidence_ready",
        "passive_evidence_sufficient",
        "passive_evidence_unlock_allowed",
        "passive_log_ready",
        "passive_logs_ready",
        "response_bridge_ready",
        "response_bridge_unlocked",
        "response_path_complete",
        "response_path_completed",
        "response_path_ready",
        "routing_seed_ready",
        "scoped_release_statement_ready",
        "scoped_release_statement_counts_toward_completion",
        "scoped_release_statement_counts_toward_complete_sdk_claim",
        "scoped_release_statement_outcomes_satisfy_completion",
        "status_report_accepted",
        "status_report_completed",
        "status_report_counts_toward_p0",
        "status_report_counts_toward_p0_dependency_chain",
        "status_report_progress_ready",
        "status_report_ready",
        "status_snapshot_accepted",
        "status_snapshot_ready",
        "status_update_accepted",
        "status_update_ready",
        "v1_0_stable_ready",
        "v1_completion_evidence",
        "v1_completion_ready",
    )
)
POSITIVE_ALIAS_CLAIMS = frozenset(
    (
        "activation_preconditions_met",
        "activation_preconditions_ready",
        "approved_runtime_evidence_placeholder",
        "approved_runtime_evidence_placeholder_ready",
        "approved_runtime_placeholder",
        "approved_runtime_placeholder_ready",
        "beta_notice_ready",
        "beta_notice_state",
        "beta_notice_state_ready",
        "beta_notice_sent",
        "beta_capture_pack_ready",
        "beta_capture_plan_ready",
        "beta_plan_ready",
        "multi_surface_beta_capture_pack_ready",
        "multi_surface_beta_capture_plan_ready",
        "multi_surface_beta_plan_ready",
        "candidate_capture_ready",
        "candidate_plan_ready",
        "authz_bridge_ready",
        "authz_ready",
        "authz_response_ready",
        "authorization_ready",
        "command_candidate_ready",
        "command_chat_response_path_complete",
        "command_chat_response_path_completed",
        "command_chat_response_path_ready",
        "command_response_path_complete",
        "command_response_path_completed",
        "command_response_alias",
        "command_response_alias_ready",
        "command_chat_response_alias",
        "command_chat_response_alias_ready",
        "commands_replies_candidate_ready",
        "commands_replies_final_gate_ready",
        "commands_replies_final_ready",
        "copied_log_status",
        "copied_log_status_ready",
        "active_player_presence_ready",
        "active_players_ready",
        "debug_capture_ready",
        "diagnostic_planning_artifact",
        "diagnostic_planning_artifact_ready",
        "diagnostic_drift_ready",
        "drift_ready",
        "observer_enabled",
        "observer_enabled_ready",
        "observer_enablement_ready",
        "player_presence_ready",
        "discord_sent",
        "public_abi_unlocked",
        "public_reply_abi_unlocked",
        "public_reply_api_unlocked",
        "public_reply_or_send_chat_abi_unlocked",
        "public_send_chat_abi_unlocked",
        "public_send_chat_api_unlocked",
        "public_reachability_ready",
        "request_check_ready",
        "request_pack_ready",
        "reply_path_ready",
        "reply_ready",
        "reply_abi_unlocked",
        "reply_api_unlocked",
        "reply_unlocked",
        "planning_layout_accepted",
        "planning_layout_gate_ready",
        "planning_layout_public_abi_ready",
        "planning_layout_public_reply_abi_ready",
        "planning_layout_public_reply_or_send_chat_abi_ready",
        "planning_layout_public_send_chat_abi_ready",
        "planning_layout_reply_abi_ready",
        "planning_layout_reply_or_send_chat_abi_ready",
        "planning_layout_send_chat_abi_ready",
        "accepted_runtime_evidence_only",
        "accepted_runtime_evidence_only_ready",
        "accepted_runtime_evidence_sufficient",
        "accepted_runtime_evidence_alone",
        "identity_public_contract_gate_accepted",
        "identity_public_contract_gate_passed",
        "identity_public_contract_gate_resolved",
        "reviewed_identity_contract_complete",
        "reviewed_identity_public_contract",
        "reviewed_identity_public_contract_ready",
        "reviewed_player_identity_public_contract",
        "reviewed_player_identity_public_contract_ready",
        "raw_fstring_shortcut",
        "raw_fstring_shortcut_ready",
        "raw_process_event_shortcut",
        "raw_process_event_shortcut_ready",
        "process_event_shortcut_allowed",
        "process_event_shortcut_ready",
        "call_process_event_shortcut_allowed",
        "call_process_event_shortcut_ready",
        "chat_seed_ready",
        "command_principal_authz_response_bridge_ready",
        "copied_response_intent_planning_ready",
        "copied_response_intent_ready",
        "route_blocker_bypass",
        "route_blocker_bypassed",
        "dependency_gate_bypass_allowed",
        "dependency_route_bypass_allowed",
        "local_chat_seed_ready",
        "local_routing_seed_ready",
        "machine_next_action_ready",
        "next_action_ready",
        "next_action_sequence_ready",
        "notice_status_ready",
        "passive_status_ready",
        "passive_chat_evidence_ready",
        "passive_evidence_ready",
        "passive_evidence_sufficient",
        "passive_log_ready",
        "passive_logs_ready",
        "response_bridge_ready",
        "response_complete",
        "response_completed",
        "response_path_complete",
        "response_path_completed",
        "response_path_ready",
        "status_report_ready",
        "status_snapshot_ready",
        "status_update_ready",
        "p0_progress_ready",
        "p0_dependency_satisfied",
        "sdk_p0_progress_ready",
        "live_ops_authorized",
        "live_ops_authorization_granted",
        "live_ops_approval_granted",
        "live_operations_authorized",
        "live_server_authorized",
        "live_posture_ready",
        "live_server_posture_ready",
        "runtime_posture_ready",
        "server_posture_ready",
        "route_accepted",
        "route_accepted_as_public_abi",
        "route_accepted_as_public_reply_abi",
        "route_accepted_as_public_reply_or_send_chat_abi",
        "route_accepted_as_public_send_chat_abi",
        "route_accepted_for_public_abi",
        "route_accepted_for_public_reply_abi",
        "route_accepted_for_public_reply_or_send_chat_abi",
        "route_accepted_for_public_send_chat_abi",
        "route_accepted_for_reply_send_chat_abi",
        "route_acceptance_ready",
        "final_artifact_accepted",
        "final_artifact_ready",
        "final_certificate_accepted",
        "final_certificate_metadata_ready",
        "final_certificate_ready",
        "final_certificate_status_ready",
        "final_gate_accepted",
        "final_gate_ready",
        "final_gate_unlocked",
        "send_chat_abi_unlocked",
        "send_chat_api_unlocked",
        "send_chat_unlocked",
        "send_ready",
        "send_route_ready",
        "send_source_ready",
        "send_source_status_ready",
        "send_status_ready",
    )
)
CERTIFICATE_GATED_ALIAS_CLAIMS = frozenset(
    (
        "bridge_ready",
        "bridge_unlocked",
        "activation_preconditions_met",
        "activation_preconditions_ready",
        "approved_runtime_evidence_placeholder",
        "approved_runtime_evidence_placeholder_ready",
        "approved_runtime_placeholder",
        "approved_runtime_placeholder_ready",
        "beta_notice_sent",
        "beta_notice_state",
        "beta_notice_state_ready",
        "beta_capture_pack_ready",
        "beta_capture_plan_ready",
        "beta_plan_ready",
        "multi_surface_beta_capture_pack_ready",
        "multi_surface_beta_capture_plan_ready",
        "multi_surface_beta_plan_ready",
        "candidate_capture_ready",
        "candidate_plan_ready",
        "authz_bridge_ready",
        "authz_ready",
        "authz_response_ready",
        "authorization_ready",
        "chat_seed_ready",
        "command_candidate_ready",
        "command_chat_response_path_complete",
        "command_chat_response_path_completed",
        "command_chat_response_path_ready",
        "command_response_path_complete",
        "command_response_path_completed",
        "command_response_alias",
        "command_response_alias_ready",
        "command_chat_response_alias",
        "command_chat_response_alias_ready",
        "commands_replies_candidate_ready",
        "commands_replies_final_gate_ready",
        "commands_replies_final_ready",
        "command_principal_authz_response_bridge_ready",
        "copied_log_status",
        "copied_log_status_ready",
        "copied_response_intent_planning_ready",
        "copied_response_intent_ready",
        "active_player_presence_ready",
        "active_players_ready",
        "diagnostic_planning_artifact",
        "diagnostic_planning_artifact_ready",
        "diagnostic_drift_ready",
        "drift_ready",
        "discord_sent",
        "observer_enabled",
        "observer_enabled_ready",
        "observer_enablement_ready",
        "local_chat_seed_ready",
        "local_route_seed_ready",
        "local_routing_seed_ready",
        "player_presence_ready",
        "machine_next_action_ready",
        "next_action_ready",
        "next_action_sequence_ready",
        "notice_status_ready",
        "passive_status_ready",
        "passive_chat_evidence_ready",
        "passive_evidence_ready",
        "passive_evidence_sufficient",
        "passive_log_ready",
        "passive_logs_ready",
        "package_shape_accepted",
        "package_shape_evidence",
        "package_shape_evidence_ready",
        "package_shape_install_ready",
        "public_reachability_ready",
        "public_readiness_ready",
        "public_runtime_readiness_accepted",
        "public_runtime_readiness_ready",
        "public_runtime_ready",
        "public_response_send_broadcast_ready",
        "reply_path_ready",
        "reply_ready",
        "response_status_report",
        "response_status_report_accepted",
        "response_status_report_ready",
        "response_send_broadcast_ready",
        "request_check_ready",
        "request_pack_ready",
        "route_acceptance_ready",
        "route_accepted",
        "route_cleared",
        "route_cleared_for_public_abi",
        "route_cleared_for_public_reply_or_send_chat_abi",
        "route_cleared_for_public_send_chat_abi",
        "identity_public_contract_gate_accepted",
        "identity_public_contract_gate_passed",
        "identity_public_contract_gate_resolved",
        "reviewed_identity_public_contract",
        "reviewed_identity_public_contract_ready",
        "reviewed_player_identity_public_contract",
        "reviewed_player_identity_public_contract_ready",
        "response_bridge_ready",
        "response_complete",
        "response_completed",
        "response_path_complete",
        "response_path_completed",
        "response_path_ready",
        "runtime_readiness_accepted",
        "runtime_readiness_ready",
        "runtime_ready",
        "live_posture_ready",
        "live_server_posture_ready",
        "runtime_posture_ready",
        "server_posture_ready",
        "routing_seed_ready",
        "scoped_release_statement_counts_toward_complete_sdk_claim",
        "scoped_release_statement_counts_toward_completion",
        "scoped_release_statement_outcomes_satisfy_completion",
        "scoped_release_statement_ready",
        "scoped_statement_counts_toward_complete_sdk_claim",
        "scoped_statement_counts_toward_completion",
        "scoped_statement_outcomes_satisfy_completion",
        "scoped_statement_ready",
        "status_report_ready",
        "status_snapshot_ready",
        "status_update_ready",
        "support_tier_package_ready",
        "support_tier_package_shape_ready",
        "support_tier_readiness",
        "support_tier_report",
        "support_tier_report_ready",
        "final_artifact_accepted",
        "final_artifact_ready",
        "final_certificate_accepted",
        "final_certificate_metadata_ready",
        "final_certificate_ready",
        "final_certificate_status_ready",
        "final_gate_accepted",
        "final_gate_ready",
        "final_gate_unlocked",
        "terminal_certificate_accepted",
        "terminal_certificate_metadata",
        "terminal_certificate_metadata_accepted",
        "terminal_certificate_metadata_ready",
        "terminal_certificate_ready",
        "terminal_certificate_status",
        "terminal_certificate_status_ready",
    )
)
IDENTITY_GATE_ALIAS_KEY_TOKENS = frozenset(
    (
        "allow",
        "allowed",
        "allows",
        "authorizes",
        "authorized",
        "broadcast",
        "bypass",
        "bypassed",
        "bypasses",
        "command_reply",
        "command_replies",
        "commands_replies",
        "enable",
        "enabled",
        "enables",
        "opened",
        "opens",
        "pass",
        "passed",
        "passes",
        "ready",
        "replies",
        "reply",
        "send_chat",
        "unlock",
        "unlocked",
        "unlocks",
    )
)
UPSTREAM_PROMOTION_CERTIFICATE_SCHEMAS = (
    PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
    PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA,
    COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA,
)
PROMOTION_CERTIFICATE_BUILD_REPORT_SCHEMAS = (
    PLAYER_IDENTITY_PROMOTION_CERTIFICATE_BUILD_REPORT_SCHEMA,
    PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_BUILD_REPORT_SCHEMA,
    COMMAND_RESPONSE_PROMOTION_CERTIFICATE_BUILD_REPORT_SCHEMA,
    COMMANDS_REPLIES_PROMOTION_CERTIFICATE_BUILD_REPORT_SCHEMA,
)
PROMOTION_CERTIFICATE_METADATA_SCHEMAS = frozenset(
    UPSTREAM_PROMOTION_CERTIFICATE_SCHEMAS
    + (COMMANDS_REPLIES_PROMOTION_CERTIFICATE_SCHEMA,)
    + PROMOTION_CERTIFICATE_BUILD_REPORT_SCHEMAS
)
PROMOTION_CERTIFICATE_METADATA_KEYS = frozenset(
    (
        "certificate_build_report",
        "certificate_builder_report",
        "certificate_generation_report",
        "certificate_schema",
        "depends_on_certificate_schema",
        "depends_on_certificate_schemas",
        "generated_certificate",
        "generated_certificate_reference",
        "generated_promotion_certificate",
        "generated_promotion_certificate_reference",
        "identity_surface_certificate_binding_valid",
        "output_certificate",
        "player_identity_promotion_certificate",
        "permissions_admin_promotion_certificate",
        "command_response_promotion_certificate",
        "commands_replies_promotion_certificate",
        "promotion_certificate",
        "promotion_certificate_schema",
        "promotion_certificate_builder_report",
        "required_certificate_schema",
        "required_prior_certificate_schema",
        "reviewed_artifact_hash",
        "reviewed_surface_record_sha256",
        "v1_dependency_chain_position",
    )
)
HASH_BOUND_PROMOTION_CERTIFICATE_BINDING_KEYS = frozenset(("path", "sha256"))
PROMOTION_CERTIFICATE_OVERCLAIM_SCAN_EXEMPT_KEYS = frozenset(
    (
        "chain_position",
        "dependency_chain",
        "missing_mismatched_or_stale_certificate_counts",
        "promotion_status",
        "required_by_chain_position",
        "required_by_surface",
        "required_by_v1_dependency_chain_position",
        "required_reviewed_artifact_hash",
        "reviewed_artifact_hash_policy",
        "schema",
        "surface_id",
        "v1_dependency_chain",
        "v1_dependency_chain_position",
    )
)
PROMOTION_CERTIFICATE_BUILDER_REPORT_KEYS = frozenset(
    (
        "certificate_build_report",
        "certificate_builder_report",
        "certificate_generation_report",
        "generated_certificate",
        "generated_certificate_reference",
        "generated_promotion_certificate",
        "generated_promotion_certificate_reference",
        "promotion_certificate_builder_report",
    )
)
SPLIT_CLAIM_NAME_KEYS = frozenset(
    (
        "alias",
        "claim",
        "field",
        "flag",
        "key",
        "name",
        "property",
    )
)
SPLIT_CLAIM_VALUE_KEYS = frozenset(
    (
        "allowed",
        "enabled",
        "ready",
        "state",
        "status",
        "value",
        "claim_state",
        "claim_value",
        "is_ready",
        "accepted",
        "approved",
        "authorized",
        "available",
        "complete",
        "completed",
        "delivered",
        "outcome",
        "promoted",
        "public",
        "result",
        "sent",
        "source_accepted",
        "source_outcome",
        "source_ready",
        "source_result",
        "source_state",
        "source_status",
        "source_supported",
        "unlocked",
        "verdict",
    )
)
SOURCE_MARKER_KEYS = frozenset(("source_marker", "source_markers"))
SOURCE_PROVENANCE_CONTEXT_KEYS = frozenset(
    (
        "artifact_provenance",
        "channel",
        "command_channel",
        "command_source",
        "delivery_channel",
        "delivery_source",
        "evidence_provenance",
        "metadata_provenance",
        "provenance",
        "provenance_marker",
        "provenance_markers",
        "reply_channel",
        "reply_source",
        "response_channel",
        "response_source",
        "route_channel",
        "route_source",
        "review_provenance",
        "route_provenance",
        "send_channel",
        "send_source",
        "snapshot_provenance",
        "source",
        "source_channel",
        "source_kind",
        "source_provenance",
        "source_provenances",
        "source_type",
        "transport",
        "transport_channel",
        "transport_source",
    )
)
SOURCE_CONTEXT_KEYS = SOURCE_MARKER_KEYS | SOURCE_PROVENANCE_CONTEXT_KEYS
SOURCE_STATUS_KEYS = frozenset(
    (
        "source_accepted",
        "source_outcome",
        "source_ready",
        "source_result",
        "source_state",
        "source_status",
        "source_supported",
        "is_ready",
        "outcome",
        "ready",
        "result",
        "state",
        "status",
    )
)
SOURCE_ALIAS_CONTEXT_VALUES = frozenset(
    (
        "approved_runtime_evidence_placeholder",
        "approved_runtime_placeholder",
        "broadcast",
        "broadcast_source",
        "broadcast_status",
        "chat",
        "chat_channel",
        "chat_rcon_broadcast_send",
        "chat_rcon_broadcast_send_source_alias",
        "chat_source",
        "command_reply",
        "command_replies",
        "command_response_alias",
        "command_chat_response_alias",
        "console",
        "copied_log_status",
        "diagnostic_planning_artifact",
        "rcon",
        "rcon_command",
        "rcon_command_candidate",
        "rcon_route",
        "rcon_route_candidate",
        "rcon_source",
        "rcon_status",
        "replies",
        "reply",
        "reply_channel",
        "reply_request",
        "response_bridge",
        "response_bridge_candidate",
        "send",
        "send_chat",
        "send_channel",
        "send_chat_request",
        "send_source",
        "send_source_alias",
        "server_console",
        "source_alias",
        "status_metadata",
    )
)
NON_EVIDENCE_ARTIFACT_NAME_KEYS = frozenset(
    (
        "artifact",
        "artifact_class",
        "artifact_kind",
        "artifact_type",
        "class",
        "kind",
        "name",
        "field",
        "claim",
        "key",
    )
)
NON_EVIDENCE_ARTIFACT_NON_CREDIT_MARKER_KEYS = frozenset(
    (
        "blocked",
        "dependency_chain_locked",
        "diagnostic_only",
        "manifest_status",
        "metadata_only",
        "non_authorizing",
        "non_counting_until_present",
        "non_evidence",
        "planning_only",
        "route_blocked",
        "upstream_promotions_satisfied",
        "valid_hash_bound_promotion_certificate_present",
    )
)
NON_EVIDENCE_ARTIFACT_CONTEXT_VALUE_KEYS = frozenset(
    (
        "artifact",
        "artifact_class",
        "artifact_kind",
        "artifact_source",
        "artifact_status",
        "artifact_type",
        "class",
        "channel",
        "delivery_source",
        "evidence_class",
        "evidence_kind",
        "evidence_source",
        "input_kind",
        "input_scope",
        "intake_kind",
        "kind",
        "metadata_kind",
        "metadata_source",
        "name",
        "ready_scope",
        "report_kind",
        "review_scope",
        "route_source",
        "source",
        "source_class",
        "source_classes",
        "source_kind",
        "source_path",
        "source_paths",
        "source_type",
        "sources",
        "transport",
    )
)
NON_EVIDENCE_ARTIFACT_CONTEXT_TERMS = frozenset(
    (
        "activation_precondition",
        "activation_preconditions",
        "approved_runtime_evidence_placeholder",
        "approved_runtime_placeholder",
        "beta_notice",
        "beta_notice_state",
        "beta_capture",
        "beta_capture_pack",
        "beta_capture_plan",
        "beta_plan",
        "beta_session_plan",
        "beta_tester_plan",
        "candidate_capture",
        "candidate_only",
        "candidate_plan",
        "checker_report",
        "chat_rcon_broadcast_send_source_alias",
        "chat_rcon_broadcast_send_source_aliases",
        "command_candidate",
        "command_reply_candidate",
        "command_response_alias",
        "command_chat_response_alias",
        "commands_replies_candidate",
        "copied_log",
        "copied_log_status",
        "copied_response_intent",
        "debug_capture",
        "diagnostic",
        "diagnostic_candidate",
        "diagnostic_drift",
        "diagnostic_plan",
        "diagnostic_planning",
        "diagnostic_planning_artifact",
        "active_player_presence",
        "active_players",
        "guarded_beta_notice",
        "installed_sdk_package_shape",
        "local_chat_seed",
        "local_route_seed",
        "local_routing_seed",
        "lifecycle_start_end_evidence",
        "machine_next_action",
        "multi_surface_beta_capture_pack",
        "multi_surface_beta_capture_plan",
        "multi_surface_capture_pack",
        "multi_surface_capture_plan",
        "next_action",
        "no_user",
        "no_users",
        "no_users_passive_runtime",
        "notice_artifact",
        "notice_status",
        "package_shape",
        "package_shape_install",
        "package_shape_support",
        "passive_evidence",
        "passive_log",
        "passive_logs",
        "passive_monitor",
        "passive_player",
        "player_presence",
        "observer_enabled",
        "observer_enablement",
        "passive_runtime",
        "passive_snapshot",
        "passive_status",
        "public_reachability",
        "plugin_hub",
        "plugin_hub_package_shape",
        "plugin_hub_support",
        "post_runtime",
        "post_runtime_metadata",
        "post_runtime_plan",
        "post_runtime_planning",
        "post_runtime_planning_metadata",
        "post_runtime_status",
        "rcon_command_candidate",
        "rcon_command_route",
        "rcon_command_status",
        "rcon_route",
        "rcon_route_candidate",
        "rcon_status",
        "request_check",
        "request_pack",
        "response_bridge",
        "route_bundle",
        "route_snapshot",
        "runtime_status",
        "runtime_principal_lifecycle_start_end_evidence",
        "runtime_principal_start_end_evidence",
        "runtime_window",
        "runtime_window_artifact",
        "runtime_window_execution",
        "runtime_window_manifest",
        "runtime_window_report",
        "runtime_window_request",
        "runtime_window_status",
        "scoped_release_statement",
        "scoped_statement",
        "side_lane",
        "send_source_alias",
        "send_source_aliases",
        "source_alias",
        "source_aliases",
        "start_end_evidence",
        "start_end_only",
        "start_end_only_evidence",
        "status_artifact",
        "status_metadata",
        "terminal_certificate",
        "terminal_certificate_metadata",
        "terminal_certificate_status",
        "route_status_metadata",
        "runtime_status_metadata",
        "sdk_status_metadata",
        "live_posture",
        "live_server_posture",
        "runtime_posture",
        "server_posture",
        "status_report",
        "status_snapshot",
        "status_update",
        "support_tier_package_shape",
        "window_artifact",
        "window_execution",
        "window_manifest",
        "window_report",
        "window_request",
        "window_status",
        "transfer_b_accept_candidate",
        "transfer_b_accept_route",
        "transfer_baccept_candidate",
        "transfer_baccept_route",
        "zero_user",
        "zero_users",
    )
)
NON_EVIDENCE_ARTIFACT_CONTEXT_RE = re.compile(
    r"(?:^|_)(?:"
    r"(?:multi_?surface_?)?beta_?(?:capture_?)?(?:plans?|packs?)|beta_?(?:session|tester)_?(?:plans?|packs?)|"
    r"(?:commands?_replies?_?|command_?reply_?)?candidate_?(?:captures?|plans?|logs?|snapshots?)|"
    r"debug_?captures?|"
    r"(?:diagnostic_?)?drift(?:_?(?:checks?|diagnostics?|reports?|status|summar(?:y|ies)))?|"
    r"(?:active_?)?players?_?presence(?:_?(?:reports?|status|summar(?:y|ies)|snapshots?))?|"
    r"active_?players?(?:_?(?:detected|present|presence|reports?|status|summar(?:y|ies)))?|"
    r"(?:player_?)?presence(?:_?(?:active|detected|reports?|status|summar(?:y|ies)))?|"
    r"(?:lifecycle_?|principal_?|player_?principal_?|runtime_?)?observers?(?:_?(?:enable|enabled|enablement|reports?|status))?|"
    r"(?:live_?|server_?|runtime_?)?posture(?:_?(?:checks?|reports?|status|snapshots?))?|"
    r"next_?action(?:_?(?:artifact|artifacts|output|outputs|plan|planner|runner|report|reports|status))?|"
    r"passive_?(?:monitor|monitors|monitor_?tick|monitor_?ticks|monitor_?output|output|outputs|"
    r"player_?summar(?:y|ies)|player_?snapshot|player_?snapshots|snapshot|snapshots|status|"
    r"(?:chat_?|runtime_?)?logs?)|"
    r"(?:beta_?)?notice_?(?:artifact|artifacts|action|actions|draft|drafts|report|reports|send|sends|status)|"
    r"(?:broadcast_?)?notice_?(?:artifact|artifacts|action|actions|bundle|bundles|package|packages|"
    r"report|reports|snapshot|snapshots|status)|"
    r"(?:runtime_?principal_?lifecycle_?)?start_?end(?:_?only)?(?:_?evidence)?|"
    r"post_?runtime(?:_?(?:metadata|plans?|planning|planning_?metadata|status))?|"
    r"(?:chat_?rcon_?broadcast_?send_?source|send_?source|source)_?aliases?|"
    r"rcon_?(?:command_?)?routes?|rcon_?command_?candidates?|rcon_?route_?candidates?|"
    r"send_?(?:sources?|routes?|status|reports?)|"
    r"transfer_?b_?accept(?:_?(?:candidates?|routes?))?|transfer_?baccept(?:_?(?:candidates?|routes?))?|"
    r"(?:route|runtime|sdk|public_?sdk|obelisk_?sdk|closure|command_?response|"
    r"command_?chat_?response|commands?_replies?)_?status(?:_?(?:artifact|artifacts|report|reports|snapshot|snapshots))?|"
    r"status_?metadata(?:_?(?:artifact|artifacts|report|reports|snapshot|snapshots|updates?))?|"
    r"status_?(?:artifact|artifacts|report|reports|snapshot|snapshots|updates?)"
    r")(?:_|$)"
)
NON_EVIDENCE_ARTIFACT_CREDIT_KEY_RE = re.compile(
    r"(?:^|_)(?:"
    r"accepted|approved|complete|completed|counts?(?:_towards?|_toward|_as)?|credit|credited|"
    r"evidence|progress|progress_?contribution|readiness|ready|result|state|status|"
    r"supported|verified"
    r")(?:_|$)"
)
BROAD_P0_ALIAS_SCOPE_RE = re.compile(
    r"(?:^|_)(?:"
    r"admin_authority|authz(?:_?(?:bridge|response|ready))?|authorization|broadcast|chat(?:_send)?|"
    r"beta(?:_capture)?_plans?|beta_(?:session|tester)_plans?|"
    r"bridge(?:_report)?|"
    r"(?:commands?_replies?_?|command_?reply_?)?candidate_?(?:captures?|plans?|logs?|snapshots?)|"
    r"command(?:_chat)?_response(?:_path)?|command_parser|command_planning|command_router|command_routing|"
    r"command_principal_authz_response_bridge(?:_report)?|authz_response_bridge(?:_report)?|response_bridge(?:_report)?|"
    r"copied_response_intent(?:_planning)?|"
    r"commands?_repl(?:y|ies)|dependency_chain|parser|"
    r"(?:player_?identity|permissions?_admin|command_?chat_?response(?:_path)?)_?promotion_?certificates?|"
    r"final_?(?:gate|certificate|artifact)(?:_?(?:metadata|reports?|status))?|"
    r"(?:local_)?(?:route|routing|chat)_seed|"
    r"debug_?captures?|"
    r"(?:diagnostic_?)?drift(?:_?(?:checks?|diagnostics?|reports?|status|summar(?:y|ies)))?|"
    r"(?:active_?)?players?_?presence(?:_?(?:reports?|status|summar(?:y|ies)|snapshots?))?|"
    r"active_?players?(?:_?(?:detected|present|presence|reports?|status|summar(?:y|ies)))?|"
    r"(?:player_?)?presence(?:_?(?:active|detected|reports?|status|summar(?:y|ies)))?|"
    r"(?:lifecycle_?|principal_?|player_?principal_?|runtime_?)?observers?(?:_?(?:enable|enabled|enablement|reports?|status))?|"
    r"(?:live_?|server_?|runtime_?)?posture(?:_?(?:checks?|reports?|status|snapshots?))?|"
    r"(?:no_?users?_?)?passive_(?:chat_)?evidence|no_?users?_?passive_?runtime|"
    r"passive_(?:chat_)?evidence|passive_runtime_evidence|passive_(?:chat_|runtime_)?logs?|"
    r"permissions?_admin|permissions?_quer(?:y|ies)|permission(?:_header|_query)?|"
    r"plugin_hub(?:_planning|_support|_package|_package_shape)?|"
    r"public_(?:abi|api|header|readiness|reachability|route|runtime|sdk)|"
    r"rcon(?:_command)?(?:_candidate|_route|_status)?|"
    r"reply(?:_(?:abi|api|endpoint|path))?|replies(?:_(?:abi|api|endpoint|path))?|"
    r"response(?:_path)?|"
    r"route(?:_(?:accepted|acceptance|gate|readiness|snapshot))?|"
    r"runtime(?:_(?:capture|delivery|readiness|wiring|work))?|"
    r"send(?:_(?:chat|source|status|route))?|server_operations|stable_(?:claim|sdk)|"
    r"machine_next_action(?:_sequence)?|next_action(?:_sequence)?|"
    r"notice_status|passive_status|status_(?:report|snapshot|update)|"
    r"scoped(?:_non_complete)?(?:_v1)?_release_statement(?:_outcomes)?|"
    r"side_?lanes?(?:_?(?:accounting|artifacts?|candidates?|evidence|reports?|status|summar(?:y|ies)))?|"
    r"support(?:_tier)?(?:_readiness|_report|_package|_package_shape)|"
    r"(?:complete|full|production)_sdk|"
    r"p0(?:_(?:completion|dependency|progress|release|surface|chain))*|"
    r"v1(?:_0)?(?:_(?:api|completion|release|sdk|stable|support))*"
    r")(?:_|$)"
)
BROAD_P0_ALIAS_STATE_RE = re.compile(
    r"(?:^|_)(?:"
    r"accepted|approved|allowed|allows|available|authorized|authorizes|bypassed|bypasses|"
    r"complete|completed|delivered|enabled|enables|granted|implemented|live|met|opened|opens|"
    r"passed|promoted|public|ready|resolved|reviewed|satisfied|satisfies|stable|state|status|"
    r"sufficient|supported|unblocked|unblocks|unlocked|unlocks|validated|verified"
    r")(?:_|$)"
)
BROAD_P0_PROGRESS_OR_CREDIT_ALIAS_RE = re.compile(
    r"(?:^|_)(?:"
    r"claim_progress|credit|credited|progress|progress_contribution|progress_percent|"
    r"progress_ratio|readiness_credit|sdk_credit|sdk_completion_credit|"
    r"v1_completion_credit|public_sdk_credit|counts?(?:_towards?|_toward|_as)?"
    r")(?:_|$)"
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
FAKE_IDENTITY_GATE_BYPASS_ALIAS_RE = re.compile(
    r"(?:^|_)(?:"
    r"child_pass(?:ed|es)?|"
    r"supplied_surfaces?|"
    r"readiness_alias(?:es)?"
    r")(?:_|$)"
)
BROAD_P0_ALIAS_EXEMPT_KEYS = frozenset(
    (
        "accepted_for_planning",
        "accepted_runtime_evidence_context",
        "approved_runtime_evidence_present",
        "not_sufficient_for_v1",
        "required_before_public_header",
        "runtime_evidence_ready",
    )
)
NON_AUTHORIZING_ROUTE_ALIAS_CONTEXT_RE = re.compile(
    r"(?:"
    r"(?:accepted_?)?runtime_?simulations?|"
    r"(?:multi_?surface_?)?beta_?(?:capture_?)?(?:plans?|packs?)|beta_?(?:session|tester)_?(?:plans?|packs?)|"
    r"(?:commands?_replies?_?|command_?reply_?)?candidate_?(?:captures?|plans?|logs?|snapshots?)|"
    r"debug_?captures?|"
    r"(?:diagnostic_?)?drift(?:_?(?:checks?|diagnostics?|reports?|status|summar(?:y|ies)))?|"
    r"(?:active_?)?players?_?presence(?:_?(?:reports?|status|summar(?:y|ies)|snapshots?))?|"
    r"active_?players?(?:_?(?:detected|present|presence|reports?|status|summar(?:y|ies)))?|"
    r"(?:player_?)?presence(?:_?(?:active|detected|reports?|status|summar(?:y|ies)))?|"
    r"(?:lifecycle_?|principal_?|player_?principal_?|runtime_?)?observers?(?:_?(?:enable|enabled|enablement|reports?|status))?|"
    r"(?:live_?|server_?|runtime_?)?posture(?:_?(?:checks?|reports?|status|snapshots?))?|"
    r"(?:command_?principal_?authz_?response_?|authz_?response_?|response_?)?bridge_?reports?|"
    r"(?:player_?)?notice_?actions?(?:_?reports?)?|"
    r"beta_?notice_?actions?(?:_?reports?)?|"
    r"(?:broadcast_?)?notices?(?:_?(?:actions?|reports?|bundles?|packages?|snapshots?))?|"
    r"activation_?preconditions?(?:_?(?:artifacts?|reports?))?|"
    r"precondition_?(?:artifacts?|reports?)|"
    r"public_?contract_?records?(?:_?packages?)?|"
    r"request_?pack(?:_?public_?contract_?record)?|"
    r"support_?tiers?(?:_?(?:readiness|reports?))?|"
    r"support_?tier_?(?:packages?|package_?shapes?)|"
    r"(?:support_?)?package_?shapes?|"
    r"(?:runtime_?principal_?lifecycle_?)?start_?end(?:_?only)?(?:_?evidence)?|"
    r"post_?runtime(?:_?(?:metadata|plans?|planning|planning_?metadata|status))?|"
    r"plugin_?hub(?:_?(?:planning|readiness|reports?|support|package|package_?shape))?|"
    r"public_?reachability(?:_?(?:checks?|reports?|status))?|"
    r"rcon_?(?:command_?)?(?:routes?|status|reports?)|rcon_?command_?candidates?|rcon_?route_?candidates?|"
    r"(?:chat_?rcon_?broadcast_?send_?source|send_?source|source)_?aliases?|"
    r"send_?(?:sources?|routes?|status|reports?)|"
    r"transfer_?b_?accept(?:_?(?:candidates?|routes?))?|transfer_?baccept(?:_?(?:candidates?|routes?))?|"
    r"side_?lanes?(?:_?(?:accounting|artifacts?|candidates?|evidence|reports?|status|summar(?:y|ies)))?|"
    r"no_?users?_?passive_?runtime(?:_?(?:evidence|reports?|status|summar(?:y|ies)))?|"
    r"passive_?(?:chat_?|runtime_?)?logs?|"
    r"command_?planning(?:_?packages?|_?package_?shapes?)?|"
    r"command_?(?:chat_?)?response_?planning(?:_?packages?)?|"
    r"copied_?(?:response_?)?intent(?:_?planning)?(?:_?packages?|_?package_?shapes?)?"
    r"|machine_?next_?actions?(?:_?(?:sequence|reports?|snapshots?|status|updates?))?"
    r"|next_?actions?(?:_?(?:sequence|reports?|snapshots?|status|updates?))?"
    r"|(?:notice|passive)_?status(?:_?(?:reports?|snapshots?|updates?))?"
    r"|status_?(?:reports?|snapshots?|updates?)"
    r"|(?:route_?)?bundles?(?:_?(?:packages?|snapshots?|reports?))?"
    r"|route_?snapshots?(?:_?packages?)?"
    r")"
)
NEGATIVE_CONTEXT_TOKENS = (
    "blocker",
    "blockers",
    "blocked",
    "claim_requires",
    "decision_required",
    "exclusion",
    "exclusions",
    "forbidden",
    "not_sufficient",
    "non_claim",
    "promotion_requires",
    "registration_semantics",
    "required_behavior",
    "required_evidence",
    "required_exclusions",
    "v1_sequence_gate",
    "stable_release_contract",
    "why_blocked",
)
NEGATED_CLAIM_RE = re.compile(
    r"\b(before|blocked|cannot|does\s+not|fail[s-]?closed|forbidden|future|must|must\s+be|must\s+not|need[s]?|"
    r"never|no|not|only|planning|post-v1|require[sd]?|unresolved|until|without)\b",
    re.IGNORECASE,
)
LOCK_BYPASS_NEGATED_CLAIM_RE = re.compile(
    r"\b(before|blocked|cannot|does\s+not|fail[s-]?closed|forbidden|future|must|must\s+be|must\s+not|need[s]?|"
    r"never|no|not|planning|post-v1|require[sd]?|unresolved|until|without)\b",
    re.IGNORECASE,
)
ZERO_PROGRESS_CLAIM_RE = re.compile(r"\b0+(?:\.0+)?\s*(?:/|%|percent)\b", re.IGNORECASE)
LOCK_BYPASS_CLAIM_RE = re.compile(
    r"\b("
    r"activation[_ -]?preconditions?(?:[_ -]?(?:artifacts?|reports?))?|"
    r"(?:multi[_ -]?surface[_ -]?)?beta[_ -]?(?:capture[_ -]?)?(?:plans?|packs?)|beta[_ -]?(?:session|tester)[_ -]?(?:plans?|packs?)|"
    r"(?:beta[_ -]?)?notice[_ -]?actions?(?:[_ -]?reports?)?|beta[_ -]?notices?|discord[_ -]?notices?|"
    r"(?:broadcast[_ -]?)?notices?(?:[_ -]?(?:actions?|reports?|bundles?|packages?|snapshots?))?|"
    r"accepted[_ -]?runtime[_ -]?evidence[_ -]?(?:only|alone|sufficient)|"
    r"authz(?:[_ -]?(?:ready|bridge|response))?|authorization|"
    r"final[_ -]?(?:gate|certificate|artifact)(?:[_ -]?(?:metadata|status|reports?))?|"
    r"(?:command[_ -]?principal[_ -]?authz[_ -]?response[_ -]?|authz[_ -]?response[_ -]?|response[_ -]?)?bridge[_ -]?reports?|"
    r"command[_ -]?principal[_ -]?authz[_ -]?response[_ -]?bridge|authz[_ -]?response[_ -]?bridge|response[_ -]?bridge|"
    r"copied[_ -]?response[_ -]?intent(?:[_ -]?planning)?|"
    r"(?:accepted[_ -]?)?runtime[_ -]?simulations?|"
    r"public[_ -]?contract[_ -]?records?(?:[_ -]?packages?)?|"
    r"support[_ -]?tiers?(?:[_ -]?(?:readiness|reports?))?|"
    r"support[_ -]?tier[_ -]?(?:packages?|package[_ -]?shapes?)|"
    r"(?:support[_ -]?)?package[_ -]?shapes?|"
    r"side[_ -]?lanes?(?:[_ -]?(?:accounting|artifacts?|candidates?|evidence|reports?|status|summar(?:y|ies)))?|"
    r"(?:commands?[_ -]?replies?[_ -]?|command[_ -]?reply[_ -]?)?candidate[_ -]?(?:captures?|plans?|logs?|snapshots?)|"
    r"debug[_ -]?captures?|"
    r"(?:diagnostic[_ -]?)?drift(?:[_ -]?(?:checks?|diagnostics?|reports?|status|summar(?:y|ies)))?|"
    r"(?:active[_ -]?)?players?[_ -]?presence(?:[_ -]?(?:reports?|status|summar(?:y|ies)|snapshots?))?|"
    r"active[_ -]?players?(?:[_ -]?(?:detected|present|presence|reports?|status|summar(?:y|ies)))?|"
    r"(?:player[_ -]?)?presence(?:[_ -]?(?:active|detected|reports?|status|summar(?:y|ies)))?|"
    r"(?:lifecycle[_ -]?|principal[_ -]?|player[_ -]?principal[_ -]?|runtime[_ -]?)?observers?(?:[_ -]?(?:enable|enabled|enablement|reports?|status))?|"
    r"(?:live[_ -]?|server[_ -]?|runtime[_ -]?)?posture(?:[_ -]?(?:checks?|reports?|status|snapshots?))?|"
    r"no[_ -]?users?[_ -]?passive[_ -]?runtime(?:[_ -]?(?:evidence|reports?|status|summar(?:y|ies)))?|"
    r"command[_ -]?planning(?:[_ -]?(?:packages?|package[_ -]?shapes?))?|"
    r"command[_ -]?(?:chat[_ -]?)?response[_ -]?planning(?:[_ -]?packages?)?|"
    r"copied[_ -]?(?:response[_ -]?)?intent(?:[_ -]?planning)?(?:[_ -]?packages?|[_ -]?package[_ -]?shapes?)?|"
    r"machine[_ -]?next[_ -]?actions?(?:[_ -]?(?:sequence|reports?|snapshots?|status|updates?))?|"
    r"next[_ -]?actions?(?:[_ -]?(?:sequence|reports?|snapshots?|status|updates?))?|"
    r"(?:notice|passive)[_ -]?status(?:[_ -]?(?:reports?|snapshots?|updates?))?|"
    r"status[_ -]?(?:reports?|snapshots?|updates?)|"
    r"(?:route[_ -]?)?bundles?(?:[_ -]?(?:packages?|snapshots?|reports?))?|"
    r"identity[_ -]?public[_ -]?contract[_ -]?gate[_ -]?missing|"
    r"scoped[_ -]?(?:non[-_ ]complete[_ -]?)?(?:v1[_ -]?)?release[_ -]?statements?|"
    r"(?:local[_ -]?)?(?:route|routing|chat)[_ -]?seeds?|"
    r"passive[_ -]?(?:chat[_ -]?)?evidence|passive[_ -]?runtime[_ -]?evidence|"
    r"passive[_ -]?(?:chat[_ -]?|runtime[_ -]?)?logs?|"
    r"public[_ -]?reachability|request[_ -]?checks?|request[_ -]?packs?|"
    r"response[_ -]?path|"
    r"raw[_ -]?fstring[_ -]?(?:command|reply|response|shortcuts?)|"
    r"(?:raw[_ -]?)?processevent[_ -]?(?:command|reply|response|shortcuts?)|"
    r"callprocessevent[_ -]?(?:command|reply|response|shortcuts?)|"
    r"route[_ -]?blocker[_ -]?bypass(?:es|ed)?|route[_ -]?snapshots?|"
    r"(?:dependency|route)[_ -]?gate[_ -]?bypass|"
    r"(?:sdk[/_ -]?)?p0[_ -]?(?:progress|dependency|surface|completion)|"
    r"live[_ -]?(?:ops|operations|server)[_ -]?(?:authorization|approval|authorized|approved)|"
    r"production[_ -]?server[_ -]?authorized"
    r")\b.{0,100}\b("
    r"accepted|allow(?:s|ed)?|available|authori[sz](?:es|ed)?|bypassed|complete|completed|copied|count(?:ed|s|ing)?|delivered|enabled|enough|granted|implemented|met|operational|passed|promoted|reachable|ready|satisf(?:ied|ies|y)?|sent|sufficient|supported|unblock(?:s|ed)?|unlock(?:s|ed)?|verified"
    r")\b",
    re.IGNORECASE,
)
LOCK_BYPASS_CLAIM_REVERSED = re.compile(
    r"\b("
    r"accepted|allow(?:s|ed)?|available|authori[sz](?:es|ed)?|bypassed|complete|completed|copied|delivered|enabled|enough|granted|implemented|met|operational|passed|promoted|reachable|ready|sent|sufficient|supported|unblock(?:s|ed)?|unlock(?:s|ed)?|verified"
    r")\b.{0,100}\b("
    r"activation[_ -]?preconditions?(?:[_ -]?(?:artifacts?|reports?))?|"
    r"(?:multi[_ -]?surface[_ -]?)?beta[_ -]?(?:capture[_ -]?)?(?:plans?|packs?)|beta[_ -]?(?:session|tester)[_ -]?(?:plans?|packs?)|"
    r"(?:beta[_ -]?)?notice[_ -]?actions?(?:[_ -]?reports?)?|beta[_ -]?notices?|discord[_ -]?notices?|"
    r"accepted[_ -]?runtime[_ -]?evidence[_ -]?(?:only|alone|sufficient)|"
    r"authz(?:[_ -]?(?:ready|bridge|response))?|authorization|"
    r"final[_ -]?(?:gate|certificate|artifact)(?:[_ -]?(?:metadata|status|reports?))?|"
    r"(?:command[_ -]?principal[_ -]?authz[_ -]?response[_ -]?|authz[_ -]?response[_ -]?|response[_ -]?)?bridge[_ -]?reports?|"
    r"command[_ -]?principal[_ -]?authz[_ -]?response[_ -]?bridge|authz[_ -]?response[_ -]?bridge|response[_ -]?bridge|"
    r"copied[_ -]?response[_ -]?intent(?:[_ -]?planning)?|"
    r"(?:accepted[_ -]?)?runtime[_ -]?simulations?|"
    r"public[_ -]?contract[_ -]?records?(?:[_ -]?packages?)?|"
    r"support[_ -]?tiers?(?:[_ -]?(?:readiness|reports?))?|"
    r"support[_ -]?tier[_ -]?(?:packages?|package[_ -]?shapes?)|"
    r"(?:support[_ -]?)?package[_ -]?shapes?|"
    r"side[_ -]?lanes?(?:[_ -]?(?:accounting|artifacts?|candidates?|evidence|reports?|status|summar(?:y|ies)))?|"
    r"(?:commands?[_ -]?replies?[_ -]?|command[_ -]?reply[_ -]?)?candidate[_ -]?(?:captures?|plans?|logs?|snapshots?)|"
    r"debug[_ -]?captures?|"
    r"(?:diagnostic[_ -]?)?drift(?:[_ -]?(?:checks?|diagnostics?|reports?|status|summar(?:y|ies)))?|"
    r"(?:active[_ -]?)?players?[_ -]?presence(?:[_ -]?(?:reports?|status|summar(?:y|ies)|snapshots?))?|"
    r"active[_ -]?players?(?:[_ -]?(?:detected|present|presence|reports?|status|summar(?:y|ies)))?|"
    r"(?:player[_ -]?)?presence(?:[_ -]?(?:active|detected|reports?|status|summar(?:y|ies)))?|"
    r"(?:lifecycle[_ -]?|principal[_ -]?|player[_ -]?principal[_ -]?|runtime[_ -]?)?observers?(?:[_ -]?(?:enable|enabled|enablement|reports?|status))?|"
    r"(?:live[_ -]?|server[_ -]?|runtime[_ -]?)?posture(?:[_ -]?(?:checks?|reports?|status|snapshots?))?|"
    r"no[_ -]?users?[_ -]?passive[_ -]?runtime(?:[_ -]?(?:evidence|reports?|status|summar(?:y|ies)))?|"
    r"command[_ -]?planning(?:[_ -]?(?:packages?|package[_ -]?shapes?))?|"
    r"command[_ -]?(?:chat[_ -]?)?response[_ -]?planning(?:[_ -]?packages?)?|"
    r"copied[_ -]?(?:response[_ -]?)?intent(?:[_ -]?planning)?(?:[_ -]?packages?|[_ -]?package[_ -]?shapes?)?|"
    r"machine[_ -]?next[_ -]?actions?(?:[_ -]?(?:sequence|reports?|snapshots?|status|updates?))?|"
    r"next[_ -]?actions?(?:[_ -]?(?:sequence|reports?|snapshots?|status|updates?))?|"
    r"(?:notice|passive)[_ -]?status(?:[_ -]?(?:reports?|snapshots?|updates?))?|"
    r"status[_ -]?(?:reports?|snapshots?|updates?)|"
    r"identity[_ -]?public[_ -]?contract[_ -]?gate[_ -]?missing|"
    r"scoped[_ -]?(?:non[-_ ]complete[_ -]?)?(?:v1[_ -]?)?release[_ -]?statements?|"
    r"(?:local[_ -]?)?(?:route|routing|chat)[_ -]?seeds?|"
    r"passive[_ -]?(?:chat[_ -]?)?evidence|passive[_ -]?runtime[_ -]?evidence|"
    r"passive[_ -]?(?:chat[_ -]?|runtime[_ -]?)?logs?|"
    r"public[_ -]?reachability|request[_ -]?checks?|request[_ -]?packs?|"
    r"response[_ -]?path|"
    r"raw[_ -]?fstring[_ -]?(?:command|reply|response|shortcuts?)|"
    r"(?:raw[_ -]?)?processevent[_ -]?(?:command|reply|response|shortcuts?)|"
    r"callprocessevent[_ -]?(?:command|reply|response|shortcuts?)|"
    r"route[_ -]?blocker[_ -]?bypass(?:es|ed)?|route[_ -]?snapshots?|"
    r"(?:dependency|route)[_ -]?gate[_ -]?bypass|"
    r"(?:sdk[/_ -]?)?p0[_ -]?(?:progress|dependency|surface|completion)|"
    r"live[_ -]?(?:ops|operations|server)[_ -]?(?:authorization|approval|authorized|approved)|"
    r"production[_ -]?server[_ -]?authorized"
    r")\b",
    re.IGNORECASE,
)
CLAIM_SCOPE_SPLIT_RE = re.compile(
    r"(?<!\d)\.(?!\d)|[;:\n\r]|\s+\b(?:and|but|then|however|unless)\b\s+",
    re.IGNORECASE,
)
NEGATED_CLAIM_SUFFIX_RE = re.compile(
    r"^\s+(?:remains?|stays?|is|are)?\s*(?:blocked|not\s+(?:ready|enabled|authorized|allowed)|"
    r"unauthorized|unsupported|unresolved|.*\b(?:before|only|never|until|requires?)\b)",
    re.IGNORECASE,
)
POSITIVE_CLAIM_RE = re.compile(
    r"\b("
    r"activation[_ -]?preconditions?(?:[_ -]?(?:artifacts?|reports?))?|"
    r"(?:multi[_ -]?surface[_ -]?)?beta[_ -]?(?:capture[_ -]?)?(?:plans?|packs?)|beta[_ -]?(?:session|tester)[_ -]?(?:plans?|packs?)|"
    r"(?:beta[_ -]?)?notice[_ -]?actions?(?:[_ -]?reports?)?|beta[_ -]?notices?|discord[_ -]?notices?|"
    r"(?:broadcast[_ -]?)?notices?(?:[_ -]?(?:actions?|reports?|bundles?|packages?|snapshots?))?|"
    r"accepted\s+runtime\s+evidence|player\s+identity\s+runtime\s+evidence|"
    r"principal\s+runtime\s+evidence|runtime\s+identity\s+evidence|admin\s+authority|"
    r"authz(?:[_ -]?(?:ready|bridge|response))?|authorization|"
    r"final[_ -]?(?:gate|certificate|artifact)(?:[_ -]?(?:metadata|status|reports?))?|"
    r"(?:command[_ -]?principal[_ -]?authz[_ -]?response[_ -]?|authz[_ -]?response[_ -]?|response[_ -]?)?bridge[_ -]?reports?|"
    r"command[_ -]?principal[_ -]?authz[_ -]?response[_ -]?bridge|authz[_ -]?response[_ -]?bridge|response[_ -]?bridge|"
    r"copied[_ -]?response[_ -]?intent(?:[_ -]?planning)?|"
    r"(?:accepted[_ -]?)?runtime[_ -]?simulations?|"
    r"public[_ -]?contract[_ -]?records?(?:[_ -]?packages?)?|"
    r"support[_ -]?tiers?(?:[_ -]?(?:readiness|reports?))?|"
    r"support[_ -]?tier[_ -]?(?:packages?|package[_ -]?shapes?)|"
    r"(?:support[_ -]?)?package[_ -]?shapes?|"
    r"command[_ -]?planning(?:[_ -]?(?:packages?|package[_ -]?shapes?))?|"
    r"(?:commands?[_ -]?replies?[_ -]?|command[_ -]?reply[_ -]?)?candidate[_ -]?(?:captures?|plans?|logs?|snapshots?)|"
    r"debug[_ -]?captures?|"
    r"(?:diagnostic[_ -]?)?drift(?:[_ -]?(?:checks?|diagnostics?|reports?|status|summar(?:y|ies)))?|"
    r"(?:active[_ -]?)?players?[_ -]?presence(?:[_ -]?(?:reports?|status|summar(?:y|ies)|snapshots?))?|"
    r"active[_ -]?players?(?:[_ -]?(?:detected|present|presence|reports?|status|summar(?:y|ies)))?|"
    r"(?:player[_ -]?)?presence(?:[_ -]?(?:active|detected|reports?|status|summar(?:y|ies)))?|"
    r"(?:lifecycle[_ -]?|principal[_ -]?|player[_ -]?principal[_ -]?|runtime[_ -]?)?observers?(?:[_ -]?(?:enable|enabled|enablement|reports?|status))?|"
    r"(?:live[_ -]?|server[_ -]?|runtime[_ -]?)?posture(?:[_ -]?(?:checks?|reports?|status|snapshots?))?|"
    r"command[_ -]?(?:chat[_ -]?)?response[_ -]?planning(?:[_ -]?packages?)?|"
    r"copied[_ -]?(?:response[_ -]?)?intent(?:[_ -]?planning)?(?:[_ -]?packages?|[_ -]?package[_ -]?shapes?)?|"
    r"(?:route[_ -]?)?bundles?(?:[_ -]?(?:packages?|snapshots?|reports?))?|"
    r"identity\s+(?:public\s+)?contract|player\s+identity\s+public\s+contract|promotion\s+certificate|"
    r"identity[_ -]?public[_ -]?contract[_ -]?gate[_ -]?missing|"
    r"machine[_ -]?next[_ -]?actions?(?:[_ -]?(?:sequence|reports?|snapshots?|status|updates?))?|"
    r"next[_ -]?actions?(?:[_ -]?(?:sequence|reports?|snapshots?|status|updates?))?|"
    r"(?:notice|passive)[_ -]?status(?:[_ -]?(?:reports?|snapshots?|updates?))?|"
    r"scoped[_ -]?(?:non[-_ ]complete[_ -]?)?(?:v1[_ -]?)?release[_ -]?statements?|"
    r"status[_ -]?(?:reports?|snapshots?|updates?)|"
    r"(?:local[_ -]?)?(?:route|routing|chat)[_ -]?seeds?|"
    r"passive[_ -]?(?:chat[_ -]?)?evidence|passive[_ -]?runtime[_ -]?evidence|"
    r"passive[_ -]?(?:chat[_ -]?|runtime[_ -]?)?logs?|"
    r"capability\s+bits?|public[_ -]?(?:abi|capabilit(?:y|ies)|contract)|permission[_ -]?headers?|"
    r"permissions?[_ -]?quer(?:y|ies)|permissions?/admin|"
    r"public[_ -]?reachability|request[_ -]?checks?|request[_ -]?packs?|"
    r"arkapi\s+(?:command\s+)?parser|aseapi\s+(?:command\s+)?parser|"
    r"callprocessevent\s+(?:command|reply|response)|"
    r"response[_ -]?path|command[_ -]?chat[_ -]?response[_ -]?path|"
    r"command[_ -]?parser|command[_ -]?rout(?:e|er|ing)|chat[_ -]?rout(?:e|er|ing)|router|"
    r"(?:complete|full|production|stable)[_ -]?sdk|public[_ -]?(?:command[_ -]?)?sdk(?:[_ -]?readiness)?|"
    r"release[_ -]?readiness|route[_ -]?gate|route[_ -]?snapshots?|runtime[_ -]?readiness|v1(?:\.0)?[_ -]?stable|"
    r"v1[_ -]?(?:sdk[_ -]?)?completion|"
    r"repl(?:y|ies)(?:[_ -]?(?:abi|api|path|request))?|send[_ -]?(?:chat|source|status|route)(?:[_ -]?(?:abi|api|path|request))?|"
    r"broadcast(?:[/_ -]?notices?)?(?:[_ -]?(?:abi|api|path|request|scheduler|service))?|"
    r"notices?(?:[_ -]?(?:abi|api|path|request|scheduler|service))?|moderation(?:[_ -]?(?:abi|api|path|request|authority))?"
    r")\b.{0,100}\b(accepted|advertised|allowed|available|complete|completed|copied|count(?:ed|s|ing)?|delivered|enabled|established|implemented|met|opened|passed|promoted|public|reachable|ready|reviewed|satisf(?:ied|ies|y)?|sent|supported|unblock(?:s|ed)?|unlock(?:s|ed)?|verified)\b",
    re.IGNORECASE,
)
POSITIVE_CLAIM_REVERSED_RE = re.compile(
    r"\b(accepted|advertised|allowed|available|complete|completed|copied|delivered|enabled|established|implemented|met|opened|passed|promoted|public|reachable|ready|reviewed|sent|supported|unblock(?:s|ed)?|unlock(?:s|ed)?|verified)\b"
    r".{0,100}\b("
    r"activation[_ -]?preconditions?(?:[_ -]?(?:artifacts?|reports?))?|"
    r"(?:multi[_ -]?surface[_ -]?)?beta[_ -]?(?:capture[_ -]?)?(?:plans?|packs?)|beta[_ -]?(?:session|tester)[_ -]?(?:plans?|packs?)|"
    r"(?:beta[_ -]?)?notice[_ -]?actions?(?:[_ -]?reports?)?|beta[_ -]?notices?|discord[_ -]?notices?|"
    r"(?:broadcast[_ -]?)?notices?(?:[_ -]?(?:actions?|reports?|bundles?|packages?|snapshots?))?|"
    r"accepted\s+runtime\s+evidence|player\s+identity\s+runtime\s+evidence|"
    r"principal\s+runtime\s+evidence|runtime\s+identity\s+evidence|admin\s+authority|"
    r"authz(?:[_ -]?(?:ready|bridge|response))?|authorization|"
    r"final[_ -]?(?:gate|certificate|artifact)(?:[_ -]?(?:metadata|status|reports?))?|"
    r"(?:command[_ -]?principal[_ -]?authz[_ -]?response[_ -]?|authz[_ -]?response[_ -]?|response[_ -]?)?bridge[_ -]?reports?|"
    r"command[_ -]?principal[_ -]?authz[_ -]?response[_ -]?bridge|authz[_ -]?response[_ -]?bridge|response[_ -]?bridge|"
    r"copied[_ -]?response[_ -]?intent(?:[_ -]?planning)?|"
    r"(?:accepted[_ -]?)?runtime[_ -]?simulations?|"
    r"public[_ -]?contract[_ -]?records?(?:[_ -]?packages?)?|"
    r"support[_ -]?tiers?(?:[_ -]?(?:readiness|reports?))?|"
    r"support[_ -]?tier[_ -]?(?:packages?|package[_ -]?shapes?)|"
    r"(?:support[_ -]?)?package[_ -]?shapes?|"
    r"side[_ -]?lanes?(?:[_ -]?(?:accounting|artifacts?|candidates?|evidence|reports?|status|summar(?:y|ies)))?|"
    r"(?:commands?[_ -]?replies?[_ -]?|command[_ -]?reply[_ -]?)?candidate[_ -]?(?:captures?|plans?|logs?|snapshots?)|"
    r"debug[_ -]?captures?|"
    r"(?:diagnostic[_ -]?)?drift(?:[_ -]?(?:checks?|diagnostics?|reports?|status|summar(?:y|ies)))?|"
    r"(?:active[_ -]?)?players?[_ -]?presence(?:[_ -]?(?:reports?|status|summar(?:y|ies)|snapshots?))?|"
    r"active[_ -]?players?(?:[_ -]?(?:detected|present|presence|reports?|status|summar(?:y|ies)))?|"
    r"(?:player[_ -]?)?presence(?:[_ -]?(?:active|detected|reports?|status|summar(?:y|ies)))?|"
    r"(?:lifecycle[_ -]?|principal[_ -]?|player[_ -]?principal[_ -]?|runtime[_ -]?)?observers?(?:[_ -]?(?:enable|enabled|enablement|reports?|status))?|"
    r"(?:live[_ -]?|server[_ -]?|runtime[_ -]?)?posture(?:[_ -]?(?:checks?|reports?|status|snapshots?))?|"
    r"no[_ -]?users?[_ -]?passive[_ -]?runtime(?:[_ -]?(?:evidence|reports?|status|summar(?:y|ies)))?|"
    r"command[_ -]?planning(?:[_ -]?(?:packages?|package[_ -]?shapes?))?|"
    r"command[_ -]?(?:chat[_ -]?)?response[_ -]?planning(?:[_ -]?packages?)?|"
    r"copied[_ -]?(?:response[_ -]?)?intent(?:[_ -]?planning)?(?:[_ -]?packages?|[_ -]?package[_ -]?shapes?)?|"
    r"(?:route[_ -]?)?bundles?(?:[_ -]?(?:packages?|snapshots?|reports?))?|"
    r"identity\s+(?:public\s+)?contract|player\s+identity\s+public\s+contract|promotion\s+certificate|"
    r"identity[_ -]?public[_ -]?contract[_ -]?gate[_ -]?missing|"
    r"machine[_ -]?next[_ -]?actions?(?:[_ -]?(?:sequence|reports?|snapshots?|status|updates?))?|"
    r"next[_ -]?actions?(?:[_ -]?(?:sequence|reports?|snapshots?|status|updates?))?|"
    r"(?:notice|passive)[_ -]?status(?:[_ -]?(?:reports?|snapshots?|updates?))?|"
    r"scoped[_ -]?(?:non[-_ ]complete[_ -]?)?(?:v1[_ -]?)?release[_ -]?statements?|"
    r"status[_ -]?(?:reports?|snapshots?|updates?)|"
    r"(?:local[_ -]?)?(?:route|routing|chat)[_ -]?seeds?|"
    r"passive[_ -]?(?:chat[_ -]?)?evidence|passive[_ -]?runtime[_ -]?evidence|"
    r"passive[_ -]?(?:chat[_ -]?|runtime[_ -]?)?logs?|"
    r"capability\s+bits?|public[_ -]?(?:abi|capabilit(?:y|ies)|contract)|permission[_ -]?headers?|"
    r"permissions?[_ -]?quer(?:y|ies)|permissions?/admin|"
    r"public[_ -]?reachability|request[_ -]?checks?|request[_ -]?packs?|"
    r"arkapi\s+(?:command\s+)?parser|aseapi\s+(?:command\s+)?parser|"
    r"callprocessevent\s+(?:command|reply|response)|"
    r"response[_ -]?path|command[_ -]?chat[_ -]?response[_ -]?path|"
    r"command[_ -]?parser|command[_ -]?rout(?:e|er|ing)|chat[_ -]?rout(?:e|er|ing)|router|"
    r"(?:complete|full|production|stable)[_ -]?sdk|public[_ -]?(?:command[_ -]?)?sdk(?:[_ -]?readiness)?|"
    r"release[_ -]?readiness|route[_ -]?gate|route[_ -]?snapshots?|runtime[_ -]?readiness|v1(?:\.0)?[_ -]?stable|"
    r"v1[_ -]?(?:sdk[_ -]?)?completion|"
    r"repl(?:y|ies)(?:[_ -]?(?:abi|api|path|request))?|send[_ -]?(?:chat|source|status|route)(?:[_ -]?(?:abi|api|path|request))?|"
    r"broadcast(?:[/_ -]?notices?)?(?:[_ -]?(?:abi|api|path|request|scheduler|service))?|"
    r"notices?(?:[_ -]?(?:abi|api|path|request|scheduler|service))?|moderation(?:[_ -]?(?:abi|api|path|request|authority))?"
    r")\b",
    re.IGNORECASE,
)
PUBLIC_ABI_CONTEXT_TERMS = (
    "public_abi",
    "public_api",
    "public_callback_abi",
    "public_header",
    "plugin_abi",
    "sdk_abi",
)
IDENTITY_LOOKUP_HANDLE_TERMS = (
    "identity_handle",
    "identity_handles",
    "identity_lookup",
    "identity_resolver",
    "lookup_handle",
    "lookup_handles",
    "persistent_handle",
    "player_handle",
    "player_handles",
    "player_lookup",
    "player_resolver",
    "principal_lookup",
    "public_handle",
    "public_handles",
    "resolve_identity",
    "resolve_player",
    "resolve_principal",
    "resource_handle",
    "resourcehandle",
)
ACCEPTED_RUNTIME_EVIDENCE_ALIAS_TEXT_TERMS = (
    "accepted_runtime_evidence",
    "accepted_runtime_principal_lifecycle_evidence",
    "runtime_evidence",
    "runtime_principal_lifecycle_evidence",
)
ACCEPTED_RUNTIME_EVIDENCE_SKIP_TERMS = (
    "admin_authority",
    "allows",
    "bypass",
    "bypassed",
    "complete_sdk",
    "command_response",
    "commands_replies",
    "count",
    "dependency_chain",
    "permission_header",
    "permissions_admin",
    "permissions_query",
    "promote",
    "promoted",
    "public_abi",
    "public_api",
    "public_header",
    "public_runtime",
    "public_sdk",
    "ready",
    "sufficient",
    "unblock",
    "unblocked",
    "unlock",
    "unlocked",
    "v1_completion",
)
ACCEPTED_RUNTIME_EVIDENCE_NEGATED_ALIAS_TERMS = (
    "blocked",
    "cannot",
    "failed",
    "fail_closed",
    "false",
    "insufficient",
    "missing",
    "not_accepted",
    "not_ready",
    "not_sufficient",
    "only_moves_to_identity_public_contract_gate_missing",
    "requires",
    "unresolved",
    "without",
)
NON_AUTHORIZING_ACCEPTED_RUNTIME_EVIDENCE_TERMS = frozenset(
    (
        "activation_preconditions",
        "approved_runtime_evidence_placeholder",
        "approved_runtime_placeholder",
        "beta_notice",
        "beta_notice_state",
        "beta_capture",
        "beta_capture_pack",
        "beta_capture_plan",
        "beta_plan",
        "beta_session_plan",
        "beta_tester_plan",
        "candidate_capture",
        "candidate_plan",
        "child_pass",
        "child_passed",
        "child_passes",
        "chat_rcon_broadcast_send_source_alias",
        "command_candidate",
        "command_reply_candidate",
        "command_response_alias",
        "command_chat_response_alias",
        "commands_replies_candidate",
        "copied_log",
        "copied_log_status",
        "copied_response_intent",
        "discord_notice",
        "debug_capture",
        "diagnostic_drift",
        "diagnostic_plan",
        "diagnostic_planning",
        "diagnostic_planning_artifact",
        "drift",
        "guarded_beta_notice",
        "active_player_presence",
        "active_players",
        "installed_sdk_package_shape",
        "lifecycle_start_end_evidence",
        "local_chat_seed",
        "local_route_seed",
        "local_routing_seed",
        "multi_surface_beta_capture_pack",
        "multi_surface_beta_capture_plan",
        "multi_surface_capture_pack",
        "multi_surface_capture_plan",
        "next_action",
        "no_user",
        "no_users",
        "notice_action",
        "notice_artifact",
        "package_shape",
        "passive_evidence",
        "passive_log",
        "passive_logs",
        "passive_monitor",
        "passive_player",
        "player_presence",
        "observer_enabled",
        "observer_enablement",
        "passive_runtime",
        "passive_snapshot",
        "passive_status",
        "post_runtime",
        "post_runtime_planning_metadata",
        "public_reachability",
        "public_readiness",
        "request_check",
        "request_pack",
        "response_bridge",
        "readiness_alias",
        "readiness_aliases",
        "route_snapshot",
        "side_lane",
        "side_lanes",
        "send_source_alias",
        "source_alias",
        "runtime_principal_lifecycle_start_end_evidence",
        "runtime_principal_start_end_evidence",
        "start_end_evidence",
        "start_end_only",
        "start_end_only_evidence",
        "status_artifact",
        "status_report",
        "status_snapshot",
        "supplied_surface",
        "supplied_surfaces",
        "live_posture",
        "live_server_posture",
        "runtime_posture",
        "server_posture",
        "support_tier",
        "zero_user",
        "zero_users",
    )
)
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
APPROVED_RUNTIME_EVIDENCE_BINDING_EXPECTED_VALUES = {
    "schema": APPROVED_RUNTIME_EVIDENCE_BINDING_SCHEMA,
    "accepted_for_contract_review": True,
    "resolved_input": APPROVED_RUNTIME_EVIDENCE_BINDING_RESOLVED_INPUT,
    "next_blocker": IDENTITY_CONTRACT_ROUTE_BLOCKER,
    "binding_scope": APPROVED_RUNTIME_EVIDENCE_BINDING_SCOPE,
}
APPROVED_RUNTIME_EVIDENCE_BINDING_REQUIRED_KEYS = frozenset(
    {
        *APPROVED_RUNTIME_EVIDENCE_BINDING_EXPECTED_VALUES,
        *APPROVED_RUNTIME_EVIDENCE_BINDING_FALSE_FLAGS,
        "non_claim",
    }
)
ACCEPTED_RUNTIME_EVIDENCE_REQUIRED_KEYS = frozenset(
    {
        "schema",
        "result",
        "next_blocker",
        "approved_runtime_evidence_binding_required",
        "approved_runtime_evidence_binding",
    }
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    parser.add_argument("--surfaces", type=Path, default=DEFAULT_SURFACES)
    parser.add_argument("--public-header", type=Path, default=DEFAULT_PUBLIC_HEADER)
    parser.add_argument(
        "--response-path-report",
        type=Path,
        help="Required composed command/chat response public-readiness report.",
    )
    parser.add_argument("--response-path-root", type=Path)
    parser.add_argument("--response-path-readiness", type=Path)
    parser.add_argument("--response-path-report-root", type=Path)
    parser.add_argument(
        "--current-route-blocker",
        choices=ALLOWED_ROUTE_BLOCKERS,
        default=CURRENT_ROUTE_BLOCKER,
        help="Parent identity-route blocker to mirror while this surface remains locked.",
    )
    parser.add_argument("--json", action="store_true", help="Compatibility flag; output is always JSON.")
    return parser.parse_args()


def add(blockers: list[dict[str, Any]], reason: str, label: str, **details: Any) -> None:
    item = {"reason": reason, "label": label}
    item.update(details)
    blockers.append(item)


def load_json(path: Path, label: str, blockers: list[dict[str, Any]]) -> dict[str, Any] | None:
    try:
        reject_symlink_component(path, label)
        resolved = reject_protected_input_path(path, label)
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except SystemExit as exc:
        add(blockers, f"{label}_path_rejected", f"$.{label}", path=str(path), detail=str(exc))
        return None
    except OSError as exc:
        add(blockers, f"{label}_unreadable", f"$.{label}", path=str(path), detail=str(exc))
        return None
    except json.JSONDecodeError as exc:
        add(blockers, f"{label}_invalid_json", f"$.{label}", path=str(path), detail=str(exc))
        return None
    if not isinstance(payload, dict):
        add(blockers, f"{label}_not_object", f"$.{label}", path=str(path))
        return None
    return payload


def resolve_source_artifact_path(path: Path, label: str, blockers: list[dict[str, Any]]) -> Path | None:
    try:
        reject_symlink_component(path, label)
        resolved = reject_protected_input_path(path, label)
        if not resolved.is_file():
            add(
                blockers,
                "response_path_report_source_artifact_missing_or_unreadable",
                f"$.response_path_report.{label}",
                path=str(path),
            )
            return None
        with resolved.open("r", encoding="utf-8"):
            pass
    except SystemExit as exc:
        add(
            blockers,
            "response_path_report_source_artifact_missing_or_unreadable",
            f"$.response_path_report.{label}",
            path=str(path),
            detail=str(exc),
        )
        return None
    except OSError as exc:
        add(
            blockers,
            "response_path_report_source_artifact_missing_or_unreadable",
            f"$.response_path_report.{label}",
            path=str(path),
            detail=str(exc),
        )
        return None
    return resolved


def resolve_expected_path(path: Path, label: str, blockers: list[dict[str, Any]]) -> Path | None:
    try:
        reject_symlink_component(path, label)
        return reject_protected_input_path(path, label)
    except SystemExit as exc:
        add(
            blockers,
            "response_path_report_expected_artifact_rejected",
            f"$.{label}",
            path=str(path),
            detail=str(exc),
        )
        return None


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def source_artifact_hashes(paths: dict[str, Path | None]) -> dict[str, str | None]:
    return {key: sha256_file(path) if path is not None else None for key, path in paths.items()}


def p0_metadata_non_claim_fields() -> dict[str, Any]:
    fields: dict[str, Any] = {}
    fields.update(P0_METADATA_FALSE_FLAGS)
    fields.update(P0_METADATA_ZERO_FIELDS)
    return fields


def build_candidate_capture_guardrail(current_route_blocker: str) -> dict[str, Any]:
    return {
        "classification": CANDIDATE_CAPTURE_CLASSIFICATION,
        "capture_scope": "offline_beta_planning_input_only",
        "capture_inputs": sorted(CANDIDATE_CAPTURE_NON_COUNTING_SOURCES),
        "requires_player_principal_runtime_blocker": current_route_blocker,
        "approved_runtime_evidence_predecessor": RUNTIME_EVIDENCE_ROUTE_BLOCKER,
        "post_approved_runtime_evidence_parent_lock": IDENTITY_CONTRACT_ROUTE_BLOCKER,
        "current_route_blocker": current_route_blocker,
        "identity_public_contract_gate_missing_planning_only": current_route_blocker
        == IDENTITY_CONTRACT_ROUTE_BLOCKER,
        "accepted_runtime_evidence": False,
        "approved_runtime_evidence": False,
        "command_support_ready": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "p0_dependency_chain_progress_contribution": 0,
        "public_or_runtime_accounting_allowed": False,
        "public_readiness_ready": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "runtime_ready": False,
    }


def downstream_blocker_non_claim_fields() -> dict[str, Any]:
    fields = {
        "planning_metadata_only": True,
        "blocked": True,
        "satisfied": False,
        "counts_as_downstream_progress": False,
        "downstream_progress_contribution": 0,
        "v1_completion_progress_contribution": 0,
    }
    fields.update(p0_metadata_non_claim_fields())
    return fields


def build_downstream_blocker(spec: dict[str, Any]) -> dict[str, Any]:
    item = dict(spec)
    item.update(downstream_blocker_non_claim_fields())
    item["artifact_classes_not_progress"] = sorted(DOWNSTREAM_NON_COUNTING_ARTIFACT_CLASSES)
    item["non_claim"] = (
        "downstream blocker metadata is ordering data only; passive/status/notice/"
        "package-shape artifacts and next-action records do not satisfy this blocker"
    )
    return item


def build_downstream_chain_gate(current_route_blocker: str) -> dict[str, Any]:
    return {
        "schema": DOWNSTREAM_CHAIN_GATE_SCHEMA,
        "surface": SURFACE,
        "planning_only": True,
        "dependency_chain_locked": True,
        "current_route_blocker": current_route_blocker,
        "remaining_route_blockers": [current_route_blocker],
        "blocked_behind_surfaces": BLOCKED_BEHIND_SURFACES,
        "non_counting_artifact_classes": sorted(DOWNSTREAM_NON_COUNTING_ARTIFACT_CLASSES),
        "post_command_response_required_sequence": [
            build_downstream_blocker(spec) for spec in DOWNSTREAM_BLOCKER_SPECS
        ],
        **p0_metadata_non_claim_fields(),
        "non_claim": (
            "commands/replies downstream blockers remain non-counting planning metadata; "
            "they do not unlock v1 completion, runtime readiness, public SDK accounting, "
            "command dispatch, replies, send-chat, notices, broadcast, or moderation"
        ),
    }


def current_route_next_action(current_route_blocker: str) -> dict[str, Any]:
    return ROUTE_BLOCKER_NEXT_ACTIONS.get(
        current_route_blocker,
        {
            "next_action": "resolve_identity_lock_blocker",
            "blocked_until": current_route_blocker,
        },
    )


def command_response_promotion_gate_metadata() -> dict[str, Any]:
    return {
        "surface": RESPONSE_PATH_SURFACE,
        "required_before_surface": SURFACE,
        "required_certificate_schema": COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA,
        "required_artifact": COMMAND_RESPONSE_PROMOTION_REQUIRED_ARTIFACT,
        "blocked_until": "command_chat_response_path_promotion_certificate",
        "commands_replies_can_advance_before_command_response_promotion": False,
        "planning_metadata_only": True,
        **p0_metadata_non_claim_fields(),
        "non_claim": (
            "command-response promotion metadata is a route description only; it is not "
            "commands/replies evidence, readiness, runtime authority, SDK/P0 progress, "
            "or public ABI approval"
        ),
    }


def build_post_command_response_blocker_diagnostic(current_route_blocker: str) -> dict[str, Any]:
    return {
        "schema": POST_COMMAND_RESPONSE_BLOCKER_DIAGNOSTIC_SCHEMA,
        "surface": SURFACE,
        "diagnostic_scope": "post_command_chat_response_path_blocker",
        "planning_only": True,
        "non_evidence": True,
        "non_authorizing": True,
        "current_route_blocker": current_route_blocker,
        "remaining_route_blockers": [current_route_blocker],
        "blocked_behind_surfaces": BLOCKED_BEHIND_SURFACES,
        "requires_prior_surface": RESPONSE_PATH_SURFACE,
        "requires_prior_certificate_schema": COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA,
        "blocked_until_prior_certificate": "command_chat_response_path_promotion_certificate",
        "next_blocker_after_command_chat_response_path": POST_COMMAND_RESPONSE_BLOCKER,
        "next_action_after_command_chat_response_path": POST_COMMAND_RESPONSE_NEXT_ACTION,
        "required_actions_before_commands_replies_promotion": list(
            POST_COMMAND_RESPONSE_REQUIRED_ACTIONS
        ),
        "required_test_artifacts_before_promotion": list(
            COMMANDS_REPLIES_PROMOTION_REQUIRED_ARTIFACT["required_evidence"]
        ),
        "forbidden_unlocks": list(POST_COMMAND_RESPONSE_FORBIDDEN_UNLOCKS),
        "commands_replies_can_advance_before_command_response_promotion": False,
        "reply_send_chat_router_claims_allowed": False,
        "public_command_router_allowed": False,
        "public_reply_or_send_chat_abi_allowed": False,
        "public_send_chat_api_allowed": False,
        "public_broadcast_api_allowed": False,
        "public_notices_api_allowed": False,
        "public_call_process_event_allowed": False,
        "runtime_delivery_allowed": False,
        "stable_sdk_ready": False,
        **p0_metadata_non_claim_fields(),
        "non_claim": (
            "this diagnostic names the first commands/replies blocker after a valid "
            "command_chat_response_path promotion certificate; it is not evidence, "
            "authorization, runtime delivery, SDK/P0 progress, public readiness, "
            "reply/send-chat delivery, broadcast/notices readiness, or public "
            "CallProcessEvent approval"
        ),
    }


def build_next_action_sequence(current_route_blocker: str) -> list[dict[str, Any]]:
    route_action = current_route_next_action(current_route_blocker)
    return [
        {
            "id": "current_route_lock_next_action",
            "planning_metadata_only": True,
            "current_surface": DEPENDENCY_CHAIN[0],
            "current_route_blocker": current_route_blocker,
            "next_action": route_action["next_action"],
            "blocked_until": route_action["blocked_until"],
            "next_after_runtime_evidence": IDENTITY_CONTRACT_ROUTE_BLOCKER,
            **p0_metadata_non_claim_fields(),
            "non_claim": (
                "current route next-action metadata is not runtime evidence, SDK/P0 "
                "progress, public readiness, or publication authority"
            ),
        },
        {
            "id": "command_response_promotion_required_before_commands_replies",
            "planning_metadata_only": True,
            "surface": RESPONSE_PATH_SURFACE,
            "next_action": "promote_command_chat_response_path",
            "blocked_until": "command_chat_response_path_promotion_certificate",
            "required_certificate_schema": COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA,
            "required_artifact": COMMAND_RESPONSE_PROMOTION_REQUIRED_ARTIFACT,
            "required_by_surface": SURFACE,
            **p0_metadata_non_claim_fields(),
            "non_claim": (
                "this step names the required upstream promotion only; command-response "
                "planning reports, passive chat evidence, notices, status reports, and "
                "next-action records do not satisfy it"
            ),
        },
        {
            "id": "commands_replies_promotion_package_after_response_path",
            "planning_metadata_only": True,
            "surface": SURFACE,
            "next_action": "prepare_commands_replies_promotion_evidence_after_command_response",
            "blocked_until": "command_chat_response_path_promotion_certificate",
            "required_prior_certificate_schema": COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA,
            "required_artifact": COMMANDS_REPLIES_PROMOTION_REQUIRED_ARTIFACT,
            **p0_metadata_non_claim_fields(),
            "non_claim": (
                "commands/replies evidence can be prepared only after the command-response "
                "promotion certificate exists; this metadata is not evidence or readiness"
            ),
        },
    ]


def validate_response_path_report_location(
    report_path: Path | None,
    blockers: list[dict[str, Any]],
    *,
    expected_report_root: Path | None,
) -> Path | None:
    if report_path is None:
        return None
    try:
        reject_symlink_component(report_path, "response_path_report")
        resolved_report_path = reject_protected_input_path(report_path, "response_path_report")
    except SystemExit as exc:
        add(
            blockers,
            "response_path_report_path_rejected",
            "$.response_path_report_path",
            path=str(report_path),
            detail=str(exc),
        )
        return None
    if expected_report_root is None:
        add(blockers, "response_path_report_expected_report_root_required", "$.response_path_report_root")
        return resolved_report_path
    resolved_report_root = resolve_expected_path(expected_report_root, "response_path_report_root", blockers)
    if resolved_report_root is None:
        return resolved_report_path
    expected_report_path = resolved_report_root / DEFAULT_RESPONSE_PATH_REPORT_NAME
    if resolved_report_path != expected_report_path:
        add(
            blockers,
            "response_path_report_path_mismatch",
            "$.response_path_report_path",
            expected=str(expected_report_path),
            value=str(resolved_report_path),
        )
    return resolved_report_path


def strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def string_set(value: Any) -> set[str]:
    return set(strings(value))


def iter_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        found: list[str] = []
        for child in value.values():
            found.extend(iter_strings(child))
        return found
    if isinstance(value, list):
        found = []
        for child in value:
            found.extend(iter_strings(child))
        return found
    return []


def surface_by_id(payload: dict[str, Any] | None, surface_id: str) -> dict[str, Any] | None:
    surfaces = payload.get("surfaces") if isinstance(payload, dict) else None
    if not isinstance(surfaces, list):
        return None
    for surface in surfaces:
        if isinstance(surface, dict) and surface.get("id") == surface_id:
            return surface
    return None


def player_identity_has_approved_runtime_evidence(identity: dict[str, Any]) -> bool:
    evidence = identity.get("evidence")
    accepted = evidence.get("accepted_runtime_evidence") if isinstance(evidence, dict) else None
    if not isinstance(accepted, dict):
        return False
    if accepted.get("schema") != "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1":
        return False
    if accepted.get("result") != "approved runtime principal lifecycle evidence":
        return False
    if accepted.get("next_blocker") != IDENTITY_CONTRACT_ROUTE_BLOCKER:
        return False
    if accepted.get("approved_runtime_evidence_binding_required") is not True:
        return False
    if not approved_runtime_evidence_binding_is_canonical(
        accepted.get("approved_runtime_evidence_binding")
    ):
        return False
    if accepted_runtime_evidence_has_non_authorizing_context(accepted):
        return False
    text = "\n".join(iter_strings(identity)).lower()
    return not any(
        term in text
        for term in (
            "no approved runtime principal lifecycle evidence",
            RUNTIME_EVIDENCE_ROUTE_BLOCKER,
        )
    )


def surfaces_have_accepted_runtime_evidence(payload: dict[str, Any] | None) -> bool:
    identity = surface_by_id(payload, DEPENDENCY_CHAIN[0])
    return isinstance(identity, dict) and player_identity_has_approved_runtime_evidence(identity)


def validate_route_blocker_order(
    current_route_blocker: str,
    surfaces: dict[str, Any] | None,
    blockers: list[dict[str, Any]],
    *,
    label: str = "$.current_route_blocker",
) -> None:
    accepted_runtime = surfaces_have_accepted_runtime_evidence(surfaces)
    if current_route_blocker == RUNTIME_EVIDENCE_ROUTE_BLOCKER and accepted_runtime:
        add(
            blockers,
            "current_route_blocker_stale_after_approved_runtime_evidence",
            label,
            value=current_route_blocker,
            expected=IDENTITY_CONTRACT_ROUTE_BLOCKER,
            required_evidence="accepted_runtime_evidence.next_blocker=identity_public_contract_gate_missing",
        )
        return
    if current_route_blocker != IDENTITY_CONTRACT_ROUTE_BLOCKER:
        return
    if accepted_runtime:
        return
    add(
        blockers,
        "current_route_blocker_out_of_order",
        label,
        value=current_route_blocker,
        required_predecessor=RUNTIME_EVIDENCE_ROUTE_BLOCKER,
        required_evidence="accepted_runtime_evidence.next_blocker=identity_public_contract_gate_missing",
    )


def validate_accounting_lock_route_order(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    label: str,
    surfaces: dict[str, Any] | None,
    current_route_blocker: str | None,
) -> None:
    lock = payload.get("accounting_lock")
    if not isinstance(lock, dict):
        return
    lock_blocker = lock.get("current_route_blocker")
    accepted_runtime = surfaces_have_accepted_runtime_evidence(surfaces)
    post_runtime_identity_context = (
        accepted_runtime
        and current_route_blocker == IDENTITY_CONTRACT_ROUTE_BLOCKER
    )
    if lock_blocker not in ALLOWED_ROUTE_BLOCKERS:
        add(
            blockers,
            "accounting_lock_route_blocker_mismatch",
            f"{label}.accounting_lock.current_route_blocker",
            expected=list(ALLOWED_ROUTE_BLOCKERS),
            value=lock_blocker,
        )
    elif lock_blocker == IDENTITY_CONTRACT_ROUTE_BLOCKER and not accepted_runtime:
        add(
            blockers,
            "accounting_lock_route_blocker_out_of_order",
            f"{label}.accounting_lock.current_route_blocker",
            value=lock_blocker,
            required_predecessor=RUNTIME_EVIDENCE_ROUTE_BLOCKER,
        )
    elif (
        lock_blocker == RUNTIME_EVIDENCE_ROUTE_BLOCKER
        and accepted_runtime
        and not post_runtime_identity_context
    ):
        add(
            blockers,
            "accounting_lock_route_blocker_stale_after_approved_runtime_evidence",
            f"{label}.accounting_lock.current_route_blocker",
            value=lock_blocker,
            expected=IDENTITY_CONTRACT_ROUTE_BLOCKER,
        )
    remaining = lock.get("remaining_route_blockers")
    if lock_blocker in ALLOWED_ROUTE_BLOCKERS and remaining != [lock_blocker]:
        add(
            blockers,
            "accounting_lock_remaining_route_blockers_mismatch",
            f"{label}.accounting_lock.remaining_route_blockers",
            expected=[lock_blocker],
            value=remaining,
        )
    if isinstance(remaining, list) and IDENTITY_CONTRACT_ROUTE_BLOCKER in remaining and not accepted_runtime:
        add(
            blockers,
            "accounting_lock_remaining_route_blocker_out_of_order",
            f"{label}.accounting_lock.remaining_route_blockers",
            value=remaining,
            required_predecessor=RUNTIME_EVIDENCE_ROUTE_BLOCKER,
        )
    if (
        isinstance(remaining, list)
        and RUNTIME_EVIDENCE_ROUTE_BLOCKER in remaining
        and accepted_runtime
        and not post_runtime_identity_context
    ):
        add(
            blockers,
            "accounting_lock_remaining_route_blocker_stale_after_approved_runtime_evidence",
            f"{label}.accounting_lock.remaining_route_blockers",
            value=remaining,
            expected=IDENTITY_CONTRACT_ROUTE_BLOCKER,
        )
    if lock.get("dependency_chain_locked") is not True:
        add(
            blockers,
            "accounting_lock_dependency_chain_not_locked",
            f"{label}.accounting_lock.dependency_chain_locked",
            value=lock.get("dependency_chain_locked"),
        )
    for key in (
        "counts_toward_public_sdk",
        "counts_toward_runtime",
        "counts_toward_v1_completion",
        "public_or_runtime_accounting_allowed",
    ):
        if key in lock and lock.get(key) is not False:
            add(blockers, f"accounting_lock_{key}_not_false", f"{label}.accounting_lock.{key}", value=lock.get(key))


def validate_downstream_chain_gate(
    gate: Any,
    blockers: list[dict[str, Any]],
    *,
    label: str,
) -> None:
    if not isinstance(gate, dict):
        add(blockers, "downstream_chain_gate_missing", label, value=gate)
        return
    expected_fields = {
        "schema": DOWNSTREAM_CHAIN_GATE_SCHEMA,
        "surface": SURFACE,
        "planning_only": True,
        "dependency_chain_locked": True,
        "blocked_behind_surfaces": BLOCKED_BEHIND_SURFACES,
    }
    for key, expected in expected_fields.items():
        if gate.get(key) != expected:
            add(
                blockers,
                f"downstream_chain_gate_{key}_mismatch",
                f"{label}.{key}",
                expected=expected,
                value=gate.get(key),
            )
    missing_artifacts = DOWNSTREAM_NON_COUNTING_ARTIFACT_CLASSES - string_set(
        gate.get("non_counting_artifact_classes")
    )
    if missing_artifacts:
        add(
            blockers,
            "downstream_chain_gate_non_counting_artifacts_missing",
            f"{label}.non_counting_artifact_classes",
            missing=sorted(missing_artifacts),
        )
    sequence = gate.get("post_command_response_required_sequence")
    if not isinstance(sequence, list):
        add(blockers, "downstream_chain_gate_sequence_missing", f"{label}.post_command_response_required_sequence")
        return
    expected_ids = [spec["id"] for spec in DOWNSTREAM_BLOCKER_SPECS]
    observed_ids = [
        item.get("id")
        for item in sequence
        if isinstance(item, dict)
    ]
    if observed_ids != expected_ids:
        add(
            blockers,
            "downstream_chain_gate_sequence_mismatch",
            f"{label}.post_command_response_required_sequence",
            expected=expected_ids,
            value=observed_ids,
        )
    by_id = {item.get("id"): item for item in sequence if isinstance(item, dict)}
    for spec in DOWNSTREAM_BLOCKER_SPECS:
        item = by_id.get(spec["id"])
        item_label = f"{label}.post_command_response_required_sequence[{spec['id']}]"
        if not isinstance(item, dict):
            add(blockers, "downstream_chain_gate_blocker_missing", item_label, id=spec["id"])
            continue
        for key, expected in spec.items():
            if item.get(key) != expected:
                add(
                    blockers,
                    "downstream_chain_gate_blocker_field_mismatch",
                    f"{item_label}.{key}",
                    expected=expected,
                    value=item.get(key),
                )
        for key in DOWNSTREAM_BLOCKER_FALSE_FIELDS:
            if item.get(key) is not False:
                add(
                    blockers,
                    "downstream_chain_gate_blocker_false_field_not_false",
                    f"{item_label}.{key}",
                    field=key,
                    value=item.get(key),
                )
        for key in DOWNSTREAM_BLOCKER_ZERO_FIELDS:
            if item.get(key) != 0:
                add(
                    blockers,
                    "downstream_chain_gate_blocker_zero_field_not_zero",
                    f"{item_label}.{key}",
                    field=key,
                    value=item.get(key),
                )
        missing_item_artifacts = DOWNSTREAM_NON_COUNTING_ARTIFACT_CLASSES - string_set(
            item.get("artifact_classes_not_progress")
        )
        if missing_item_artifacts:
            add(
                blockers,
                "downstream_chain_gate_blocker_non_counting_artifacts_missing",
                f"{item_label}.artifact_classes_not_progress",
                missing=sorted(missing_item_artifacts),
            )


def validate_post_response_abi_evidence_guardrail(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    guardrail = payload.get("post_response_abi_evidence_guardrail")
    if guardrail != POST_RESPONSE_ABI_EVIDENCE_GUARDRAIL:
        add(
            blockers,
            "post_response_abi_evidence_guardrail_mismatch",
            "$.decisions.post_response_abi_evidence_guardrail",
            expected=POST_RESPONSE_ABI_EVIDENCE_GUARDRAIL,
            value=guardrail,
        )


def validate_response_path_report_handoff_requirement(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    requirement = payload.get("response_path_handoff_required")
    if requirement != RESPONSE_PATH_REPORT_HANDOFF_REQUIREMENT:
        add(
            blockers,
            "response_path_report_handoff_requirement_mismatch",
            "$.decisions.response_path_handoff_required",
            expected=RESPONSE_PATH_REPORT_HANDOFF_REQUIREMENT,
            value=requirement,
        )


def normalized_key(key: Any) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(key))
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
        normalized_key(key) in SOURCE_STATUS_KEYS | SPLIT_CLAIM_VALUE_KEYS
        and broad_public_surface_alias_value_is_positive(normalized_key(key), child)
        for key, child in value.items()
    )


def is_positive_claim_value(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        normalized = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
        return normalized in {
            "accepted",
            "allowed",
            "approved",
            "authorized",
            "available",
            "complete",
            "completed",
            "delivered",
            "enabled",
            "live",
            "met",
            "operational",
            "passed",
            "promoted",
            "public",
            "reachable",
            "ready",
            "reviewed",
            "sent",
            "supported",
            "true",
            "unblocked",
            "unlocked",
            "verified",
            "yes",
        }
    return False


def contains_positive_claim_value(value: Any) -> bool:
    if is_positive_claim_value(value):
        return True
    if isinstance(value, list):
        return any(contains_positive_claim_value(item) for item in value)
    if isinstance(value, dict):
        return any(contains_positive_claim_value(item) for item in value.values())
    return False


def progress_claim_value_is_nonzero(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().casefold()
        normalized_key_value = normalized_key(value)
        if not normalized or normalized_key_value in {
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
    if isinstance(value, list):
        return any(progress_claim_value_is_nonzero(item) for item in value)
    if isinstance(value, dict):
        return any(progress_claim_value_is_nonzero(item) for item in value.values())
    return False


def broad_progress_or_credit_alias_key(key_name: str) -> bool:
    return (
        key_name in {
            "progress",
            "claim_progress",
            "claim_progress_contribution",
            "complete_sdk_claim_progress_contribution",
            "complete_sdk_progress_contribution",
            "p0_dependency_chain_claim_progress_contribution",
            "p0_dependency_chain_progress_contribution",
            "public_sdk_progress_contribution",
            "runtime_progress_contribution",
            "v1_completion_contribution",
        }
        or key_name in PROMOTED_SURFACE_COUNT_ALIAS_KEYS
        or BROAD_P0_PROGRESS_OR_CREDIT_ALIAS_RE.search(key_name) is not None
    )


def fake_identity_gate_bypass_alias_key(key_name: str) -> bool:
    return FAKE_IDENTITY_GATE_BYPASS_ALIAS_RE.search(key_name) is not None


def fake_identity_gate_bypass_alias_value_is_positive(value: Any) -> bool:
    if contains_positive_claim_value(value):
        return True
    if isinstance(value, (list, dict)):
        return bool(value)
    if isinstance(value, str):
        normalized = normalized_key(value)
        return normalized not in {
            "",
            "0",
            "blocked",
            "false",
            "missing",
            "no",
            "none",
            "not_ready",
            "pending",
        }
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    return False


def broad_public_surface_alias_key(key_name: str) -> bool:
    if key_name in BROAD_P0_ALIAS_EXEMPT_KEYS:
        return False
    return (
        key_name in FALSE_ONLY_KEYS
        or fake_identity_gate_bypass_alias_key(key_name)
        or NON_AUTHORIZING_ROUTE_ALIAS_CONTEXT_RE.search(key_name) is not None
        or key_name in PROMOTED_SURFACE_COUNT_ALIAS_KEYS
        or (
            BROAD_P0_ALIAS_SCOPE_RE.search(key_name) is not None
            and (
                BROAD_P0_ALIAS_STATE_RE.search(key_name) is not None
                or broad_progress_or_credit_alias_key(key_name)
            )
        )
        or key_name in {"progress", "claim_progress", "claim_progress_contribution"}
    )


def broad_public_surface_alias_value_is_positive(key_name: str, value: Any) -> bool:
    if fake_identity_gate_bypass_alias_key(key_name):
        return fake_identity_gate_bypass_alias_value_is_positive(value)
    if broad_progress_or_credit_alias_key(key_name) and progress_claim_value_is_nonzero(value):
        return True
    return contains_positive_claim_value(value)


def non_evidence_artifact_context_key(key_name: str) -> bool:
    return (
        "non_evidence_artifacts" in key_name
        or NON_EVIDENCE_ARTIFACT_CONTEXT_RE.search(key_name) is not None
        or any(term in key_name for term in NON_EVIDENCE_ARTIFACT_CONTEXT_TERMS)
    )


def non_evidence_artifact_context_value(value: Any) -> bool:
    if isinstance(value, str):
        normalized = normalized_key(value)
        return (
            normalized in SOURCE_ALIAS_CONTEXT_VALUES
            or NON_EVIDENCE_ARTIFACT_CONTEXT_RE.search(normalized) is not None
            or any(term in normalized for term in NON_EVIDENCE_ARTIFACT_CONTEXT_TERMS)
        )
    if isinstance(value, list):
        return any(non_evidence_artifact_context_value(item) for item in value)
    if isinstance(value, dict):
        return any(non_evidence_artifact_context_value(item) for item in value.values())
    return False


def dict_declares_non_evidence_artifact_context(value: dict[str, Any]) -> bool:
    return any(
        normalized_key(key) in (
            NON_EVIDENCE_ARTIFACT_CONTEXT_VALUE_KEYS
            | SOURCE_CONTEXT_KEYS
        )
        and non_evidence_artifact_context_value(child)
        for key, child in value.items()
    )


def non_evidence_artifact_claim_name_key(key_name: str) -> bool:
    return key_name in SPLIT_CLAIM_NAME_KEYS or key_name in NON_EVIDENCE_ARTIFACT_NAME_KEYS


def non_evidence_artifact_non_credit_marker_key(key_name: str) -> bool:
    return (
        key_name in NON_EVIDENCE_ARTIFACT_NON_CREDIT_MARKER_KEYS
        or key_name.startswith("blocks_")
        or key_name.endswith("_blocked")
    )


def non_evidence_artifact_credit_key(key_name: str) -> bool:
    if non_evidence_artifact_non_credit_marker_key(key_name):
        return False
    return (
        NON_EVIDENCE_ARTIFACT_CREDIT_KEY_RE.search(key_name) is not None
        or broad_progress_or_credit_alias_key(key_name)
    )


def non_evidence_artifact_credit_value_is_positive(key_name: str, value: Any) -> bool:
    if non_evidence_artifact_non_credit_marker_key(key_name):
        return False
    if broad_progress_or_credit_alias_key(key_name) and progress_claim_value_is_nonzero(value):
        return True
    if isinstance(value, list):
        return any(non_evidence_artifact_credit_value_is_positive(key_name, item) for item in value)
    if isinstance(value, dict):
        return any(
            non_evidence_artifact_credit_value_is_positive(normalized_key(key), child)
            for key, child in value.items()
        )
    return contains_positive_claim_value(value)


def source_marker_value_is_non_authorizing(value: Any) -> bool:
    if isinstance(value, str):
        normalized = normalized_key(value)
        return (
            normalized in SOURCE_ALIAS_CONTEXT_VALUES
            or NON_AUTHORIZING_ROUTE_ALIAS_CONTEXT_RE.search(normalized) is not None
            or fake_identity_gate_bypass_alias_key(normalized)
            or alias_requires_upstream_certificates(normalized)
            or identity_gate_alias_requires_upstream(normalized)
            or (
                BROAD_P0_ALIAS_SCOPE_RE.search(normalized) is not None
                and (
                    BROAD_P0_ALIAS_STATE_RE.search(normalized) is not None
                    or broad_progress_or_credit_alias_key(normalized)
                )
            )
        )
    if isinstance(value, list):
        return any(source_marker_value_is_non_authorizing(item) for item in value)
    if isinstance(value, dict):
        return any(source_marker_value_is_non_authorizing(item) for item in value.values())
    return False


def source_marker_value_claims_positive_alias(value: Any) -> bool:
    if isinstance(value, str):
        normalized = normalized_key(value)
        return (
            fake_identity_gate_bypass_alias_key(normalized)
            or alias_requires_upstream_certificates(normalized)
            or identity_gate_alias_requires_upstream(normalized)
            or (
                BROAD_P0_ALIAS_SCOPE_RE.search(normalized) is not None
                and (
                    BROAD_P0_ALIAS_STATE_RE.search(normalized) is not None
                    or broad_progress_or_credit_alias_key(normalized)
                )
            )
        )
    if isinstance(value, list):
        return any(source_marker_value_claims_positive_alias(item) for item in value)
    if isinstance(value, dict):
        return any(source_marker_value_claims_positive_alias(item) for item in value.values())
    return False


def provenance_value_marks_non_authorizing_context(value: Any) -> bool:
    if isinstance(value, str):
        normalized = normalized_key(value)
        return source_marker_value_is_non_authorizing(value) or any(
            term in normalized
            for term in (
                "accepted_runtime_evidence",
                "approved_runtime_evidence",
                "identity_public_contract_decision_record",
                "public_contract_decision_record",
                "reviewed_hash_current_contract_review_only",
                "reviewed_identity_public_contract",
                "route_snapshot",
            )
        )
    if isinstance(value, list):
        return any(provenance_value_marks_non_authorizing_context(item) for item in value)
    if isinstance(value, dict):
        return any(provenance_value_marks_non_authorizing_context(item) for item in value.values())
    return False


def split_source_marker_status_overclaims(value: dict[str, Any]) -> bool:
    marker_values = [
        child
        for key, child in value.items()
        if normalized_key(key) in SOURCE_CONTEXT_KEYS
    ]
    if not marker_values or not any(provenance_value_marks_non_authorizing_context(item) for item in marker_values):
        return False
    return any(
        broad_public_surface_alias_value_is_positive(normalized_key(key), child)
        for key, child in value.items()
        if normalized_key(key) in SOURCE_STATUS_KEYS
    )


def is_negative_context(trail: str) -> bool:
    lowered = trail.casefold()
    return any(token in lowered for token in NEGATIVE_CONTEXT_TOKENS)


def is_requirement_metadata_context(trail: str) -> bool:
    lowered = trail.casefold()
    return any(
        token in lowered
        for token in (
            "claim_requires",
            "decision_required",
            "promotion_requires",
            "required_behavior",
            "required_evidence",
            "required_exclusions",
            "required_fail_closed_guardrails",
            "v1_sequence_gate",
        )
    )


def is_claim_container_context(trail: str) -> bool:
    segments = (segment.split("[", 1)[0] for segment in trail.split("."))
    return any(
        normalized_key(segment) in {"blocker", "blockers", "block_reasons", "why_blocked"}
        for segment in segments
    )


def is_structural_claim_field(trail: str) -> bool:
    if trail.endswith(".id"):
        return True
    field_name = trail.rsplit(".", 1)[-1].split("[", 1)[0]
    normalized_field = normalized_key(field_name)
    if normalized_field.endswith("_path") or normalized_field.endswith("_root"):
        return True
    return trail in {
        "$.schema",
        "$.surface",
        "$.decisions.schema",
        "$.decisions.surface",
        "$.surfaces.schema",
        "$.response_path_report.schema",
        "$.response_path_report.surface",
    }


def is_non_claim_inventory_context(trail: str) -> bool:
    return any(
        normalized_key(segment.split("[", 1)[0])
        in {
            "capture_inputs",
            "non_authorizing_inputs",
        }
        for segment in trail.split(".")
    )


def strip_c_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//.*", "", text)


def declared_header_path(value: Any) -> Path | None:
    if not isinstance(value, str):
        return None
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        return None
    return REPO_ROOT / path


def validate_public_header_declaration(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    source: str,
    scanned_path: Path,
) -> None:
    declared = payload.get("public_header")
    if declared != DEFAULT_PUBLIC_HEADER_DECL:
        add(
            blockers,
            f"{source}_public_header_mismatch",
            f"$.{source}.public_header",
            expected=DEFAULT_PUBLIC_HEADER_DECL,
            value=declared,
        )
    declared_path = declared_header_path(declared)
    if declared_path is not None and declared_path.resolve() != scanned_path.expanduser().resolve():
        add(
            blockers,
            f"{source}_public_header_not_scanned_header",
            f"$.{source}.public_header",
            declared=str(declared_path),
            scanned=str(scanned_path),
        )


def preceding_claim_scope(text: str, start: int) -> str:
    parts = CLAIM_SCOPE_SPLIT_RE.split(text[:start])
    return parts[-1] if parts else text[:start]


def planning_word_is_claim_subject(text: str) -> bool:
    normalized = normalized_key(text)
    return any(
        term in normalized
        for term in (
            "command_planning",
            "command_principal_authz_response_bridge_planning",
            "authz_response_bridge_planning",
            "response_bridge_planning",
            "copied_response_intent_planning",
            "diagnostic_planning",
            "diagnostic_planning_artifact",
        )
    )


def negation_is_only_planning_word(text: str, regex: re.Pattern[str]) -> bool:
    matches = list(regex.finditer(text))
    return bool(matches) and planning_word_is_claim_subject(text) and all(
        normalized_key(match.group(0)) == "planning" for match in matches
    )


def claim_match_is_negated(text: str, match: re.Match[str]) -> bool:
    if NEGATED_CLAIM_RE.search(match.group(0)) and not negation_is_only_planning_word(match.group(0), NEGATED_CLAIM_RE):
        return True
    if NEGATED_CLAIM_RE.search(preceding_claim_scope(text, match.start())):
        return True
    return bool(NEGATED_CLAIM_SUFFIX_RE.match(text[match.end() :]))


def lock_bypass_match_is_negated(text: str, match: re.Match[str]) -> bool:
    if ZERO_PROGRESS_CLAIM_RE.search(match.group(0)):
        return True
    if "normalized_only_to_identity_public_contract_gate_missing" in normalized_key(match.group(0)):
        return True
    if LOCK_BYPASS_NEGATED_CLAIM_RE.search(match.group(0)) and not negation_is_only_planning_word(
        match.group(0),
        LOCK_BYPASS_NEGATED_CLAIM_RE,
    ):
        return True
    if LOCK_BYPASS_NEGATED_CLAIM_RE.search(preceding_claim_scope(text, match.start())):
        return True
    return bool(NEGATED_CLAIM_SUFFIX_RE.match(text[match.end() :]))


def has_unnegated_positive_claim(text: str) -> bool:
    for clause in CLAIM_SCOPE_SPLIT_RE.split(text):
        for regex in (POSITIVE_CLAIM_RE, POSITIVE_CLAIM_REVERSED_RE):
            for match in regex.finditer(clause):
                if not claim_match_is_negated(clause, match):
                    return True
    return False


def has_unnegated_lock_bypass_claim(text: str) -> bool:
    for clause in CLAIM_SCOPE_SPLIT_RE.split(text):
        for regex in (LOCK_BYPASS_CLAIM_RE, LOCK_BYPASS_CLAIM_REVERSED):
            for match in regex.finditer(clause):
                if not lock_bypass_match_is_negated(clause, match):
                    return True
    return False


def has_unnegated_positive_alias_claim(text: str) -> bool:
    for clause in CLAIM_SCOPE_SPLIT_RE.split(text):
        if NEGATED_CLAIM_RE.search(clause) and not negation_is_only_planning_word(
            clause,
            NEGATED_CLAIM_RE,
        ):
            continue
        normalized = normalized_key(clause)
        if "reviewed_identity_public_contract_decision_record" in normalized:
            continue
        if fake_identity_gate_bypass_alias_key(normalized) or any(
            alias in normalized for alias in POSITIVE_ALIAS_CLAIMS
        ):
            return True
    return False


def has_unnegated_certificate_gated_alias_claim(text: str) -> bool:
    for clause in CLAIM_SCOPE_SPLIT_RE.split(text):
        if NEGATED_CLAIM_RE.search(clause) and not negation_is_only_planning_word(
            clause,
            NEGATED_CLAIM_RE,
        ):
            continue
        normalized = normalized_key(clause)
        if (
            alias_requires_upstream_certificates(normalized)
            or identity_gate_alias_requires_upstream(normalized)
            or fake_identity_gate_bypass_alias_key(normalized)
        ):
            return True
    return False


def has_unnegated_public_abi_identity_lookup_handle_claim(text: str) -> bool:
    for clause in CLAIM_SCOPE_SPLIT_RE.split(text):
        normalized = normalized_key(clause)
        negated = any(
            match.group(0).casefold() != "before" or "resource_handle" not in normalized
            for match in NEGATED_CLAIM_RE.finditer(clause)
        )
        if negated:
            continue
        if any(term in normalized for term in PUBLIC_ABI_CONTEXT_TERMS) and any(
            term in normalized for term in IDENTITY_LOOKUP_HANDLE_TERMS
        ):
            return True
    return False


def accepted_runtime_evidence_text_skips_identity_gate(text: str) -> bool:
    for clause in CLAIM_SCOPE_SPLIT_RE.split(text):
        if NEGATED_CLAIM_RE.search(clause):
            continue
        normalized = normalized_key(clause)
        if re.search(r"(?:^|_)not(?:_|$)", normalized) or any(
            term in normalized for term in ACCEPTED_RUNTIME_EVIDENCE_NEGATED_ALIAS_TERMS
        ):
            continue
        if any(term in normalized for term in ACCEPTED_RUNTIME_EVIDENCE_ALIAS_TEXT_TERMS) and any(
            term in normalized for term in ACCEPTED_RUNTIME_EVIDENCE_SKIP_TERMS
        ):
            return True
    return False


def accepted_runtime_evidence_has_non_authorizing_context(value: Any) -> bool:
    if isinstance(value, str):
        normalized = normalized_key(value)
        return any(term in normalized for term in NON_AUTHORIZING_ACCEPTED_RUNTIME_EVIDENCE_TERMS)
    if isinstance(value, list):
        return any(accepted_runtime_evidence_has_non_authorizing_context(item) for item in value)
    if isinstance(value, dict):
        return any(accepted_runtime_evidence_has_non_authorizing_context(item) for item in value.values())
    return False


def approved_runtime_evidence_binding_is_canonical(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if set(value) != APPROVED_RUNTIME_EVIDENCE_BINDING_REQUIRED_KEYS:
        return False
    if any(value.get(key) != expected for key, expected in APPROVED_RUNTIME_EVIDENCE_BINDING_EXPECTED_VALUES.items()):
        return False
    if any(value.get(key) is not False for key in APPROVED_RUNTIME_EVIDENCE_BINDING_FALSE_FLAGS):
        return False
    non_claim = value.get("non_claim")
    return isinstance(non_claim, str) and bool(non_claim.strip())


def accepted_runtime_evidence_record_is_canonical(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == ACCEPTED_RUNTIME_EVIDENCE_REQUIRED_KEYS
        and value.get("schema") == "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1"
        and value.get("result") == "approved runtime principal lifecycle evidence"
        and value.get("next_blocker") == IDENTITY_CONTRACT_ROUTE_BLOCKER
        and value.get("approved_runtime_evidence_binding_required") is True
        and approved_runtime_evidence_binding_is_canonical(value.get("approved_runtime_evidence_binding"))
        and not accepted_runtime_evidence_has_non_authorizing_context(value)
    )


def validate_approved_runtime_evidence_binding(
    accepted: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    label: str,
) -> None:
    if accepted.get("approved_runtime_evidence_binding_required") is not True:
        add(
            blockers,
            "player_identity_accepted_runtime_evidence_binding_required_missing",
            f"{label}.approved_runtime_evidence_binding_required",
            expected=True,
            value=accepted.get("approved_runtime_evidence_binding_required"),
        )
    binding = accepted.get("approved_runtime_evidence_binding")
    if not isinstance(binding, dict):
        add(
            blockers,
            "player_identity_accepted_runtime_evidence_binding_missing_or_not_object",
            f"{label}.approved_runtime_evidence_binding",
            value=binding,
        )
        return
    if set(binding) != APPROVED_RUNTIME_EVIDENCE_BINDING_REQUIRED_KEYS:
        add(
            blockers,
            "player_identity_accepted_runtime_evidence_binding_keys_mismatch",
            f"{label}.approved_runtime_evidence_binding",
            expected=sorted(APPROVED_RUNTIME_EVIDENCE_BINDING_REQUIRED_KEYS),
            value=sorted(binding),
        )
    for key, expected in APPROVED_RUNTIME_EVIDENCE_BINDING_EXPECTED_VALUES.items():
        if binding.get(key) != expected:
            add(
                blockers,
                f"player_identity_accepted_runtime_evidence_binding_{key}_mismatch",
                f"{label}.approved_runtime_evidence_binding.{key}",
                expected=expected,
                value=binding.get(key),
            )
    for key in APPROVED_RUNTIME_EVIDENCE_BINDING_FALSE_FLAGS:
        if binding.get(key) is not False:
            add(
                blockers,
                f"player_identity_accepted_runtime_evidence_binding_{key}_not_false",
                f"{label}.approved_runtime_evidence_binding.{key}",
                value=binding.get(key),
            )
    if not isinstance(binding.get("non_claim"), str) or not binding.get("non_claim").strip():
        add(
            blockers,
            "player_identity_accepted_runtime_evidence_binding_non_claim_missing",
            f"{label}.approved_runtime_evidence_binding.non_claim",
            value=binding.get("non_claim"),
        )


def alias_requires_upstream_certificates(normalized: str) -> bool:
    if "reviewed_identity_public_contract_decision_record" in normalized:
        return False
    return fake_identity_gate_bypass_alias_key(normalized) or any(
        alias in normalized for alias in CERTIFICATE_GATED_ALIAS_CLAIMS
    )


def identity_gate_alias_requires_upstream(normalized: str) -> bool:
    if "identity_public_contract_gate_missing" not in normalized:
        return False
    return any(token in normalized for token in IDENTITY_GATE_ALIAS_KEY_TOKENS)


def add_upstream_certificate_alias_blocker(
    blockers: list[dict[str, Any]],
    label: str,
    *,
    field: str | None = None,
    value: Any = None,
) -> None:
    details: dict[str, Any] = {
        "required_certificate_schemas": list(UPSTREAM_PROMOTION_CERTIFICATE_SCHEMAS),
        "blocked_behind_surfaces": BLOCKED_BEHIND_SURFACES,
    }
    if field is not None:
        details["field"] = field
    if value is not None:
        details["value"] = value
    add(blockers, "route_or_runtime_readiness_alias_missing_upstream_certificates", label, **details)


def add_promotion_certificate_metadata_blocker(
    blockers: list[dict[str, Any]],
    label: str,
    *,
    field: str | None = None,
    value: Any = None,
) -> None:
    details: dict[str, Any] = {
        "required_upstream_certificate_schemas": list(UPSTREAM_PROMOTION_CERTIFICATE_SCHEMAS),
        "certificate_metadata_counts_as_promotion": False,
    }
    if field is not None:
        details["field"] = field
    if value is not None:
        details["value"] = value
    add(
        blockers,
        "promotion_certificate_metadata_missing_required_upstream_certificates",
        label,
        **details,
    )


def promotion_certificate_schema_value(value: Any) -> bool:
    if isinstance(value, str):
        return value in PROMOTION_CERTIFICATE_METADATA_SCHEMAS
    if isinstance(value, list):
        return any(promotion_certificate_schema_value(item) for item in value)
    return False


def promotion_certificate_structural_requirement_key(key_name: str) -> bool:
    return (
        "required" in key_name
        or "requires" in key_name
        or "depends_on" in key_name
        or "guardrail" in key_name
    )


def promotion_certificate_metadata_is_hash_bound_binding(value: dict[str, Any]) -> bool:
    if set(value) != {"path", "sha256"}:
        return False
    relative = repo_relative_path(value.get("path"))
    expected_sha256 = value.get("sha256")
    if (
        relative is None
        or not isinstance(expected_sha256, str)
        or re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha256) is None
    ):
        return False
    path = REPO_ROOT / relative
    try:
        reject_symlink_component(path, "promotion_certificate_metadata")
        resolved = reject_protected_input_path(path, "promotion_certificate_metadata")
        actual_sha256 = sha256_file(resolved)
    except (OSError, SystemExit):
        return False
    return actual_sha256 == expected_sha256.lower()


def promotion_certificate_plain_metadata_looks_authorizing(value: str, key_name: str) -> bool:
    return (
        not promotion_certificate_structural_requirement_key(key_name)
        and "promotion_certificate" in key_name
        and promotion_certificate_schema_value(value)
    )


def promotion_certificate_metadata_looks_authorizing(value: dict[str, Any], key_name: str) -> bool:
    if not isinstance(value, dict):
        return False
    if isinstance(value.get("id"), str) and "v1_dependency_chain_position" in value:
        return False
    normalized_keys = {normalized_key(key) for key in value}
    certificate_shaped = (
        "promotion_certificate" in key_name
        or "promotion_certificate" in "_".join(sorted(normalized_keys))
        or promotion_certificate_schema_value(value.get("schema"))
        or promotion_certificate_schema_value(value.get("certificate_schema"))
        or bool(PROMOTION_CERTIFICATE_METADATA_KEYS & normalized_keys)
    )
    if not certificate_shaped:
        return False
    if set(value) <= {"path", "sha256"}:
        return not promotion_certificate_metadata_is_hash_bound_binding(value)
    structural_requirement = promotion_certificate_structural_requirement_key(key_name)
    if not structural_requirement:
        if promotion_certificate_schema_value(value.get("schema")):
            return True
        if promotion_certificate_schema_value(value.get("certificate_schema")):
            return True
        if (
            ("promotion_certificate" in key_name or "promotion_certificate" in "_".join(sorted(normalized_keys)))
            and (
                normalized_keys <= {"path", "sha256"}
                or bool(normalized_keys & {"path", "sha256"})
            )
        ):
            return True
    positive_credit = any(
        broad_public_surface_alias_value_is_positive(normalized_key(key), child)
        for key, child in value.items()
        if normalized_key(key) in FALSE_ONLY_KEYS
        or "counts_toward" in normalized_key(key)
        or (
            not structural_requirement
            and (
                normalized_key(key) in SOURCE_STATUS_KEYS
                or normalized_key(key) in SPLIT_CLAIM_VALUE_KEYS
                or "promotion_status" == normalized_key(key)
            )
        )
    )
    if positive_credit:
        return True
    return (
        not structural_requirement
        and promotion_certificate_schema_value(value.get("schema"))
        and value.get("promotion_status") == "promoted"
    )


def promotion_certificate_payload_marks_builder_report(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    normalized_keys = {normalized_key(key) for key in value}
    if PROMOTION_CERTIFICATE_BUILDER_REPORT_KEYS & normalized_keys:
        return True
    schema = value.get("schema")
    if not isinstance(schema, str):
        return False
    normalized_schema = normalized_key(schema)
    return "promotion_certificate" in normalized_schema and (
        "builder_report" in normalized_schema
        or "build_report" in normalized_schema
        or "generation_report" in normalized_schema
    )


def collect_promotion_certificate_payload_overclaims(
    certificate: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    certificate_key: str,
    label: str,
) -> None:
    scan_payload = {
        key: value
        for key, value in certificate.items()
        if normalized_key(key) not in PROMOTION_CERTIFICATE_OVERCLAIM_SCAN_EXEMPT_KEYS
    }
    scan_blockers: list[dict[str, Any]] = []
    collect_overclaims(scan_payload, scan_blockers, label)
    for detail in scan_blockers:
        reason = detail.get("reason")
        if reason == "promotion_certificate_metadata_missing_required_upstream_certificates":
            continue
        add(
            blockers,
            f"{certificate_key}_payload_{reason}",
            str(detail.get("label", label)),
            source_reason=reason,
            source_label=detail.get("label"),
            value=detail.get("value"),
        )


def collect_overclaims(
    value: Any,
    blockers: list[dict[str, Any]],
    trail: str = "$",
    *,
    artifact_context: bool = False,
) -> None:
    if isinstance(value, dict):
        if (
            contains_source_overclaim_zero_marker(value)
            and source_overclaim_zero_has_positive_status_alias(value)
        ):
            add(blockers, "source_overclaim_zero_status_alias_overclaim", trail, value=value)
        if promotion_certificate_metadata_looks_authorizing(value, normalized_key(trail)):
            add_promotion_certificate_metadata_blocker(blockers, trail, value=value)
        current_artifact_context = (
            artifact_context
            or non_evidence_artifact_context_key(normalized_key(trail))
            or dict_declares_non_evidence_artifact_context(value)
        )
        source_marker_context = any(
            provenance_value_marks_non_authorizing_context(child)
            for key, child in value.items()
            if normalized_key(key) in SOURCE_CONTEXT_KEYS
        )
        artifact_marker_context = any(
            non_evidence_artifact_context_key(normalized_key(marker))
            for key, child in value.items()
            if normalized_key(key) in SOURCE_CONTEXT_KEYS
            for marker in iter_strings(child)
        )
        if split_source_marker_status_overclaims(value):
            add(blockers, "public_surface_overclaim", trail, value=value)
        declared_claim_names = [
            str(item)
            for key, item in value.items()
            if (
                normalized_key(key) in SPLIT_CLAIM_NAME_KEYS
                or (current_artifact_context and non_evidence_artifact_claim_name_key(normalized_key(key)))
            )
            and isinstance(item, str)
        ]
        declared_claim_values = [
            item
            for key, item in value.items()
            if normalized_key(key) in SPLIT_CLAIM_VALUE_KEYS
        ]
        declared_artifact_claim_value_pairs = [
            (normalized_key(key), item)
            for key, item in value.items()
            if normalized_key(key) in SPLIT_CLAIM_VALUE_KEYS
            or non_evidence_artifact_credit_key(normalized_key(key))
        ]
        for claim_name in declared_claim_names:
            claim_key = normalized_key(claim_name)
            positive_claim_value = any(
                broad_public_surface_alias_value_is_positive(claim_key, item)
                for item in declared_claim_values
            )
            artifact_claim_value = any(
                non_evidence_artifact_credit_value_is_positive(value_key, item)
                for value_key, item in declared_artifact_claim_value_pairs
            )
            if (
                current_artifact_context
                and non_evidence_artifact_credit_key(claim_key)
                and artifact_claim_value
            ):
                add(blockers, "non_evidence_artifact_credit_overclaim", trail, field=claim_name, value=value)
            if broad_public_surface_alias_key(claim_key) and positive_claim_value:
                add(blockers, "public_surface_overclaim", trail, field=claim_name, value=value)
            identity_gate_alias = identity_gate_alias_requires_upstream(claim_key)
            if identity_gate_alias and positive_claim_value and not broad_public_surface_alias_key(claim_key):
                add(blockers, "public_surface_overclaim", trail, field=claim_name, value=value)
            if (alias_requires_upstream_certificates(claim_key) or identity_gate_alias) and positive_claim_value:
                add_upstream_certificate_alias_blocker(blockers, trail, field=claim_name, value=value)
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            key_name = normalized_key(key)
            if key_name == "accepted_runtime_evidence" and accepted_runtime_evidence_record_is_canonical(child):
                continue
            if key_name == "approved_runtime_evidence_binding_required" and child is True:
                continue
            if (
                key_name == "approved_runtime_evidence_binding"
                and approved_runtime_evidence_binding_is_canonical(child)
            ):
                continue
            child_artifact_context = current_artifact_context or non_evidence_artifact_context_key(key_name)
            child_artifact_positive = non_evidence_artifact_credit_value_is_positive(key_name, child)
            child_positive_claim_value = broad_public_surface_alias_value_is_positive(key_name, child)
            if (
                child_artifact_context
                and "non_evidence_artifacts" not in key_name
                and (non_evidence_artifact_context_key(key_name) or non_evidence_artifact_credit_key(key_name))
                and child_artifact_positive
            ):
                add(blockers, "non_evidence_artifact_credit_overclaim", child_trail, field=str(key), value=child)
            if (
                key_name in SOURCE_CONTEXT_KEYS
                and source_marker_value_claims_positive_alias(child)
            ):
                add(blockers, "public_surface_overclaim", child_trail, field=str(key), value=child)
            if key_name in SOURCE_STATUS_KEYS and source_marker_context and child_positive_claim_value:
                add(blockers, "public_surface_overclaim", child_trail, field=str(key), value=child)
            if key_name in SOURCE_STATUS_KEYS and artifact_marker_context and child_artifact_positive:
                add(blockers, "non_evidence_artifact_credit_overclaim", child_trail, field=str(key), value=child)
            if key_name in FALSE_ONLY_KEYS and child is not False:
                add(blockers, "public_surface_overclaim", child_trail, field=str(key), value=child)
            elif broad_public_surface_alias_key(key_name) and child_positive_claim_value:
                add(blockers, "public_surface_overclaim", child_trail, field=str(key), value=child)
            identity_gate_alias = identity_gate_alias_requires_upstream(key_name)
            if identity_gate_alias and child_positive_claim_value and not broad_public_surface_alias_key(key_name):
                add(blockers, "public_surface_overclaim", child_trail, field=str(key), value=child)
            if (alias_requires_upstream_certificates(key_name) or identity_gate_alias) and child_positive_claim_value:
                add_upstream_certificate_alias_blocker(blockers, child_trail, field=str(key), value=child)
            collect_overclaims(child, blockers, child_trail, artifact_context=child_artifact_context)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            collect_overclaims(child, blockers, f"{trail}[{index}]", artifact_context=artifact_context)
        return
    if (
        not isinstance(value, str)
        or is_structural_claim_field(trail)
    ):
        return
    if is_non_claim_inventory_context(trail) and not (
        has_unnegated_positive_claim(value)
        or has_unnegated_lock_bypass_claim(value)
    ):
        return
    if "non_evidence_artifacts" in normalized_key(trail):
        return
    normalized_text = normalized_key(value)
    if (
        "release_guardrails" in normalized_key(trail)
        and "promoted_experimental" in normalized_text
        and "must_not" in normalized_text
    ):
        return
    if is_requirement_metadata_context(trail) and not is_claim_container_context(trail):
        return
    if has_unnegated_public_abi_identity_lookup_handle_claim(value):
        add(blockers, "public_abi_identity_lookup_handle_claim", trail, value=value)
    if (
        not is_negative_context(trail)
        and promotion_certificate_plain_metadata_looks_authorizing(value, normalized_key(trail))
    ):
        add_promotion_certificate_metadata_blocker(blockers, trail, value=value)
    if is_negative_context(trail) and not is_claim_container_context(trail):
        if has_unnegated_lock_bypass_claim(value):
            add(blockers, "positive_public_surface_claim", trail, value=value)
        if has_unnegated_certificate_gated_alias_claim(value):
            add_upstream_certificate_alias_blocker(blockers, trail, value=value)
        return
    if (
        has_unnegated_positive_claim(value)
        or has_unnegated_positive_alias_claim(value)
        or has_unnegated_lock_bypass_claim(value)
    ):
        add(blockers, "positive_public_surface_claim", trail, value=value)
    if has_unnegated_certificate_gated_alias_claim(value):
        add_upstream_certificate_alias_blocker(blockers, trail, value=value)


def collect_accepted_runtime_evidence_skip_aliases(
    value: Any,
    blockers: list[dict[str, Any]],
    trail: str,
) -> None:
    if isinstance(value, dict):
        declared_claim_names = [
            str(item)
            for key, item in value.items()
            if normalized_key(key) in SPLIT_CLAIM_NAME_KEYS and isinstance(item, str)
        ]
        declared_claim_values = [
            item
            for key, item in value.items()
            if normalized_key(key) in SPLIT_CLAIM_VALUE_KEYS
        ]
        for claim_name in declared_claim_names:
            claim_key = normalized_key(claim_name)
            if (
                broad_public_surface_alias_key(claim_key)
                or alias_requires_upstream_certificates(claim_key)
                or identity_gate_alias_requires_upstream(claim_key)
            ) and any(
                broad_public_surface_alias_value_is_positive(claim_key, item)
                for item in declared_claim_values
            ):
                add(
                    blockers,
                    "player_identity_accepted_runtime_evidence_alias_skips_identity_public_contract_gate",
                    trail,
                    field=claim_name,
                    value=value,
                )
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            key_name = normalized_key(key)
            if key_name == "approved_runtime_evidence_binding_required" and child is True:
                continue
            if (
                key_name == "approved_runtime_evidence_binding"
                and approved_runtime_evidence_binding_is_canonical(child)
            ):
                continue
            if key_name == "next_blocker" and child != IDENTITY_CONTRACT_ROUTE_BLOCKER:
                add(
                    blockers,
                    "player_identity_accepted_runtime_evidence_next_blocker_mismatch",
                    child_trail,
                    expected=IDENTITY_CONTRACT_ROUTE_BLOCKER,
                    value=child,
                )
            if (
                broad_public_surface_alias_key(key_name)
                or alias_requires_upstream_certificates(key_name)
                or identity_gate_alias_requires_upstream(key_name)
            ) and broad_public_surface_alias_value_is_positive(key_name, child):
                add(
                    blockers,
                    "player_identity_accepted_runtime_evidence_alias_skips_identity_public_contract_gate",
                    child_trail,
                    field=str(key),
                    value=child,
                )
            collect_accepted_runtime_evidence_skip_aliases(child, blockers, child_trail)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            collect_accepted_runtime_evidence_skip_aliases(child, blockers, f"{trail}[{index}]")
        return
    if isinstance(value, str) and (
        accepted_runtime_evidence_text_skips_identity_gate(value)
        or (
            fake_identity_gate_bypass_alias_key(normalized_key(value))
            and not NEGATED_CLAIM_RE.search(value)
        )
    ):
        add(
            blockers,
            "player_identity_accepted_runtime_evidence_alias_skips_identity_public_contract_gate",
            trail,
            value=value,
        )


def validate_player_identity_accepted_runtime_evidence(
    identity: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    label: str,
) -> None:
    evidence = identity.get("evidence")
    accepted = evidence.get("accepted_runtime_evidence") if isinstance(evidence, dict) else None
    if not isinstance(accepted, dict):
        return
    expected = {
        "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
        "result": "approved runtime principal lifecycle evidence",
        "next_blocker": IDENTITY_CONTRACT_ROUTE_BLOCKER,
    }
    for key, expected_value in expected.items():
        if accepted.get(key) != expected_value:
            add(
                blockers,
                "player_identity_accepted_runtime_evidence_mismatch",
                f"{label}.evidence.accepted_runtime_evidence.{key}",
                expected=expected_value,
                value=accepted.get(key),
            )
    validate_approved_runtime_evidence_binding(
        accepted,
        blockers,
        label=f"{label}.evidence.accepted_runtime_evidence",
    )
    if accepted_runtime_evidence_has_non_authorizing_context(accepted):
        add(
            blockers,
            "player_identity_accepted_runtime_evidence_non_authorizing_context",
            f"{label}.evidence.accepted_runtime_evidence",
            forbidden_contexts=sorted(NON_AUTHORIZING_ACCEPTED_RUNTIME_EVIDENCE_TERMS),
        )
    collect_accepted_runtime_evidence_skip_aliases(
        accepted,
        blockers,
        f"{label}.evidence.accepted_runtime_evidence",
    )


def require_equal(
    mapping: dict[str, Any],
    key: str,
    expected: Any,
    label: str,
    blockers: list[dict[str, Any]],
) -> None:
    if mapping.get(key) != expected:
        add(blockers, f"{key}_mismatch", f"{label}.{key}", expected=expected, value=mapping.get(key))


def require_false(mapping: dict[str, Any], key: str, label: str, blockers: list[dict[str, Any]]) -> None:
    if mapping.get(key) is not False:
        add(blockers, f"{key}_not_false", f"{label}.{key}", value=mapping.get(key))


def validate_decisions(payload: dict[str, Any], blockers: list[dict[str, Any]], public_header_path: Path) -> None:
    require_equal(payload, "schema", DECISIONS_SCHEMA, "$.decisions", blockers)
    require_equal(payload, "surface", SURFACE, "$.decisions", blockers)
    require_equal(payload, "status", "blocked", "$.decisions", blockers)
    require_equal(payload, "planning_stage", "v1_completion_blocker", "$.decisions", blockers)
    require_equal(payload, "not_sufficient_for_v1", True, "$.decisions", blockers)
    require_false(payload, "public_header_allowed", "$.decisions", blockers)
    require_false(payload, "public_command_router_allowed", "$.decisions", blockers)
    require_false(payload, "public_reply_or_send_chat_abi_allowed", "$.decisions", blockers)
    require_false(payload, "public_response_path_allowed", "$.decisions", blockers)
    validate_public_header_declaration(payload, blockers, source="decisions", scanned_path=public_header_path)
    if payload.get("public_header_symbols_now") != []:
        add(
            blockers,
            "public_header_symbols_now_not_empty",
            "$.decisions.public_header_symbols_now",
            value=payload.get("public_header_symbols_now"),
        )
    if payload.get("public_contract", []) != []:
        add(blockers, "public_contract_not_empty", "$.decisions.public_contract", value=payload.get("public_contract"))

    validate_downstream_chain_gate(
        payload.get("downstream_chain_gate"),
        blockers,
        label="$.decisions.downstream_chain_gate",
    )
    validate_post_response_abi_evidence_guardrail(payload, blockers)
    validate_response_path_report_handoff_requirement(payload, blockers)

    gate = payload.get("runtime_owned_principal_permissions_gate")
    if not isinstance(gate, dict):
        add(blockers, "runtime_owned_principal_permissions_gate_missing", "$.decisions.runtime_owned_principal_permissions_gate")
    else:
        for key in (
            "planning_only",
            "runtime_owned_principal_required",
            "runtime_owned_permission_allow_required",
            "same_principal_tuple_required",
            "permission_policy_provenance_required",
        ):
            if gate.get(key) is not True:
                add(
                    blockers,
                    "runtime_owned_principal_permissions_gate_required_true_missing",
                    f"$.decisions.runtime_owned_principal_permissions_gate.{key}",
                    field=key,
                    value=gate.get(key),
                )
        for key in ("reply_send_chat_router_claims_allowed", "public_abi_allowed", "runtime_delivery_allowed"):
            if gate.get(key) is not False:
                add(
                    blockers,
                    "runtime_owned_principal_permissions_gate_required_false_missing",
                    f"$.decisions.runtime_owned_principal_permissions_gate.{key}",
                    field=key,
                    value=gate.get(key),
                )
        missing_inputs = REQUIRED_RUNTIME_OWNED_GATE_INPUTS - string_set(gate.get("required_runtime_owned_inputs"))
        if missing_inputs:
            add(
                blockers,
                "runtime_owned_principal_permissions_gate_inputs_missing",
                "$.decisions.runtime_owned_principal_permissions_gate.required_runtime_owned_inputs",
                missing=sorted(missing_inputs),
            )
        missing_sources = REQUIRED_RUNTIME_OWNED_FORBIDDEN_SOURCES - string_set(gate.get("forbidden_authority_sources"))
        if missing_sources:
            add(
                blockers,
                "runtime_owned_principal_permissions_gate_forbidden_sources_missing",
                "$.decisions.runtime_owned_principal_permissions_gate.forbidden_authority_sources",
                missing=sorted(missing_sources),
            )

    migration = payload.get("migration_vocabulary_not_compatibility")
    if not isinstance(migration, dict):
        add(
            blockers,
            "migration_vocabulary_not_compatibility_missing",
            "$.decisions.migration_vocabulary_not_compatibility",
        )
    else:
        if migration.get("status") != "planning_only":
            add(
                blockers,
                "migration_vocabulary_status_mismatch",
                "$.decisions.migration_vocabulary_not_compatibility.status",
                value=migration.get("status"),
            )
        missing_terms = REQUIRED_MIGRATION_ALLOWED_TERMS - string_set(migration.get("allowed_terms"))
        if missing_terms:
            add(
                blockers,
                "migration_vocabulary_allowed_terms_missing",
                "$.decisions.migration_vocabulary_not_compatibility.allowed_terms",
                missing=sorted(missing_terms),
            )
        missing_sources = REQUIRED_MIGRATION_SOURCE_KINDS - string_set(migration.get("recognized_source_kinds"))
        if missing_sources:
            add(
                blockers,
                "migration_vocabulary_source_kinds_missing",
                "$.decisions.migration_vocabulary_not_compatibility.recognized_source_kinds",
                missing=sorted(missing_sources),
            )
        missing_semantics = REQUIRED_MIGRATION_REGISTRATION_SEMANTICS - string_set(
            migration.get("registration_semantics")
        )
        if missing_semantics:
            add(
                blockers,
                "migration_vocabulary_registration_semantics_missing",
                "$.decisions.migration_vocabulary_not_compatibility.registration_semantics",
                missing=sorted(missing_semantics),
            )
        missing_non_compatibility = REQUIRED_MIGRATION_NON_COMPATIBILITY - string_set(
            migration.get("non_compatibility_claims")
        )
        if missing_non_compatibility:
            add(
                blockers,
                "migration_vocabulary_non_compatibility_missing",
                "$.decisions.migration_vocabulary_not_compatibility.non_compatibility_claims",
                missing=sorted(missing_non_compatibility),
            )

    forbidden = string_set(payload.get("forbidden_public_contract"))
    missing_forbidden = REQUIRED_FORBIDDEN_PUBLIC_CONTRACT - forbidden
    if missing_forbidden:
        add(
            blockers,
            "forbidden_public_contract_missing_required",
            "$.decisions.forbidden_public_contract",
            missing=sorted(missing_forbidden),
        )

    requirements = payload.get("required_before_public_header")
    if not isinstance(requirements, list):
        add(blockers, "required_before_public_header_not_list", "$.decisions.required_before_public_header")
        collect_overclaims(payload, blockers, "$.decisions")
        return

    observed_prefix: list[str] = []
    by_id: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(requirements):
        label = f"$.decisions.required_before_public_header[{index}]"
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            add(blockers, "required_before_public_header_item_invalid", label)
            continue
        if index < len(REQUIRED_DECISION_PREFIX):
            observed_prefix.append(item["id"])
        by_id[item["id"]] = item
        if item.get("status") != "unresolved":
            add(
                blockers,
                "required_before_public_header_item_not_unresolved",
                f"{label}.status",
                id=item["id"],
                value=item.get("status"),
            )

    if tuple(observed_prefix) != REQUIRED_DECISION_PREFIX:
        add(
            blockers,
            "dependency_chain_decision_order_mismatch",
            "$.decisions.required_before_public_header",
            expected=list(REQUIRED_DECISION_PREFIX),
            value=observed_prefix,
        )
    if set(by_id) != REQUIRED_DECISION_IDS:
        add(
            blockers,
            "required_before_public_header_ids_mismatch",
            "$.decisions.required_before_public_header",
            missing=sorted(REQUIRED_DECISION_IDS - set(by_id)),
            unexpected=sorted(set(by_id) - REQUIRED_DECISION_IDS),
        )

    identity_dep = by_id.get("dependency.promoted_player_identity", {})
    missing_identity_dependency = REQUIRED_IDENTITY_DEPENDENCY_BEHAVIORS - string_set(
        identity_dep.get("required_behavior")
    )
    if missing_identity_dependency:
        add(
            blockers,
            "identity_dependency_behavior_missing",
            "$.decisions.required_before_public_header",
            missing=sorted(missing_identity_dependency),
        )

    permissions_dep = by_id.get("dependency.promoted_permissions_admin", {})
    missing_permissions_dependency = REQUIRED_PERMISSIONS_DEPENDENCY_BEHAVIORS - string_set(
        permissions_dep.get("required_behavior")
    )
    if missing_permissions_dependency:
        add(
            blockers,
            "permissions_dependency_behavior_missing",
            "$.decisions.required_before_public_header",
            missing=sorted(missing_permissions_dependency),
        )

    response_dep = by_id.get("dependency.promoted_command_chat_response_path", {})
    if response_dep.get("required_dependency") != RESPONSE_PATH_SURFACE:
        add(blockers, "response_path_dependency_mismatch", "$.decisions.required_before_public_header", value=response_dep.get("required_dependency"))
    response_behaviors = string_set(response_dep.get("required_behavior"))
    for required in (
        "commands/replies remains blocked while command_chat_response_path is unpromoted or unresolved",
        "commands/replies final P0 gate requires the current hash-bound command_chat_response_path promotion certificate",
        "stale/current command_chat_response_path certificate mismatches and route-ready aliases keep commands/replies non-counting",
        "passive ChatMessageEvent parsing does not authorize replies",
        "legacy CallProcessEvent debug access does not authorize responses",
        "no response path is public through commands/replies until the response path is separately promoted",
    ):
        if required not in response_behaviors:
            add(blockers, "response_path_dependency_behavior_missing", "$.decisions.required_before_public_header", behavior=required)

    no_symbols = by_id.get("abi.no_public_symbols_now", {})
    no_symbol_behaviors = string_set(no_symbols.get("required_behavior"))
    for required in (
        "public_header_symbols_now remains empty",
        "no commands/replies capability bit is advertised",
        "no public register/unregister command ABI exists",
        "no public reply or send-chat ABI exists",
        "no public command_chat_response_path ABI is exposed through commands/replies",
        "CallProcessEvent is not a public command or reply mechanism",
    ):
        if required not in no_symbol_behaviors:
            add(blockers, "no_public_symbols_behavior_missing", "$.decisions.required_before_public_header", behavior=required)

    auth = by_id.get("auth.identity_permission_provenance", {})
    missing_auth_behaviors = REQUIRED_AUTH_BEHAVIORS - string_set(auth.get("required_behavior"))
    if missing_auth_behaviors:
        add(
            blockers,
            "auth_identity_permission_behavior_missing",
            "$.decisions.required_before_public_header",
            missing=sorted(missing_auth_behaviors),
        )

    lifecycle = by_id.get("lifecycle.owner_scoped_registration_cleanup", {})
    missing_lifecycle_behaviors = REQUIRED_LIFECYCLE_BEHAVIORS - string_set(lifecycle.get("required_behavior"))
    if missing_lifecycle_behaviors:
        add(
            blockers,
            "lifecycle_owner_cleanup_behavior_missing",
            "$.decisions.required_before_public_header",
            missing=sorted(missing_lifecycle_behaviors),
        )

    parser = by_id.get("parser.no_arkapi_copy", {})
    parser_behaviors = string_set(parser.get("required_behavior"))
    for required in (
        "no ArkApi or AseApi command parser code is copied",
        "no ArkApi or AseApi constants, schemas, control flow, return semantics, offsets, vtables, or native-call wrappers are copied",
        "plugin-local parser scaffolds remain local helpers and do not become a public SDK router",
        "compatibility naming can inform demand only and cannot substitute for promotion evidence",
    ):
        if required not in parser_behaviors:
            add(blockers, "arkapi_parser_copy_guard_missing", "$.decisions.required_before_public_header", behavior=required)

    abuse = by_id.get("abuse.rate_limit_audit_moderation_boundary", {})
    missing_abuse_behaviors = REQUIRED_ABUSE_BEHAVIORS - string_set(abuse.get("required_behavior"))
    if missing_abuse_behaviors:
        add(
            blockers,
            "abuse_rate_limit_audit_behavior_missing",
            "$.decisions.required_before_public_header",
            missing=sorted(missing_abuse_behaviors),
        )

    separation = by_id.get("separation.no_response_send_reply_moderation", {})
    exclusions = string_set(separation.get("required_exclusions"))
    for required in (
        "public command_chat_response_path ABI",
        "reply ABI",
        "send-chat ABI",
        "broadcast/notices ABI",
        "moderation API",
    ):
        if required not in exclusions:
            add(blockers, "separation_exclusion_missing", "$.decisions.required_before_public_header", exclusion=required)

    evidence = by_id.get("evidence.runtime_sdk_coverage", {})
    missing_not_sufficient = REQUIRED_NOT_SUFFICIENT - string_set(evidence.get("not_sufficient"))
    if missing_not_sufficient:
        add(
            blockers,
            "evidence_not_sufficient_missing_required",
            "$.decisions.required_before_public_header",
            missing=sorted(missing_not_sufficient),
        )

    collect_overclaims(payload, blockers, "$.decisions")


PROMOTION_CERTIFICATE_SPECS = {
    DEPENDENCY_CHAIN[0]: {
        "certificate_key": "player_identity_promotion_certificate",
        "schema": PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
        "chain_position": 1,
        "required_by_surface": DEPENDENCY_CHAIN[1],
        "required_by_chain_position": 2,
        "label": "player_identity",
    },
    DEPENDENCY_CHAIN[1]: {
        "certificate_key": "permissions_admin_promotion_certificate",
        "schema": PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA,
        "chain_position": 2,
        "required_by_surface": RESPONSE_PATH_SURFACE,
        "required_by_chain_position": 3,
        "label": "permissions_admin",
    },
    RESPONSE_PATH_SURFACE: {
        "certificate_key": "command_response_promotion_certificate",
        "schema": COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA,
        "chain_position": 3,
        "required_by_surface": SURFACE,
        "required_by_chain_position": 4,
        "label": "command_chat_response_path",
    },
}


def repo_relative_path(value: Any) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        return None
    return path


def load_promotion_certificate(
    binding: Any,
    *,
    certificate_key: str,
    label: str,
    blockers: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not isinstance(binding, dict):
        add(blockers, f"{certificate_key}_missing", label)
        return None
    if isinstance(binding.get("schema"), str):
        add(
            blockers,
            f"{certificate_key}_inline_certificate_not_hash_bound",
            label,
            required_binding_keys=["path", "sha256"],
        )
        return None

    relative = repo_relative_path(binding.get("path"))
    if relative is None:
        add(blockers, f"{certificate_key}_path_invalid", f"{label}.path", value=binding.get("path"))
        return None
    path = REPO_ROOT / relative
    try:
        reject_symlink_component(path, certificate_key)
        resolved = reject_protected_input_path(path, certificate_key)
    except SystemExit as exc:
        add(blockers, f"{certificate_key}_path_rejected", f"{label}.path", value=str(relative), detail=str(exc))
        return None
    expected_sha256 = binding.get("sha256")
    if not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha256):
        add(blockers, f"{certificate_key}_sha256_invalid", f"{label}.sha256", value=expected_sha256)
        return None
    binding_keys = {normalized_key(key) for key in binding}
    if binding_keys != HASH_BOUND_PROMOTION_CERTIFICATE_BINDING_KEYS:
        add(
            blockers,
            f"{certificate_key}_binding_keys_mismatch",
            label,
            expected=sorted(HASH_BOUND_PROMOTION_CERTIFICATE_BINDING_KEYS),
            value=sorted(binding),
        )
        return None
    actual_sha256 = sha256_file(resolved)
    if actual_sha256 != expected_sha256.lower():
        add(
            blockers,
            f"{certificate_key}_sha256_mismatch",
            f"{label}.sha256",
            expected=expected_sha256.lower(),
            actual=actual_sha256,
        )
        return None
    return load_json(resolved, certificate_key, blockers)


def hash_bound_promotion_certificate_binding(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if {normalized_key(key) for key in value} != HASH_BOUND_PROMOTION_CERTIFICATE_BINDING_KEYS:
        return False
    return all(isinstance(value.get(key), str) and value.get(key) for key in ("path", "sha256"))


def hash_bound_bindings_match(left: Any, right: Any) -> bool:
    if not hash_bound_promotion_certificate_binding(left) or not hash_bound_promotion_certificate_binding(right):
        return False
    return left.get("path") == right.get("path") and left.get("sha256", "").lower() == right.get("sha256", "").lower()


def surface_record_sha256(surface: dict[str, Any], certificate_key: str) -> str:
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


def surface_has_valid_promotion_certificate(
    surface: dict[str, Any] | None,
    surface_id: str,
    blockers: list[dict[str, Any]] | None = None,
    *,
    surfaces: dict[str, Any] | None = None,
) -> bool:
    if surface_id in (DEPENDENCY_CHAIN[0], DEPENDENCY_CHAIN[1]):
        return response_path_readiness.surface_has_valid_promotion_certificate(
            surface,
            surface_id,
            blockers,
            surfaces=surfaces,
        )

    spec = PROMOTION_CERTIFICATE_SPECS[surface_id]
    if not isinstance(surface, dict) or surface.get("status") != "promoted":
        return False

    local_blockers: list[dict[str, Any]] = []
    target_blockers = blockers if blockers is not None else local_blockers
    label = f"$.surfaces.surfaces[{spec['label']}].evidence.{spec['certificate_key']}"
    evidence = surface.get("evidence")
    binding = evidence.get(spec["certificate_key"]) if isinstance(evidence, dict) else None
    certificate = load_promotion_certificate(
        binding,
        certificate_key=str(spec["certificate_key"]),
        label=label,
        blockers=target_blockers,
    )
    if not isinstance(certificate, dict):
        return False

    valid = True
    if promotion_certificate_payload_marks_builder_report(certificate):
        valid = False
        add(
            target_blockers,
            f"{spec['certificate_key']}_builder_report_not_certificate",
            label,
        )

    expected_fields = {
        "schema": spec["schema"],
        "surface_id": surface_id,
        "promotion_status": "promoted",
        "v1_dependency_chain": list(DEPENDENCY_CHAIN),
        "v1_dependency_chain_position": spec["chain_position"],
        "required_by_surface": spec["required_by_surface"],
        "required_by_v1_dependency_chain_position": spec["required_by_chain_position"],
    }
    for key, expected in expected_fields.items():
        if certificate.get(key) != expected:
            valid = False
            add(
                target_blockers,
                f"{spec['certificate_key']}_{key}_mismatch",
                f"{label}.{key}",
                expected=expected,
                value=certificate.get(key),
            )

    if certificate.get("required_reviewed_artifact_hash") != REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH:
        valid = False
        add(
            target_blockers,
            f"{spec['certificate_key']}_required_reviewed_artifact_hash_mismatch",
            f"{label}.required_reviewed_artifact_hash",
            expected=REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH,
            value=certificate.get("required_reviewed_artifact_hash"),
        )
    if certificate.get("reviewed_artifact_hash_policy") != REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH_POLICY:
        valid = False
        add(
            target_blockers,
            f"{spec['certificate_key']}_reviewed_artifact_hash_policy_mismatch",
            f"{label}.reviewed_artifact_hash_policy",
            expected=REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH_POLICY,
            value=certificate.get("reviewed_artifact_hash_policy"),
        )
    if certificate.get("missing_mismatched_or_stale_certificate_counts") is not False:
        valid = False
        add(
            target_blockers,
            f"{spec['certificate_key']}_missing_mismatched_or_stale_certificate_counts_not_false",
            f"{label}.missing_mismatched_or_stale_certificate_counts",
            value=certificate.get("missing_mismatched_or_stale_certificate_counts"),
        )

    certificate_evidence = certificate.get("evidence")
    if not isinstance(certificate_evidence, dict):
        add(target_blockers, f"{spec['certificate_key']}_evidence_missing", f"{label}.evidence")
        return False
    expected_surface_hash = surface_record_sha256(surface, str(spec["certificate_key"]))
    if certificate_evidence.get("reviewed_surface_record_sha256") != expected_surface_hash:
        valid = False
        add(
            target_blockers,
            f"{spec['certificate_key']}_surface_record_sha256_mismatch",
            f"{label}.evidence.reviewed_surface_record_sha256",
            expected=expected_surface_hash,
            value=certificate_evidence.get("reviewed_surface_record_sha256"),
        )
    if certificate_evidence.get("reviewed_artifact_hash") != expected_surface_hash:
        valid = False
        add(
            target_blockers,
            f"{spec['certificate_key']}_reviewed_artifact_hash_mismatch",
            f"{label}.evidence.reviewed_artifact_hash",
            expected=expected_surface_hash,
            value=certificate_evidence.get("reviewed_artifact_hash"),
        )
    payload_blockers: list[dict[str, Any]] = []
    collect_promotion_certificate_payload_overclaims(
        certificate,
        payload_blockers,
        certificate_key=str(spec["certificate_key"]),
        label=label,
    )
    if payload_blockers:
        valid = False
        target_blockers.extend(payload_blockers)

    input_bindings = certificate.get("input_bindings")
    if surface_id == RESPONSE_PATH_SURFACE and not isinstance(input_bindings, dict):
        valid = False
        add(
            target_blockers,
            f"{spec['certificate_key']}_input_bindings_missing",
            f"{label}.input_bindings",
            required_direct_file_bindings=[
                "player_identity_promotion_certificate",
                "permissions_admin_promotion_certificate",
            ],
            inline_evidence_summaries_count=False,
        )
    if surface_id == DEPENDENCY_CHAIN[1]:
        identity = surface_by_id(surfaces, DEPENDENCY_CHAIN[0])
        identity_evidence = identity.get("evidence") if isinstance(identity, dict) else None
        identity_binding = (
            identity_evidence.get("player_identity_promotion_certificate")
            if isinstance(identity_evidence, dict)
            else None
        )
        declared_identity_binding = (
            input_bindings.get("player_identity_promotion_certificate")
            if isinstance(input_bindings, dict)
            else None
        )
        if not hash_bound_bindings_match(declared_identity_binding, identity_binding):
            valid = False
            add(
                target_blockers,
                f"{spec['certificate_key']}_current_player_identity_certificate_binding_missing_or_mismatch",
                f"{label}.input_bindings.player_identity_promotion_certificate",
                expected=identity_binding,
                value=declared_identity_binding,
            )
    if surface_id == RESPONSE_PATH_SURFACE:
        for upstream_surface_id, binding_key, upstream_label in (
            (DEPENDENCY_CHAIN[0], "player_identity_promotion_certificate", "player_identity"),
            (DEPENDENCY_CHAIN[1], "permissions_admin_promotion_certificate", "permissions_admin"),
        ):
            upstream = surface_by_id(surfaces, upstream_surface_id)
            upstream_evidence = upstream.get("evidence") if isinstance(upstream, dict) else None
            upstream_binding = (
                upstream_evidence.get(binding_key)
                if isinstance(upstream_evidence, dict)
                else None
            )
            declared_binding = (
                input_bindings.get(binding_key)
                if isinstance(input_bindings, dict)
                else None
            )
            if not hash_bound_bindings_match(declared_binding, upstream_binding):
                valid = False
                add(
                    target_blockers,
                    f"{spec['certificate_key']}_current_{upstream_label}_certificate_binding_missing_or_mismatch",
                    f"{label}.input_bindings.{binding_key}",
                    expected=upstream_binding,
                    value=declared_binding,
                )
    return valid


def promoted_manifest_entry_has_certificate(
    promoted: set[str],
    surface: dict[str, Any] | None,
    surface_id: str,
    blockers: list[dict[str, Any]],
    *,
    reason: str,
    surfaces: dict[str, Any] | None,
) -> bool:
    if surface_id not in promoted:
        return False
    if surface_has_valid_promotion_certificate(surface, surface_id, surfaces=surfaces):
        return True
    add(blockers, reason, "$.surfaces.promoted_surfaces")
    return False


def validate_commands_replies_direct_certificate_shortcuts(
    commands: dict[str, Any] | None,
    blockers: list[dict[str, Any]],
) -> None:
    if not isinstance(commands, dict):
        return
    evidence = commands.get("evidence")
    if not isinstance(evidence, dict):
        return

    if "player_identity_promotion_certificate" in evidence:
        add(
            blockers,
            "commands_replies_direct_player_identity_promotion_certificate_shortcut",
            "$.surfaces.surfaces[commands_replies].evidence.player_identity_promotion_certificate",
            required_certificate_schema=COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA,
            certificate_metadata_counts_as_promotion=False,
        )
    if (
        "permissions_admin_promotion_certificate" in evidence
        and "command_response_promotion_certificate" not in evidence
    ):
        add(
            blockers,
            "commands_replies_permissions_admin_certificate_without_command_response_certificate",
            "$.surfaces.surfaces[commands_replies].evidence.permissions_admin_promotion_certificate",
            required_certificate_schema=COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA,
            certificate_metadata_counts_as_promotion=False,
        )

    if "commands_replies_promotion_certificate" not in evidence:
        return

    label = "$.surfaces.surfaces[commands_replies].evidence.commands_replies_promotion_certificate"
    add(
        blockers,
        "commands_replies_promotion_certificate_terminal_artifact_non_counting",
        label,
        terminal_artifact_shortcuts_count=False,
        counts_toward_public_sdk=False,
        counts_toward_runtime=False,
        counts_toward_v1_completion=False,
        public_or_runtime_accounting_allowed=False,
        required_prior_certificate_schema=COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA,
        required_prior_certificate_key="command_response_promotion_certificate",
        required_before_counting=list(
            COMMANDS_REPLIES_PROMOTION_REQUIRED_ARTIFACT["required_evidence"]
        ),
    )
    certificate = load_promotion_certificate(
        evidence.get("commands_replies_promotion_certificate"),
        certificate_key="commands_replies_promotion_certificate",
        label=label,
        blockers=blockers,
    )
    if not isinstance(certificate, dict):
        return
    if promotion_certificate_payload_marks_builder_report(certificate):
        add(
            blockers,
            "commands_replies_promotion_certificate_builder_report_not_certificate",
            label,
        )
    collect_promotion_certificate_payload_overclaims(
        certificate,
        blockers,
        certificate_key="commands_replies_promotion_certificate",
        label=label,
    )


def validate_surfaces(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    require_equal(payload, "schema", SURFACES_SCHEMA, "$.surfaces", blockers)
    require_equal(payload, "v1_completion_required", False, "$.surfaces", blockers)
    if payload.get("v1_dependency_sequence") != list(DEPENDENCY_CHAIN):
        add(
            blockers,
            "v1_dependency_sequence_mismatch",
            "$.surfaces.v1_dependency_sequence",
            expected=list(DEPENDENCY_CHAIN),
            value=payload.get("v1_dependency_sequence"),
        )

    promoted = string_set(payload.get("promoted_surfaces"))
    if SURFACE in promoted:
        add(blockers, "commands_replies_listed_as_promoted", "$.surfaces.promoted_surfaces")

    required_chain = string_set(payload.get("v1_required_dependency_chain"))
    for surface in DEPENDENCY_CHAIN:
        if surface not in required_chain:
            add(blockers, "dependency_chain_surface_missing_from_required_chain", "$.surfaces.v1_required_dependency_chain", surface=surface)

    blockers_set = string_set(payload.get("v1_sdk_completion_blockers"))
    for surface in DEPENDENCY_CHAIN:
        if surface not in blockers_set:
            add(blockers, "dependency_chain_surface_missing_from_blockers", "$.surfaces.v1_sdk_completion_blockers", surface=surface)

    surfaces = payload.get("surfaces")
    if not isinstance(surfaces, list):
        add(blockers, "surfaces_not_list", "$.surfaces.surfaces")
        collect_overclaims(payload, blockers, "$.surfaces")
        return
    by_id = {item.get("id"): item for item in surfaces if isinstance(item, dict) and isinstance(item.get("id"), str)}
    commands = by_id.get(SURFACE)
    response_path = by_id.get(RESPONSE_PATH_SURFACE)
    identity = by_id.get(DEPENDENCY_CHAIN[0])
    permissions = by_id.get(DEPENDENCY_CHAIN[1])
    validate_commands_replies_direct_certificate_shortcuts(commands, blockers)
    promoted_manifest_entry_has_certificate(
        promoted,
        response_path,
        RESPONSE_PATH_SURFACE,
        blockers,
        reason="command_chat_response_manifest_promotion_without_evidence",
        surfaces=payload,
    )
    if RESPONSE_PATH_SURFACE in promoted and not surface_has_valid_promotion_certificate(response_path, RESPONSE_PATH_SURFACE, surfaces=payload):
        add(blockers, "response_path_planning_evidence_treated_as_promoted", "$.surfaces.promoted_surfaces")
    promoted_manifest_entry_has_certificate(
        promoted,
        identity,
        DEPENDENCY_CHAIN[0],
        blockers,
        reason="player_identity_manifest_promotion_without_evidence",
        surfaces=payload,
    )
    promoted_manifest_entry_has_certificate(
        promoted,
        permissions,
        DEPENDENCY_CHAIN[1],
        blockers,
        reason="permissions_admin_manifest_promotion_without_evidence",
        surfaces=payload,
    )
    response_path_promoted = False
    if isinstance(response_path, dict) and response_path.get("status") == "promoted":
        response_path_promoted = surface_has_valid_promotion_certificate(response_path, RESPONSE_PATH_SURFACE, blockers, surfaces=payload)
    identity_promoted = False
    if isinstance(identity, dict) and identity.get("status") in MANIFEST_PROMOTION_STATUSES:
        if identity.get("status") == "promoted":
            identity_promoted = surface_has_valid_promotion_certificate(identity, DEPENDENCY_CHAIN[0], blockers, surfaces=payload)
        if not identity_promoted:
            add(blockers, "player_identity_evidence_not_approved", "$.surfaces.surfaces[player_identity].status", status=identity.get("status"))
        evidence = identity.get("evidence")
        if (
            not isinstance(evidence, dict)
            or not isinstance(evidence.get("player_identity_promotion_certificate"), dict)
        ):
            add(
                blockers,
                "player_identity_promotion_certificate_missing",
                "$.surfaces.surfaces[player_identity].evidence.player_identity_promotion_certificate",
            )
    if isinstance(identity, dict):
        validate_player_identity_accepted_runtime_evidence(
            identity,
            blockers,
            label="$.surfaces.surfaces[player_identity]",
        )
    permissions_promoted = False
    if isinstance(permissions, dict) and permissions.get("status") in MANIFEST_PROMOTION_STATUSES:
        if permissions.get("status") == "promoted":
            permissions_promoted = surface_has_valid_promotion_certificate(permissions, DEPENDENCY_CHAIN[1], blockers, surfaces=payload)
        if not permissions_promoted:
            add(blockers, "permissions_admin_evidence_not_approved", "$.surfaces.surfaces[permissions_admin].status", status=permissions.get("status"))
    if isinstance(permissions, dict) and permissions.get("status") in MANIFEST_PROMOTION_STATUSES and not identity_promoted:
        add(
            blockers,
            "permissions_admin_promoted_before_player_identity",
            "$.surfaces.surfaces[permissions_admin].status",
        )
    if identity_promoted and not permissions_promoted:
        add(
            blockers,
            "permissions_admin_dependency_not_promoted",
            "$.surfaces.surfaces[permissions_admin].status",
        )
    if isinstance(response_path, dict) and response_path.get("status") in MANIFEST_PROMOTION_STATUSES:
        if not response_path_promoted:
            add(
                blockers,
                "command_chat_response_evidence_not_approved",
                "$.surfaces.surfaces[command_chat_response_path].status",
                status=response_path.get("status"),
            )
        if not identity_promoted:
            add(
                blockers,
                "command_chat_response_promoted_before_player_identity",
                "$.surfaces.surfaces[command_chat_response_path].status",
                required_prior_surface=DEPENDENCY_CHAIN[0],
                required_prior_certificate_schema=PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
            )
        if not permissions_promoted:
            add(
                blockers,
                "command_chat_response_promoted_before_permissions_admin",
                "$.surfaces.surfaces[command_chat_response_path].status",
                required_prior_surface=DEPENDENCY_CHAIN[1],
                required_prior_certificate_schema=PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA,
            )
    if not isinstance(commands, dict):
        add(blockers, "commands_replies_surface_missing", "$.surfaces.surfaces")
    else:
        if commands.get("status") not in {"planning", "post-v1"}:
            add(
                blockers,
                "commands_replies_status_mismatch",
                "$.surfaces.surfaces",
                expected=["planning", "post-v1"],
                value=commands.get("status"),
            )
        if commands.get("public_contract") != []:
            add(blockers, "commands_replies_public_contract_not_empty", "$.surfaces.surfaces.public_contract", value=commands.get("public_contract"))
        if commands.get("depends_on") != REQUIRED_DEPENDS_ON:
            add(
                blockers,
                "dependency_chain_depends_on_mismatch",
                "$.surfaces.surfaces.depends_on",
                expected=REQUIRED_DEPENDS_ON,
                value=commands.get("depends_on"),
            )
        contract = commands.get("v1_decision_contract")
        if not isinstance(contract, dict):
            add(blockers, "commands_replies_decision_contract_missing", "$.surfaces.surfaces.v1_decision_contract")
        else:
            if contract.get("decision_manifest") != "docs/commands_replies_public_contract_decisions.json":
                add(blockers, "commands_replies_decision_manifest_mismatch", "$.surfaces.surfaces.v1_decision_contract")
            if contract.get("must_remain_without_public_contract_until_promotion") is not True:
                add(blockers, "commands_replies_public_contract_gate_missing", "$.surfaces.surfaces.v1_decision_contract")
            missing_not_sufficient = REQUIRED_SURFACE_NOT_SUFFICIENT - string_set(contract.get("not_sufficient_evidence"))
            if missing_not_sufficient:
                add(
                    blockers,
                    "commands_replies_not_sufficient_evidence_missing",
                    "$.surfaces.surfaces.v1_decision_contract.not_sufficient_evidence",
                    missing=sorted(missing_not_sufficient),
                )

    if not isinstance(response_path, dict):
        add(blockers, "response_path_surface_missing", "$.surfaces.surfaces")
    else:
        if response_path.get("status") == "promoted" and not response_path_promoted:
            add(
                blockers,
                "response_path_planning_evidence_treated_as_promoted",
                "$.surfaces.surfaces.status",
                expected=["planning", "post-v1", "valid promoted certificate"],
                value=response_path.get("status"),
            )
        elif response_path.get("status") not in {"planning", "post-v1", "promoted"}:
            add(
                blockers,
                "response_path_planning_evidence_treated_as_promoted",
                "$.surfaces.surfaces.status",
                expected=["planning", "post-v1", "valid promoted certificate"],
                value=response_path.get("status"),
            )
        if response_path.get("public_contract") not in ([], None) and response_path.get("status") != "promoted":
            add(blockers, "response_path_public_contract_not_empty_while_unpromoted", "$.surfaces.surfaces.public_contract")

    guardrails = "\n".join(strings(payload.get("release_guardrails")))
    for fragment in (
        "Identity/principal, permissions/admin, command/chat response path, and commands/replies are an ordered v1 dependency chain",
        "Commands/replies also depend on obelisk.command_chat_response_path.v1",
        "command/chat response path is unpromoted, no reply, send-chat, broadcast/notices, moderation, or public CallProcessEvent path may be documented as promoted",
        "legacy CallProcessEvent debug access are not public response-path or command/reply promotion evidence",
    ):
        if fragment not in guardrails:
            add(blockers, "release_guardrail_missing", "$.surfaces.release_guardrails", fragment=fragment)

    collect_overclaims(payload, blockers, "$.surfaces")


def validate_public_header(path: Path, blockers: list[dict[str, Any]]) -> None:
    try:
        reject_symlink_component(path, "public_header")
        resolved = reject_protected_input_path(path, "public_header")
        if resolved != DEFAULT_PUBLIC_HEADER.resolve():
            add(
                blockers,
                "public_header_path_mismatch",
                "$.public_header",
                expected=str(DEFAULT_PUBLIC_HEADER),
                path=str(path),
                resolved=str(resolved),
            )
        header = without_native_prototype_symbols(
            strip_c_comments(resolved.read_text(encoding="utf-8")), header_only=True
        )
    except SystemExit as exc:
        add(blockers, "public_header_path_rejected", "$.public_header", path=str(path), detail=str(exc))
        return
    except OSError as exc:
        add(blockers, "public_header_unreadable", "$.public_header", path=str(path), detail=str(exc))
        return
    observed = sorted(token for token in REQUIRED_HEADER_ABSENT_TOKENS if re.search(rf"\b{re.escape(token)}\b", header))
    if observed:
        add(blockers, "public_header_forbidden_symbols_present", "$.public_header", symbols=observed)


def validate_response_path_report(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    expected_root: Path | None = None,
    expected_readiness: Path | None = None,
    expected_surfaces: Path | None = None,
    expected_public_header: Path | None = None,
    expected_route_blocker: str = CURRENT_ROUTE_BLOCKER,
) -> None:
    schema = payload.get("schema")
    if schema == RESPONSE_PATH_REPORT_SCHEMA:
        resolved_expected_root: Path | None = None
        missing_source_artifacts = [
            key
            for key in RESPONSE_PATH_SOURCE_ARTIFACT_KEYS
            if key not in payload
        ]
        if missing_source_artifacts:
            add(
                blockers,
                "response_path_report_source_artifacts_missing",
                "$.response_path_report",
                missing=missing_source_artifacts,
            )
        unverifiable_source_artifacts = {
            key: payload.get(key)
            for key in RESPONSE_PATH_SOURCE_ARTIFACT_KEYS
            if key in payload and (not isinstance(payload.get(key), str) or payload.get(key) == "")
        }
        if unverifiable_source_artifacts:
            add(
                blockers,
                "response_path_report_unverifiable",
                "$.response_path_report",
                artifacts=unverifiable_source_artifacts,
            )
        if missing_source_artifacts or unverifiable_source_artifacts:
            add(
                blockers,
                "response_path_report_not_revalidatable_handoff",
                "$.response_path_report",
                required_source_artifact_keys=list(RESPONSE_PATH_SOURCE_ARTIFACT_KEYS),
                missing=missing_source_artifacts,
                unverifiable=unverifiable_source_artifacts,
            )
        resolved_source_artifacts: dict[str, Path] = {}
        if not missing_source_artifacts and not unverifiable_source_artifacts:
            for key in RESPONSE_PATH_SOURCE_ARTIFACT_KEYS:
                resolved = resolve_source_artifact_path(Path(payload[key]), key, blockers)
                if resolved is not None:
                    resolved_source_artifacts[key] = resolved
        source_hashes = payload.get("source_artifact_hashes")
        if not isinstance(source_hashes, dict):
            add(
                blockers,
                "response_path_report_source_artifact_hashes_missing",
                "$.response_path_report.source_artifact_hashes",
                value=source_hashes,
            )
        else:
            for key in RESPONSE_PATH_SOURCE_ARTIFACT_KEYS:
                observed_hash = source_hashes.get(key)
                if not isinstance(observed_hash, str) or SHA256_RE.fullmatch(observed_hash) is None:
                    add(
                        blockers,
                        "response_path_report_source_artifact_hash_missing_or_invalid",
                        f"$.response_path_report.source_artifact_hashes.{key}",
                        value=observed_hash,
                    )
                    continue
                resolved_artifact = resolved_source_artifacts.get(key)
                if resolved_artifact is not None:
                    actual_hash = sha256_file(resolved_artifact)
                    if observed_hash != actual_hash:
                        add(
                            blockers,
                            "response_path_report_source_artifact_hash_mismatch",
                            f"$.response_path_report.source_artifact_hashes.{key}",
                            expected=actual_hash,
                            value=observed_hash,
                        )
        if expected_root is None:
            add(blockers, "response_path_report_expected_root_required", "$.response_path_root")
        else:
            resolved_expected_root = resolve_expected_path(expected_root, "response_path_root", blockers)
            if resolved_expected_root is not None:
                observed_root = payload.get("readiness_root")
                if observed_root != str(resolved_expected_root):
                    add(
                        blockers,
                        "response_path_report_readiness_root_mismatch",
                        "$.response_path_report.readiness_root",
                        expected=str(resolved_expected_root),
                        value=observed_root,
                    )
                if isinstance(observed_root, str) and resolved_source_artifacts.get("readiness_path") is not None:
                    observed_source_root = resolved_source_artifacts["readiness_path"].parent
                    if observed_source_root != resolved_expected_root:
                        add(
                            blockers,
                            "response_path_report_source_readiness_root_mismatch",
                            "$.response_path_report.readiness_path",
                            expected=str(resolved_expected_root),
                            value=str(observed_source_root),
                        )
        if expected_readiness is None:
            add(blockers, "response_path_report_expected_readiness_required", "$.response_path_readiness")
        else:
            resolved_expected_readiness = resolve_expected_path(expected_readiness, "response_path_readiness", blockers)
            observed_readiness = payload.get("readiness_path")
            if (
                resolved_expected_readiness is not None
                and resolved_source_artifacts.get("readiness_path") != resolved_expected_readiness
            ):
                add(
                    blockers,
                    "response_path_report_readiness_path_mismatch",
                    "$.response_path_report.readiness_path",
                    expected=str(resolved_expected_readiness),
                    value=str(resolved_source_artifacts.get("readiness_path")),
                )
            if resolved_expected_readiness is not None and observed_readiness != str(resolved_expected_readiness):
                add(
                    blockers,
                    "response_path_report_readiness_path_metadata_mismatch",
                    "$.response_path_report.readiness_path",
                    expected=str(resolved_expected_readiness),
                    value=observed_readiness,
                )
        if expected_surfaces is not None:
            resolved_expected_surfaces = resolve_expected_path(expected_surfaces, "surfaces", blockers)
            if (
                resolved_expected_surfaces is not None
                and resolved_source_artifacts.get("surfaces_path") != resolved_expected_surfaces
            ):
                add(
                    blockers,
                    "response_path_report_surfaces_path_mismatch",
                    "$.response_path_report.surfaces_path",
                    expected=str(resolved_expected_surfaces),
                    value=str(resolved_source_artifacts.get("surfaces_path")),
                )
        if expected_public_header is not None:
            resolved_expected_public_header = resolve_expected_path(expected_public_header, "public_header", blockers)
            if (
                resolved_expected_public_header is not None
                and resolved_source_artifacts.get("public_header_path") != resolved_expected_public_header
            ):
                add(
                    blockers,
                    "response_path_report_public_header_path_mismatch",
                    "$.response_path_report.public_header_path",
                    expected=str(resolved_expected_public_header),
                    value=str(resolved_source_artifacts.get("public_header_path")),
                )
        if payload.get("valid") is not True or payload.get("accepted_for_planning") is not True:
            add(blockers, "response_path_report_not_accepted_for_planning", "$.response_path_report")
        if payload.get("planning_only") is not True:
            add(
                blockers,
                "response_path_report_not_planning_only",
                "$.response_path_report.planning_only",
                value=payload.get("planning_only"),
            )
        if payload.get("dependency_chain_locked") is not True:
            add(
                blockers,
                "response_path_report_dependency_chain_not_locked",
                "$.response_path_report.dependency_chain_locked",
                value=payload.get("dependency_chain_locked"),
            )
        if payload.get("current_route_blocker") != expected_route_blocker:
            add(
                blockers,
                "response_path_report_route_blocker_mismatch",
                "$.response_path_report.current_route_blocker",
                expected=expected_route_blocker,
                value=payload.get("current_route_blocker"),
            )
        if payload.get("remaining_route_blockers") != [expected_route_blocker]:
            add(
                blockers,
                "response_path_report_remaining_route_blockers_mismatch",
                "$.response_path_report.remaining_route_blockers",
                expected=[expected_route_blocker],
                value=payload.get("remaining_route_blockers"),
            )
        if payload.get("surface") not in (RESPONSE_PATH_SURFACE, None):
            add(
                blockers,
                "response_path_report_surface_mismatch",
                "$.response_path_report.surface",
                value=payload.get("surface"),
            )
        if payload.get("target_set") != response_path_readiness.TARGET_SET:
            add(
                blockers,
                "response_path_report_target_set_mismatch",
                "$.response_path_report.target_set",
                expected=response_path_readiness.TARGET_SET,
                value=payload.get("target_set"),
            )
        if string_set(payload.get("target_filters")) != response_path_readiness.TARGETS:
            add(
                blockers,
                "response_path_report_target_filters_mismatch",
                "$.response_path_report.target_filters",
                expected=sorted(response_path_readiness.TARGETS),
                value=payload.get("target_filters"),
            )
        if payload.get("readiness_status") != "compared":
            add(
                blockers,
                "response_path_report_readiness_status_mismatch",
                "$.response_path_report.readiness_status",
                expected="compared",
                value=payload.get("readiness_status"),
            )
        if payload.get("decisions_status") != "blocked":
            add(
                blockers,
                "response_path_report_decisions_status_mismatch",
                "$.response_path_report.decisions_status",
                expected="blocked",
                value=payload.get("decisions_status"),
            )
        if payload.get("surfaces_status") not in ("planning", "post-v1"):
            add(
                blockers,
                "response_path_report_surfaces_status_mismatch",
                "$.response_path_report.surfaces_status",
                expected=["planning", "post-v1"],
                value=payload.get("surfaces_status"),
            )
        if payload.get("blockers") != []:
            add(
                blockers,
                "response_path_report_blockers_not_empty",
                "$.response_path_report.blockers",
                value=payload.get("blockers"),
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
                add(
                    blockers,
                    f"response_path_report_{key}_not_false",
                    f"$.response_path_report.{key}",
                    value=payload.get(key),
                )
        if len(resolved_source_artifacts) == len(RESPONSE_PATH_SOURCE_ARTIFACT_KEYS):
            decisions_path = resolved_source_artifacts["decisions_path"]
            default_decisions = response_path_readiness.DEFAULT_DECISIONS.resolve()
            post_evidence_decisions_path_allowed = False
            if (
                expected_route_blocker == IDENTITY_CONTRACT_ROUTE_BLOCKER
                and resolved_expected_root is not None
                and decisions_path.name == response_path_readiness.DEFAULT_DECISIONS.name
            ):
                try:
                    decisions_path.relative_to(resolved_expected_root)
                    post_evidence_decisions_path_allowed = True
                except ValueError:
                    post_evidence_decisions_path_allowed = False
            if decisions_path != default_decisions and not post_evidence_decisions_path_allowed:
                add(
                    blockers,
                    "response_path_report_decisions_path_mismatch",
                    "$.response_path_report.decisions_path",
                    expected=str(response_path_readiness.DEFAULT_DECISIONS),
                    value=str(decisions_path),
                )
            readiness_root = resolved_source_artifacts["readiness_path"].parent
            rebuilt = response_path_readiness.build_report(
                readiness_root,
                resolved_source_artifacts["readiness_path"],
                resolved_source_artifacts["decisions_path"],
                resolved_source_artifacts["public_header_path"],
                resolved_source_artifacts["surfaces_path"],
                current_route_blocker=expected_route_blocker,
            )
            if rebuilt.get("valid") is not True or rebuilt.get("accepted_for_planning") is not True:
                add(
                    blockers,
                    "response_path_report_source_artifact_revalidation_failed",
                    "$.response_path_report",
                    rebuilt_blockers=rebuilt.get("blockers"),
                )
            for key in sorted(set(payload) | set(rebuilt)):
                if key not in payload:
                    add(
                        blockers,
                        "response_path_report_source_artifact_identity_mismatch",
                        f"$.response_path_report.{key}",
                        expected=rebuilt.get(key),
                        value="<missing>",
                    )
                elif key not in rebuilt:
                    add(
                        blockers,
                        "response_path_report_source_artifact_identity_mismatch",
                        f"$.response_path_report.{key}",
                        expected="<absent>",
                        value=payload.get(key),
                    )
                elif payload.get(key) != rebuilt.get(key):
                    add(
                        blockers,
                        "response_path_report_source_artifact_identity_mismatch",
                        f"$.response_path_report.{key}",
                        expected=rebuilt.get(key),
                        value=payload.get(key),
                    )
    else:
        add(blockers, "response_path_report_schema_mismatch", "$.response_path_report.schema", value=schema)
    collect_overclaims(payload, blockers, "$.response_path_report")


def build_report(
    *,
    decisions_path: Path,
    surfaces_path: Path,
    public_header_path: Path,
    response_path_report_path: Path | None,
    response_path_root: Path | None = None,
    response_path_readiness: Path | None = None,
    response_path_report_root: Path | None = None,
    current_route_blocker: str = CURRENT_ROUTE_BLOCKER,
) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    if current_route_blocker not in ALLOWED_ROUTE_BLOCKERS:
        add(
            blockers,
            "current_route_blocker_mismatch",
            "$.current_route_blocker",
            expected=list(ALLOWED_ROUTE_BLOCKERS),
            value=current_route_blocker,
        )
    expected_report_root = response_path_report_root if response_path_report_root is not None else response_path_root
    validate_response_path_report_location(
        response_path_report_path,
        blockers,
        expected_report_root=expected_report_root,
    )
    decisions = load_json(decisions_path, "decisions", blockers)
    surfaces = load_json(surfaces_path, "surfaces", blockers)
    response_path_report = (
        load_json(response_path_report_path, "response_path_report", blockers)
        if response_path_report_path is not None
        else None
    )
    if response_path_report_path is None:
        add(blockers, "response_path_report_required", "$.response_path_report_path")

    if decisions is not None:
        validate_decisions(decisions, blockers, public_header_path)
        validate_accounting_lock_route_order(
            decisions,
            blockers,
            label="$.decisions",
            surfaces=surfaces,
            current_route_blocker=current_route_blocker,
        )
    if surfaces is not None:
        validate_surfaces(surfaces, blockers)
    validate_route_blocker_order(current_route_blocker, surfaces, blockers)
    validate_public_header(public_header_path, blockers)
    if response_path_report is not None:
        validate_response_path_report(
            response_path_report,
            blockers,
            expected_root=response_path_root,
            expected_readiness=response_path_readiness,
            expected_surfaces=surfaces_path,
            expected_public_header=public_header_path,
            expected_route_blocker=current_route_blocker,
        )

    valid = not blockers
    route_action = current_route_next_action(current_route_blocker)
    next_action_sequence = build_next_action_sequence(current_route_blocker)
    downstream_chain_gate = build_downstream_chain_gate(current_route_blocker)
    post_command_response_blocker_diagnostic = (
        build_post_command_response_blocker_diagnostic(current_route_blocker)
    )
    return {
        "schema": REPORT_SCHEMA,
        "valid": valid,
        "accepted_for_planning": valid,
        "planning_only": valid,
        "surface": SURFACE,
        "dependency_chain": list(DEPENDENCY_CHAIN),
        "dependency_chain_locked": True,
        "blocked_behind_surfaces": BLOCKED_BEHIND_SURFACES,
        "current_route_blocker": current_route_blocker,
        "remaining_route_blockers": [current_route_blocker],
        "candidate_capture_classification": CANDIDATE_CAPTURE_CLASSIFICATION,
        "candidate_capture_guardrail": build_candidate_capture_guardrail(current_route_blocker),
        "candidate_capture_counts_toward_public_sdk": False,
        "candidate_capture_counts_toward_runtime": False,
        "candidate_capture_counts_toward_v1_completion": False,
        "candidate_capture_counts_toward_complete_sdk_claim": False,
        "candidate_capture_counts_toward_p0_dependency_chain_claim": False,
        "candidate_capture_progress_contribution": 0,
        "candidate_capture_public_or_runtime_accounting_allowed": False,
        "command_support_ready": False,
        "accepted_runtime_evidence": False,
        "approved_runtime_evidence": False,
        "next_route_action": route_action["next_action"],
        "next_route_blocked_until": route_action["blocked_until"],
        "next_route_blocker_after_runtime_evidence": IDENTITY_CONTRACT_ROUTE_BLOCKER,
        "next_required_surface": RESPONSE_PATH_SURFACE,
        "next_required_artifact": COMMAND_RESPONSE_PROMOTION_REQUIRED_ARTIFACT,
        "command_response_promotion_gate": command_response_promotion_gate_metadata(),
        "response_path_handoff_required": RESPONSE_PATH_REPORT_HANDOFF_REQUIREMENT,
        "response_path_report_implicit_synthesis_allowed": False,
        "response_path_report_summary_shortcut_allowed": False,
        "post_command_response_blocker_diagnostic": post_command_response_blocker_diagnostic,
        "downstream_chain_gate": downstream_chain_gate,
        "downstream_blockers": downstream_chain_gate["post_command_response_required_sequence"],
        "post_response_abi_evidence_guardrail": POST_RESPONSE_ABI_EVIDENCE_GUARDRAIL,
        "next_action_sequence": next_action_sequence,
        "first_missing_terminal_artifact": "commands_replies_promotion_certificate",
        "first_missing_terminal_artifact_schema": (
            COMMANDS_REPLIES_PROMOTION_CERTIFICATE_SCHEMA
        ),
        "first_missing_terminal_artifact_required_prior_certificate": (
            "command_response_promotion_certificate"
        ),
        "terminal_artifact_shortcuts_count": False,
        "terminal_promotion_required_artifact": COMMANDS_REPLIES_PROMOTION_REQUIRED_ARTIFACT,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "p0_dependency_chain_progress_contribution": 0,
        "public_or_runtime_accounting_allowed": False,
        "public_readiness_ready": False,
        "public_abi_ready": False,
        "runtime_ready": False,
        "public_command_router_allowed": False,
        "public_reply_or_send_chat_abi_allowed": False,
        "public_response_path_allowed": False,
        "public_header_allowed": False,
        "public_send_chat_api_allowed": False,
        "public_broadcast_api_allowed": False,
        "activation_preconditions_met": False,
        "activation_preconditions_unlock_allowed": False,
        "beta_notice_sent": False,
        "beta_notice_send_unlock_allowed": False,
        "public_reachability_ready": False,
        "public_reachability_unlock_allowed": False,
        "request_check_ready": False,
        "request_pack_ready": False,
        "request_check_unlock_allowed": False,
        "identity_public_contract_gate_missing_unlock_allowed": False,
        "future_public_abi": {
            "blocked_behind_surfaces": BLOCKED_BEHIND_SURFACES,
            "requires": list(FUTURE_PUBLIC_ABI_REQUIRES),
        },
        "non_claim": (
            "valid planning output does not count commands/replies while player identity remains "
            f"blocked on {current_route_blocker}"
        ),
        "decisions_path": str(decisions_path),
        "surfaces_path": str(surfaces_path),
        "public_header_path": str(public_header_path),
        "response_path_report_path": str(response_path_report_path) if response_path_report_path is not None else None,
        "source_artifact_hashes": source_artifact_hashes(
            {
                "decisions_path": decisions_path,
                "surfaces_path": surfaces_path,
                "public_header_path": public_header_path,
                "response_path_report_path": response_path_report_path,
            }
        ),
        "response_path_report_root": str(expected_report_root) if expected_report_root is not None else None,
        "decisions_status": decisions.get("status") if isinstance(decisions, dict) else None,
        "commands_replies_surface_status": (
            next(
                (
                    item.get("status")
                    for item in surfaces.get("surfaces", [])
                    if isinstance(item, dict) and item.get("id") == SURFACE
                ),
                None,
            )
            if isinstance(surfaces, dict) and isinstance(surfaces.get("surfaces"), list)
            else None
        ),
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
    }


def main() -> int:
    args = parse_args()
    report = build_report(
        decisions_path=args.decisions,
        surfaces_path=args.surfaces,
        public_header_path=args.public_header,
        response_path_report_path=args.response_path_report,
        response_path_root=args.response_path_root,
        response_path_readiness=args.response_path_readiness,
        response_path_report_root=args.response_path_report_root,
        current_route_blocker=args.current_route_blocker,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
