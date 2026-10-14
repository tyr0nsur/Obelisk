#!/usr/bin/env python3
"""Validate command/chat response public-readiness stays planning-only."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from native_prototype_guardrails import without_native_prototype_symbols
from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_ROOT = REPO_ROOT / "tests" / "fixtures" / "command_chat_response_route_planning_default"
DEFAULT_READINESS_NAME = "command-chat-response-route-planning-readiness.json"
DEFAULT_DECISIONS = REPO_ROOT / "docs" / "command_chat_response_public_contract_decisions.json"
DEFAULT_PUBLIC_HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"
DEFAULT_PUBLIC_HEADER_DECL = "include/obelisk/ObeliskApi.h"
DEFAULT_SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
EXPECTED_READINESS_PRODUCER_SCRIPT = "scripts/compare_reflection_snapshots.py"

REPORT_SCHEMA = "obelisk.command-chat-response-public-readiness-check.v1"
READINESS_SCHEMA = "obelisk.reflection-snapshot-readiness.v1"
DECISIONS_SCHEMA = "obelisk.command-chat-response-public-contract-decisions.v1"
SURFACES_SCHEMA = "obelisk.public-sdk-surfaces.v1"
SURFACE = "obelisk.command_chat_response_path.v1"
IDENTITY_SURFACE = "obelisk.player_identity.v1"
PERMISSIONS_SURFACE = "obelisk.permissions_admin.v1"
COMMANDS_REPLIES_SURFACE = "obelisk.commands_replies.v1"
DEPENDENCY_CHAIN = [IDENTITY_SURFACE, PERMISSIONS_SURFACE, SURFACE, COMMANDS_REPLIES_SURFACE]
BLOCKED_BEHIND_SURFACES = [IDENTITY_SURFACE, PERMISSIONS_SURFACE]
PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA = "obelisk.player-identity-promotion-certificate.v1"
PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA = "obelisk.permissions-admin-promotion-certificate.v1"
COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA = "obelisk.command-chat-response-path-promotion-certificate.v1"
REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH = "evidence.reviewed_surface_record_sha256"
REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH_POLICY = (
    "must match the reviewed surface record hash carried by the certificate"
)
CURRENT_ROUTE_BLOCKER = "approved_runtime_evidence_missing"
ALLOWED_ROUTE_BLOCKERS = (
    "approved_runtime_evidence_missing",
    "identity_public_contract_gate_missing",
)
RUNTIME_EVIDENCE_ROUTE_BLOCKER = "approved_runtime_evidence_missing"
IDENTITY_CONTRACT_ROUTE_BLOCKER = "identity_public_contract_gate_missing"
MANIFEST_PROMOTION_STATUSES = frozenset(("promoted", "promoted-experimental-only"))
TARGET_SET = "command-chat-response-route-planning"
TARGETS = frozenset(
    (
        "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientChatMessage",
        "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientServerChatDirectMessage",
        "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientServerChatMessage",
    )
)
REQUIRED_DECISION_IDS = frozenset(
    (
        "dependency.promoted_player_identity",
        "dependency.promoted_permissions_admin",
        "abi.copied_response_payload",
        "abi.capability_and_owner_token",
        "lifecycle.owner_scoped_unregister_and_drain",
        "privacy.redaction_and_targeting",
        "abuse.rate_limit_and_audit",
        "separation.no_commands_router_or_moderation",
        "evidence.layout_runtime_sdk_coverage",
        "evidence.response_target_set_snapshot_second_source",
    )
)
REQUIRED_FORBIDDEN_PUBLIC_CONTRACT = frozenset(
    (
        "public CallProcessEvent response path",
        "public minimal ChatMessageEvent response path",
        "public generic chat routing response path",
        "public raw ProcessEvent response path",
        "raw ProcessEvent or legacy CallProcessEvent fallback",
        "public static thunk orientation response path",
        "public commands/replies response shortcut before promoted identity and permissions/admin",
        "activation preconditions, beta notice sends, public reachability, request checks, and identity_public_contract_gate_missing aliases cannot be used as command/chat response unlocks",
        "raw UE pointers",
        "raw ProcessEvent params",
        "raw FString storage",
        "UObject pointers",
        "UFunction pointers",
        "FName/GObjects indices",
        "direct native-call wrappers",
        "reply API",
        "send-chat API",
        "reply/send-chat/router claims before promotion",
        "broadcast/notices API",
        "moderation API",
        "principal or permission claims from command text",
        "principal or permission claims from operator config",
        "player lookup",
        "mutation",
        "return override",
    )
)
REQUIRED_GUIDANCE_BLOCKERS = frozenset(
    (
        "planning_guidance_only",
        "not_release_readiness_target",
        "public_response_path_blocked",
        "player_identity_principal_blocked",
        "permissions_admin_blocked",
        "command_router_blocked",
        "runtime_observation_requires_separate_approval",
    )
)
REQUIRED_REDACTION_GUIDANCE_FRAGMENTS = (
    "ClientChatMessage.Chat remains redacted/recognition-only until separate ChatMessage ScriptStruct and privacy review",
    "raw FString storage/data is forbidden, including ClientServerChatMessage.MessageText and ClientServerChatDirectMessage.MessageText",
    "sender identity remains redacted: no player name, platform ID, Steam/EOS ID, controller/connection/object ref, UE pointer, object-array/FName identity",
    "directed recipient identity remains redacted: no player name, platform ID, Steam/EOS ID, controller/connection/object ref, UE pointer, object-array/FName identity",
    "future targeting must use only a promoted copied principal handle/generation, not command text, operator config, raw params, or response UFunction layout",
)
REQUIRED_PRIVACY_DECISION_BEHAVIORS = frozenset(
    (
        "principal tuple source must be runtime-owned player identity observation before any directed response target is public",
        "principal_handle, principal_generation, and principal_scope_flags must appear together before response targeting can consume player identity",
        "plugin-supplied principal tuple fails closed",
        "command-supplied principal tuple fails closed",
        "operator-supplied principal tuple fails closed",
        "missing principal provenance fails closed",
        "server process epoch mismatch fails closed",
        "permission allow cannot be consumed without policy provenance",
        "runtime-owned principal tuple must be paired with runtime-owned permission provenance before reply/send-chat/router planning can become public",
        "ClientChatMessage.Chat remains redacted/recognition-only until separate ChatMessage ScriptStruct and privacy review",
        "raw FString storage/data is forbidden, including ClientServerChatMessage.MessageText and ClientServerChatDirectMessage.MessageText",
        "sender identity remains redacted and does not expose player name, platform ID, Steam/EOS ID, controller/connection/object ref, UE pointer, object-array/FName identity",
        "directed recipient identity remains redacted and does not expose player name, platform ID, Steam/EOS ID, controller/connection/object ref, UE pointer, object-array/FName identity",
        "future targeting must use only a promoted copied principal handle/generation, not command text, operator config, raw params, or response UFunction layout",
    )
)
REQUIRED_IDENTITY_DEPENDENCY_BEHAVIORS = frozenset(
    (
        "runtime observation establishes principal identity before command/chat response can consume it",
        "command text cannot establish principal identity",
        "operator config enables surfaces only and cannot establish principal identity",
        "response delivery never creates identity or permission claims",
        "minimal ChatMessageEvent, raw ProcessEvent, legacy CallProcessEvent, and static thunk orientation cannot establish principal identity",
        "generic chat routing cannot establish principal identity",
        "chat intake, send mode, passive parsing, command text, and chat snapshots cannot establish principal identity or roadmap priority",
        "commands/replies planning cannot bypass identity promotion",
        "accepted runtime evidence, reviewed identity contract aliases, and player-identity promotion certificate status text cannot replace a matching player-identity promotion certificate with current artifact hash and first chain position",
    )
)
REQUIRED_PERMISSIONS_DEPENDENCY_BEHAVIORS = frozenset(
    (
        "permissions/admin must be promoted before any reply, send-chat, broadcast, or moderation delivery is public",
        "minimal ChatMessageEvent, raw ProcessEvent, legacy CallProcessEvent, and static thunk orientation cannot establish permissions or admin authority",
        "generic chat routing cannot establish permissions or admin authority",
        "chat intake, send mode, passive parsing, command text, and chat snapshots cannot establish permissions, targeting, command authority, moderation authority, or roadmap priority",
        "commands/replies planning cannot bypass permissions/admin promotion",
        "runtime-owned permissions/admin allow for the same runtime-owned principal tuple is required before any reply, send-chat, broadcast, moderation, or router response path is public",
        "activation preconditions, beta notice sends, public reachability, request checks, and identity_public_contract_gate_missing aliases cannot unlock reply, send-chat, broadcast, moderation, or router response delivery before permissions/admin promotion",
        "permissions/admin shortcut aliases, command planning records, and response bridge records cannot stand in for the promoted permissions/admin certificate or the upstream player-identity promotion certificate",
    )
)
REQUIRED_LIFECYCLE_DECISION_BEHAVIORS = frozenset(
    (
        "owner unregister cancels pending responses for that plugin owner",
        "plugin init failure cleans up registered response handles before dlclose",
        "plugin unload waits for in-flight response callbacks or fails closed without dlclose",
        "future reply/send-chat/router response paths require owner-scoped lifecycle and unregister cleanup before public ABI",
        "raw ProcessEvent and legacy CallProcessEvent fallback do not satisfy response unregister cleanup or drain",
        "response callbacks cannot outlive copied payload storage",
        "server shutdown does not call into unmapped plugin code",
    )
)
REQUIRED_ABUSE_DECISION_BEHAVIORS = frozenset(
    (
        "response attempts are rate-limited per plugin owner token",
        "reply/send-chat/router response attempts require rate-limit and sanitized audit checks per plugin owner token before delivery",
        "burst exhaustion drops or rejects the response, never bypasses permission checks",
        "raw ProcessEvent and legacy CallProcessEvent fallback cannot bypass response abuse or audit gates",
        "malformed UTF-8 or oversize messages fail closed",
        "audit records are sanitized and do not expose raw UE internals",
        "operator controls can disable response delivery without disabling passive chat intake",
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
        "next-action artifact",
        "no-users passive runtime",
        "notice artifact",
        "package-shape artifact",
        "passive evidence",
        "passive monitor output",
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
        "router metadata",
        "runtime status artifact",
        "status artifact",
        "status metadata",
        "passive ChatMessageEvent",
        "raw ProcessEvent",
        "legacy CallProcessEvent",
        "static thunk orientation",
    )
)
REQUIRED_LAYOUT_RUNTIME_SDK_NOT_SUFFICIENT = frozenset(
    (
        "activation preconditions met are not sufficient",
        "beta notice sent is not sufficient",
        "copied response intent planning is not sufficient",
        "identity_public_contract_gate_missing route blocker is not sufficient",
        "local routing or chat seeds are not sufficient",
        "next-action runner/planner artifacts are not sufficient",
        "no-users/passive runtime is not sufficient",
        "notice artifacts are not sufficient",
        "package-shape artifacts are not sufficient",
        "passive evidence is not sufficient",
        "passive monitor ticks/output and passive player summaries/snapshots are not sufficient",
        "public reachability is not sufficient",
        "request checks are not sufficient",
        "response bridge planning is not sufficient",
        "side-lane evidence is not sufficient",
        "runtime status artifacts are not sufficient",
        "status artifacts are not sufficient",
        "static thunk orientation",
        "candidate vtable slots",
        "minimal ChatMessageEvent callback registration",
        "passive ChatMessageEvent parsing",
        "generic chat routing",
        "commands/replies planning status",
        "legacy CallProcessEvent debug gate",
        "raw ProcessEvent callbacks",
    )
)
REQUIRED_RESPONSE_TARGET_NOT_SUFFICIENT = frozenset(
    (
        "activation preconditions met are not sufficient",
        "beta notice sent is not sufficient",
        "copied response intent planning is not sufficient",
        "identity_public_contract_gate_missing route blocker is not sufficient",
        "local routing or chat seeds are not sufficient",
        "next-action runner/planner artifacts are not sufficient",
        "no-users/passive runtime is not sufficient",
        "notice artifacts are not sufficient",
        "package-shape artifacts are not sufficient",
        "passive evidence is not sufficient",
        "passive monitor ticks/output and passive player summaries/snapshots are not sufficient",
        "public reachability is not sufficient",
        "request checks are not sufficient",
        "response bridge planning is not sufficient",
        "side-lane evidence is not sufficient",
        "runtime status artifacts are not sufficient",
        "status artifacts are not sufficient",
        "static thunk orientation",
        "minimal ChatMessageEvent callback registration",
        "generic chat routing",
        "raw ProcessEvent callbacks",
        "legacy CallProcessEvent debug gate",
    )
)
FUTURE_PUBLIC_ABI_REQUIRES = (
    {
        "surface": IDENTITY_SURFACE,
        "required_artifact": "approved_runtime_principal_lifecycle_evidence",
        "certificate_schema": PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
    },
    {
        "surface": PERMISSIONS_SURFACE,
        "certificate_schema": PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA,
        "requires_certificate_schema": PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
        "required_by_surface": SURFACE,
    },
    {
        "surface": SURFACE,
        "certificate_schema": COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA,
        "required_by_surface": COMMANDS_REPLIES_SURFACE,
        "required_evidence": [
            "copied_response_abi_layout_tests",
            "sdk_consumer_tests",
            "isolated_runtime_delivery_evidence",
            "second_source_or_independently_reviewed_response_target_evidence",
        ],
    },
)
POST_PERMISSIONS_NEXT_STEP_SCHEMA = "obelisk.command-chat-response-post-permissions-next-step.v1"
POST_PERMISSIONS_REQUIRED_RUNTIME_INPUTS = (
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
POST_PERMISSIONS_REQUIRED_EVIDENCE = (
    "copied_response_abi_layout_tests",
    "sdk_consumer_tests",
    "isolated_runtime_delivery_evidence",
    "second_source_or_independently_reviewed_response_target_evidence",
    "command_principal_authz_response_bridge_proof",
    "command_response_promotion_certificate",
)
POST_PERMISSIONS_FAIL_CLOSED_GUARDRAILS = (
    "append-only copied POD response ABI with abi_version and struct_size is required before promotion",
    "nonzero plugin_owner_token and an advertised response capability are required before delivery",
    "runtime-owned principal tuple and permissions/admin provenance are required for the same server process epoch",
    "permission allow for the same principal tuple is required before reply, send-chat, broadcast, or moderation delivery",
    "owner-scoped unregister must cancel pending responses and drain in-flight callbacks before unload",
    "malformed UTF-8, oversize messages, unsupported response_kind, and stale principals fail closed",
    "response/send/broadcast readiness aliases cannot count without valid upstream promotion certificates",
    "post-runtime planning metadata and chat/RCON/broadcast/send-source aliases cannot count without valid upstream promotion certificates",
    "source-kind/status metadata aliases for chat, RCON, broadcast, send-chat, replies, or response bridge cannot count without valid upstream promotion certificates",
    "certificate-looking metadata cannot replace path-and-sha-bound promotion certificates in docs/public_sdk_surfaces.json",
    "player-identity promotion certificates must carry current reviewed identity contract and approved runtime binding evidence; readiness/progress aliases cannot replace that certificate evidence",
    "permissions/admin promotion certificates must carry current hash-bound input bindings for its surface hash, upstream player-identity certificate, permissions decisions, query fail-closed contract, and readiness reports",
    "command/principal/authz/response bridge proof must be valid and hash-current; bridge reports, package shape, beta, status, and source aliases cannot replace it",
    "final/terminal, authz-ready, response-path-complete, reply-ready, public/stable SDK, P0 progress, beta/Discord ack, scoped release statement, and package-shape aliases cannot count without exact ordered predecessor certificates and current source hashes",
    "generated certificate reports; reviewed templates; package shape; beta notices stay blocked substitutes",
    "runtime status and status artifacts stay blocked substitutes",
    "plain readiness/progress aliases such as readinessReady, readinessProgress, and progressReady cannot count as evidence or route progress",
)
POST_PERMISSIONS_ABI_EVIDENCE_GUARDRAIL_SCHEMA = (
    "obelisk.command-chat-response-post-permissions-abi-evidence-guardrail.v1"
)
POST_PERMISSIONS_ABI_EVIDENCE_GUARDRAIL = {
    "schema": POST_PERMISSIONS_ABI_EVIDENCE_GUARDRAIL_SCHEMA,
    "surface": SURFACE,
    "planning_only": True,
    "trigger": "after_valid_player_identity_and_permissions_admin_promotion_certificates",
    "requires_valid_upstream_promotion_certificates": [
        PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
        PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA,
    ],
    "required_before_command_response_promotion_certificate": list(POST_PERMISSIONS_REQUIRED_EVIDENCE),
    "required_fail_closed_guardrails": list(POST_PERMISSIONS_FAIL_CLOSED_GUARDRAILS),
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
POST_PERMISSIONS_NEXT_STEP = {
    "schema": POST_PERMISSIONS_NEXT_STEP_SCHEMA,
    "surface": SURFACE,
    "step_id": "define_copied_response_contract_after_permissions",
    "trigger": "after_valid_player_identity_and_permissions_admin_promotion_certificates",
    "blocked_behind_surfaces": BLOCKED_BEHIND_SURFACES,
    "depends_on_certificate_schemas": [
        PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
        PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA,
    ],
    "required_runtime_owned_inputs": list(POST_PERMISSIONS_REQUIRED_RUNTIME_INPUTS),
    "required_evidence": list(POST_PERMISSIONS_REQUIRED_EVIDENCE),
    "required_fail_closed_guardrails": list(POST_PERMISSIONS_FAIL_CLOSED_GUARDRAILS),
    "non_evidence_artifacts": [
        "chat/RCON/broadcast/send-source alias artifacts",
        "diagnostic/candidate artifacts",
        "generated certificate/build-report artifacts",
        "next-action runner/planner artifacts",
        "no-users/passive runtime summaries",
        "passive monitor ticks/output and passive player summaries/snapshots",
        "post-runtime planning metadata",
        "reviewed-template artifacts",
        "notice artifacts",
        "beta-notice artifacts",
        "runtime status reports",
        "package-shape/support-tier artifacts",
        "side-lane evidence/status artifacts",
        "status artifacts",
    ],
    "deterministic": True,
    "metadata_only": True,
    "counts_toward_public_sdk": False,
    "counts_toward_runtime": False,
    "counts_toward_v1_completion": False,
    "public_or_runtime_accounting_allowed": False,
    "public_readiness_ready": False,
    "promotion_ready": False,
    "public_abi_ready": False,
    "runtime_ready": False,
}
POST_IDENTITY_PERMISSIONS_GAP_DIAGNOSTIC_SCHEMA = (
    "obelisk.command-chat-response-post-identity-permissions-gap-diagnostic.v1"
)
POST_IDENTITY_PERMISSIONS_DIAGNOSTIC_MISSING_AFTER_UPSTREAM = (
    "append_only_copied_response_payload_public_contract",
    "owner_token_and_response_capability_contract",
    "copied_response_abi_layout_tests",
    "sdk_consumer_tests",
    "owner_scoped_unregister_and_drain_tests",
    "privacy_redaction_and_targeting_review",
    "rate_limit_and_sanitized_audit_review",
    "isolated_runtime_delivery_evidence",
    "second_source_or_independently_reviewed_response_target_evidence",
    "command_principal_authz_response_bridge_proof",
    "command_response_promotion_certificate",
)
POST_IDENTITY_PERMISSIONS_NON_AUTHORIZING_INPUTS = (
    "approved_runtime_placeholders",
    "planning_layout_second_source_readiness",
    "static_thunk_orientation",
    "copied_response_intent_planning",
    "response_intent_planning",
    "command_principal_authz_response_bridge",
    "post_runtime_planning_metadata",
    "route_samples",
    "package_shape_installs",
)
CANDIDATE_CAPTURE_CLASSIFICATION = "candidate_only_non_counting"
CANDIDATE_CAPTURE_NON_COUNTING_SOURCES = (
    "approved runtime placeholders",
    "beta notice drafts/actions",
    "beta capture plans",
    "beta capture packs",
    "chat/RCON/broadcast/send source alias probes",
    "command candidates",
    "command/chat-response candidate captures",
    "command/chat-response candidate snapshots",
    "debug capture artifacts",
    "multi-surface beta capture packs",
    "multi-surface beta capture plans",
    "package-shape installs",
    "passive logs",
    "passive monitor ticks/output",
    "post-runtime planning metadata",
    "response bridge candidates",
    "response intent planning artifacts",
    "route samples",
    "static thunk orientation records",
)
REQUIRED_PUBLIC_HEADER_FORBIDDEN_TOKENS = frozenset(
    (
        "OBELISK_API_CAPABILITY_COMMANDS",
        "OBELISK_API_CAPABILITY_CHAT_COMMANDS",
        "OBELISK_API_CAPABILITY_COMMAND_CHAT_RESPONSE_PATH",
        "OBELISK_API_CAPABILITY_COMMAND_RESPONSE",
        "OBELISK_API_CAPABILITY_CHAT_RESPONSE",
        "OBELISK_API_CAPABILITY_CHAT_REPLY",
        "OBELISK_API_CAPABILITY_CHAT_REPLIES",
        "OBELISK_API_CAPABILITY_CHAT_ROUTING",
        "OBELISK_API_CAPABILITY_CHAT_LOCAL_ROUTING",
        "OBELISK_API_CAPABILITY_COMMAND_REPLY",
        "OBELISK_API_CAPABILITY_COMMAND_REPLIES",
        "OBELISK_API_CAPABILITY_COMMANDS_REPLIES",
        "OBELISK_API_CAPABILITY_COMMAND_ROUTER",
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
        "ObeliskCommandReply",
        "ObeliskChatReply",
        "ObeliskChatRoute",
        "ObeliskChatRouter",
        "ObeliskSendChat",
        "ObeliskBroadcast",
        "ObeliskNotice",
        "ObeliskModeration",
        "ObeliskRawFStringResponse",
        "ObeliskProcessEventResponseShortcut",
        "ObeliskCallProcessEventResponseShortcut",
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
        "RawFStringCommandResponse",
        "RawFStringChatResponse",
        "RawProcessEventCommandResponse",
        "RawProcessEventChatResponse",
        "ProcessEventCommandResponse",
        "ProcessEventChatResponse",
        "ProcessEventReply",
        "CallProcessEventShortcut",
        "CallProcessEventResponseShortcut",
        "CallProcessEventCommandResponse",
        "CallProcessEventChatResponse",
        "CallProcessEventReply",
    )
)
REQUIRED_PUBLIC_HEADER_FORBIDDEN_PREFIXES = frozenset()
REQUIRED_PUBLIC_HEADER_FORBIDDEN_EXACT_TOKENS = (
    REQUIRED_PUBLIC_HEADER_FORBIDDEN_TOKENS - REQUIRED_PUBLIC_HEADER_FORBIDDEN_PREFIXES
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
        "beta_notice",
        "beta_capture_pack_ready",
        "beta_capture_plan_ready",
        "beta_notice_ready",
        "beta_notice_send_unlock_allowed",
        "beta_notice_sent",
        "beta_plan_ready",
        "candidate_capture_ready",
        "candidate_plan_ready",
        "command_router",
        "command_router_allowed",
        "command_candidate_ready",
        "command_chat_response_candidate_ready",
        "command_response_candidate_ready",
        "command_support_ready",
        "active_player_presence_ready",
        "active_players_ready",
        "debug_capture_ready",
        "diagnostic_drift_ready",
        "drift_ready",
        "observer_enabled",
        "observer_enabled_ready",
        "observer_enablement_ready",
        "player_presence_ready",
        "broadcast_abi_allowed",
        "broadcast_allowed",
        "broadcast_api",
        "broadcast_api_allowed",
        "broadcast_ready",
        "broadcast_notice_api",
        "broadcast_notice_api_allowed",
        "broadcast_notice_ready",
        "chat_api",
        "chat_api_allowed",
        "chat_router",
        "chat_routing",
        "chat_send_api",
        "chat_send_api_allowed",
        "chat_send_ready",
        "command_route_ready",
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
        "command_chat_response_path_complete",
        "command_chat_response_path_completed",
        "command_chat_response_path_ready",
        "command_response_path_complete",
        "command_response_path_completed",
        "commands_unlocked",
        "commands_replies_final_gate_ready",
        "commands_replies_final_ready",
        "commands_replies_ready",
        "full_sdk_claim_allowed",
        "full_sdk_ready",
        "generic_chat_router",
        "generic_chat_routing",
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
        "identity_ready",
        "identity_review_complete",
        "identity_contract_review_complete",
        "permission_admin_contract",
        "permission_header_allowed",
        "permission_ready",
        "permissions_admin_ready",
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
        "player_identity_contract",
        "player_identity_public_contract_ready",
        "player_identity_promotion_certificate_ready",
        "player_identity_ready",
        "principal_identity_ready",
        "principal_ready",
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
        "permissions_admin_route_ready",
        "production_sdk_claim_allowed",
        "production_sdk_ready",
        "promotion_certificate_ready",
        "promotion_ready",
        "public_or_runtime_accounting_allowed",
        "public_abi_allowed",
        "public_abi_ready",
        "public_abi_unlocked",
        "public_bridge_abi_allowed",
        "public_capability_advertised",
        "public_capability_allowed",
        "public_capability_ready",
        "public_broadcast_abi_allowed",
        "public_broadcast_api",
        "public_broadcast_api_allowed",
        "public_broadcast_notice_api",
        "public_broadcast_notice_api_allowed",
        "public_chat_api",
        "public_chat_api_allowed",
        "public_chat_router",
        "public_chat_routing",
        "public_chat_send_api",
        "public_chat_send_api_allowed",
        "public_chat_send_ready",
        "public_command_router",
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
        "public_readiness_ready",
        "progress_ready",
        "readiness_progress",
        "readiness_ready",
        "public_reply_or_send_chat_abi_allowed",
        "public_reply_or_send_chat_abi_unlocked",
        "public_header_allowed",
        "public_header_ready",
        "public_headers_ready",
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
        "public_response_path_allowed",
        "public_reply_abi_ready",
        "public_reply_abi_allowed",
        "public_reply_abi_unlocked",
        "public_reply_api",
        "public_reply_api_unlocked",
        "public_response_abi_allowed",
        "reply_path_ready",
        "reply_ready",
        "release_readiness_ready",
        "response_complete",
        "response_completed",
        "response_header_allowed",
        "generic_chat_routing_public_response_allowed",
        "minimal_chat_message_event_public_response_allowed",
        "raw_process_event_public_response_allowed",
        "static_thunk_orientation_public_response_allowed",
        "static_thunk_orientation_planning_ready",
        "static_thunk_orientation_promotion_ready",
        "static_thunk_orientation_promoted",
        "static_thunk_orientation_ready",
        "commands_replies_shortcut_public_response_allowed",
        "public_response_path_ready",
        "public_sdk",
        "public_sdk_ready",
        "public_send_chat_abi_allowed",
        "public_send_chat_abi_unlocked",
        "public_send_chat_api",
        "public_send_chat_api_unlocked",
        "raw_fstring_response_allowed",
        "raw_fstring_shortcut",
        "raw_fstring_shortcut_allowed",
        "raw_fstring_shortcut_ready",
        "raw_process_event_shortcut",
        "raw_process_event_shortcut_allowed",
        "raw_process_event_shortcut_ready",
        "reply_send_chat_router_claims_allowed",
        "reply_allowed",
        "reply_unlocked",
        "reply_api",
        "reply_api_allowed",
        "reply_api_unlocked",
        "reply_abi_allowed",
        "reply_abi_unlocked",
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
        "route_readiness_progress",
        "route_readiness_ready",
        "router_ready",
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
        "runtime_command_router",
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
        "production_server_authorized",
        "send_chat_allowed",
        "send_chat_api",
        "send_chat_api_allowed",
        "send_chat_api_unlocked",
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
        "response_intent_planning_ready",
        "response_intent_promotion_ready",
        "response_intent_promoted",
        "response_intent_ready",
        "server_operations_authorized",
        "stable_claim_allowed",
        "stable_sdk_claim_allowed",
        "stable_sdk_ready",
        "local_chat_seed_ready",
        "local_route_seed_ready",
        "local_routing_seed_ready",
        "next_action_evidence_ready",
        "next_action_progress_ready",
        "next_action_readiness_ready",
        "next_action_runner_output_ready",
        "next_action_status_ready",
        "notice_artifact_evidence_ready",
        "notice_artifact_progress_ready",
        "notice_artifact_readiness_ready",
        "notice_status_artifact_ready",
        "passive_chat_evidence_ready",
        "passive_evidence_ready",
        "passive_evidence_sufficient",
        "passive_evidence_unlock_allowed",
        "passive_log_ready",
        "passive_logs_ready",
        "passive_monitor_evidence_ready",
        "passive_monitor_output_ready",
        "passive_monitor_progress_ready",
        "passive_monitor_readiness_ready",
        "passive_player_snapshot_ready",
        "passive_player_summary_ready",
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
        "sdk_status_artifact_ready",
        "sdk_status_progress_ready",
        "status_artifact_evidence_ready",
        "status_artifact_progress_ready",
        "status_artifact_readiness_ready",
        "status_report_progress_ready",
        "v1_0_stable_ready",
        "v1_completion_evidence",
        "v1_completion_ready",
    )
)
POSITIVE_ALIAS_CLAIMS = frozenset(
    (
        "activation_preconditions_met",
        "activation_preconditions_ready",
        "beta_notice_ready",
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
        "command_chat_response_candidate_ready",
        "command_response_path_complete",
        "command_response_path_completed",
        "command_response_candidate_ready",
        "commands_replies_final_gate_ready",
        "commands_replies_final_ready",
        "commands_replies_ready",
        "active_player_presence_ready",
        "active_players_ready",
        "debug_capture_ready",
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
        "static_thunk_orientation_planning_ready",
        "static_thunk_orientation_promotion_ready",
        "static_thunk_orientation_promoted",
        "static_thunk_orientation_ready",
        "response_intent_planning_ready",
        "response_intent_promotion_ready",
        "response_intent_promoted",
        "response_intent_ready",
        "route_blocker_bypass",
        "route_blocker_bypassed",
        "dependency_gate_bypass_allowed",
        "dependency_route_bypass_allowed",
        "local_chat_seed_ready",
        "local_routing_seed_ready",
        "next_action_evidence_ready",
        "next_action_progress_ready",
        "next_action_readiness_ready",
        "notice_artifact_evidence_ready",
        "notice_artifact_progress_ready",
        "notice_artifact_readiness_ready",
        "passive_chat_evidence_ready",
        "passive_evidence_ready",
        "passive_evidence_sufficient",
        "passive_log_ready",
        "passive_logs_ready",
        "passive_monitor_evidence_ready",
        "passive_monitor_progress_ready",
        "passive_monitor_readiness_ready",
        "response_bridge_ready",
        "response_complete",
        "response_completed",
        "response_path_complete",
        "response_path_completed",
        "response_path_ready",
        "status_artifact_evidence_ready",
        "status_artifact_progress_ready",
        "status_artifact_readiness_ready",
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
        "chat_seed_ready",
        "command_candidate_ready",
        "command_chat_response_path_complete",
        "command_chat_response_path_completed",
        "command_chat_response_path_ready",
        "command_chat_response_candidate_ready",
        "command_response_path_complete",
        "command_response_path_completed",
        "command_response_candidate_ready",
        "commands_replies_final_gate_ready",
        "commands_replies_final_ready",
        "commands_replies_ready",
        "active_player_presence_ready",
        "active_players_ready",
        "command_principal_authz_response_bridge_ready",
        "copied_response_intent_planning_ready",
        "copied_response_intent_ready",
        "static_thunk_orientation_planning_ready",
        "static_thunk_orientation_promotion_ready",
        "static_thunk_orientation_promoted",
        "static_thunk_orientation_ready",
        "response_intent_planning_ready",
        "response_intent_promotion_ready",
        "response_intent_promoted",
        "response_intent_ready",
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
        "routing_seed_ready",
        "scoped_release_statement_counts_toward_complete_sdk_claim",
        "scoped_release_statement_counts_toward_completion",
        "scoped_release_statement_outcomes_satisfy_completion",
        "scoped_release_statement_ready",
        "scoped_statement_counts_toward_complete_sdk_claim",
        "scoped_statement_counts_toward_completion",
        "scoped_statement_outcomes_satisfy_completion",
        "scoped_statement_ready",
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
)
PROMOTION_CERTIFICATE_METADATA_SCHEMAS = frozenset(
    UPSTREAM_PROMOTION_CERTIFICATE_SCHEMAS
    + (COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA,)
)
PROMOTION_CERTIFICATE_METADATA_KEYS = frozenset(
    (
        "certificate_schema",
        "depends_on_certificate_schema",
        "depends_on_certificate_schemas",
        "player_identity_promotion_certificate",
        "permissions_admin_promotion_certificate",
        "command_response_promotion_certificate",
        "promotion_certificate",
        "promotion_certificate_schema",
        "required_certificate_schema",
        "required_prior_certificate_schema",
        "reviewed_artifact_hash",
        "reviewed_surface_record_sha256",
        "v1_dependency_chain_position",
    )
)
HASH_BOUND_PROMOTION_CERTIFICATE_BINDING_KEYS = frozenset(("path", "sha256"))
HASH_BOUND_ARTIFACT_BINDING_REQUIRED_KEYS = frozenset(("path", "sha256"))
HASH_BOUND_ARTIFACT_BINDING_ALLOWED_KEYS = frozenset(("path", "sha256", "schema"))
ZERO_SHA256 = "0" * 64
PLAYER_IDENTITY_APPROVED_RUNTIME_EVIDENCE_SCHEMA = (
    "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1"
)
PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_SCHEMA = (
    "obelisk.player-identity-public-contract-decision-record.v1"
)
PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_ID = (
    "reviewed_identity_public_contract_decision_record"
)
PLAYER_IDENTITY_PUBLIC_CONTRACT_REVIEW_INPUT = "runtime.lifecycle_evidence"
PUBLIC_HEADER_ROUTE_BLOCKER = "public_header_gate_missing"
PLAYER_IDENTITY_CERTIFICATE_PROMOTION_EVIDENCE_KIND = "player_identity_promotion_certificate"
PLAYER_IDENTITY_DECISION_RUNTIME_BINDING_DIGEST_SCHEMA = (
    "obelisk.player-identity-promotion-certificate-decision-runtime-binding-digest.v1"
)
PLAYER_IDENTITY_DECISION_RUNTIME_BINDING_DIGEST_POLICY = "same-binding-digest-required"
REQUIRED_IDENTITY_PUBLIC_CONTRACT_REVIEW_DECISION_KEYS = (
    "identity_public_contract.reviewed_copied_opaque_principal_pod_abi",
    "identity_public_contract.reviewed_owner_token_lifecycle",
    "identity_public_contract.reviewed_process_local_non_persistent_handles",
    "identity_public_contract.reviewed_no_lookup_persistence_permissions_commands_mutation_return_override",
)
REQUIRED_IDENTITY_CONTRACT_REVIEW_FALSE_KEYS = (
    "promotion_ready",
    "public_contract_allowed",
    "public_header_allowed",
    "public_abi_ready",
    "public_api_ready",
    "public_sdk_ready",
    "runtime_ready",
    "lookup_ready",
    "permissions_ready",
    "commands_ready",
    "v1_completion_evidence",
    "live_ops_authorized",
    "server_operations_authorized",
    "workspace_writes_authorized",
    "runtime_capture_authorized",
    "reads_live_logs",
)
REQUIRED_IDENTITY_CONTRACT_REVIEW_EXACT_FIELDS = {
    "complete_identity_public_contract_reviewed": True,
    "partial_identity_contract": False,
    "hash_current_identity_public_contract_decision_record": True,
    "permissions_admin_unlock_allowed": False,
    "permissions_admin_counting_allowed": False,
    "sdk_or_p0_counting_allowed": False,
}
CERTIFICATE_REVIEWED_TEMPLATE_ONLY_KEYS = frozenset(
    (
        "decision_record_template_only",
        "reviewed_decision_record_template_only",
        "reviewed_identity_contract_template_only",
        "reviewed_identity_public_contract_decision_record_template_only",
        "reviewed_template_only",
        "template_only",
    )
)
PERMISSIONS_ADMIN_PUBLIC_CONTRACT_DECISIONS_SCHEMA = (
    "obelisk.permissions-admin-public-contract-decisions.v1"
)
PERMISSIONS_ADMIN_QUERY_FAILCLOSED_CONTRACT_SCHEMA = (
    "obelisk.permissions-admin-query-failclosed-contract.v1"
)
REQUIRED_PERMISSIONS_CERTIFICATE_INPUT_BINDINGS = frozenset(
    (
        "public_sdk_surfaces",
        "permissions_admin_surface_record_sha256",
        "player_identity_surface_record_sha256",
        "player_identity_promotion_certificate",
        "permissions_admin_public_contract_decisions",
        "permissions_admin_query_failclosed_contract",
        "permissions_admin_public_readiness_report_sha256",
        "query_failclosed_contract_report_sha256",
    )
)
PERMISSIONS_CERTIFICATE_INPUT_ARTIFACT_SCHEMAS = {
    "public_sdk_surfaces": SURFACES_SCHEMA,
    "permissions_admin_public_contract_decisions": PERMISSIONS_ADMIN_PUBLIC_CONTRACT_DECISIONS_SCHEMA,
    "permissions_admin_query_failclosed_contract": PERMISSIONS_ADMIN_QUERY_FAILCLOSED_CONTRACT_SCHEMA,
}
PERMISSIONS_CERTIFICATE_REPORT_HASH_INPUTS = (
    "permissions_admin_public_readiness_report_sha256",
    "query_failclosed_contract_report_sha256",
)
DIRECT_IDENTITY_RUNTIME_EVIDENCE_KEYS = frozenset(
    (
        "accepted_runtime_evidence",
        "approved_runtime_evidence",
        "approved_runtime_principal_lifecycle_evidence",
        "identity_public_contract_decision_record",
        "player_identity_accepted_runtime_evidence",
        "player_identity_approved_runtime_evidence",
        "player_identity_public_contract_decision_record",
        "player_identity_runtime_evidence",
        "runtime_principal_lifecycle_evidence",
    )
)
PLAYER_IDENTITY_CERTIFICATE_ALLOWED_DIRECT_EVIDENCE_KEYS = frozenset(
    (
        "approved_runtime_evidence",
        "identity_public_contract_decision_record",
    )
)
PROMOTION_CERTIFICATE_OVERCLAIM_SCAN_EXEMPT_KEYS = frozenset(
    (
        "chain_position",
        "dependency_chain",
        "input_bindings",
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
        "approved_runtime_evidence_placeholders",
        "approved_runtime_placeholder",
        "approved_runtime_placeholders",
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
        "console",
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
        "route_sample",
        "route_samples",
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
        "approved_runtime_evidence_placeholders",
        "approved_runtime_placeholder",
        "approved_runtime_placeholders",
        "beta_window",
        "beta_window_status",
        "beta_notice",
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
        "command_chat_response_candidate",
        "command_reply_candidate",
        "command_response_candidate",
        "capture_window",
        "capture_window_status",
        "copied_response_intent",
        "response_intent",
        "debug_capture",
        "diagnostic_drift",
        "diagnostic",
        "diagnostic_candidate",
        "active_player_presence",
        "active_players",
        "guarded_beta_notice",
        "installed_sdk_package_shape",
        "local_chat_seed",
        "local_route_seed",
        "local_routing_seed",
        "lifecycle_start_end_evidence",
        "multi_surface_beta_capture_pack",
        "multi_surface_beta_capture_plan",
        "multi_surface_capture_pack",
        "multi_surface_capture_plan",
        "next_action",
        "no_user",
        "no_users",
        "no_users_passive_runtime",
        "notice_artifact",
        "package_shape",
        "package_shape_install",
        "package_shape_installs",
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
        "response_status",
        "response_status_report",
        "route_cleared",
        "route_sample",
        "route_samples",
        "static_thunk_orientation",
        "route_bundle",
        "route_snapshot",
        "runtime_placeholder",
        "runtime_placeholders",
        "runtime_window_status",
        "runtime_status",
        "runtime_principal_lifecycle_start_end_evidence",
        "runtime_principal_start_end_evidence",
        "runtime_window",
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
        "support_tier_package_shape",
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
    r"(?:approved_?)?runtime_?(?:evidence_?)?placeholders?(?:_?(?:artifacts?|reports?|status))?|"
    r"(?:command_?(?:chat_?)?response_?|command_?reply_?)?candidate_?(?:captures?|plans?|logs?|snapshots?)|"
    r"debug_?captures?|"
    r"(?:diagnostic_?)?drift(?:_?(?:checks?|diagnostics?|reports?|status|summar(?:y|ies)))?|"
    r"(?:active_?)?players?_?presence(?:_?(?:reports?|status|summar(?:y|ies)|snapshots?))?|"
    r"active_?players?(?:_?(?:detected|present|presence|reports?|status|summar(?:y|ies)))?|"
    r"(?:player_?)?presence(?:_?(?:active|detected|reports?|status|summar(?:y|ies)))?|"
    r"(?:lifecycle_?|principal_?|player_?principal_?|runtime_?)?observers?(?:_?(?:enable|enabled|enablement|reports?|status))?|"
    r"(?:live_?|server_?|runtime_?)?posture(?:_?(?:checks?|reports?|status|snapshots?))?|"
    r"next_?action(?:_?(?:artifact|artifacts|output|outputs|plan|planner|runner|report|reports|status))?|"
    r"passive_?(?:monitor|monitors|monitor_?tick|monitor_?ticks|monitor_?output|output|outputs|"
    r"player_?summar(?:y|ies)|player_?snapshot|player_?snapshots|snapshot|snapshots|"
    r"(?:chat_?|runtime_?)?logs?)|"
    r"(?:beta_?)?notice_?(?:artifact|artifacts|action|actions|draft|drafts|report|reports|send|sends|status)|"
    r"(?:broadcast_?)?notice_?(?:artifact|artifacts|action|actions|bundle|bundles|package|packages|"
    r"report|reports|snapshot|snapshots|status)|"
    r"(?:runtime_?principal_?lifecycle_?)?start_?end(?:_?only)?(?:_?evidence)?|"
    r"post_?runtime(?:_?(?:metadata|plans?|planning|planning_?metadata|status))?|"
    r"(?:installed_?sdk_?)?package_?shape(?:_?(?:installs?|installation|artifacts?|checks?|reports?|support))?|"
    r"(?:chat_?rcon_?broadcast_?send_?source|send_?source|source)_?aliases?|"
    r"rcon_?(?:command_?)?routes?|rcon_?command_?candidates?|rcon_?route_?candidates?|"
    r"transfer_?b_?accept(?:_?(?:candidates?|routes?))?|transfer_?baccept(?:_?(?:candidates?|routes?))?|"
    r"(?:route|runtime|sdk|public_?sdk|obelisk_?sdk|closure|command_?response|"
    r"command_?chat_?response)_?status(?:_?(?:artifact|artifacts|report|reports|snapshot|snapshots))?|"
    r"(?:command_?(?:chat_?)?response_?)?route_?samples?(?:_?(?:artifacts?|reports?|snapshots?))?|"
    r"response_?intent(?:_?planning)?(?:_?(?:artifacts?|packages?|reports?|status))?|"
    r"static_?thunk_?orientation(?:_?(?:artifacts?|reports?|status))?|"
    r"status_?metadata(?:_?(?:artifact|artifacts|report|reports|snapshot|snapshots))?|"
    r"status_?(?:artifact|artifacts|report|reports|snapshot|snapshots)"
    r")(?:_|$)"
)
NON_EVIDENCE_ARTIFACT_CREDIT_KEY_RE = re.compile(
    r"(?:^|_)(?:"
    r"accepted|approved|complete|completed|counts?(?:_towards?|_toward|_as)?|credit|credited|"
    r"delivered|evidence|progress|progress_?contribution|readiness|ready|result|state|status|"
    r"supported|verified"
    r")(?:_|$)"
)
NON_EVIDENCE_ARTIFACT_TEXT_RE = re.compile(
    r"\b("
    r"(?:multi[-_ ]?surface[-_ ]?)?beta[-_ ]?(?:capture[-_ ]?)?(?:plans?|packs?)|beta[-_ ]?(?:session|tester)[-_ ]?(?:plans?|packs?)|"
    r"(?:approved[-_ ]?)?runtime[-_ ]?(?:evidence[-_ ]?)?placeholders?(?:[-_ ]?(?:artifacts?|reports?|status))?|"
    r"(?:command[-_ ]?(?:chat[-_ ]?)?response[-_ ]?|command[-_ ]?reply[-_ ]?)?candidate[-_ ]?(?:captures?|plans?|logs?|snapshots?)?|"
    r"debug[-_ ]?captures?|"
    r"(?:diagnostic[-_ ]?)?drift(?:[-_ ]?(?:checks?|diagnostics?|reports?|status|summar(?:y|ies)))?|"
    r"(?:active[-_ ]?)?players?[-_ ]?presence(?:[-_ ]?(?:reports?|status|summar(?:y|ies)|snapshots?))?|"
    r"active[-_ ]?players?(?:[-_ ]?(?:detected|present|presence|reports?|status|summar(?:y|ies)))?|"
    r"(?:player[-_ ]?)?presence(?:[-_ ]?(?:active|detected|reports?|status|summar(?:y|ies)))?|"
    r"(?:lifecycle[-_ ]?|principal[-_ ]?|player[-_ ]?principal[-_ ]?|runtime[-_ ]?)?observers?(?:[-_ ]?(?:enable|enabled|enablement|reports?|status))?|"
    r"(?:live[-_ ]?|server[-_ ]?|runtime[-_ ]?)?posture(?:[-_ ]?(?:checks?|reports?|status|snapshots?))?|"
    r"next[-_ ]?action(?:[-_ ]?(?:artifact|artifacts|output|outputs|plan|planner|runner|report|reports|status))?|"
    r"passive[-_ ]?(?:monitor|monitors|monitor[-_ ]?ticks?|monitor[-_ ]?output|output|outputs|"
    r"player[-_ ]?summar(?:y|ies)|player[-_ ]?snapshots?|snapshots?|"
    r"(?:chat[-_ ]?|runtime[-_ ]?)?logs?)|"
    r"(?:beta[-_ ]?)?notice[-_ ]?(?:artifacts?|actions?|drafts?|reports?|sends?|status)|"
    r"(?:broadcast[-_ ]?)?notice[-_ ]?(?:artifacts?|actions?|bundles?|packages?|reports?|snapshots?|status)|"
    r"post[-_ ]?runtime(?:[-_ ]?(?:metadata|plans?|planning|planning[-_ ]?metadata|status))?|"
    r"(?:installed[-_ ]?sdk[-_ ]?)?package[-_ ]?shape(?:[-_ ]?(?:installs?|installation|artifacts?|checks?|reports?|support))?|"
    r"(?:chat[-_ ]?rcon[-_ ]?broadcast[-_ ]?send[-_ ]?source|send[-_ ]?source|source)[-_ ]?aliases?|"
    r"(?:command[-_ ]?(?:chat[-_ ]?)?response[-_ ]?)?route[-_ ]?samples?(?:[-_ ]?(?:artifacts?|reports?|snapshots?))?|"
    r"response[-_ ]?intent(?:[-_ ]?planning)?(?:[-_ ]?(?:artifacts?|packages?|reports?|status))?|"
    r"static[-_ ]?thunk[-_ ]?orientation(?:[-_ ]?(?:artifacts?|reports?|status))?|"
    r"(?:route|runtime|sdk|public[-_ ]?sdk|obelisk[-_ ]?sdk|closure|command[-_ ]?response|"
    r"command[-_ ]?chat[-_ ]?response)[-_ ]?status(?:[-_ ]?(?:artifacts?|reports?|snapshots?))?|"
    r"status[-_ ]?metadata(?:[-_ ]?(?:artifacts?|reports?|snapshots?))?|"
    r"status[-_ ]?(?:artifacts?|reports?|snapshots?)"
    r")\b.{0,80}\b("
    r"accepted|approved|complete|completed|count(?:ed|s|ing)?|credit|credited|delivered|evidence|"
    r"progress|readiness|ready|supported|verified"
    r")\b",
    re.IGNORECASE,
)
NON_EVIDENCE_ARTIFACT_TEXT_REVERSED = re.compile(
    r"\b("
    r"accepted|approved|complete|completed|count(?:ed|s|ing)?|credit|credited|delivered|evidence|"
    r"progress|readiness|ready|supported|verified"
    r")\b.{0,80}\b("
    r"(?:multi[-_ ]?surface[-_ ]?)?beta[-_ ]?(?:capture[-_ ]?)?(?:plans?|packs?)|beta[-_ ]?(?:session|tester)[-_ ]?(?:plans?|packs?)|"
    r"(?:approved[-_ ]?)?runtime[-_ ]?(?:evidence[-_ ]?)?placeholders?(?:[-_ ]?(?:artifacts?|reports?|status))?|"
    r"(?:command[-_ ]?(?:chat[-_ ]?)?response[-_ ]?|command[-_ ]?reply[-_ ]?)?candidate[-_ ]?(?:captures?|plans?|logs?|snapshots?)?|"
    r"debug[-_ ]?captures?|"
    r"(?:diagnostic[-_ ]?)?drift(?:[-_ ]?(?:checks?|diagnostics?|reports?|status|summar(?:y|ies)))?|"
    r"(?:active[-_ ]?)?players?[-_ ]?presence(?:[-_ ]?(?:reports?|status|summar(?:y|ies)|snapshots?))?|"
    r"active[-_ ]?players?(?:[-_ ]?(?:detected|present|presence|reports?|status|summar(?:y|ies)))?|"
    r"(?:player[-_ ]?)?presence(?:[-_ ]?(?:active|detected|reports?|status|summar(?:y|ies)))?|"
    r"(?:lifecycle[-_ ]?|principal[-_ ]?|player[-_ ]?principal[-_ ]?|runtime[-_ ]?)?observers?(?:[-_ ]?(?:enable|enabled|enablement|reports?|status))?|"
    r"(?:live[-_ ]?|server[-_ ]?|runtime[-_ ]?)?posture(?:[-_ ]?(?:checks?|reports?|status|snapshots?))?|"
    r"next[-_ ]?action(?:[-_ ]?(?:artifact|artifacts|output|outputs|plan|planner|runner|report|reports|status))?|"
    r"passive[-_ ]?(?:monitor|monitors|monitor[-_ ]?ticks?|monitor[-_ ]?output|output|outputs|"
    r"player[-_ ]?summar(?:y|ies)|player[-_ ]?snapshots?|snapshots?|"
    r"(?:chat[-_ ]?|runtime[-_ ]?)?logs?)|"
    r"(?:beta[-_ ]?)?notice[-_ ]?(?:artifacts?|actions?|drafts?|reports?|sends?|status)|"
    r"(?:broadcast[-_ ]?)?notice[-_ ]?(?:artifacts?|actions?|bundles?|packages?|reports?|snapshots?|status)|"
    r"post[-_ ]?runtime(?:[-_ ]?(?:metadata|plans?|planning|planning[-_ ]?metadata|status))?|"
    r"(?:installed[-_ ]?sdk[-_ ]?)?package[-_ ]?shape(?:[-_ ]?(?:installs?|installation|artifacts?|checks?|reports?|support))?|"
    r"(?:chat[-_ ]?rcon[-_ ]?broadcast[-_ ]?send[-_ ]?source|send[-_ ]?source|source)[-_ ]?aliases?|"
    r"(?:command[-_ ]?(?:chat[-_ ]?)?response[-_ ]?)?route[-_ ]?samples?(?:[-_ ]?(?:artifacts?|reports?|snapshots?))?|"
    r"response[-_ ]?intent(?:[-_ ]?planning)?(?:[-_ ]?(?:artifacts?|packages?|reports?|status))?|"
    r"static[-_ ]?thunk[-_ ]?orientation(?:[-_ ]?(?:artifacts?|reports?|status))?|"
    r"(?:route|runtime|sdk|public[-_ ]?sdk|obelisk[-_ ]?sdk|closure|command[-_ ]?response|"
    r"command[-_ ]?chat[-_ ]?response)[-_ ]?status(?:[-_ ]?(?:artifacts?|reports?|snapshots?))?|"
    r"status[-_ ]?metadata(?:[-_ ]?(?:artifacts?|reports?|snapshots?))?|"
    r"status[-_ ]?(?:artifacts?|reports?|snapshots?)"
    r")\b",
    re.IGNORECASE,
)
BROAD_P0_ALIAS_SCOPE_RE = re.compile(
    r"(?:^|_)(?:"
    r"admin_authority|authz(?:_?(?:bridge|response|ready))?|authorization|broadcast|chat(?:_send)?|"
    r"(?:approved_?)?runtime_?(?:evidence_?)?placeholders?|"
    r"(?:multi_?surface_?)?beta(?:_capture)?_(?:plans?|packs?)|beta_(?:session|tester)_(?:plans?|packs?)|"
    r"bridge(?:_report)?|"
    r"(?:command_?(?:chat_?)?response_?|command_?reply_?)?candidate_?(?:captures?|plans?|logs?|snapshots?)|"
    r"command(?:_chat)?_response(?:_path)?|command_planning|command_router|command_routing|"
    r"command_principal_authz_response_bridge(?:_report)?|authz_response_bridge(?:_report)?|response_bridge(?:_report)?|"
    r"copied_response_intent(?:_planning)?|"
    r"response_intent(?:_planning)?|"
    r"commands?_repl(?:y|ies)|dependency_chain|"
    r"(?:player_?identity|permissions?_admin|command_?chat_?response(?:_path)?)_?promotion_?certificates?|"
    r"final_?(?:gate|certificate|artifact)(?:_?(?:metadata|reports?|status))?|"
    r"(?:local_)?(?:route|routing|chat)_seed|"
    r"debug_?captures?|"
    r"(?:no_?users?_?)?passive_(?:chat_)?evidence|no_?users?_?passive_?runtime|"
    r"passive_(?:chat_)?evidence|passive_runtime_evidence|passive_(?:chat_|runtime_)?logs?|"
    r"permissions?_admin|permissions?_quer(?:y|ies)|permission(?:_header|_query)?|"
    r"plugin_hub(?:_planning|_support|_package|_package_shape)?|"
    r"(?:installed_?sdk_?)?package_?shape(?:_installs?|_installation)?|"
    r"public_(?:abi|api|header|readiness|reachability|route|runtime|sdk)|"
    r"rcon(?:_command)?(?:_candidate|_route|_status)?|"
    r"reply(?:_(?:abi|api|endpoint|path))?|replies(?:_(?:abi|api|endpoint|path))?|"
    r"response(?:_path)?|"
    r"route(?:_(?:accepted|acceptance|gate|readiness|snapshot|sample))?|"
    r"runtime(?:_(?:capture|delivery|readiness|wiring|work))?|"
    r"send(?:_(?:chat|source|status|route))?|server_operations|stable_(?:claim|sdk)|"
    r"scoped(?:_non_complete)?(?:_v1)?_release_statement(?:_outcomes)?|"
    r"side_?lanes?(?:_?(?:accounting|artifacts?|candidates?|evidence|reports?|status|summar(?:y|ies)))?|"
    r"static_thunk_orientation|"
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
BROAD_P0_ALIAS_EXEMPT_KEYS = frozenset(
    (
        "accepted_for_planning",
        "accepted_runtime_evidence_context",
        "approved_runtime_evidence_present",
        "required_before_public_header",
        "runtime_evidence_ready",
    )
)
NON_AUTHORIZING_ROUTE_ALIAS_CONTEXT_RE = re.compile(
    r"(?:"
    r"(?:accepted_?)?runtime_?simulations?|"
    r"(?:approved_?)?runtime_?(?:evidence_?)?placeholders?|"
    r"(?:multi_?surface_?)?beta_?(?:capture_?)?(?:plans?|packs?)|beta_?(?:session|tester)_?(?:plans?|packs?)|"
    r"(?:command_?(?:chat_?)?response_?|command_?reply_?)?candidate_?(?:captures?|plans?|logs?|snapshots?)|"
    r"debug_?captures?|"
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
    r"(?:installed_?sdk_?|support_?)?package_?shape(?:_?(?:installs?|installation|support))?s?|"
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
    r"|response_?intent(?:_?planning)?(?:_?(?:artifacts?|packages?|reports?|status))?"
    r"|(?:route_?)?bundles?(?:_?(?:packages?|snapshots?|reports?))?"
    r"|route_?snapshots?(?:_?packages?)?"
    r"|(?:command_?(?:chat_?)?response_?)?route_?samples?(?:_?(?:packages?|reports?|snapshots?))?"
    r"|static_?thunk_?orientation(?:_?(?:artifacts?|reports?|status))?"
    r")"
)
NEGATIVE_CONTEXT_TOKENS = (
    "block",
    "claim_requires",
    "exclusion",
    "exclusions",
    "forbid",
    "guidance",
    "negative",
    "non_claim",
    "not_promoted",
    "not_sufficient",
    "not_sufficient_for",
    "promotion_requires",
    "registration_semantics",
    "required_behavior",
    "required_exclusions",
    "required_evidence",
    "stable_release_contract",
    "snapshot_prep_checks",
    "v1_sequence_gate",
    "why_blocked",
)
POSITIVE_SURFACE_RE = re.compile(
    r"\b("
    r"activation[_ -]?preconditions?(?:[_ -]?(?:artifacts?|reports?))?|"
    r"(?:multi[_ -]?surface[_ -]?)?beta[_ -]?(?:capture[_ -]?)?(?:plans?|packs?)|beta[_ -]?(?:session|tester)[_ -]?(?:plans?|packs?)|"
    r"(?:beta[_ -]?)?notice[_ -]?actions?(?:[_ -]?reports?)?|beta[_ -]?notices?|discord[_ -]?notices?|"
    r"(?:broadcast[_ -]?)?notices?(?:[_ -]?(?:actions?|reports?|bundles?|packages?|snapshots?))?|"
    r"(?:approved[_ -]?)?runtime[_ -]?(?:evidence[_ -]?)?placeholders?|"
    r"accepted\s+runtime\s+evidence|admin\s+authority|authz(?:[_ -]?(?:ready|bridge|response))?|authorization|"
    r"final[_ -]?(?:gate|certificate|artifact)(?:[_ -]?(?:metadata|status|reports?))?|"
    r"(?:command[_ -]?principal[_ -]?authz[_ -]?response[_ -]?|authz[_ -]?response[_ -]?|response[_ -]?)?bridge[_ -]?reports?|"
    r"command[_ -]?principal[_ -]?authz[_ -]?response[_ -]?bridge|authz[_ -]?response[_ -]?bridge|response[_ -]?bridge|"
    r"copied[_ -]?response[_ -]?intent(?:[_ -]?planning)?|"
    r"response[_ -]?intent(?:[_ -]?planning)?|"
    r"(?:accepted[_ -]?)?runtime[_ -]?simulations?|"
    r"public[_ -]?contract[_ -]?records?(?:[_ -]?packages?)?|"
    r"support[_ -]?tiers?(?:[_ -]?(?:readiness|reports?))?|"
    r"support[_ -]?tier[_ -]?(?:packages?|package[_ -]?shapes?)|"
    r"(?:installed[_ -]?sdk[_ -]?|support[_ -]?)?package[_ -]?shape(?:[_ -]?(?:installs?|installation|support))?s?|"
    r"side[_ -]?lanes?(?:[_ -]?(?:accounting|artifacts?|candidates?|evidence|reports?|status|summar(?:y|ies)))?|"
    r"(?:command[_ -]?(?:chat[_ -]?)?response[_ -]?|command[_ -]?reply[_ -]?)?candidate[_ -]?(?:captures?|plans?|logs?|snapshots?)|"
    r"debug[_ -]?captures?|"
    r"no[_ -]?users?[_ -]?passive[_ -]?runtime(?:[_ -]?(?:evidence|reports?|status|summar(?:y|ies)))?|"
    r"command[_ -]?planning(?:[_ -]?(?:packages?|package[_ -]?shapes?))?|"
    r"command[_ -]?(?:chat[_ -]?)?response[_ -]?planning(?:[_ -]?packages?)?|"
    r"copied[_ -]?(?:response[_ -]?)?intent(?:[_ -]?planning)?(?:[_ -]?packages?|[_ -]?package[_ -]?shapes?)?|"
    r"(?:route[_ -]?)?bundles?(?:[_ -]?(?:packages?|snapshots?|reports?))?|"
    r"(?:command[_ -]?(?:chat[_ -]?)?response[_ -]?)?route[_ -]?samples?(?:[_ -]?(?:artifacts?|packages?|reports?|snapshots?))?|"
    r"static[_ -]?thunk[_ -]?orientation|"
    r"identity\s+(?:public\s+)?contract|player\s+identity\s+public\s+contract|promotion\s+certificate|"
    r"identity[_ -]?public[_ -]?contract[_ -]?gate[_ -]?missing|"
    r"scoped[_ -]?(?:non[-_ ]complete[_ -]?)?(?:v1[_ -]?)?release[_ -]?statements?|"
    r"(?:local[_ -]?)?(?:route|routing|chat)[_ -]?seeds?|"
    r"passive[_ -]?(?:chat[_ -]?)?evidence|passive[_ -]?runtime[_ -]?evidence|"
    r"passive[_ -]?(?:chat[_ -]?|runtime[_ -]?)?logs?|"
    r"capability\s+bits?|public[_ -]?(?:abi|capabilit(?:y|ies)|contract)|permission\s+headers?|"
    r"permissions?\s+quer(?:y|ies)|"
    r"public[_ -]?reachability|request[_ -]?checks?|request[_ -]?packs?|"
    r"public\s+headers?|runtime\s+(?:delivery|readiness|response\s+path|hooks?)|"
    r"(?:complete|full|production|stable)\s+sdk|public[_ -]?(?:command[_ -]?)?sdk(?:[_ -]?readiness)?|"
    r"release\s+readiness|v1(?:\.0)?\s+stable|v1\s+(?:sdk\s+)?completion|"
    r"repl(?:y|ies)(?:[_ -]?(?:api|abi|endpoint|path|request))?|send[_ -]?(?:chat|source|status|route)(?:[_ -]?(?:api|abi|endpoint|path|request))?|"
    r"broadcast(?:/notices?|[- ]?notices?)?(?:\s+(?:api|abi|endpoint|path|request|scheduler|service))?|"
    r"notices?(?:\s+(?:api|abi|endpoint|path|request|scheduler|service))?|moderation(?:\s+(?:api|abi|endpoint|path|request|authority))?|"
    r"response[_ -]?path|command\s+response\s+path|command\s+rout(?:e|er|ing)|chat\s+rout(?:e|er|ing)|generic\s+chat\s+rout(?:e|er|ing)|router|"
    r"route\s+gate|route[_ -]?snapshots?|route[_ -]?samples?|"
    r"player\s+identity|principal\s+identity|permissions?(?:/admin)?"
    r")\b.{0,80}\b(accepted|advertised|allowed|available|complete|completed|count(?:ed|s|ing)?|delivered|enabled|established|live|met|opened|operational|passed|promoted|public|reachable|ready|reviewed|satisf(?:ied|ies|y)?|sent|supported|unblock(?:s|ed)?|unlock(?:s|ed)?|verified)\b",
    re.IGNORECASE,
)
POSITIVE_SURFACE_REVERSED = re.compile(
r"\b(accepted|advertised|allowed|available|complete|completed|delivered|enabled|established|live|met|opened|operational|passed|promoted|public|reachable|ready|reviewed|sent|supported|unblock(?:s|ed)?|unlock(?:s|ed)?|verified)\b"
    r".{0,80}\b("
    r"activation[_ -]?preconditions?(?:[_ -]?(?:artifacts?|reports?))?|"
    r"(?:multi[_ -]?surface[_ -]?)?beta[_ -]?(?:capture[_ -]?)?(?:plans?|packs?)|beta[_ -]?(?:session|tester)[_ -]?(?:plans?|packs?)|"
    r"(?:beta[_ -]?)?notice[_ -]?actions?(?:[_ -]?reports?)?|beta[_ -]?notices?|discord[_ -]?notices?|"
    r"(?:broadcast[_ -]?)?notices?(?:[_ -]?(?:actions?|reports?|bundles?|packages?|snapshots?))?|"
    r"(?:approved[_ -]?)?runtime[_ -]?(?:evidence[_ -]?)?placeholders?|"
    r"accepted\s+runtime\s+evidence|admin\s+authority|authz(?:[_ -]?(?:ready|bridge|response))?|authorization|"
    r"final[_ -]?(?:gate|certificate|artifact)(?:[_ -]?(?:metadata|status|reports?))?|"
    r"(?:command[_ -]?principal[_ -]?authz[_ -]?response[_ -]?|authz[_ -]?response[_ -]?|response[_ -]?)?bridge[_ -]?reports?|"
    r"command[_ -]?principal[_ -]?authz[_ -]?response[_ -]?bridge|authz[_ -]?response[_ -]?bridge|response[_ -]?bridge|"
    r"copied[_ -]?response[_ -]?intent(?:[_ -]?planning)?|"
    r"response[_ -]?intent(?:[_ -]?planning)?|"
    r"(?:accepted[_ -]?)?runtime[_ -]?simulations?|"
    r"public[_ -]?contract[_ -]?records?(?:[_ -]?packages?)?|"
    r"support[_ -]?tiers?(?:[_ -]?(?:readiness|reports?))?|"
    r"support[_ -]?tier[_ -]?(?:packages?|package[_ -]?shapes?)|"
    r"(?:installed[_ -]?sdk[_ -]?|support[_ -]?)?package[_ -]?shape(?:[_ -]?(?:installs?|installation|support))?s?|"
    r"side[_ -]?lanes?(?:[_ -]?(?:accounting|artifacts?|candidates?|evidence|reports?|status|summar(?:y|ies)))?|"
    r"(?:command[_ -]?(?:chat[_ -]?)?response[_ -]?|command[_ -]?reply[_ -]?)?candidate[_ -]?(?:captures?|plans?|logs?|snapshots?)|"
    r"debug[_ -]?captures?|"
    r"no[_ -]?users?[_ -]?passive[_ -]?runtime(?:[_ -]?(?:evidence|reports?|status|summar(?:y|ies)))?|"
    r"command[_ -]?planning(?:[_ -]?(?:packages?|package[_ -]?shapes?))?|"
    r"command[_ -]?(?:chat[_ -]?)?response[_ -]?planning(?:[_ -]?packages?)?|"
    r"copied[_ -]?(?:response[_ -]?)?intent(?:[_ -]?planning)?(?:[_ -]?packages?|[_ -]?package[_ -]?shapes?)?|"
    r"(?:route[_ -]?)?bundles?(?:[_ -]?(?:packages?|snapshots?|reports?))?|"
    r"(?:command[_ -]?(?:chat[_ -]?)?response[_ -]?)?route[_ -]?samples?(?:[_ -]?(?:artifacts?|packages?|reports?|snapshots?))?|"
    r"static[_ -]?thunk[_ -]?orientation|"
    r"identity\s+(?:public\s+)?contract|player\s+identity\s+public\s+contract|promotion\s+certificate|"
    r"identity[_ -]?public[_ -]?contract[_ -]?gate[_ -]?missing|"
    r"scoped[_ -]?(?:non[-_ ]complete[_ -]?)?(?:v1[_ -]?)?release[_ -]?statements?|"
    r"(?:local[_ -]?)?(?:route|routing|chat)[_ -]?seeds?|"
    r"passive[_ -]?(?:chat[_ -]?)?evidence|passive[_ -]?runtime[_ -]?evidence|"
    r"passive[_ -]?(?:chat[_ -]?|runtime[_ -]?)?logs?|"
    r"capability\s+bits?|public[_ -]?(?:abi|capabilit(?:y|ies)|contract|headers?|sdk)|permission\s+headers?|"
    r"permissions?\s+quer(?:y|ies)|runtime\s+(?:delivery|readiness|response\s+path|hooks?)|"
    r"public[_ -]?reachability|request[_ -]?checks?|request[_ -]?packs?|"
    r"(?:complete|full|production|stable)\s+sdk|release\s+readiness|v1(?:\.0)?\s+stable|"
    r"v1\s+(?:sdk\s+)?completion|repl(?:y|ies)(?:[_ -]?(?:api|abi|endpoint|path|request))?|"
    r"send[_ -]?(?:chat|source|status|route)(?:[_ -]?(?:api|abi|endpoint|path|request))?|"
    r"broadcast(?:/notices?|[- ]?notices?)?(?:\s+(?:api|abi|endpoint|path|request|scheduler|service))?|"
    r"notices?(?:\s+(?:api|abi|endpoint|path|request|scheduler|service))?|"
    r"moderation(?:\s+(?:api|abi|endpoint|path|request|authority))?|"
    r"response[_ -]?path|command\s+response\s+path|command\s+rout(?:e|er|ing)|chat\s+rout(?:e|er|ing)|generic\s+chat\s+rout(?:e|er|ing)|"
    r"router|route\s+gate|route[_ -]?snapshots?|route[_ -]?samples?|player\s+identity|principal\s+identity|permissions?(?:/admin)?"
    r")\b",
    re.IGNORECASE,
)
NEGATED_CLAIM_RE = re.compile(
    r"\b(before|blocked|cannot|does\s+not|fail[s-]?closed|forbidden|future|must|must\s+be|need[s]?|"
    r"never|no|not|only|planning|require[sd]?|until|without)\b",
    re.IGNORECASE,
)
LOCK_BYPASS_NEGATED_CLAIM_RE = re.compile(
    r"\b(before|blocked|cannot|does\s+not|fail[s-]?closed|forbidden|future|must|must\s+be|need[s]?|"
    r"never|no|not|planning|require[sd]?|until|without)\b",
    re.IGNORECASE,
)
ZERO_PROGRESS_CLAIM_RE = re.compile(r"\b0+(?:\.0+)?\s*(?:/|%|percent)\b", re.IGNORECASE)
LOCK_BYPASS_CLAIM_RE = re.compile(
    r"\b("
    r"activation[_ -]?preconditions?(?:[_ -]?(?:artifacts?|reports?))?|"
    r"(?:multi[_ -]?surface[_ -]?)?beta[_ -]?(?:capture[_ -]?)?(?:plans?|packs?)|beta[_ -]?(?:session|tester)[_ -]?(?:plans?|packs?)|"
    r"(?:beta[_ -]?)?notice[_ -]?actions?(?:[_ -]?reports?)?|beta[_ -]?notices?|discord[_ -]?notices?|"
    r"(?:approved[_ -]?)?runtime[_ -]?(?:evidence[_ -]?)?placeholders?|"
    r"accepted[_ -]?runtime[_ -]?evidence[_ -]?(?:only|alone|sufficient)|"
    r"authz(?:[_ -]?(?:ready|bridge|response))?|authorization|"
    r"final[_ -]?(?:gate|certificate|artifact)(?:[_ -]?(?:metadata|status|reports?))?|"
    r"(?:command[_ -]?principal[_ -]?authz[_ -]?response[_ -]?|authz[_ -]?response[_ -]?|response[_ -]?)?bridge[_ -]?reports?|"
    r"command[_ -]?principal[_ -]?authz[_ -]?response[_ -]?bridge|authz[_ -]?response[_ -]?bridge|response[_ -]?bridge|"
    r"copied[_ -]?response[_ -]?intent(?:[_ -]?planning)?|"
    r"response[_ -]?intent(?:[_ -]?planning)?|"
    r"(?:accepted[_ -]?)?runtime[_ -]?simulations?|"
    r"public[_ -]?contract[_ -]?records?(?:[_ -]?packages?)?|"
    r"support[_ -]?tiers?(?:[_ -]?(?:readiness|reports?))?|"
    r"support[_ -]?tier[_ -]?(?:packages?|package[_ -]?shapes?)|"
    r"(?:installed[_ -]?sdk[_ -]?|support[_ -]?)?package[_ -]?shape(?:[_ -]?(?:installs?|installation|support))?s?|"
    r"side[_ -]?lanes?(?:[_ -]?(?:accounting|artifacts?|candidates?|evidence|reports?|status|summar(?:y|ies)))?|"
    r"(?:command[_ -]?(?:chat[_ -]?)?response[_ -]?|command[_ -]?reply[_ -]?)?candidate[_ -]?(?:captures?|plans?|logs?|snapshots?)|"
    r"debug[_ -]?captures?|"
    r"no[_ -]?users?[_ -]?passive[_ -]?runtime(?:[_ -]?(?:evidence|reports?|status|summar(?:y|ies)))?|"
    r"command[_ -]?planning(?:[_ -]?(?:packages?|package[_ -]?shapes?))?|"
    r"command[_ -]?(?:chat[_ -]?)?response[_ -]?planning(?:[_ -]?packages?)?|"
    r"copied[_ -]?(?:response[_ -]?)?intent(?:[_ -]?planning)?(?:[_ -]?packages?|[_ -]?package[_ -]?shapes?)?|"
    r"(?:command[_ -]?(?:chat[_ -]?)?response[_ -]?)?route[_ -]?samples?(?:[_ -]?(?:artifacts?|packages?|reports?|snapshots?))?|"
    r"identity[_ -]?public[_ -]?contract[_ -]?gate[_ -]?missing|"
    r"scoped[_ -]?(?:non[-_ ]complete[_ -]?)?(?:v1[_ -]?)?release[_ -]?statements?|"
    r"(?:local[_ -]?)?(?:route|routing|chat)[_ -]?seeds?|"
    r"passive[_ -]?(?:chat[_ -]?)?evidence|passive[_ -]?runtime[_ -]?evidence|"
    r"passive[_ -]?(?:chat[_ -]?|runtime[_ -]?)?logs?|"
    r"public[_ -]?reachability|request[_ -]?checks?|request[_ -]?packs?|"
    r"response[_ -]?path|"
    r"raw[_ -]?fstring[_ -]?(?:response|shortcuts?)|"
    r"(?:raw[_ -]?)?processevent[_ -]?(?:response|shortcuts?)|"
    r"callprocessevent[_ -]?(?:response|reply|command|shortcuts?)|"
    r"route[_ -]?blocker[_ -]?bypass(?:es|ed)?|route[_ -]?snapshots?|route[_ -]?samples?|"
    r"static[_ -]?thunk[_ -]?orientation|"
    r"(?:dependency|route)[_ -]?gate[_ -]?bypass|"
    r"(?:sdk[/_ -]?)?p0[_ -]?(?:progress|dependency|surface|completion)|"
    r"live[_ -]?(?:ops|operations|server)[_ -]?(?:authorization|approval|authorized|approved)|"
    r"production[_ -]?server[_ -]?authorized"
    r")\b.{0,80}\b("
    r"accepted|allow(?:s|ed)?|available|authori[sz](?:es|ed)?|bypassed|complete|completed|count(?:ed|s|ing)?|delivered|enabled|enough|granted|met|operational|passed|promoted|reachable|ready|satisf(?:ied|ies|y)?|sent|sufficient|supported|unblock(?:s|ed)?|unlock(?:s|ed)?|verified"
    r")\b",
    re.IGNORECASE,
)
LOCK_BYPASS_CLAIM_REVERSED = re.compile(
    r"\b("
    r"accepted|allow(?:s|ed)?|available|authori[sz](?:es|ed)?|bypassed|complete|completed|delivered|enabled|enough|granted|met|operational|passed|promoted|reachable|ready|sent|sufficient|supported|unblock(?:s|ed)?|unlock(?:s|ed)?|verified"
    r")\b.{0,80}\b("
    r"activation[_ -]?preconditions?(?:[_ -]?(?:artifacts?|reports?))?|"
    r"(?:multi[_ -]?surface[_ -]?)?beta[_ -]?(?:capture[_ -]?)?(?:plans?|packs?)|beta[_ -]?(?:session|tester)[_ -]?(?:plans?|packs?)|"
    r"(?:beta[_ -]?)?notice[_ -]?actions?(?:[_ -]?reports?)?|beta[_ -]?notices?|discord[_ -]?notices?|"
    r"(?:broadcast[_ -]?)?notices?(?:[_ -]?(?:actions?|reports?|bundles?|packages?|snapshots?))?|"
    r"(?:approved[_ -]?)?runtime[_ -]?(?:evidence[_ -]?)?placeholders?|"
    r"accepted[_ -]?runtime[_ -]?evidence[_ -]?(?:only|alone|sufficient)|"
    r"authz(?:[_ -]?(?:ready|bridge|response))?|authorization|"
    r"final[_ -]?(?:gate|certificate|artifact)(?:[_ -]?(?:metadata|status|reports?))?|"
    r"(?:command[_ -]?principal[_ -]?authz[_ -]?response[_ -]?|authz[_ -]?response[_ -]?|response[_ -]?)?bridge[_ -]?reports?|"
    r"command[_ -]?principal[_ -]?authz[_ -]?response[_ -]?bridge|authz[_ -]?response[_ -]?bridge|response[_ -]?bridge|"
    r"copied[_ -]?response[_ -]?intent(?:[_ -]?planning)?|"
    r"response[_ -]?intent(?:[_ -]?planning)?|"
    r"(?:accepted[_ -]?)?runtime[_ -]?simulations?|"
    r"public[_ -]?contract[_ -]?records?(?:[_ -]?packages?)?|"
    r"support[_ -]?tiers?(?:[_ -]?(?:readiness|reports?))?|"
    r"support[_ -]?tier[_ -]?(?:packages?|package[_ -]?shapes?)|"
    r"(?:installed[_ -]?sdk[_ -]?|support[_ -]?)?package[_ -]?shape(?:[_ -]?(?:installs?|installation|support))?s?|"
    r"side[_ -]?lanes?(?:[_ -]?(?:accounting|artifacts?|candidates?|evidence|reports?|status|summar(?:y|ies)))?|"
    r"no[_ -]?users?[_ -]?passive[_ -]?runtime(?:[_ -]?(?:evidence|reports?|status|summar(?:y|ies)))?|"
    r"command[_ -]?planning(?:[_ -]?(?:packages?|package[_ -]?shapes?))?|"
    r"command[_ -]?(?:chat[_ -]?)?response[_ -]?planning(?:[_ -]?packages?)?|"
    r"copied[_ -]?(?:response[_ -]?)?intent(?:[_ -]?planning)?(?:[_ -]?packages?|[_ -]?package[_ -]?shapes?)?|"
    r"(?:route[_ -]?)?bundles?(?:[_ -]?(?:packages?|snapshots?|reports?))?|"
    r"(?:command[_ -]?(?:chat[_ -]?)?response[_ -]?)?route[_ -]?samples?(?:[_ -]?(?:artifacts?|packages?|reports?|snapshots?))?|"
    r"identity[_ -]?public[_ -]?contract[_ -]?gate[_ -]?missing|"
    r"scoped[_ -]?(?:non[-_ ]complete[_ -]?)?(?:v1[_ -]?)?release[_ -]?statements?|"
    r"(?:local[_ -]?)?(?:route|routing|chat)[_ -]?seeds?|"
    r"passive[_ -]?(?:chat[_ -]?)?evidence|passive[_ -]?runtime[_ -]?evidence|"
    r"public[_ -]?reachability|request[_ -]?checks?|request[_ -]?packs?|"
    r"response[_ -]?path|"
    r"raw[_ -]?fstring[_ -]?(?:response|shortcuts?)|"
    r"(?:raw[_ -]?)?processevent[_ -]?(?:response|shortcuts?)|"
    r"callprocessevent[_ -]?(?:response|reply|command|shortcuts?)|"
    r"route[_ -]?blocker[_ -]?bypass(?:es|ed)?|route[_ -]?snapshots?|route[_ -]?samples?|"
    r"static[_ -]?thunk[_ -]?orientation|"
    r"(?:dependency|route)[_ -]?gate[_ -]?bypass|"
    r"(?:sdk[/_ -]?)?p0[_ -]?(?:progress|dependency|surface|completion)|"
    r"live[_ -]?(?:ops|operations|server)[_ -]?(?:authorization|approval|authorized|approved)|"
    r"production[_ -]?server[_ -]?authorized"
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
        "beta_capture",
        "beta_capture_pack",
        "beta_capture_plan",
        "beta_plan",
        "beta_session_plan",
        "beta_tester_plan",
        "candidate_capture",
        "candidate_plan",
        "chat_rcon_broadcast_send_source_alias",
        "command_candidate",
        "command_chat_response_candidate",
        "command_reply_candidate",
        "command_response_candidate",
        "copied_response_intent",
        "response_intent",
        "debug_capture",
        "discord_notice",
        "diagnostic_drift",
        "drift",
        "guarded_beta_notice",
        "active_player_presence",
        "active_players",
        "installed_sdk_package_shape",
        "installed_sdk_package_shape_install",
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
        "package_shape_install",
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
        "route_sample",
        "route_samples",
        "route_snapshot",
        "runtime_placeholder",
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
        "static_thunk_orientation",
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
CLAIM_SCOPE_SPLIT_RE = re.compile(
    r"(?<!\d)\.(?!\d)|[;:\n\r]|\s+\b(?:and|but|then|however|unless)\b\s+",
    re.IGNORECASE,
)
NEGATED_CLAIM_SUFFIX_RE = re.compile(
    r"^\s+(?:remains?|stays?|is|are)?\s*(?:blocked|not\s+(?:ready|enabled|authorized|allowed)|"
    r"unauthorized|unsupported|unresolved|.*\b(?:before|only|never|until|requires?)\b)",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Second-source planning layout root.")
    parser.add_argument(
        "--readiness",
        type=Path,
        help=f"Readiness JSON. Defaults to --root/{DEFAULT_READINESS_NAME}.",
    )
    parser.add_argument(
        "--decisions",
        type=Path,
        default=DEFAULT_DECISIONS,
        help="Command/chat response public contract decisions JSON.",
    )
    parser.add_argument(
        "--public-header",
        type=Path,
        default=DEFAULT_PUBLIC_HEADER,
        help="Public Obelisk API header to scan for forbidden response-path symbols.",
    )
    parser.add_argument(
        "--surfaces",
        type=Path,
        default=DEFAULT_SURFACES,
        help="Public SDK surfaces manifest to verify response path remains planning/post-v1.",
    )
    parser.add_argument(
        "--current-route-blocker",
        choices=ALLOWED_ROUTE_BLOCKERS,
        default=CURRENT_ROUTE_BLOCKER,
        help="Parent identity-route blocker to mirror while this surface remains locked.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON. The checker always emits JSON.")
    return parser.parse_args()


def add(blockers: list[dict[str, Any]], reason: str, label: str, **details: Any) -> None:
    item = {"reason": reason, "label": label}
    item.update(details)
    blockers.append(item)


def safe_load_json(path: Path, label: str, blockers: list[dict[str, Any]]) -> dict[str, Any] | None:
    try:
        reject_symlink_component(path, label)
        resolved = reject_protected_input_path(path, label)
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except SystemExit as exc:
        add(blockers, f"{label}_path_rejected", f"${label}", path=str(path), detail=str(exc))
        return None
    except OSError as exc:
        add(blockers, f"{label}_unreadable", f"${label}", path=str(path), detail=str(exc))
        return None
    except json.JSONDecodeError as exc:
        add(blockers, f"{label}_invalid_json", f"${label}", path=str(path), detail=str(exc))
        return None
    if not isinstance(payload, dict):
        add(blockers, f"{label}_not_object", f"${label}", path=str(path))
        return None
    return payload


def safe_resolve_input_path(path: Path, label: str, blockers: list[dict[str, Any]]) -> Path | None:
    try:
        reject_symlink_component(path, label)
        return reject_protected_input_path(path, label)
    except SystemExit as exc:
        add(blockers, f"{label}_path_rejected", f"${label}", path=str(path), detail=str(exc))
        return None


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
    identity = surface_by_id(payload, IDENTITY_SURFACE)
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


def contains_fragment(haystack: str, needle: str) -> bool:
    return needle.casefold() in haystack.casefold()


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


def broad_public_surface_alias_key(key_name: str) -> bool:
    if key_name in BROAD_P0_ALIAS_EXEMPT_KEYS:
        return False
    return (
        key_name in FALSE_ONLY_KEYS
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


def non_evidence_artifact_credit_key(key_name: str) -> bool:
    return (
        NON_EVIDENCE_ARTIFACT_CREDIT_KEY_RE.search(key_name) is not None
        or broad_progress_or_credit_alias_key(key_name)
    )


def non_evidence_artifact_credit_value_is_positive(key_name: str, value: Any) -> bool:
    if broad_progress_or_credit_alias_key(key_name) and progress_claim_value_is_nonzero(value):
        return True
    return contains_positive_claim_value(value)


def source_marker_value_is_non_authorizing(value: Any) -> bool:
    if isinstance(value, str):
        normalized = normalized_key(value)
        return (
            normalized in SOURCE_ALIAS_CONTEXT_VALUES
            or
            non_evidence_artifact_context_key(normalized)
            or NON_AUTHORIZING_ROUTE_ALIAS_CONTEXT_RE.search(normalized) is not None
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
            alias_requires_upstream_certificates(normalized)
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


def negative_context(trail: str) -> bool:
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


def validate_post_permissions_next_step(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    metadata = payload.get("post_permissions_next_step")
    if metadata != POST_PERMISSIONS_NEXT_STEP:
        add(
            blockers,
            "post_permissions_next_step_mismatch",
            "$.decisions.post_permissions_next_step",
            expected=POST_PERMISSIONS_NEXT_STEP,
            value=metadata,
        )


def validate_post_permissions_abi_evidence_guardrail(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    guardrail = payload.get("post_permissions_abi_evidence_guardrail")
    if guardrail != POST_PERMISSIONS_ABI_EVIDENCE_GUARDRAIL:
        add(
            blockers,
            "post_permissions_abi_evidence_guardrail_mismatch",
            "$.decisions.post_permissions_abi_evidence_guardrail",
            expected=POST_PERMISSIONS_ABI_EVIDENCE_GUARDRAIL,
            value=guardrail,
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
            "response_intent_planning",
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


def has_unnegated_positive_surface_claim(text: str) -> bool:
    for clause in CLAIM_SCOPE_SPLIT_RE.split(text):
        for regex in (POSITIVE_SURFACE_RE, POSITIVE_SURFACE_REVERSED):
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


def has_unnegated_non_evidence_artifact_credit_claim(text: str) -> bool:
    for clause in CLAIM_SCOPE_SPLIT_RE.split(text):
        if NEGATED_CLAIM_RE.search(clause) and not negation_is_only_planning_word(
            clause,
            NEGATED_CLAIM_RE,
        ):
            continue
        for regex in (NON_EVIDENCE_ARTIFACT_TEXT_RE, NON_EVIDENCE_ARTIFACT_TEXT_REVERSED):
            if regex.search(clause):
                return True
    return False


def has_unnegated_positive_alias_claim(text: str) -> bool:
    for clause in CLAIM_SCOPE_SPLIT_RE.split(text):
        if NEGATED_CLAIM_RE.search(clause):
            continue
        normalized = normalized_key(clause)
        if "reviewed_identity_public_contract_decision_record" in normalized:
            continue
        if any(alias in normalized for alias in POSITIVE_ALIAS_CLAIMS):
            return True
    return False


def has_unnegated_certificate_gated_alias_claim(text: str) -> bool:
    for clause in CLAIM_SCOPE_SPLIT_RE.split(text):
        if NEGATED_CLAIM_RE.search(clause):
            continue
        normalized = normalized_key(clause)
        if alias_requires_upstream_certificates(normalized) or identity_gate_alias_requires_upstream(normalized):
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
    return any(alias in normalized for alias in CERTIFICATE_GATED_ALIAS_CLAIMS)


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


def direct_identity_runtime_evidence_allowed_context(trail: str, key_name: str) -> bool:
    normalized_trail = normalized_key(trail)
    return (
        "player_identity_promotion_certificate" in normalized_trail
        and "permissions_admin_promotion_certificate" not in normalized_trail
        and key_name in PLAYER_IDENTITY_CERTIFICATE_ALLOWED_DIRECT_EVIDENCE_KEYS
    )


def direct_identity_runtime_evidence_key(key_name: str) -> bool:
    return key_name in DIRECT_IDENTITY_RUNTIME_EVIDENCE_KEYS


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
    if hash_bound_promotion_certificate_binding(value):
        return False
    structural_requirement = promotion_certificate_structural_requirement_key(key_name)
    if not structural_requirement:
        if promotion_certificate_schema_value(value.get("schema")):
            return True
        if promotion_certificate_schema_value(value.get("certificate_schema")):
            return True
        if (
            ("promotion_certificate" in key_name or "promotion_certificate" in "_".join(sorted(normalized_keys)))
            and (
                normalized_keys <= HASH_BOUND_PROMOTION_CERTIFICATE_BINDING_KEYS
                or bool(normalized_keys & HASH_BOUND_PROMOTION_CERTIFICATE_BINDING_KEYS)
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


def c_identifier_exact_re(token: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9_]){re.escape(token)}(?![A-Za-z0-9_])")


def c_identifier_prefix_re(prefix: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9_]){re.escape(prefix)}[A-Za-z0-9_]*")


def collect_surface_overclaims(
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
                (current_artifact_context and non_evidence_artifact_credit_key(claim_key))
                or non_evidence_artifact_context_key(claim_key)
            ) and artifact_claim_value:
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
                if direct_identity_runtime_evidence_allowed_context(trail, key_name):
                    continue
                add(
                    blockers,
                    "direct_identity_or_runtime_evidence_substitute",
                    child_trail,
                    field=str(key),
                    value=child,
                )
                continue
            if direct_identity_runtime_evidence_key(key_name) and not direct_identity_runtime_evidence_allowed_context(
                trail,
                key_name,
            ):
                add(
                    blockers,
                    "direct_identity_or_runtime_evidence_substitute",
                    child_trail,
                    field=str(key),
                    value=child,
                )
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
            collect_surface_overclaims(
                child,
                blockers,
                child_trail,
                artifact_context=child_artifact_context,
            )
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            collect_surface_overclaims(child, blockers, f"{trail}[{index}]", artifact_context=artifact_context)
        return
    if not isinstance(value, str):
        return
    if "non_evidence_artifacts" in normalized_key(trail):
        return
    if is_requirement_metadata_context(trail) and not is_claim_container_context(trail):
        return
    if has_unnegated_public_abi_identity_lookup_handle_claim(value):
        add(blockers, "public_abi_identity_lookup_handle_claim", trail, value=value)
    negative_trail = negative_context(trail) and not is_claim_container_context(trail)
    if (
        not negative_trail
        and promotion_certificate_plain_metadata_looks_authorizing(value, normalized_key(trail))
    ):
        add_promotion_certificate_metadata_blocker(blockers, trail, value=value)
    if not negative_trail and has_unnegated_non_evidence_artifact_credit_claim(value):
        add(blockers, "non_evidence_artifact_credit_overclaim", trail, value=value)
    if negative_trail:
        if has_unnegated_lock_bypass_claim(value):
            add(blockers, "positive_public_surface_claim", trail, value=value)
        if has_unnegated_certificate_gated_alias_claim(value):
            add_upstream_certificate_alias_blocker(blockers, trail, value=value)
        return
    if (
        has_unnegated_positive_surface_claim(value)
        or has_unnegated_positive_alias_claim(value)
        or has_unnegated_lock_bypass_claim(value)
    ):
        add(blockers, "positive_public_surface_claim", trail, value=value)
    if has_unnegated_certificate_gated_alias_claim(value):
        add_upstream_certificate_alias_blocker(blockers, trail, value=value)


def collect_manifest_candidate_artifact_overclaims(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    response_surface: dict[str, Any] | None,
) -> None:
    for key, child in payload.items():
        if key == "surfaces":
            continue
        if non_evidence_artifact_context_key(normalized_key(key)):
            collect_surface_overclaims(
                child,
                blockers,
                f"$.surfaces.{key}",
                artifact_context=True,
            )

    surfaces = payload.get("surfaces")
    if not isinstance(surfaces, list):
        return
    for index, surface in enumerate(surfaces):
        if not isinstance(surface, dict) or surface is response_surface:
            continue
        for key, child in surface.items():
            key_name = normalized_key(key)
            if non_evidence_artifact_context_key(key_name):
                collect_surface_overclaims(
                    child,
                    blockers,
                    f"$.surfaces.surfaces[{index}].{key}",
                    artifact_context=True,
                )


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
    if isinstance(value, str) and accepted_runtime_evidence_text_skips_identity_gate(value):
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


def require_false(mapping: dict[str, Any], key: str, label: str, blockers: list[dict[str, Any]]) -> None:
    if mapping.get(key) is not False:
        add(blockers, f"{key}_not_false", f"{label}.{key}", value=mapping.get(key))


def require_equal(
    mapping: dict[str, Any],
    key: str,
    expected: Any,
    label: str,
    blockers: list[dict[str, Any]],
) -> None:
    if mapping.get(key) != expected:
        add(blockers, f"{key}_mismatch", f"{label}.{key}", expected=expected, value=mapping.get(key))


def validate_gate(
    gate: Any,
    *,
    label: str,
    expected_ready: bool,
    blockers: list[dict[str, Any]],
) -> None:
    if not isinstance(gate, dict):
        add(blockers, f"{label.strip('$.')}_missing", label)
        return
    require_equal(gate, "ready_scope", "planning_only", label, blockers)
    require_equal(gate, "layout_ready", True, label, blockers)
    require_equal(gate, "ready", expected_ready, label, blockers)
    for key in ("promotion_ready", "public_sdk_ready", "runtime_ready"):
        if key in gate:
            require_false(gate, key, label, blockers)


def expected_snapshot_path(root: Path, target: str) -> Path:
    return root / "base-snapshots" / f"{target.rsplit(':', 1)[1]}.snapshot.json"


def validate_readiness_path_bound_to_root(
    *,
    root: Path,
    readiness_path: Path,
    blockers: list[dict[str, Any]],
) -> Path | None:
    resolved_root = safe_resolve_input_path(root, "root", blockers)
    resolved_readiness = safe_resolve_input_path(readiness_path, "readiness", blockers)
    if resolved_root is None or resolved_readiness is None:
        return resolved_root
    expected_readiness = resolved_root / DEFAULT_READINESS_NAME
    if resolved_readiness != expected_readiness:
        add(
            blockers,
            "readiness_path_not_bound_to_root",
            "$.readiness_path",
            expected=str(expected_readiness),
            value=str(resolved_readiness),
            root=str(resolved_root),
        )
    return resolved_root


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def canonical_json_sha256(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def source_artifact_hashes(paths: dict[str, Path]) -> dict[str, str | None]:
    return {key: sha256_file(path) for key, path in paths.items()}


def build_candidate_capture_guardrail(current_route_blocker: str) -> dict[str, Any]:
    return {
        "classification": CANDIDATE_CAPTURE_CLASSIFICATION,
        "capture_scope": "offline_beta_planning_input_only",
        "capture_inputs": sorted(CANDIDATE_CAPTURE_NON_COUNTING_SOURCES),
        "requires_player_principal_runtime_blocker": RUNTIME_EVIDENCE_ROUTE_BLOCKER,
        "current_route_blocker": current_route_blocker,
        "accepted_runtime_evidence": False,
        "approved_runtime_evidence": False,
        "command_support_ready": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
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


def validate_target_detail_path(
    detail: dict[str, Any],
    *,
    label: str,
    root: Path,
    blockers: list[dict[str, Any]],
) -> None:
    target = detail.get("target")
    path_value = detail.get("path")
    if not isinstance(target, str) or not isinstance(path_value, str):
        add(blockers, "target_detail_path_missing", f"{label}.path", target=target, value=path_value)
        return
    expected = expected_snapshot_path(root, target)
    observed = safe_resolve_input_path(Path(path_value), "readiness_target_detail_path", blockers)
    if observed is None:
        return
    if observed != expected:
        add(
            blockers,
            "target_detail_path_root_mismatch",
            f"{label}.path",
            target=target,
            expected=str(expected),
            value=str(observed),
        )
    if not observed.is_file():
        add(blockers, "target_detail_path_not_regular_file", f"{label}.path", target=target, value=str(observed))
        return
    validate_target_snapshot_content(observed, target=target, label=label, blockers=blockers)


def validate_target_snapshot_content(
    path: Path,
    *,
    target: str,
    label: str,
    blockers: list[dict[str, Any]],
) -> None:
    payload = safe_load_json(path, "readiness_target_snapshot", blockers)
    if payload is None:
        return
    if payload.get("status") == "fixture-placeholder":
        add(blockers, "target_snapshot_placeholder", f"{label}.path", target=target, path=str(path))
    if payload.get("schema") != "obelisk.ufunction-chain.snapshot.v1":
        add(
            blockers,
            "target_snapshot_schema_mismatch",
            f"{label}.schema",
            target=target,
            value=payload.get("schema"),
        )
    evidence = payload.get("evidence")
    if not isinstance(evidence, dict):
        add(blockers, "target_snapshot_evidence_missing", f"{label}.evidence", target=target)
    else:
        for key in ("artifact_sha256", "capture_id", "evidence_pack_id", "source", "status"):
            if not isinstance(evidence.get(key), str) or not evidence.get(key):
                add(blockers, "target_snapshot_evidence_field_missing", f"{label}.evidence.{key}", target=target)
    snapshots = payload.get("targets")
    if not isinstance(snapshots, list) or len(snapshots) != 1 or not isinstance(snapshots[0], dict):
        add(blockers, "target_snapshot_targets_invalid", f"{label}.targets", target=target)
        return
    snapshot = snapshots[0]
    target_payload = snapshot.get("target")
    if not isinstance(target_payload, dict) or target_payload.get("name") != target.rsplit(".", 1)[1]:
        add(blockers, "target_snapshot_target_mismatch", f"{label}.targets[0].target", target=target)
    property_chain = snapshot.get("property_chain")
    if not isinstance(property_chain, dict) or not isinstance(property_chain.get("properties"), list):
        add(blockers, "target_snapshot_property_chain_missing", f"{label}.targets[0].property_chain", target=target)


def validate_readiness_provenance(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    root: Path,
    required: bool,
) -> None:
    source_root = payload.get("source_root")
    if not isinstance(source_root, str) or not source_root:
        if required:
            add(blockers, "readiness_provenance_missing", "$.readiness.source_root")
    else:
        observed_root = safe_resolve_input_path(Path(source_root), "readiness_source_root", blockers)
        expected_root = safe_resolve_input_path(root, "root", blockers)
        if observed_root is not None and expected_root is not None and observed_root != expected_root:
            add(
                blockers,
                "readiness_source_root_mismatch",
                "$.readiness.source_root",
                expected=str(expected_root),
                value=str(observed_root),
            )

    producer = payload.get("producer")
    if not isinstance(producer, dict):
        if required:
            add(blockers, "readiness_producer_missing", "$.readiness.producer")
        return
    if producer.get("script") != EXPECTED_READINESS_PRODUCER_SCRIPT:
        add(
            blockers,
            "readiness_producer_script_mismatch",
            "$.readiness.producer.script",
            expected=EXPECTED_READINESS_PRODUCER_SCRIPT,
            value=producer.get("script"),
        )
    if producer.get("output_name") != DEFAULT_READINESS_NAME:
        add(
            blockers,
            "readiness_producer_output_name_mismatch",
            "$.readiness.producer.output_name",
            expected=DEFAULT_READINESS_NAME,
            value=producer.get("output_name"),
        )
    argv = producer.get("argv")
    if not isinstance(argv, list) or not all(isinstance(item, str) for item in argv):
        add(blockers, "readiness_producer_argv_missing", "$.readiness.producer.argv")
        return
    if EXPECTED_READINESS_PRODUCER_SCRIPT not in argv:
        add(blockers, "readiness_producer_argv_script_missing", "$.readiness.producer.argv")
    if "--target-set" not in argv:
        add(blockers, "readiness_producer_argv_target_set_missing", "$.readiness.producer.argv")
    else:
        target_set_index = argv.index("--target-set") + 1
        if target_set_index >= len(argv) or argv[target_set_index] != TARGET_SET:
            add(
                blockers,
                "readiness_producer_argv_target_set_mismatch",
                "$.readiness.producer.argv",
                expected=TARGET_SET,
                value=argv[target_set_index] if target_set_index < len(argv) else None,
            )
    if "--readiness-report" not in argv:
        add(blockers, "readiness_producer_argv_readiness_report_missing", "$.readiness.producer.argv")
    if "--json" not in argv:
        add(blockers, "readiness_producer_argv_json_missing", "$.readiness.producer.argv")
    validate_readiness_producer_root_arg(
        argv,
        "--base-root",
        root,
        "readiness_producer_argv_base_root",
        "$.readiness.producer.argv",
        blockers,
    )
    candidate_root = validate_readiness_producer_root_arg(
        argv,
        "--candidate-root",
        None,
        "readiness_producer_argv_candidate_root",
        "$.readiness.producer.argv",
        blockers,
    )
    expected_root = safe_resolve_input_path(root, "root", blockers)
    if candidate_root is not None and expected_root is not None and candidate_root == expected_root:
        add(
            blockers,
            "readiness_producer_candidate_root_matches_base_root",
            "$.readiness.producer.argv",
            value=str(candidate_root),
        )


def validate_readiness_producer_root_arg(
    argv: list[str],
    option: str,
    expected_root: Path | None,
    reason_prefix: str,
    label: str,
    blockers: list[dict[str, Any]],
) -> Path | None:
    if option not in argv:
        add(blockers, f"{reason_prefix}_missing", label)
        return None
    index = argv.index(option) + 1
    if index >= len(argv):
        add(blockers, f"{reason_prefix}_value_missing", label)
        return None
    observed = safe_resolve_input_path(Path(argv[index]), reason_prefix, blockers)
    if observed is None:
        return None
    if expected_root is not None:
        expected = safe_resolve_input_path(expected_root, "root", blockers)
        if expected is not None and observed != expected:
            add(blockers, f"{reason_prefix}_mismatch", label, expected=str(expected), value=str(observed))
    if not observed.is_dir():
        add(blockers, f"{reason_prefix}_not_directory", label, value=str(observed))
    return observed


def validate_readiness(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    root: Path,
    require_provenance: bool,
) -> None:
    require_equal(payload, "schema", READINESS_SCHEMA, "$.readiness", blockers)
    require_equal(payload, "evidence_scope", "second_source_layout_evidence_only", "$.readiness", blockers)
    require_equal(payload, "gate_mode", "planning_layout_intake", "$.readiness", blockers)
    require_equal(payload, "second_source_status", "compared", "$.readiness", blockers)
    require_equal(payload, "strict_identity_indices", False, "$.readiness", blockers)
    validate_readiness_provenance(payload, blockers, root=root, required=require_provenance)
    if string_set(payload.get("target_sets")) != {TARGET_SET}:
        add(blockers, "target_sets_mismatch", "$.readiness.target_sets", expected=[TARGET_SET], value=payload.get("target_sets"))
    if string_set(payload.get("target_filters")) != TARGETS:
        add(
            blockers,
            "target_filters_mismatch",
            "$.readiness.target_filters",
            expected=sorted(TARGETS),
            value=payload.get("target_filters"),
        )

    totals = payload.get("totals")
    if not isinstance(totals, dict):
        add(blockers, "totals_missing", "$.readiness.totals")
    else:
        for key, expected in (
            ("targets", 3),
            ("comparable", 3),
            ("blocked", 0),
            ("second_source_accepted", 3),
            ("second_source_inconclusive", 0),
            ("second_source_missing", 0),
            ("second_source_rejected", 0),
        ):
            require_equal(totals, key, expected, "$.readiness.totals", blockers)

    modules = payload.get("modules")
    if not isinstance(modules, list) or len(modules) != 1 or not isinstance(modules[0], dict):
        add(blockers, "modules_mismatch", "$.readiness.modules")
    else:
        module = modules[0]
        require_equal(module, "module", "base-snapshots", "$.readiness.modules[0]", blockers)
        require_equal(module, "targets", 3, "$.readiness.modules[0]", blockers)
        require_equal(module, "comparable", 3, "$.readiness.modules[0]", blockers)
        require_equal(module, "blocked", 0, "$.readiness.modules[0]", blockers)
        second_source = module.get("second_source")
        if not isinstance(second_source, dict):
            add(blockers, "module_second_source_missing", "$.readiness.modules[0].second_source")
        else:
            for key, expected in (("accepted", 3), ("inconclusive", 0), ("missing", 0), ("rejected", 0)):
                require_equal(second_source, key, expected, "$.readiness.modules[0].second_source", blockers)
        details = module.get("target_details")
        if not isinstance(details, list) or len(details) != 3:
            add(blockers, "target_details_mismatch", "$.readiness.modules[0].target_details")
        else:
            detail_targets = set()
            for index, detail in enumerate(details):
                label = f"$.readiness.modules[0].target_details[{index}]"
                if not isinstance(detail, dict):
                    add(blockers, "target_detail_invalid", label)
                    continue
                detail_targets.add(detail.get("target"))
                require_equal(detail, "comparable", True, label, blockers)
                require_equal(detail, "second_source_status", "accepted", label, blockers)
                validate_target_detail_path(detail, label=label, root=root, blockers=blockers)
                if detail.get("block_reasons") != []:
                    add(blockers, "target_detail_block_reasons_not_empty", f"{label}.block_reasons")
            if detail_targets != TARGETS:
                add(blockers, "target_detail_targets_mismatch", "$.readiness.modules[0].target_details")

    validate_gate(payload.get("planning_layout_gate"), label="$.readiness.planning_layout_gate", expected_ready=True, blockers=blockers)
    validate_gate(payload.get("promotion_gate"), label="$.readiness.promotion_gate", expected_ready=False, blockers=blockers)
    promotion_gate = payload.get("promotion_gate")
    if isinstance(promotion_gate, dict):
        reasons = {
            item.get("reason")
            for item in promotion_gate.get("blockers", [])
            if isinstance(item, dict) and isinstance(item.get("reason"), str)
        }
        if "planning_layout_intake_not_promotion_gate" not in reasons:
            add(blockers, "promotion_gate_blocker_missing", "$.readiness.promotion_gate.blockers")

    guidance = payload.get("target_set_guidance")
    if not isinstance(guidance, list) or len(guidance) != 1 or not isinstance(guidance[0], dict):
        add(blockers, "target_set_guidance_missing", "$.readiness.target_set_guidance")
    else:
        item = guidance[0]
        label = "$.readiness.target_set_guidance[0]"
        require_equal(item, "target_set", TARGET_SET, label, blockers)
        require_equal(item, "classification", "command_chat_response_route_guidance_only_candidate", label, blockers)
        blockers_seen = string_set(item.get("why_blocked"))
        if not REQUIRED_GUIDANCE_BLOCKERS.issubset(blockers_seen):
            add(
                blockers,
                "target_set_guidance_missing_blockers",
                f"{label}.why_blocked",
                missing=sorted(REQUIRED_GUIDANCE_BLOCKERS - blockers_seen),
            )
        guidance_text = "\n".join(strings(item.get("snapshot_prep_checks")) + strings([item.get("non_claim")]))
        missing_redaction = [
            fragment
            for fragment in REQUIRED_REDACTION_GUIDANCE_FRAGMENTS
            if not contains_fragment(guidance_text, fragment)
        ]
        if missing_redaction:
            add(
                blockers,
                "target_set_guidance_missing_redaction_checks",
                label,
                missing=missing_redaction,
            )

    collect_surface_overclaims(payload, blockers, "$.readiness")


def validate_decisions(payload: dict[str, Any], blockers: list[dict[str, Any]], public_header_path: Path) -> None:
    require_equal(payload, "schema", DECISIONS_SCHEMA, "$.decisions", blockers)
    require_equal(payload, "surface", SURFACE, "$.decisions", blockers)
    require_equal(payload, "status", "blocked", "$.decisions", blockers)
    validate_public_header_declaration(payload, blockers, source="decisions", scanned_path=public_header_path)
    validate_post_permissions_next_step(payload, blockers)
    validate_post_permissions_abi_evidence_guardrail(payload, blockers)
    require_false(payload, "public_header_allowed", "$.decisions", blockers)
    require_false(payload, "legacy_call_process_event_public_response_allowed", "$.decisions", blockers)
    require_false(payload, "minimal_chat_message_event_public_response_allowed", "$.decisions", blockers)
    require_false(payload, "generic_chat_routing_public_response_allowed", "$.decisions", blockers)
    require_false(payload, "raw_process_event_public_response_allowed", "$.decisions", blockers)
    require_false(payload, "static_thunk_orientation_public_response_allowed", "$.decisions", blockers)
    require_false(payload, "commands_replies_shortcut_public_response_allowed", "$.decisions", blockers)
    if payload.get("public_header_symbols_now") != []:
        add(blockers, "public_header_symbols_now_not_empty", "$.decisions.public_header_symbols_now", value=payload.get("public_header_symbols_now"))

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

    forbidden = string_set(payload.get("forbidden_public_contract"))
    if not REQUIRED_FORBIDDEN_PUBLIC_CONTRACT.issubset(forbidden):
        add(
            blockers,
            "forbidden_public_contract_missing_required",
            "$.decisions.forbidden_public_contract",
            missing=sorted(REQUIRED_FORBIDDEN_PUBLIC_CONTRACT - forbidden),
        )

    requirements = payload.get("required_before_public_header")
    if not isinstance(requirements, list):
        add(blockers, "required_before_public_header_not_list", "$.decisions.required_before_public_header")
        collect_surface_overclaims(payload, blockers, "$.decisions")
        return

    by_id: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(requirements):
        label = f"$.decisions.required_before_public_header[{index}]"
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            add(blockers, "required_before_public_header_item_invalid", label)
            continue
        by_id[item["id"]] = item
        if item.get("status") != "unresolved":
            add(blockers, "required_before_public_header_item_not_unresolved", f"{label}.status", id=item["id"], value=item.get("status"))

    if set(by_id) != REQUIRED_DECISION_IDS:
        add(
            blockers,
            "required_before_public_header_ids_mismatch",
            "$.decisions.required_before_public_header",
            missing=sorted(REQUIRED_DECISION_IDS - set(by_id)),
            unexpected=sorted(set(by_id) - REQUIRED_DECISION_IDS),
        )

    identity = by_id.get("dependency.promoted_player_identity", {})
    behaviors = string_set(identity.get("required_behavior"))
    for required in REQUIRED_IDENTITY_DEPENDENCY_BEHAVIORS:
        if required not in behaviors:
            add(blockers, "identity_dependency_behavior_missing", "$.decisions.required_before_public_header", behavior=required)

    permissions = by_id.get("dependency.promoted_permissions_admin", {})
    permission_behaviors = string_set(permissions.get("required_behavior"))
    for required in REQUIRED_PERMISSIONS_DEPENDENCY_BEHAVIORS:
        if required not in permission_behaviors:
            add(blockers, "permissions_dependency_behavior_missing", "$.decisions.required_before_public_header", behavior=required)

    capability = by_id.get("abi.capability_and_owner_token", {})
    capability_behaviors = string_set(capability.get("required_behavior"))
    for required in (
        "captured post-init debug CallProcessEvent tables do not authorize response delivery",
        "minimal ChatMessageEvent registration does not authorize response delivery",
        "generic chat routing does not authorize response delivery",
        "raw ProcessEvent callbacks do not authorize response delivery",
        "static thunk orientation does not authorize response delivery",
    ):
        if required not in capability_behaviors:
            add(blockers, "capability_behavior_missing", "$.decisions.required_before_public_header", behavior=required)

    lifecycle = by_id.get("lifecycle.owner_scoped_unregister_and_drain", {})
    missing_lifecycle = REQUIRED_LIFECYCLE_DECISION_BEHAVIORS - string_set(lifecycle.get("required_behavior"))
    if missing_lifecycle:
        add(
            blockers,
            "lifecycle_owner_unregister_behavior_missing",
            "$.decisions.required_before_public_header",
            missing=sorted(missing_lifecycle),
        )

    abuse = by_id.get("abuse.rate_limit_and_audit", {})
    missing_abuse = REQUIRED_ABUSE_DECISION_BEHAVIORS - string_set(abuse.get("required_behavior"))
    if missing_abuse:
        add(
            blockers,
            "abuse_rate_limit_audit_behavior_missing",
            "$.decisions.required_before_public_header",
            missing=sorted(missing_abuse),
        )

    separation = by_id.get("separation.no_commands_router_or_moderation", {})
    sequence_gate = string_set(separation.get("v1_sequence_gate"))
    for required in (
        "minimal ChatMessageEvent remains passive input and cannot route replies/send-chat/broadcast/moderation",
        "generic chat routing cannot bypass promoted identity and permissions/admin",
        "chat intake is observation only and cannot become identity, permission, command authority, moderation authority, targeting, or roadmap priority",
        "raw ProcessEvent, legacy CallProcessEvent, and static thunk orientation cannot bypass identity and permissions/admin",
        "activation preconditions, beta notice sends, public reachability, request checks, and identity_public_contract_gate_missing aliases cannot bypass promoted identity and permissions/admin",
    ):
        if required not in sequence_gate:
            add(blockers, "separation_sequence_gate_missing", "$.decisions.required_before_public_header", gate=required)
    exclusions = string_set(separation.get("required_exclusions"))
    for required in (
        "command router",
        "command registration API",
        "commands/replies shortcut before identity and permissions/admin",
        "public response path through ChatMessageEvent",
        "public response path through generic chat routing",
        "public response path through raw ProcessEvent",
        "public response path through static thunk orientation",
        "reply/send-chat/broadcast/moderation through legacy CallProcessEvent",
        "reply/send-chat/router claims before promotion",
        "moderation API",
    ):
        if required not in exclusions:
            add(blockers, "separation_exclusion_missing", "$.decisions.required_before_public_header", exclusion=required)

    privacy = by_id.get("privacy.redaction_and_targeting", {})
    privacy_behaviors = string_set(privacy.get("required_behavior"))
    missing_privacy = REQUIRED_PRIVACY_DECISION_BEHAVIORS - privacy_behaviors
    if missing_privacy:
        add(
            blockers,
            "privacy_redaction_behavior_missing",
            "$.decisions.required_before_public_header",
            missing=sorted(missing_privacy),
        )

    evidence = by_id.get("evidence.response_target_set_snapshot_second_source", {})
    if string_set(evidence.get("required_targets")) != TARGETS:
        add(blockers, "decision_response_targets_mismatch", "$.decisions.required_before_public_header", value=evidence.get("required_targets"))
    response_not_sufficient = string_set(evidence.get("not_sufficient"))
    missing_response_not_sufficient = REQUIRED_RESPONSE_TARGET_NOT_SUFFICIENT - response_not_sufficient
    if missing_response_not_sufficient:
        add(
            blockers,
            "response_target_not_sufficient_missing",
            "$.decisions.required_before_public_header",
            missing=sorted(missing_response_not_sufficient),
        )

    coverage = by_id.get("evidence.layout_runtime_sdk_coverage", {})
    not_sufficient = string_set(coverage.get("not_sufficient"))
    missing_not_sufficient = REQUIRED_LAYOUT_RUNTIME_SDK_NOT_SUFFICIENT - not_sufficient
    if missing_not_sufficient:
        add(
            blockers,
            "evidence_not_sufficient_missing_required",
            "$.decisions.required_before_public_header",
            missing=sorted(missing_not_sufficient),
        )

    collect_surface_overclaims(payload, blockers, "$.decisions")


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
        text = without_native_prototype_symbols(
            strip_c_comments(resolved.read_text(encoding="utf-8")), header_only=True
        )
    except SystemExit as exc:
        add(blockers, "public_header_path_rejected", "$.public_header", path=str(path), detail=str(exc))
        return
    except OSError as exc:
        add(blockers, "public_header_unreadable", "$.public_header", path=str(path), detail=str(exc))
        return
    present = sorted(
        token
        for token in REQUIRED_PUBLIC_HEADER_FORBIDDEN_EXACT_TOKENS
        if c_identifier_exact_re(token).search(text)
    )
    present.extend(
        sorted(
            prefix
            for prefix in REQUIRED_PUBLIC_HEADER_FORBIDDEN_PREFIXES
            if c_identifier_prefix_re(prefix).search(text)
        )
    )
    if present:
        add(
            blockers,
            "public_header_forbidden_symbols_present",
            "$.public_header",
            path=str(path),
            symbols=present,
        )


PROMOTION_CERTIFICATE_SPECS = {
    IDENTITY_SURFACE: {
        "certificate_key": "player_identity_promotion_certificate",
        "schema": PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
        "chain_position": 1,
        "required_by_surface": PERMISSIONS_SURFACE,
        "required_by_chain_position": 2,
        "label": "player_identity",
    },
    PERMISSIONS_SURFACE: {
        "certificate_key": "permissions_admin_promotion_certificate",
        "schema": PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA,
        "chain_position": 2,
        "required_by_surface": SURFACE,
        "required_by_chain_position": 3,
        "label": "permissions_admin",
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
    payload = safe_load_json(resolved, certificate_key, blockers)
    return payload


def sha256_hex(value: Any, *, allow_zero: bool = False) -> bool:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-fA-F]{64}", value) is None:
        return False
    return allow_zero or value.lower() != ZERO_SHA256


def validate_hash_bound_artifact_binding_current(
    binding: Any,
    *,
    reason_prefix: str,
    label: str,
    blockers: list[dict[str, Any]],
    expected_schema: str | None = None,
) -> bool:
    if not isinstance(binding, dict):
        add(blockers, f"{reason_prefix}_binding_missing", label, value=binding)
        return False

    normalized_keys = {normalized_key(key) for key in binding}
    if (
        not HASH_BOUND_ARTIFACT_BINDING_REQUIRED_KEYS.issubset(normalized_keys)
        or not normalized_keys.issubset(HASH_BOUND_ARTIFACT_BINDING_ALLOWED_KEYS)
    ):
        add(
            blockers,
            f"{reason_prefix}_binding_keys_mismatch",
            label,
            expected=sorted(HASH_BOUND_ARTIFACT_BINDING_ALLOWED_KEYS),
            required=sorted(HASH_BOUND_ARTIFACT_BINDING_REQUIRED_KEYS),
            value=sorted(binding),
        )
        return False

    if expected_schema is not None and binding.get("schema") != expected_schema:
        add(
            blockers,
            f"{reason_prefix}_schema_mismatch",
            f"{label}.schema",
            expected=expected_schema,
            value=binding.get("schema"),
        )
        return False

    relative = repo_relative_path(binding.get("path"))
    if relative is None:
        add(blockers, f"{reason_prefix}_path_invalid", f"{label}.path", value=binding.get("path"))
        return False

    path = REPO_ROOT / relative
    try:
        reject_symlink_component(path, reason_prefix)
        resolved = reject_protected_input_path(path, reason_prefix)
    except SystemExit as exc:
        add(
            blockers,
            f"{reason_prefix}_path_rejected",
            f"{label}.path",
            value=str(relative),
            detail=str(exc),
        )
        return False

    expected_sha256 = binding.get("sha256")
    if not sha256_hex(expected_sha256):
        add(blockers, f"{reason_prefix}_sha256_invalid", f"{label}.sha256", value=expected_sha256)
        return False

    actual_sha256 = sha256_file(resolved)
    if actual_sha256 != expected_sha256.lower():
        add(
            blockers,
            f"{reason_prefix}_sha256_mismatch",
            f"{label}.sha256",
            expected=actual_sha256,
            value=expected_sha256.lower(),
            path=str(relative),
        )
        return False

    return True


def validate_identity_certificate_current_evidence(
    certificate_evidence: dict[str, Any],
    *,
    expected_surface_hash: str,
    label: str,
    blockers: list[dict[str, Any]],
) -> bool:
    valid = True

    if certificate_evidence.get("promotion_evidence_kind") != PLAYER_IDENTITY_CERTIFICATE_PROMOTION_EVIDENCE_KIND:
        valid = False
        add(
            blockers,
            "player_identity_promotion_certificate_promotion_evidence_kind_mismatch",
            f"{label}.evidence.promotion_evidence_kind",
            expected=PLAYER_IDENTITY_CERTIFICATE_PROMOTION_EVIDENCE_KIND,
            value=certificate_evidence.get("promotion_evidence_kind"),
        )

    runtime_summary = certificate_evidence.get("approved_runtime_evidence")
    expected_runtime_summary = {
        "schema": PLAYER_IDENTITY_APPROVED_RUNTIME_EVIDENCE_SCHEMA,
        "result": "approved runtime principal lifecycle evidence",
        "next_blocker": IDENTITY_CONTRACT_ROUTE_BLOCKER,
    }
    if runtime_summary != expected_runtime_summary:
        valid = False
        add(
            blockers,
            "player_identity_promotion_certificate_approved_runtime_evidence_mismatch",
            f"{label}.evidence.approved_runtime_evidence",
            expected=expected_runtime_summary,
            value=runtime_summary,
        )

    review = certificate_evidence.get("identity_public_contract_decision_record")
    if not isinstance(review, dict):
        valid = False
        add(
            blockers,
            "player_identity_promotion_certificate_identity_contract_review_missing",
            f"{label}.evidence.identity_public_contract_decision_record",
        )
    else:
        expected_review_fields = {
            "schema": PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_SCHEMA,
            "artifact_id": PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_ID,
            "surface": IDENTITY_SURFACE,
            "active_after_resolved_input": PLAYER_IDENTITY_PUBLIC_CONTRACT_REVIEW_INPUT,
            "review_status": "reviewed",
            "accepted_for_contract_review": True,
            "next_blocker": PUBLIC_HEADER_ROUTE_BLOCKER,
            "reviewed_surface_record_sha256": expected_surface_hash,
        }
        for key, expected in expected_review_fields.items():
            if review.get(key) != expected:
                valid = False
                add(
                    blockers,
                    "player_identity_promotion_certificate_identity_contract_review_mismatch",
                    f"{label}.evidence.identity_public_contract_decision_record.{key}",
                    expected=expected,
                    value=review.get(key),
                )
        if review.get("resolved_decision_keys") != list(REQUIRED_IDENTITY_PUBLIC_CONTRACT_REVIEW_DECISION_KEYS):
            valid = False
            add(
                blockers,
                "player_identity_promotion_certificate_identity_contract_review_keys_mismatch",
                f"{label}.evidence.identity_public_contract_decision_record.resolved_decision_keys",
                expected=list(REQUIRED_IDENTITY_PUBLIC_CONTRACT_REVIEW_DECISION_KEYS),
                value=review.get("resolved_decision_keys"),
            )
        for key in REQUIRED_IDENTITY_CONTRACT_REVIEW_FALSE_KEYS:
            if review.get(key) is not False:
                valid = False
                add(
                    blockers,
                    "player_identity_promotion_certificate_identity_contract_review_false_flag_not_false",
                    f"{label}.evidence.identity_public_contract_decision_record.{key}",
                    value=review.get(key),
                )
        for key, expected in REQUIRED_IDENTITY_CONTRACT_REVIEW_EXACT_FIELDS.items():
            if review.get(key) != expected:
                valid = False
                add(
                    blockers,
                    "player_identity_promotion_certificate_identity_contract_review_completeness_mismatch",
                    f"{label}.evidence.identity_public_contract_decision_record.{key}",
                    expected=expected,
                    value=review.get(key),
                )
        for key in CERTIFICATE_REVIEWED_TEMPLATE_ONLY_KEYS:
            if review.get(key) is True:
                valid = False
                add(
                    blockers,
                    "player_identity_promotion_certificate_reviewed_template_only",
                    f"{label}.evidence.identity_public_contract_decision_record.{key}",
                    value=review.get(key),
                )

        expected_review_sha256 = canonical_json_sha256(review)
        if certificate_evidence.get("identity_public_contract_decision_record_sha256") != expected_review_sha256:
            valid = False
            add(
                blockers,
                "player_identity_promotion_certificate_identity_contract_review_record_hash_mismatch",
                f"{label}.evidence.identity_public_contract_decision_record_sha256",
                expected=expected_review_sha256,
                value=certificate_evidence.get("identity_public_contract_decision_record_sha256"),
            )

    runtime_binding = certificate_evidence.get("identity_public_contract_decision_record_runtime_binding")
    if not isinstance(runtime_binding, dict):
        valid = False
        add(
            blockers,
            "player_identity_promotion_certificate_identity_contract_runtime_binding_missing",
            f"{label}.evidence.identity_public_contract_decision_record_runtime_binding",
        )
    else:
        expected_runtime_binding_fields = {
            "schema": PLAYER_IDENTITY_DECISION_RUNTIME_BINDING_DIGEST_SCHEMA,
            "policy": PLAYER_IDENTITY_DECISION_RUNTIME_BINDING_DIGEST_POLICY,
        }
        for key, expected in expected_runtime_binding_fields.items():
            if runtime_binding.get(key) != expected:
                valid = False
                add(
                    blockers,
                    "player_identity_promotion_certificate_identity_contract_runtime_binding_mismatch",
                    f"{label}.evidence.identity_public_contract_decision_record_runtime_binding.{key}",
                    expected=expected,
                    value=runtime_binding.get(key),
                )
        decision_digest = runtime_binding.get(
            "decision_record_approved_runtime_evidence_binding_sha256"
        )
        runtime_digest = runtime_binding.get("approved_runtime_evidence_binding_sha256")
        if (
            not sha256_hex(decision_digest)
            or not sha256_hex(runtime_digest)
            or decision_digest.lower() != runtime_digest.lower()
        ):
            valid = False
            add(
                blockers,
                "player_identity_promotion_certificate_identity_contract_runtime_binding_digest_mismatch",
                f"{label}.evidence.identity_public_contract_decision_record_runtime_binding",
                decision_record_approved_runtime_evidence_binding_sha256=decision_digest,
                approved_runtime_evidence_binding_sha256=runtime_digest,
            )

    return valid


def validate_permissions_certificate_current_input_bindings(
    certificate_evidence: dict[str, Any],
    *,
    input_bindings: Any,
    expected_surface_hash: str,
    surfaces: dict[str, Any] | None,
    label: str,
    blockers: list[dict[str, Any]],
) -> bool:
    valid = True
    if not isinstance(input_bindings, dict):
        add(
            blockers,
            "permissions_admin_promotion_certificate_input_bindings_missing",
            f"{label}.input_bindings",
        )
        identity = surface_by_id(surfaces, IDENTITY_SURFACE)
        identity_evidence = identity.get("evidence") if isinstance(identity, dict) else None
        current_identity_binding = (
            identity_evidence.get("player_identity_promotion_certificate")
            if isinstance(identity_evidence, dict)
            else None
        )
        add(
            blockers,
            "permissions_admin_promotion_certificate_current_player_identity_certificate_binding_missing_or_mismatch",
            f"{label}.input_bindings.player_identity_promotion_certificate",
            expected=current_identity_binding,
            value=None,
        )
        return False

    input_binding_keys = set(input_bindings)
    if input_binding_keys != REQUIRED_PERMISSIONS_CERTIFICATE_INPUT_BINDINGS:
        valid = False
        add(
            blockers,
            "permissions_admin_promotion_certificate_input_bindings_keys_mismatch",
            f"{label}.input_bindings",
            expected=sorted(REQUIRED_PERMISSIONS_CERTIFICATE_INPUT_BINDINGS),
            value=sorted(input_binding_keys),
        )

    for key, schema in PERMISSIONS_CERTIFICATE_INPUT_ARTIFACT_SCHEMAS.items():
        if not validate_hash_bound_artifact_binding_current(
            input_bindings.get(key),
            reason_prefix=f"permissions_admin_promotion_certificate_{key}",
            label=f"{label}.input_bindings.{key}",
            blockers=blockers,
            expected_schema=schema,
        ):
            valid = False

    if input_bindings.get("permissions_admin_surface_record_sha256") != expected_surface_hash:
        valid = False
        add(
            blockers,
            "permissions_admin_promotion_certificate_permissions_surface_record_sha256_mismatch",
            f"{label}.input_bindings.permissions_admin_surface_record_sha256",
            expected=expected_surface_hash,
            value=input_bindings.get("permissions_admin_surface_record_sha256"),
        )

    identity = surface_by_id(surfaces, IDENTITY_SURFACE)
    identity_evidence = identity.get("evidence") if isinstance(identity, dict) else None
    current_identity_binding = (
        identity_evidence.get("player_identity_promotion_certificate")
        if isinstance(identity_evidence, dict)
        else None
    )
    declared_identity_binding = input_bindings.get("player_identity_promotion_certificate")
    if not hash_bound_bindings_match(declared_identity_binding, current_identity_binding):
        valid = False
        add(
            blockers,
            "permissions_admin_promotion_certificate_current_player_identity_certificate_binding_missing_or_mismatch",
            f"{label}.input_bindings.player_identity_promotion_certificate",
            expected=current_identity_binding,
            value=declared_identity_binding,
        )

    expected_identity_hash = (
        surface_record_sha256(identity, "player_identity_promotion_certificate")
        if isinstance(identity, dict)
        else None
    )
    if input_bindings.get("player_identity_surface_record_sha256") != expected_identity_hash:
        valid = False
        add(
            blockers,
            "permissions_admin_promotion_certificate_player_identity_surface_record_sha256_mismatch",
            f"{label}.input_bindings.player_identity_surface_record_sha256",
            expected=expected_identity_hash,
            value=input_bindings.get("player_identity_surface_record_sha256"),
        )

    for key in PERMISSIONS_CERTIFICATE_REPORT_HASH_INPUTS:
        if not sha256_hex(input_bindings.get(key)):
            valid = False
            add(
                blockers,
                f"permissions_admin_promotion_certificate_{key}_invalid",
                f"{label}.input_bindings.{key}",
                value=input_bindings.get(key),
            )

    expected_input_binding_sha256 = canonical_json_sha256(input_bindings)
    if certificate_evidence.get("input_binding_sha256") != expected_input_binding_sha256:
        valid = False
        add(
            blockers,
            "permissions_admin_promotion_certificate_input_binding_sha256_mismatch",
            f"{label}.evidence.input_binding_sha256",
            expected=expected_input_binding_sha256,
            value=certificate_evidence.get("input_binding_sha256"),
        )

    return valid


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
    collect_surface_overclaims(scan_payload, scan_blockers, label)
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
    spec = PROMOTION_CERTIFICATE_SPECS[surface_id]
    if not isinstance(surface, dict) or surface.get("status") != "promoted":
        return False

    local_blockers: list[dict[str, Any]] = []
    target_blockers = blockers if blockers is not None else local_blockers
    label = f"$.surfaces.{spec['label']}.evidence.{spec['certificate_key']}"
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
        "v1_dependency_chain": DEPENDENCY_CHAIN,
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
    if surface_id == IDENTITY_SURFACE:
        if not validate_identity_certificate_current_evidence(
            certificate_evidence,
            expected_surface_hash=expected_surface_hash,
            label=label,
            blockers=target_blockers,
        ):
            valid = False
    if surface_id == PERMISSIONS_SURFACE:
        if not validate_permissions_certificate_current_input_bindings(
            certificate_evidence,
            input_bindings=certificate.get("input_bindings"),
            expected_surface_hash=expected_surface_hash,
            surfaces=surfaces,
            label=label,
            blockers=target_blockers,
        ):
            valid = False
    return valid


def promoted_manifest_entry_has_certificate(
    promoted: set[str],
    surface: dict[str, Any] | None,
    surface_id: str,
    blockers: list[dict[str, Any]],
    *,
    surfaces: dict[str, Any] | None,
    reason: str,
) -> bool:
    if surface_id not in promoted:
        return False
    if surface_has_valid_promotion_certificate(surface, surface_id, surfaces=surfaces):
        return True
    add(blockers, reason, "$.surfaces.promoted_surfaces")
    return False


def validate_upstream_promotion_certificate_metadata(
    surface: dict[str, Any] | None,
    surface_id: str,
    certificate_valid: bool,
    blockers: list[dict[str, Any]],
) -> None:
    if not isinstance(surface, dict) or certificate_valid:
        return
    spec = PROMOTION_CERTIFICATE_SPECS[surface_id]
    evidence = surface.get("evidence")
    if not isinstance(evidence, dict) or spec["certificate_key"] not in evidence:
        return
    add_promotion_certificate_metadata_blocker(
        blockers,
        f"$.surfaces.{spec['label']}.evidence.{spec['certificate_key']}",
        value=evidence.get(spec["certificate_key"]),
    )


def validate_response_terminal_certificate_metadata(
    response: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    evidence = response.get("evidence")
    if not isinstance(evidence, dict) or "command_response_promotion_certificate" not in evidence:
        return

    label = "$.surfaces.command_chat_response_path.evidence.command_response_promotion_certificate"
    add(
        blockers,
        "command_response_promotion_certificate_terminal_artifact_non_counting",
        label,
        terminal_artifact_shortcuts_count=False,
        counts_toward_public_sdk=False,
        counts_toward_runtime=False,
        counts_toward_v1_completion=False,
        public_or_runtime_accounting_allowed=False,
        required_before_counting=list(POST_PERMISSIONS_REQUIRED_EVIDENCE),
    )
    certificate = load_promotion_certificate(
        evidence.get("command_response_promotion_certificate"),
        certificate_key="command_response_promotion_certificate",
        label=label,
        blockers=blockers,
    )
    if not isinstance(certificate, dict):
        return
    if promotion_certificate_payload_marks_builder_report(certificate):
        add(
            blockers,
            "command_response_promotion_certificate_builder_report_not_certificate",
            label,
        )
    collect_promotion_certificate_payload_overclaims(
        certificate,
        blockers,
        certificate_key="command_response_promotion_certificate",
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
    required_chain = string_set(payload.get("v1_required_dependency_chain"))
    for surface in DEPENDENCY_CHAIN:
        if surface not in required_chain:
            add(
                blockers,
                "dependency_chain_surface_missing_from_required_chain",
                "$.surfaces.v1_required_dependency_chain",
                surface=surface,
            )
    blockers_set = string_set(payload.get("v1_sdk_completion_blockers"))
    for surface in DEPENDENCY_CHAIN:
        if surface not in blockers_set:
            add(
                blockers,
                "dependency_chain_surface_missing_from_blockers",
                "$.surfaces.v1_sdk_completion_blockers",
                surface=surface,
            )
    surfaces = payload.get("surfaces")
    if not isinstance(surfaces, list):
        add(blockers, "surfaces_not_list", "$.surfaces.surfaces")
        return
    by_id = {item.get("id"): item for item in surfaces if isinstance(item, dict)}
    response = by_id.get(SURFACE)
    identity = by_id.get(IDENTITY_SURFACE)
    permissions = by_id.get(PERMISSIONS_SURFACE)
    if not isinstance(response, dict):
        add(blockers, "command_chat_response_surface_missing", "$.surfaces")
        return
    if response.get("status") not in {"planning", "post-v1"}:
        add(
            blockers,
            "status_mismatch",
            "$.surfaces.command_chat_response_path",
            expected=["planning", "post-v1"],
            value=response.get("status"),
        )
    require_equal(response, "support_tier", "blocked", "$.surfaces.command_chat_response_path", blockers)
    require_false(response, "public_abi", "$.surfaces.command_chat_response_path", blockers)
    require_false(response, "adds_obelisk_api", "$.surfaces.command_chat_response_path", blockers)
    if response.get("public_contract") != []:
        add(
            blockers,
            "command_chat_response_surface_public_contract_not_empty",
            "$.surfaces.command_chat_response_path.public_contract",
            value=response.get("public_contract"),
        )
    if response.get("depends_on") != [IDENTITY_SURFACE, PERMISSIONS_SURFACE]:
        add(
            blockers,
            "command_chat_response_surface_dependencies_mismatch",
            "$.surfaces.command_chat_response_path.depends_on",
            expected=[IDENTITY_SURFACE, PERMISSIONS_SURFACE],
            value=response.get("depends_on"),
        )
    promoted = string_set(payload.get("promoted_surfaces"))
    if SURFACE in promoted:
        add(blockers, "response_path_planning_evidence_treated_as_promoted", "$.surfaces.promoted_surfaces")
        add(blockers, "command_chat_response_manifest_promotion_without_evidence", "$.surfaces.promoted_surfaces")
    promoted_manifest_entry_has_certificate(
        promoted,
        identity,
        IDENTITY_SURFACE,
        blockers,
        surfaces=payload,
        reason="player_identity_manifest_promotion_without_evidence",
    )
    promoted_manifest_entry_has_certificate(
        promoted,
        permissions,
        PERMISSIONS_SURFACE,
        blockers,
        surfaces=payload,
        reason="permissions_admin_manifest_promotion_without_evidence",
    )
    if response.get("status") in MANIFEST_PROMOTION_STATUSES:
        add(
            blockers,
            "command_chat_response_evidence_not_approved",
            "$.surfaces.command_chat_response_path.status",
            status=response.get("status"),
        )
    validate_response_terminal_certificate_metadata(response, blockers)
    identity_promoted = False
    if isinstance(identity, dict) and identity.get("status") in MANIFEST_PROMOTION_STATUSES:
        if identity.get("status") == "promoted":
            identity_promoted = surface_has_valid_promotion_certificate(
                identity,
                IDENTITY_SURFACE,
                blockers,
                surfaces=payload,
            )
        if not identity_promoted:
            add(blockers, "player_identity_evidence_not_approved", "$.surfaces.player_identity.status", status=identity.get("status"))
        evidence = identity.get("evidence")
        if (
            not isinstance(evidence, dict)
            or not isinstance(evidence.get("player_identity_promotion_certificate"), dict)
        ):
            add(
                blockers,
                "player_identity_promotion_certificate_missing",
                "$.surfaces.player_identity.evidence.player_identity_promotion_certificate",
            )
    if isinstance(identity, dict):
        validate_player_identity_accepted_runtime_evidence(
            identity,
            blockers,
            label="$.surfaces.player_identity",
        )
    permissions_promoted = False
    if isinstance(permissions, dict) and permissions.get("status") in MANIFEST_PROMOTION_STATUSES:
        if permissions.get("status") == "promoted":
            permissions_promoted = surface_has_valid_promotion_certificate(
                permissions,
                PERMISSIONS_SURFACE,
                blockers,
                surfaces=payload,
            )
        if not permissions_promoted:
            add(
                blockers,
                "permissions_admin_evidence_not_approved",
                "$.surfaces.permissions_admin.status",
                status=permissions.get("status"),
            )
    if (
        isinstance(permissions, dict)
        and permissions.get("status") in MANIFEST_PROMOTION_STATUSES
        and not identity_promoted
    ):
        add(
            blockers,
            "permissions_admin_promoted_before_player_identity",
            "$.surfaces.permissions_admin.status",
        )
    if identity_promoted and not permissions_promoted:
        add(
            blockers,
            "permissions_admin_dependency_not_promoted",
            "$.surfaces.permissions_admin.status",
        )
    validate_upstream_promotion_certificate_metadata(
        identity,
        IDENTITY_SURFACE,
        identity_promoted,
        blockers,
    )
    validate_upstream_promotion_certificate_metadata(
        permissions,
        PERMISSIONS_SURFACE,
        permissions_promoted,
        blockers,
    )
    contract = response.get("v1_decision_contract")
    if not isinstance(contract, dict):
        add(blockers, "command_chat_response_surface_decision_contract_missing", "$.surfaces.command_chat_response_path.v1_decision_contract")
    else:
        require_equal(
            contract,
            "decision_manifest",
            "docs/command_chat_response_public_contract_decisions.json",
            "$.surfaces.command_chat_response_path.v1_decision_contract",
            blockers,
        )
        if contract.get("must_remain_without_public_contract_until_promotion") is not True:
            add(
                blockers,
                "command_chat_response_surface_public_contract_gate_missing",
                "$.surfaces.command_chat_response_path.v1_decision_contract.must_remain_without_public_contract_until_promotion",
            )
    collect_surface_overclaims(response, blockers, "$.surfaces.command_chat_response_path")
    collect_manifest_candidate_artifact_overclaims(
        payload,
        blockers,
        response_surface=response,
    )


def surface_by_id(surfaces: dict[str, Any] | None, surface_id: str) -> dict[str, Any] | None:
    if not isinstance(surfaces, dict) or not isinstance(surfaces.get("surfaces"), list):
        return None
    for item in surfaces["surfaces"]:
        if isinstance(item, dict) and item.get("id") == surface_id:
            return item
    return None


def upstream_promotion_diagnostic_item(
    surfaces: dict[str, Any] | None,
    surface_id: str,
) -> dict[str, Any]:
    spec = PROMOTION_CERTIFICATE_SPECS[surface_id]
    surface = surface_by_id(surfaces, surface_id)
    certificate_valid = surface_has_valid_promotion_certificate(
        surface,
        surface_id,
        surfaces=surfaces,
    )
    return {
        "surface": surface_id,
        "manifest_status": surface.get("status") if isinstance(surface, dict) else None,
        "required_certificate_schema": spec["schema"],
        "valid_hash_bound_promotion_certificate_present": certificate_valid,
        "blocks_command_chat_response_path": not certificate_valid,
    }


def build_post_identity_permissions_gap_diagnostic(
    surfaces: dict[str, Any] | None,
    current_route_blocker: str,
) -> dict[str, Any]:
    upstream_dependencies = [
        upstream_promotion_diagnostic_item(surfaces, IDENTITY_SURFACE),
        upstream_promotion_diagnostic_item(surfaces, PERMISSIONS_SURFACE),
    ]
    upstream_missing = [
        item["surface"]
        for item in upstream_dependencies
        if item["blocks_command_chat_response_path"]
    ]
    upstream_promotions_satisfied = not upstream_missing
    return {
        "schema": POST_IDENTITY_PERMISSIONS_GAP_DIAGNOSTIC_SCHEMA,
        "surface": SURFACE,
        "diagnostic_only": True,
        "metadata_only": True,
        "non_evidence": True,
        "non_authorizing": True,
        "current_route_blocker": current_route_blocker,
        "upstream_dependencies": upstream_dependencies,
        "upstream_missing_surfaces": upstream_missing,
        "upstream_promotions_satisfied": upstream_promotions_satisfied,
        "route_blocked": True,
        "state": (
            "upstream_promoted_but_response_path_still_blocked"
            if upstream_promotions_satisfied
            else "blocked_waiting_for_upstream_identity_permissions"
        ),
        "missing_after_valid_upstream_promotions": list(
            POST_IDENTITY_PERMISSIONS_DIAGNOSTIC_MISSING_AFTER_UPSTREAM
        ),
        "non_authorizing_inputs": list(POST_IDENTITY_PERMISSIONS_NON_AUTHORIZING_INPUTS),
        "required_fail_closed_guardrails": list(POST_PERMISSIONS_FAIL_CLOSED_GUARDRAILS),
        "required_runtime_owned_inputs": list(POST_PERMISSIONS_REQUIRED_RUNTIME_INPUTS),
        "reply_send_chat_router_claims_allowed": False,
        "reply_api_allowed": False,
        "send_chat_api_allowed": False,
        "command_support_ready": False,
        "accepted_runtime_evidence": False,
        "approved_runtime_evidence": False,
        "public_header_allowed": False,
        "public_abi_allowed": False,
        "runtime_delivery_allowed": False,
        "public_or_runtime_accounting_allowed": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "p0_dependency_chain_progress_contribution": 0,
        "public_readiness_ready": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "runtime_ready": False,
        "readiness_ready": False,
        "non_claim": (
            "This diagnostic explains remaining command/chat response gaps only; it does not provide "
            "runtime evidence, public ABI, reply/send-chat delivery, SDK/P0 progress, or readiness."
        ),
    }


def build_report(
    root: Path,
    readiness_path: Path,
    decisions_path: Path,
    public_header_path: Path,
    surfaces_path: Path,
    current_route_blocker: str = CURRENT_ROUTE_BLOCKER,
) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    resolved_root = validate_readiness_path_bound_to_root(root=root, readiness_path=readiness_path, blockers=blockers)
    readiness = safe_load_json(readiness_path, "readiness", blockers)
    decisions = safe_load_json(decisions_path, "decisions", blockers)
    surfaces = safe_load_json(surfaces_path, "surfaces", blockers)
    if readiness is not None:
        validation_root = resolved_root or root
        validate_readiness(
            readiness,
            blockers,
            root=validation_root,
            require_provenance=True,
        )
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
    validate_public_header(public_header_path, blockers)
    if current_route_blocker not in ALLOWED_ROUTE_BLOCKERS:
        add(
            blockers,
            "current_route_blocker_mismatch",
            "$.current_route_blocker",
            expected=list(ALLOWED_ROUTE_BLOCKERS),
            value=current_route_blocker,
        )
    validate_route_blocker_order(current_route_blocker, surfaces, blockers)

    valid = not blockers
    return {
        "schema": REPORT_SCHEMA,
        "valid": valid,
        "accepted_for_planning": valid,
        "planning_only": valid,
        "dependency_chain": DEPENDENCY_CHAIN,
        "dependency_chain_locked": True,
        "blocked_behind_surfaces": BLOCKED_BEHIND_SURFACES,
        "current_route_blocker": current_route_blocker,
        "remaining_route_blockers": [current_route_blocker],
        "candidate_capture_classification": CANDIDATE_CAPTURE_CLASSIFICATION,
        "candidate_capture_guardrail": build_candidate_capture_guardrail(current_route_blocker),
        "candidate_capture_counts_toward_public_sdk": False,
        "candidate_capture_counts_toward_runtime": False,
        "candidate_capture_counts_toward_v1_completion": False,
        "candidate_capture_counts_toward_p0_dependency_chain_claim": False,
        "candidate_capture_progress_contribution": 0,
        "candidate_capture_public_or_runtime_accounting_allowed": False,
        "command_support_ready": False,
        "accepted_runtime_evidence": False,
        "approved_runtime_evidence": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "p0_dependency_chain_progress_contribution": 0,
        "public_or_runtime_accounting_allowed": False,
        "public_readiness_ready": False,
        "public_header_allowed": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "public_command_router_allowed": False,
        "public_reply_or_send_chat_abi_allowed": False,
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
        "runtime_ready": False,
        "post_permissions_next_step": POST_PERMISSIONS_NEXT_STEP,
        "post_permissions_abi_evidence_guardrail": POST_PERMISSIONS_ABI_EVIDENCE_GUARDRAIL,
        "post_identity_permissions_gap_diagnostic": build_post_identity_permissions_gap_diagnostic(
            surfaces,
            current_route_blocker,
        ),
        "future_public_abi": {
            "blocked_behind_surfaces": BLOCKED_BEHIND_SURFACES,
            "requires": list(FUTURE_PUBLIC_ABI_REQUIRES),
        },
        "non_claim": (
            "valid planning output does not count command/chat response while player identity remains "
            f"blocked on {current_route_blocker}"
        ),
        "surface": SURFACE,
        "target_set": TARGET_SET,
        "target_filters": sorted(TARGETS),
        "readiness_root": str(root),
        "readiness_path": str(readiness_path),
        "decisions_path": str(decisions_path),
        "surfaces_path": str(surfaces_path),
        "public_header_path": str(public_header_path),
        "source_artifact_hashes": source_artifact_hashes(
            {
                "readiness_path": readiness_path,
                "decisions_path": decisions_path,
                "surfaces_path": surfaces_path,
                "public_header_path": public_header_path,
            }
        ),
        "readiness_status": readiness.get("second_source_status") if isinstance(readiness, dict) else None,
        "decisions_status": decisions.get("status") if isinstance(decisions, dict) else None,
        "surfaces_status": (
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
    root = args.readiness.parent if args.readiness is not None and args.root == DEFAULT_ROOT else args.root
    readiness_path = args.readiness if args.readiness is not None else root / DEFAULT_READINESS_NAME
    report = build_report(
        root,
        readiness_path,
        args.decisions,
        args.public_header,
        args.surfaces,
        current_route_blocker=args.current_route_blocker,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
