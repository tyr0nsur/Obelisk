#!/usr/bin/env python3
"""Validate the command/principal/authz/response bridge stays planning-only."""

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
DEFAULT_DECISIONS = REPO_ROOT / "docs" / "command_principal_authz_response_bridge_decisions.json"
DEFAULT_PLAYER_IDENTITY = REPO_ROOT / "docs" / "player_identity_public_contract_decisions.json"
DEFAULT_PERMISSIONS_ADMIN = REPO_ROOT / "docs" / "permissions_admin_public_contract_decisions.json"
DEFAULT_COMMAND_RESPONSE = REPO_ROOT / "docs" / "command_chat_response_public_contract_decisions.json"
DEFAULT_COMMANDS_REPLIES = REPO_ROOT / "docs" / "commands_replies_public_contract_decisions.json"
DEFAULT_PUBLIC_HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"

REPORT_SCHEMA = "obelisk.command-principal-authz-response-bridge-check.v1"
DECISIONS_SCHEMA = "obelisk.command-principal-authz-response-bridge-decisions.v1"
SURFACE = "obelisk.command_principal_authz_response_bridge.v1"
DEPENDENCY_DOCS = [
    "docs/player_identity_public_contract_decisions.json",
    "docs/permissions_admin_public_contract_decisions.json",
    "docs/command_chat_response_public_contract_decisions.json",
    "docs/commands_replies_public_contract_decisions.json",
]
DEPENDENCY_CHAIN = [
    "obelisk.player_identity.v1",
    "obelisk.permissions_admin.v1",
    "obelisk.command_chat_response_path.v1",
    "obelisk.commands_replies.v1",
]
SOURCE_DOCS = {
    "player_identity": ("obelisk.player_identity.v1", DEFAULT_PLAYER_IDENTITY),
    "permissions_admin": ("obelisk.permissions_admin.v1", DEFAULT_PERMISSIONS_ADMIN),
    "command_response": ("obelisk.command_chat_response_path.v1", DEFAULT_COMMAND_RESPONSE),
    "commands_replies": ("obelisk.commands_replies.v1", DEFAULT_COMMANDS_REPLIES),
}
SOURCE_SCHEMAS = {
    "player_identity": "obelisk.player-identity-public-contract-decisions.v1",
    "permissions_admin": "obelisk.permissions-admin-public-contract-decisions.v1",
    "command_response": "obelisk.command-chat-response-public-contract-decisions.v1",
    "commands_replies": "obelisk.commands-replies-public-contract-decisions.v1",
}
SHARED_VOCABULARY = ("principal_handle", "principal_generation", "principal_scope_flags")
REQUIRED_FAIL_CLOSED = frozenset(
    (
        "missing principal_handle",
        "missing principal",
        "missing principal_generation",
        "missing principal_scope_flags",
        "stale principal",
        "principal_generation mismatch",
        "unsupported principal_scope_flags",
        "scope mismatch",
        "process mismatch",
        "missing established runtime principal identity",
        "command text principal claim",
        "command text permission claim",
        "operator config principal claim",
        "operator config permission claim",
        "missing plugin_owner_token",
        "zero plugin_owner_token",
        "missing capability",
        "missing permission policy provenance",
        "missing permission policy source",
        "unknown policy source",
        "missing policy source provenance",
        "missing policy source generation",
        "policy source generation mismatch",
        "missing policy_epoch provenance",
        "allow without policy_epoch provenance",
        "unknown permission authority",
        "missing authority kind",
        "missing authority generation",
        "authority generation mismatch",
        "plugin-supplied provenance",
        "plugin-supplied authority provenance",
        "permission deny result",
        "permission unknown result",
        "missing action",
        "malformed action_size",
        "rate limit exceeded",
        "malformed UTF-8",
        "oversize response message",
        "oversize command",
        "unsupported source kind",
        "minimal ChatMessageEvent response shortcut",
        "raw ProcessEvent response shortcut",
        "legacy CallProcessEvent response shortcut",
        "static thunk orientation response shortcut",
        "commands/replies response shortcut before promoted identity and permissions/admin",
        "missing promoted player identity",
        "missing promoted permissions/admin",
        "missing command_chat_response_path promotion",
        "missing commands_replies promotion",
    )
)
REQUIRED_BEHAVIORS = frozenset(
    (
        "principal_handle, principal_generation, and principal_scope_flags must appear together in any future command, permission, or response payload that consumes player identity",
        "principal_handle alone never authorizes",
        "permissions/admin cannot return allow from command text, operator config, plugin input, or missing runtime principal observation",
        "permission allow requires policy_source_id, policy_source_generation, authority_kind, authority_generation, and policy_epoch provenance",
        "operator-config authority is recognized but not allow-capable until separately promoted",
        "plugin input and command callbacks cannot self-attest permission authority or policy provenance",
        "command/chat response targeting cannot create principal or permission claims",
        "command/chat response path requires copied response payload, nonzero plugin_owner_token, owner-scoped handles, and promoted identity/permissions before any directed response",
        "minimal ChatMessageEvent is passive copied input only and cannot authorize replies, send-chat, broadcast, moderation, identity, permissions, or response delivery",
        "raw ProcessEvent callbacks cannot authorize replies, send-chat, broadcast, moderation, identity, permissions, or response delivery",
        "static thunk orientation cannot authorize replies, send-chat, broadcast, moderation, identity, permissions, or response delivery",
        "commands/replies cannot dispatch when permission result is deny or unknown",
        "commands/replies cannot dispatch from missing permission policy_epoch or missing command_chat_response_path promotion",
        "commands/replies planning cannot bypass promoted player identity, promoted permissions/admin, or promoted command_chat_response_path",
        "commands/replies cannot imply replies, send-chat, broadcast, moderation, storage, or admin mutation",
        "permission or command rate-limit exhaustion fails closed",
        "malformed UTF-8, oversize messages or commands, and unsupported command source kinds fail closed",
        "missing or zero plugin_owner_token fails closed for every future owner-token bridge operation",
        "missing capability fails closed and no capability bit is reserved by this bridge",
        "legacy CallProcessEvent debug access is not a command, reply, response, permission, or principal bridge",
        "ArkServerApi, ArkApi, AseApi, and NextGenPlugins names may inform demand only and cannot provide offsets, layouts, vtables, code, control flow, or ABI semantics",
    )
)
REQUIRED_BRIDGE_ERGONOMICS_STEPS = (
    "copied chat text",
    "plugin-local parse",
    "copied command payload",
    "permission query",
    "response request",
)
REQUIRED_BRIDGE_ERGONOMICS_BOUNDARY_FRAGMENTS = {
    "copied chat text": frozenset(
        (
            "request input only",
            "cannot establish principal identity",
            "permission authority",
            "dispatch authority",
            "reply/send-chat/broadcast/moderation authority",
            "response delivery",
        )
    ),
    "plugin-local parse": frozenset(
        (
            "private plugin intent only",
            "cannot become a public command router",
            "public parser",
            "ArkApi/AseApi parser compatibility claim",
            "dispatch ordering claim",
        )
    ),
    "copied command payload": frozenset(
        (
            "nonzero plugin_owner_token",
            "principal_handle",
            "principal_generation",
            "principal_scope_flags",
            "permission_policy_epoch",
            "source_kind",
            "normalized command name",
        )
    ),
    "permission query": frozenset(
        (
            "fail closed",
            "deny",
            "unknown",
            "missing provenance",
            "stale principal generation",
            "unsupported scope",
            "malformed action",
            "oversize command",
            "unsupported source_kind",
        )
    ),
    "response request": frozenset(
        (
            "copied intent only",
            "cannot imply reply/send-chat/broadcast/moderation delivery",
            "promoted player identity",
            "promoted permissions/admin",
            "command_chat_response_path are separately promoted",
        )
    ),
}
REQUIRED_FORBIDDEN = frozenset(
    (
        "public bridge ABI",
        "public header symbols",
        "public capability bits",
        "public command SDK/router",
        "public command_chat_response_path ABI",
        "public CallProcessEvent response path",
        "public CallProcessEvent command or reply path",
        "public minimal ChatMessageEvent response path",
        "public raw ProcessEvent response path",
        "public static thunk orientation response path",
        "public commands/replies response shortcut before promoted identity and permissions/admin",
        "response ABI",
        "reply ABI",
        "send-chat ABI",
        "broadcast/notices API",
        "command router",
        "command parser",
        "command registration API",
        "console command API",
        "RCON command API",
        "admin command API",
        "player command API",
        "permission cache ABI",
        "permission groups",
        "admin groups",
        "grant/revoke API",
        "admin mutation",
        "admin actions",
        "principal or permission claims from command text",
        "principal or permission claims from operator config",
        "raw UE pointers",
        "raw ProcessEvent params",
        "raw FString storage",
        "direct native-call wrappers",
        "public UFunction or vtable details",
        "FName/GObjects indices",
        "ResourceHandle",
        "pointer-derived identity",
        "platform account ids",
        "player names",
        "tribe ids",
        "network addresses",
        "player lookup",
        "mutation",
        "return override",
    )
)
REQUIRED_PUBLIC_HEADER_FORBIDDEN_TOKENS = frozenset(
    (
        "OBELISK_API_CAPABILITY_COMMAND_PRINCIPAL_AUTHZ_RESPONSE_BRIDGE",
        "OBELISK_API_CAPABILITY_ADMIN",
        "OBELISK_API_CAPABILITY_AUTHORIZATION",
        "OBELISK_API_CAPABILITY_COMMANDS",
        "OBELISK_API_CAPABILITY_COMMANDS_REPLIES",
        "OBELISK_API_CAPABILITY_COMMAND_REPLIES",
        "OBELISK_API_CAPABILITY_COMMAND_ROUTER",
        "OBELISK_API_CAPABILITY_CHAT_RESPONSES",
        "OBELISK_API_CAPABILITY_CHAT_REPLIES",
        "OBELISK_API_CAPABILITY_SEND_CHAT",
        "OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT_RESPONSE",
        "OBELISK_API_CAPABILITY_COMMAND_CHAT_RESPONSE_PATH",
        "OBELISK_API_CAPABILITY_PERMISSIONS_ADMIN",
        "OBELISK_API_CAPABILITY_PERMISSION_CHECKS",
        "OBELISK_API_CAPABILITY_PERMISSION_EVENTS",
        "OBELISK_API_CAPABILITY_IDENTITY",
        "OBELISK_API_CAPABILITY_PLAYER_IDENTITY",
        "OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_LIFECYCLE",
        "OBELISK_COMMAND_PRINCIPAL_AUTHZ_RESPONSE_BRIDGE_ABI_VERSION",
        "OBELISK_COMMANDS_REPLIES_ABI_VERSION",
        "OBELISK_COMMAND_ROUTER_ABI_VERSION",
        "OBELISK_COMMAND_CHAT_RESPONSE_ABI_VERSION",
        "OBELISK_PERMISSION_CACHE_ABI_VERSION",
        "OBELISK_PERMISSION_QUERY_ABI_VERSION",
        "OBELISK_PERMISSION_REASON_FLAGS",
        "OBELISK_PERMISSION_REASON_",
        "OBELISK_ADMIN_REASON_",
        "ObeliskCommandPrincipalAuthzResponseBridge",
        "ObeliskCommand",
        "ObeliskCommandContext",
        "ObeliskCommandRegistration",
        "ObeliskCommandCallback",
        "ObeliskCommandPayload",
        "ObeliskCommandParser",
        "ObeliskArkApiCommandParser",
        "ObeliskAseApiCommandParser",
        "ObeliskAdminAction",
        "ObeliskAuthorizationDecision",
        "ObeliskPermissionCache",
        "ObeliskPermissionQuery",
        "ObeliskPermissionDecision",
        "ObeliskPermissionReasonFlags",
        "ReasonFlags",
        "reason_flags",
        "ObeliskCommandChatResponse",
        "ObeliskCommandReply",
        "ObeliskChatResponse",
        "ObeliskChatReply",
        "ObeliskSendChat",
        "ObeliskPlayerPrincipalLifecycleEvent",
        "RegisterCommand",
        "RegisterCommandWithOwnerToken",
        "UnregisterCommand",
        "UnregisterCommandWithOwnerToken",
        "RegisterPlayerPrincipalLifecycleEvent",
        "UnregisterPlayerPrincipalLifecycleEvent",
        "AuthorizePermission",
        "CheckPermissionWithOwnerToken",
        "CheckPermissionCachedWithOwnerToken",
        "RegisterPermission",
        "GrantPermission",
        "RevokePermission",
        "BanPlayer",
        "KickPlayer",
        "ReplyToCommand",
        "ReplyToCommandWithOwnerToken",
        "SendChat",
        "SendChatWithOwnerToken",
    )
)
REQUIRED_AUTHZ_REASON_FLAGS_DIAGNOSTIC = {
    "source_surface": "obelisk.permissions_admin.v1",
    "source_artifact": "docs/permissions_admin_query_failclosed_contract.json",
    "diagnostic_only": True,
    "candidate_only": True,
    "public_header_allowed": False,
    "public_capability_bit_allowed": False,
    "public_abi_allowed": False,
    "response_abi_allowed": False,
    "command_payload_allowed": False,
    "response_payload_allowed": False,
    "server_validation_allowed": False,
    "authorization_decision_source": False,
    "changes_allow_deny_unknown": False,
    "replaces_policy_provenance": False,
    "permits_dispatch_or_response": False,
    "plugin_supplied_allowed": False,
    "command_text_supplied_allowed": False,
    "operator_config_supplied_allowed": False,
}
REASON_FLAG_TERMS = (
    "authz_reason_flags",
    "fail_closed_reason_flags",
    "reason_flags",
    "ReasonFlags",
    "ObeliskPermissionReasonFlags",
    "OBELISK_PERMISSION_REASON_FLAGS",
    "OBELISK_PERMISSION_REASON_",
    "OBELISK_ADMIN_REASON_",
)
REASON_FLAG_ALLOWED_PATH_FRAGMENTS = (
    ".candidate_only_diagnostics.authz_reason_flags",
    ".non_claims[",
    ".public_header_forbidden_tokens[",
)
REQUIRED_SOURCE_SEMANTICS = {
    "player_identity": frozenset(
        (
            "principal_handle",
            "principal_generation",
            "principal_scope_flags",
            "stale generation fails closed",
            "unsupported scope fails closed",
            "no lookup handle",
            "no mutation or return override authority",
        )
    ),
    "permissions_admin": frozenset(
        (
            "principal_handle alone never authorizes",
            "missing principal_generation",
            "principal_generation_mismatch",
            "unsupported principal_scope_flags",
            "policy_source_id",
            "policy_source_generation",
            "authority_kind",
            "authority_generation",
            "policy_epoch",
            "missing policy_epoch provenance fails closed",
            "operator-config authority is recognized but not allow-capable until separately promoted",
            "plugin input cannot self-attest authority provenance",
            "rate limit exceeded",
            "permission cache ABI",
        )
    ),
    "command_response": frozenset(
        (
            "response_handle",
            "plugin_owner_token",
            "principal_handle",
            "principal_generation",
            "principal_scope_flags",
            "missing or zero plugin_owner_token fails closed",
            "captured post-init debug CallProcessEvent tables do not authorize response delivery",
            "minimal ChatMessageEvent registration does not authorize response delivery",
            "raw ProcessEvent callbacks do not authorize response delivery",
            "static thunk orientation does not authorize response delivery",
            "malformed UTF-8 or oversize messages fail closed",
            "response delivery never creates identity or permission claims",
            "future targeting must use only a promoted copied principal handle/generation",
        )
    ),
    "commands_replies": frozenset(
        (
            "permission_policy_epoch",
            "principal_handle",
            "principal_generation",
            "principal_scope_flags",
            "missing permission policy provenance fails closed",
            "permission denial or unknown result never dispatches a command",
            "malformed UTF-8, oversize commands, and unsupported source kinds fail closed",
            "operator config remains policy input only and cannot establish command identity, principal identity, permission authority, or policy provenance",
            "commands/replies remains blocked while command_chat_response_path is unpromoted or unresolved",
            "command callbacks cannot self-attest permission authority",
        )
    ),
}
FALSE_ONLY_KEYS = frozenset(
    (
        "accounting_credit_allowed",
        "activation_precondition_report",
        "activation_preconditions_report",
        "beta_notice_action_report",
        "broadcast_status",
        "broadcast_status_ready",
        "broadcast_ready",
        "broadcast_source_ready",
        "broadcast_source_status_ready",
        "authz_bridge_ready",
        "authz_ready",
        "authz_response_ready",
        "authorization_ready",
        "bridge_report",
        "bridge_claims_allowed",
        "canonical_route_gate_ready",
        "canonical_route_ready",
        "chat_ready",
        "chat_source_ready",
        "chat_source_status_ready",
        "command_candidate_ready",
        "command_planning_report",
        "command_reply_candidate_ready",
        "command_chat_response_path_complete",
        "command_chat_response_path_completed",
        "command_chat_response_path_ready",
        "command_response_path_ready",
        "command_response_path_complete",
        "command_response_path_completed",
        "command_response_ready",
        "command_response_unlocked",
        "command_router_ready",
        "commands_replies_candidate_ready",
        "commands_replies_final_gate_ready",
        "commands_replies_final_ready",
        "commands_replies_ready",
        "commands_replies_unlocked",
        "copied_response_intent_planning_ready",
        "copied_response_intent_ready",
        "complete_sdk_claim_allowed",
        "counts_as_public_sdk",
        "counts_as_runtime",
        "counts_as_v1_completion",
        "counts_toward_complete_sdk",
        "counts_toward_complete_sdk_claim",
        "counts_toward_public_sdk",
        "counts_toward_runtime",
        "counts_toward_sdk",
        "counts_toward_v1_completion",
        "accepted_runtime_evidence_ready",
        "accepted_runtime_evidence_sufficient",
        "accepted_runtime_evidence_only_ready",
        "beta_notice_ready",
        "beta_notice_sent",
        "identity_public_contract_gate_missing_unlock_allowed",
        "identity_public_contract_gate_accepted",
        "identity_public_contract_gate_passed",
        "identity_public_contract_gate_resolved",
        "multi_surface_beta_capture_pack_ready",
        "multi_surface_beta_capture_plan_ready",
        "multi_surface_beta_plan_ready",
        "final_artifact_accepted",
        "final_artifact_ready",
        "final_certificate_accepted",
        "final_certificate_metadata_ready",
        "final_certificate_ready",
        "final_certificate_status_ready",
        "final_gate_accepted",
        "final_gate_ready",
        "final_gate_unlocked",
        "player_identity_promotion_certificate_ready",
        "operator_approval_granted",
        "notice_action_report",
        "notice_ready",
        "notice_sent",
        "next_action_artifact",
        "next_action_output",
        "next_action_report",
        "next_action_runner_output",
        "next_action_runner_report",
        "next_action_status_report",
        "package_install",
        "package_install_ready",
        "package_shape",
        "package_shape_evidence",
        "package_shape_evidence_accepted",
        "package_shape_evidence_ready",
        "package_shape_install",
        "package_shape_install_ready",
        "package_shape_report",
        "passive_chat_evidence_ready",
        "passive_evidence_ready",
        "passive_evidence_sufficient",
        "permissions_admin_unlocked",
        "plugin_hub_planning",
        "plugin_hub_planning_accepted",
        "plugin_hub_planning_ready",
        "plugin_hub_planning_supported",
        "plugin_hub_ready",
        "progress_ready",
        "promotion_ready",
        "public_or_runtime_accounting_allowed",
        "public_sdk_ready",
        "public_sdk_complete",
        "public_sdk_stable",
        "public_abi_ready",
        "public_header_ready",
        "public_header_symbols_ready",
        "public_reachability_ready",
        "public_reachability_unlock_allowed",
        "rcon_command_candidate_ready",
        "rcon_command_route_ready",
        "rcon_ready",
        "rcon_route_candidate_ready",
        "rcon_route_ready",
        "rcon_status",
        "rcon_status_ready",
        "rcon_source_ready",
        "rcon_source_status_ready",
        "reply_abi_ready",
        "reply_api_ready",
        "reply_ready",
        "readiness_progress",
        "readiness_ready",
        "request_check_ready",
        "request_pack_ready",
        "response_bridge_candidate_ready",
        "response_complete",
        "response_completed",
        "response_path_complete",
        "response_path_completed",
        "response_path_ready",
        "response_ready",
        "response_bridge_ready",
        "response_bridge_unlocked",
        "response_planning_report",
        "response_planning_report_accepted",
        "response_planning_report_ready",
        "response_status_report",
        "response_status_report_accepted",
        "response_status_report_ready",
        "route_claim_allowed",
        "route_cleared",
        "route_cleared_for_public_abi",
        "route_cleared_for_public_reply_or_send_chat_abi",
        "route_cleared_for_public_send_chat_abi",
        "route_gate_ready",
        "route_ready",
        "local_chat_seed_ready",
        "local_route_seed_ready",
        "local_routing_seed_ready",
        "runtime_approval_granted",
        "runtime_delivery_ready",
        "runtime_readiness_ready",
        "runtime_ready",
        "runtime_status_artifact",
        "runtime_status_report",
        "runtime_window_artifact_ready",
        "runtime_window_plan_ready",
        "runtime_window_ready",
        "runtime_work_authorized",
        "sdk_status_artifact",
        "sdk_status_report",
        "public_header_allowed",
        "runtime_wiring_allowed",
        "server_validation_allowed",
        "server_operations_authorized",
        "side_lane_artifact",
        "side_lane_artifact_ready",
        "side_lane_ready",
        "public_bridge_abi_allowed",
        "public_command_router_allowed",
        "command_router_allowed",
        "permissions_admin_ready",
        "public_reply_abi_ready",
        "public_reply_or_send_chat_abi_allowed",
        "public_response_abi_allowed",
        "public_response_path_allowed",
        "public_response_path_ready",
        "response_abi_allowed",
        "capability_bit_allowed",
        "sdk_complete",
        "sdk_completion_allowed",
        "sdk_completion_claim_allowed",
        "sdk_completion_evidence",
        "sdk_completion_ready",
        "sdk_ready",
        "sdk_stable",
        "send_chat_abi_ready",
        "send_chat_allowed",
        "send_chat_api_ready",
        "send_chat_ready",
        "send_ready",
        "send_route_ready",
        "send_source_ready",
        "send_source_status_ready",
        "send_status",
        "send_status_ready",
        "source_ready",
        "source_status",
        "source_status_ready",
        "stable_claim_allowed",
        "stable_sdk",
        "scoped_statement_ready",
        "scoped_statement_counts_toward_completion",
        "scoped_statement_counts_toward_complete_sdk_claim",
        "scoped_statement_outcomes_satisfy_completion",
        "support_tier_readiness",
        "support_tier_report",
        "terminal_certificate",
        "terminal_certificate_accepted",
        "terminal_certificate_metadata",
        "terminal_certificate_metadata_accepted",
        "terminal_certificate_metadata_ready",
        "terminal_certificate_ready",
        "terminal_certificate_status",
        "terminal_certificate_status_ready",
        "child_checker_placeholder",
        "child_checker_placeholder_accepted",
        "child_checker_placeholder_ready",
        "status_artifact",
        "status_artifact_report",
        "status_report",
        "status_report_accepted",
        "status_report_ready",
        "status_metadata",
        "status_metadata_ready",
        "transfer_b_accept_candidate_ready",
        "transfer_b_accept_route_ready",
        "transfer_b_accept_ready",
        "transfer_baccept_candidate_ready",
        "transfer_baccept_route_ready",
        "transfer_baccept_ready",
        "v1_complete",
        "v1_completion_allowed",
        "v1_completion_evidence",
        "v1_sdk_complete",
    )
)
CREDIT_ONLY_KEYS = frozenset(
    (
        "accounting_credit",
        "blocker_credit",
        "canonical_route_gate_credit",
        "public_sdk_credit",
        "readiness_credit",
        "route_gate_credit",
        "sdk_completion_credit",
        "sdk_credit",
        "v1_completion_credit",
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
        "review_provenance",
        "response_channel",
        "response_source",
        "route_channel",
        "route_source",
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
SOURCE_ALIAS_CONTEXT_VALUES = frozenset(
    (
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
        "response_planning_report",
        "response_status_report",
        "send",
        "send_chat",
        "send_channel",
        "send_chat_request",
        "send_source",
        "send_source_alias",
        "server_console",
        "source_alias",
        "status_metadata",
        "status_report",
        "terminal_certificate",
        "terminal_certificate_metadata",
    )
)
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
BROAD_P0_ALIAS_SCOPE_RE = re.compile(
    r"(?:^|_)(?:"
    r"accepted_runtime_evidence|activation_preconditions?(?:_(?:artifacts?|reports?))?|admin_authority|"
    r"authz(?:_?(?:bridge|response|ready))?|authorization|"
    r"broadcast(?:_(?:source|status|route))?|bridge|canonical_route|canonical_route_gate|capability|"
    r"(?:beta_)?notice_actions?(?:_reports?)?|"
    r"next_?action(?:_?(?:artifacts?|outputs?|plans?|planners?|reports?|runners?|status))*|"
    r"child_?checker_?placeholders?|checker_?placeholders?|"
    r"command(?:_chat)?_response(?:_path)?|command_planning|command_router|command_routing|"
    r"copied_response_intent(?:_planning)?|"
    r"commands?_repl(?:y|ies)|dependency_chain|identity_public_contract_gate|"
    r"final_?(?:gate|certificate|artifact)(?:_?(?:metadata|reports?|status))?|"
    r"(?:local_)?(?:route|routing|chat)_seed|"
    r"passive_(?:chat_)?evidence|passive_runtime_evidence|"
    r"plugin_?hub(?:_?(?:planning|readiness|reports?|support|package|package_?shape))?|"
    r"permissions?_admin|permissions?_quer(?:y|ies)|permission(?:_header|_query)?|"
    r"public_(?:abi|api|bridge|header|readiness|reply|response|route|runtime|sdk)|"
    r"rcon(?:_command)?(?:_candidate|_route|_source|_status)?|"
    r"reply(?:_(?:abi|api|endpoint|path|request))?|replies(?:_(?:abi|api|endpoint|path|request))?|"
    r"response(?:_path)?|"
    r"package_?(?:install|shape(?:_?(?:evidence|install|support))?)|precondition_(?:artifacts?|reports?)|"
    r"route(?:_(?:accepted|acceptance|claim|cleared|gate|readiness|snapshot))?|"
    r"(?:route|runtime|sdk|public_?sdk|obelisk_?sdk|bridge|command_?response)_?status(?:_?(?:artifacts?|reports?|snapshots?))*|"
    r"status_?metadata(?:_?(?:artifacts?|reports?|snapshots?))?|"
    r"status_?(?:artifacts?|reports?|snapshots?)|"
    r"response_?planning(?:_?(?:reports?|packages?))?|response_?status(?:_?reports?)?|"
    r"runtime(?:_(?:capture|delivery|readiness|wiring|work))?|"
    r"send(?:_(?:chat|source|status|route))?|source(?:_(?:ready|status))?|server_operations|stable_(?:claim|sdk)|"
    r"side_?lane(?:_?(?:artifacts?|reports?|candidate|candidates))?|"
    r"support(?:_tier)?(?:_readiness|_report|_package|_package_shape)|"
    r"terminal_?certificates?(?:_?(?:metadata|status|reports?))?|"
    r"(?:complete|full|production)_sdk|"
    r"p0(?:_(?:completion|dependency|progress|release|surface|chain))*|"
    r"v1(?:_0)?(?:_(?:api|completion|release|sdk|stable|support))*"
    r")(?:_|$)"
)
BROAD_P0_ALIAS_STATE_RE = re.compile(
    r"(?:^|_)(?:"
    r"accepted|approved|allowed|available|authorized|claimed|complete|completed|"
    r"credited|delivered|enabled|earned|finished|granted|implemented|live|met|opened|"
    r"operational|passed|promoted|public|reachable|ready|reviewed|sent|stable|"
    r"supported|unblocked|unlocked|validated|verified"
    r")(?:_|$)"
)
BROAD_P0_PROGRESS_OR_CREDIT_ALIAS_RE = re.compile(
    r"(?:^|_)(?:"
    r"claim_progress|credit|credited|progress|progress_contribution|progress_percent|"
    r"progress_ratio|readiness_credit|sdk_credit|sdk_completion_credit|"
    r"v1_completion_credit|public_sdk_credit|counts?(?:_towards?|_toward|_as)?"
    r")(?:_|$)"
)
BROAD_P0_ALIAS_EXEMPT_KEYS = frozenset(
    (
        "accepted_for_planning",
        "post_approved_runtime_evidence_gate",
        "post_approved_runtime_evidence_route_check",
        "required_before_public_header",
    )
)
NON_AUTHORIZING_ROUTE_CONTEXT_TERMS = frozenset(
    (
        "beta_notice",
        "broadcast",
        "discord_notice",
        "broadcast_source",
        "broadcast_status",
        "chat_source",
        "command_candidate",
        "command_reply_candidate",
        "commands_replies_candidate",
        "child_checker_placeholder",
        "checker_placeholder",
        "lifecycle_start_end_evidence",
        "multi_surface_beta_capture_pack",
        "multi_surface_beta_capture_plan",
        "multi_surface_capture_pack",
        "multi_surface_capture_plan",
        "notice_action",
        "notice_artifact",
        "notice_report",
        "notice_status",
        "public_reachability",
        "rcon",
        "rcon_command_candidate",
        "rcon_command_route",
        "rcon_status",
        "rcon_route_candidate",
        "rcon_route",
        "rcon_source",
        "reply_request",
        "response_bridge",
        "send_route",
        "send_chat",
        "send_chat_request",
        "send_source",
        "send_status",
        "source_alias",
        "request_check",
        "request_pack",
        "response_bridge_candidate",
        "response_planning_report",
        "response_status_report",
        "route_cleared",
        "runtime_window",
        "runtime_principal_lifecycle_start_end_evidence",
        "runtime_principal_start_end_evidence",
        "start_end_evidence",
        "start_end_only",
        "start_end_only_evidence",
        "source_ready",
        "source_status",
        "status_metadata",
        "status_report",
        "scoped_statement",
        "terminal_certificate",
        "terminal_certificate_metadata",
        "terminal_certificate_status",
        "route_status_metadata",
        "runtime_status_metadata",
        "sdk_status_metadata",
        "transfer_b_accept_candidate",
        "transfer_b_accept_route",
        "transfer_b_accept",
        "transfer_baccept_candidate",
        "transfer_baccept_route",
        "transfer_baccept",
    )
)
NEGATIVE_CONTEXT_TOKENS = (
    "artifact_classes_not_progress",
    "blocker",
    "blockers",
    "blocked",
    "deny",
    "exclusion",
    "forbid",
    "forbidden",
    "forbidden_authority_sources",
    "negative",
    "non_counting",
    "not_progress",
    "not_sufficient",
    "required_behavior",
    "required_exclusions",
    "why_blocked",
)
FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_KEYS = frozenset(
    (
        "authority_claim_source",
        "principal_source",
    )
)
FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_VALUES = frozenset(
    (
        "command_text",
        "broadcast",
        "broadcast_source",
        "broadcast_status",
        "chat_source",
        "command_candidate",
        "command_reply_candidate",
        "commands_replies_candidate",
        "multi_surface_beta_capture_pack",
        "multi_surface_beta_capture_plan",
        "operator_config",
        "rcon",
        "rcon_command_candidate",
        "rcon_command_route",
        "rcon_route_candidate",
        "rcon_source",
        "rcon_status",
        "reply_request",
        "response_bridge",
        "send_chat",
        "send_chat_request",
        "send_route",
        "send_source",
        "send_status",
        "source_alias",
        "status_metadata",
        "status_report",
        "response_bridge_candidate",
        "response_planning_report",
        "response_status_report",
        "terminal_certificate",
        "terminal_certificate_metadata",
        "child_checker_placeholder",
        "transfer_b_accept_candidate",
        "transfer_b_accept_route",
        "transfer_baccept_candidate",
        "transfer_baccept_route",
    )
)
POSITIVE_CLAIM_RE = re.compile(
    r"\b("
    r"accounting\s+credit|activation[_ -]?preconditions?(?:[_ -]?(?:artifacts?|reports?))?|"
    r"(?:beta[_ -]?)?notice[_ -]?actions?(?:[_ -]?reports?)?|bridge|capability|canonical\s+route\s+gate|"
    r"authz(?:[_ -]?(?:ready|bridge|response))?|authorization|"
    r"final[_ -]?(?:gate|certificate|artifact)(?:[_ -]?(?:metadata|status|reports?))?|"
    r"next[_ -]?action(?:[_ -]?(?:artifacts?|outputs?|plans?|planners?|reports?|runners?|status))*|"
    r"child[_ -]?checker[_ -]?placeholders?|checker[_ -]?placeholders?|"
    r"command[_ -]?candidate|command[_ -]?reply[_ -]?candidate|commands?/replies[_ -]?candidate|"
    r"command[_ -]?planning|command[_ -]?router|"
    r"copied[_ -]?response[_ -]?intent(?:[_ -]?planning)?|"
    r"command\s+response\s+path|commands?/replies|complete\s+sdk|permissions?/admin|player[_ -]?identity|"
    r"(?:local[_ -]?)?(?:route|routing|chat)[_ -]?seeds?|"
    r"passive[_ -]?(?:chat[_ -]?)?evidence|passive[_ -]?runtime[_ -]?evidence|"
    r"package[_ -]?(?:install|shapes?(?:[_ -]?(?:evidence|install|support))?)|"
    r"plugin[_ -]?hub(?:[_ -]?(?:planning|readiness|reports?|support|package|package[_ -]?shape))?|"
    r"precondition[_ -]?(?:artifacts?|reports?)|principal|"
    r"public\s+abi|public\s+header|public\s+sdk|reply(?:\s+(?:api|abi|endpoint))?|response|response\s+bridge\s+candidate|"
    r"response[_ -]?path|"
    r"response[_ -]?planning(?:[_ -]?(?:reports?|packages?))?|response[_ -]?status(?:[_ -]?reports?)?|"
    r"route(?:\s+(?:cleared|gate))?|runtime(?:\s+readiness)?|sdk(?:\s+completion)?|send[_ -]?(?:chat|source|status|route)|stable\s+sdk|v1(?:\s+sdk)?"
    r"|side[_ -]?lane(?:[_ -]?(?:artifacts?|reports?|candidate|candidates))?"
    r"|scoped[_ -]?(?:non[_ -]complete[_ -]?)?(?:v1[_ -]?)?statements?"
    r"|(?:route|runtime|sdk|public[_ -]?sdk|obelisk[_ -]?sdk|bridge|command[_ -]?response)[_ -]?status(?:[_ -]?(?:artifacts?|reports?|snapshots?))*"
    r"|status[_ -]?(?:artifacts?|reports?|snapshots?)"
    r"|support[_ -]?tiers?(?:[_ -]?(?:readiness|reports?))?|support[_ -]?tier[_ -]?(?:packages?|package[_ -]?shapes?)"
    r"|terminal[_ -]?certificates?(?:[_ -]?(?:metadata|status|reports?))?"
    r")\b.{0,100}\b("
    r"accepted|allowed|approved|available|awarded|claimed|complete|completed|credited|done|earned|enabled|finished|implemented|"
    r"live|promoted|public|ready|runtime|stable|sufficient|supported|unlocked|validated|verified"
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
ACCEPTED_RUNTIME_EVIDENCE_TEXT_TERMS = (
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
    "non_claim",
    "non_counting",
    "non_evidence",
    "not_accepted",
    "not_ready",
    "not_sufficient",
    "only_moves_to_identity_public_contract_gate_missing",
    "requires",
    "unresolved",
    "without",
)
NEGATED_CLAIM_RE = re.compile(
    r"\b("
    r"before|blocked|blocker|cannot|closed|does\s+not|fail[s-]?closed|false|forbidden|missing|must|never|no|non[-_ ]?(?:claim|counting|evidence)|not|only|planning|"
    r"reject(?:s|ed)?|requires?|until|without"
    r")\b",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    parser.add_argument("--player-identity", type=Path, default=DEFAULT_PLAYER_IDENTITY)
    parser.add_argument("--permissions-admin", type=Path, default=DEFAULT_PERMISSIONS_ADMIN)
    parser.add_argument("--command-response", type=Path, default=DEFAULT_COMMAND_RESPONSE)
    parser.add_argument("--commands-replies", type=Path, default=DEFAULT_COMMANDS_REPLIES)
    parser.add_argument("--public-header", type=Path, default=DEFAULT_PUBLIC_HEADER)
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


def sha256_file(path: Path, label: str, blockers: list[dict[str, Any]]) -> str | None:
    try:
        reject_symlink_component(path, label)
        resolved = reject_protected_input_path(path, label)
        digest = hashlib.sha256()
        with resolved.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except SystemExit as exc:
        add(blockers, f"{label}_path_rejected", f"$.{label}", path=str(path), detail=str(exc))
    except OSError as exc:
        add(blockers, f"{label}_unreadable", f"$.{label}", path=str(path), detail=str(exc))
    return None


def source_artifact_hashes(
    *,
    decisions_path: Path,
    source_paths: dict[str, tuple[str, Path]],
    public_header_path: Path,
    blockers: list[dict[str, Any]],
) -> dict[str, str | None]:
    hashes = {
        "bridge_decisions_path": sha256_file(decisions_path, "bridge_decisions_path", blockers),
        "public_header_path": sha256_file(public_header_path, "public_header_path", blockers),
    }
    for label, (_, path) in source_paths.items():
        hashes[f"{label}_decisions_path"] = sha256_file(
            path,
            f"{label}_decisions_path",
            blockers,
        )
    return hashes


def strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def string_set(value: Any) -> set[str]:
    return set(strings(value))


def normalized_key(value: Any) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value))
    return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")


def normalized_claim_source(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).casefold()).strip("_")


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
        and broad_public_or_runtime_alias_value_is_positive(normalized_key(key), child)
        for key, child in value.items()
    )


def is_negative_context(trail: str) -> bool:
    lowered = trail.casefold()
    return any(token in lowered for token in NEGATIVE_CONTEXT_TOKENS)


def is_claim_container_context(trail: str) -> bool:
    segments = (segment.split("[", 1)[0] for segment in trail.split("."))
    return any(
        normalized_key(segment) in {"blocker", "blockers", "block_reasons", "why_blocked"}
        for segment in segments
    )


def is_non_claim_artifact_list_context(trail: str) -> bool:
    normalized = normalized_key(trail)
    return any(
        token in normalized
        for token in (
            "artifact_classes_not_progress",
            "non_evidence_artifacts",
            "shortcut_artifacts_never_count",
        )
    )


def contains_forbidden_pre_runtime_claim_source(value: Any) -> bool:
    if isinstance(value, str):
        normalized = normalized_claim_source(value)
        return (
            normalized in SOURCE_ALIAS_CONTEXT_VALUES
            or normalized in FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_VALUES
            or non_authorizing_route_context_key(normalized)
        )
    if isinstance(value, list):
        return any(contains_forbidden_pre_runtime_claim_source(item) for item in value)
    if isinstance(value, dict):
        return any(contains_forbidden_pre_runtime_claim_source(item) for item in value.values())
    return False


def has_credit_claim_value(value: Any) -> bool:
    if value in (False, None, "", [], {}):
        return False
    return True


def is_positive_claim_value(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        return normalized_claim_source(value) in {
            "accepted",
            "allowed",
            "approved",
            "available",
            "authorized",
            "claimed",
            "certified",
            "complete",
            "completed",
            "credited",
            "delivered",
            "earned",
            "enabled",
            "finished",
            "implemented",
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
            "runtime",
            "sent",
            "signed",
            "stable",
            "supported",
            "terminal",
            "true",
            "unblocked",
            "unlocked",
            "validated",
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
        key_name in CREDIT_ONLY_KEYS
        or key_name in {
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


def non_authorizing_route_context_key(key_name: str) -> bool:
    return any(term in key_name for term in NON_AUTHORIZING_ROUTE_CONTEXT_TERMS)


def non_authorizing_route_alias_key(key_name: str) -> bool:
    return non_authorizing_route_context_key(key_name) and (
        BROAD_P0_ALIAS_STATE_RE.search(key_name) is not None
        or broad_progress_or_credit_alias_key(key_name)
    )


def broad_public_or_runtime_alias_key(key_name: str) -> bool:
    if key_name in BROAD_P0_ALIAS_EXEMPT_KEYS:
        return False
    if non_claiming_requirement_or_negative_key(key_name):
        return False
    return (
        key_name in FALSE_ONLY_KEYS
        or key_name in CREDIT_ONLY_KEYS
        or non_authorizing_route_alias_key(key_name)
        or (
            BROAD_P0_ALIAS_SCOPE_RE.search(key_name) is not None
            and (
                BROAD_P0_ALIAS_STATE_RE.search(key_name) is not None
                or broad_progress_or_credit_alias_key(key_name)
            )
        )
        or key_name in {"progress", "claim_progress", "claim_progress_contribution"}
    )


def broad_public_or_runtime_alias_value_is_positive(key_name: str, value: Any) -> bool:
    if broad_progress_or_credit_alias_key(key_name) and progress_claim_value_is_nonzero(value):
        return True
    return contains_positive_claim_value(value)


def source_marker_value_is_non_authorizing(value: Any) -> bool:
    if isinstance(value, str):
        normalized = normalized_key(value)
        return (
            normalized in SOURCE_ALIAS_CONTEXT_VALUES
            or non_authorizing_route_context_key(normalized)
            or
            BROAD_P0_ALIAS_SCOPE_RE.search(normalized) is not None
            or broad_progress_or_credit_alias_key(normalized)
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
            non_authorizing_route_alias_key(normalized)
            or
            BROAD_P0_ALIAS_SCOPE_RE.search(normalized) is not None
            and (
                BROAD_P0_ALIAS_STATE_RE.search(normalized) is not None
                or broad_progress_or_credit_alias_key(normalized)
            )
        )
    if isinstance(value, list):
        return any(source_marker_value_claims_positive_alias(item) for item in value)
    if isinstance(value, dict):
        return any(source_marker_value_claims_positive_alias(item) for item in value.values())
    return False


def split_source_marker_status_overclaims(value: dict[str, Any]) -> bool:
    marker_values = [
        child
        for key, child in value.items()
        if normalized_key(key) in SOURCE_CONTEXT_KEYS
    ]
    if not marker_values or not any(source_marker_value_is_non_authorizing(item) for item in marker_values):
        return False
    return any(
        broad_public_or_runtime_alias_value_is_positive(normalized_key(key), child)
        for key, child in value.items()
        if normalized_key(key) in SOURCE_STATUS_KEYS
    )


def planning_word_is_claim_subject(text: str) -> bool:
    normalized = normalized_key(text)
    return any(
        term in normalized
        for term in (
            "command_planning",
            "response_planning",
            "response_bridge_planning",
            "copied_response_intent_planning",
            "plugin_hub_planning",
        )
    )


def negation_is_only_planning_word(text: str, regex: re.Pattern[str]) -> bool:
    matches = list(regex.finditer(text))
    return bool(matches) and planning_word_is_claim_subject(text) and all(
        normalized_key(match.group(0)) == "planning" for match in matches
    )


def positive_claim_is_negated(value: str, match: re.Match[str]) -> bool:
    prefix_sentence = re.split(r"[;\n]", value[: match.start()])[-1]
    suffix_sentence = re.split(r"[;\n]", value[match.end() :], maxsplit=1)[0]
    return (
        NEGATED_CLAIM_RE.search(prefix_sentence) is not None
        or (
            NEGATED_CLAIM_RE.search(match.group(0)) is not None
            and not negation_is_only_planning_word(match.group(0), NEGATED_CLAIM_RE)
        )
        or NEGATED_CLAIM_RE.search(suffix_sentence) is not None
    )


def has_unnegated_public_abi_identity_lookup_handle_claim(value: str) -> bool:
    for clause in re.split(r"[;\n]", value):
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


def has_unnegated_accepted_runtime_evidence_skip_claim(value: str) -> bool:
    for clause in re.split(r"[;\n]", value):
        if NEGATED_CLAIM_RE.search(clause):
            continue
        normalized = normalized_key(clause)
        if re.search(r"(?:^|_)not(?:_|$)", normalized) or any(
            term in normalized for term in ACCEPTED_RUNTIME_EVIDENCE_NEGATED_ALIAS_TERMS
        ):
            continue
        if any(term in normalized for term in ACCEPTED_RUNTIME_EVIDENCE_TEXT_TERMS) and any(
            term in normalized for term in ACCEPTED_RUNTIME_EVIDENCE_SKIP_TERMS
        ):
            return True
    return False


def has_unnegated_non_authorizing_route_claim(value: str) -> bool:
    for clause in re.split(r"[;\n]", value):
        if NEGATED_CLAIM_RE.search(clause):
            continue
        normalized = normalized_key(clause)
        if non_authorizing_route_context_key(normalized) and (
            BROAD_P0_ALIAS_STATE_RE.search(normalized) is not None
            or broad_progress_or_credit_alias_key(normalized)
        ):
            return True
    return False


def collect_strings(value: Any) -> list[str]:
    if isinstance(value, dict):
        observed: list[str] = []
        for key, child in value.items():
            observed.append(str(key))
            observed.extend(collect_strings(child))
        return observed
    if isinstance(value, list):
        observed = []
        for child in value:
            observed.extend(collect_strings(child))
        return observed
    if isinstance(value, str):
        return [value]
    return []


def text_claim_path_is_exempt_metadata(trail: str) -> bool:
    exempt_segments = {
        "next_required_action",
        "operator_next_command",
        "operator_next_commands",
        "required_action",
        "required_next_action",
    }
    return any(
        normalized_key(segment.split("[", 1)[0]) in exempt_segments
        for segment in trail.split(".")
        if segment
    )


def collect_overclaims(value: Any, blockers: list[dict[str, Any]], trail: str = "$") -> None:
    if isinstance(value, dict):
        if (
            contains_source_overclaim_zero_marker(value)
            and source_overclaim_zero_has_positive_status_alias(value)
        ):
            add(blockers, "source_overclaim_zero_status_alias_overclaim", trail, value=value)
        source_marker_context = any(
            source_marker_value_is_non_authorizing(child)
            for key, child in value.items()
            if normalized_key(key) in SOURCE_CONTEXT_KEYS
        )
        if split_source_marker_status_overclaims(value):
            add(blockers, "public_or_runtime_overclaim", trail, value=value)
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
            positive_claim_value = any(
                broad_public_or_runtime_alias_value_is_positive(claim_key, item)
                for item in declared_claim_values
            )
            if broad_public_or_runtime_alias_key(claim_key) and positive_claim_value:
                reason = (
                    "accounting_credit_overclaim"
                    if broad_progress_or_credit_alias_key(claim_key)
                    and claim_key not in FALSE_ONLY_KEYS
                    else "public_or_runtime_overclaim"
                )
                add(blockers, reason, trail, field=claim_name, value=value)
            if (
                claim_key in FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_KEYS
                and contains_forbidden_pre_runtime_claim_source(declared_claim_values)
            ):
                add(blockers, "pre_runtime_principal_or_authority_claim_source", trail, field=claim_name, value=value)
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            key_name = normalized_key(key)
            non_claiming_guardrail_key = non_claiming_requirement_or_negative_key(key_name)
            if (
                key_name in SOURCE_CONTEXT_KEYS
                and source_marker_value_claims_positive_alias(child)
            ):
                add(blockers, "public_or_runtime_overclaim", child_trail, field=str(key), value=child)
            if (
                key_name in SOURCE_STATUS_KEYS
                and source_marker_context
                and broad_public_or_runtime_alias_value_is_positive(key_name, child)
            ):
                add(blockers, "public_or_runtime_overclaim", child_trail, field=str(key), value=child)
            if key_name in FALSE_ONLY_KEYS and child is not False:
                add(blockers, "public_or_runtime_overclaim", child_trail, field=str(key), value=child)
            if key_name in CREDIT_ONLY_KEYS and has_credit_claim_value(child):
                add(blockers, "accounting_credit_overclaim", child_trail, field=str(key), value=child)
            if (
                not non_claiming_guardrail_key
                and non_authorizing_route_context_key(key_name)
                and contains_positive_claim_value(child)
            ):
                add(blockers, "public_or_runtime_overclaim", child_trail, field=str(key), value=child)
            if (
                not non_claiming_guardrail_key
                and
                key_name not in FALSE_ONLY_KEYS
                and key_name not in CREDIT_ONLY_KEYS
                and broad_public_or_runtime_alias_key(key_name)
                and broad_public_or_runtime_alias_value_is_positive(key_name, child)
            ):
                reason = (
                    "accounting_credit_overclaim"
                    if broad_progress_or_credit_alias_key(key_name)
                    else "public_or_runtime_overclaim"
                )
                add(blockers, reason, child_trail, field=str(key), value=child)
            if (
                key_name in FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_KEYS
                and contains_forbidden_pre_runtime_claim_source(child)
            ):
                add(blockers, "pre_runtime_principal_or_authority_claim_source", child_trail, field=str(key), value=child)
            collect_overclaims(child, blockers, child_trail)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            collect_overclaims(child, blockers, f"{trail}[{index}]")
        return
    if (
        not isinstance(value, str)
        or trail.endswith(".schema")
        or trail.endswith(".surface")
        or trail.endswith(".id")
        or ".required_tests_before_public_header" in trail
    ):
        return
    if is_non_claim_artifact_list_context(trail) and normalized_key(value) in NON_AUTHORIZING_ROUTE_CONTEXT_TERMS:
        return
    if text_claim_path_is_exempt_metadata(trail):
        return
    if has_unnegated_public_abi_identity_lookup_handle_claim(value):
        add(blockers, "public_abi_identity_lookup_handle_claim", trail, value=value)
    if has_unnegated_accepted_runtime_evidence_skip_claim(value):
        add(blockers, "accepted_runtime_evidence_alias_skips_identity_public_contract_gate", trail, value=value)
    if is_negative_context(trail) and not is_claim_container_context(trail):
        return
    if has_unnegated_non_authorizing_route_claim(value):
        add(blockers, "positive_public_or_runtime_claim", trail, value=value)
    for match in POSITIVE_CLAIM_RE.finditer(value):
        if not positive_claim_is_negated(value, match):
            add(blockers, "positive_public_or_runtime_claim", trail, value=value)
            return


def collect_reason_flag_terms(value: Any, blockers: list[dict[str, Any]], trail: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if any(term in str(key) for term in REASON_FLAG_TERMS) and not is_reason_flag_allowed_path(child_trail):
                add(blockers, "authz_reason_flags_leaked_outside_diagnostic_containment", child_trail, value=str(key))
            collect_reason_flag_terms(child, blockers, child_trail)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            collect_reason_flag_terms(child, blockers, f"{trail}[{index}]")
        return
    if isinstance(value, str) and any(term in value for term in REASON_FLAG_TERMS) and not is_reason_flag_allowed_path(trail):
        add(blockers, "authz_reason_flags_leaked_outside_diagnostic_containment", trail, value=value)


def is_reason_flag_allowed_path(trail: str) -> bool:
    return any(fragment in trail for fragment in REASON_FLAG_ALLOWED_PATH_FRAGMENTS)


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


def validate_candidate_only_diagnostics(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    diagnostics = payload.get("candidate_only_diagnostics")
    if not isinstance(diagnostics, dict):
        add(blockers, "candidate_only_diagnostics_missing", "$.decisions.candidate_only_diagnostics")
        return
    authz = diagnostics.get("authz_reason_flags")
    if not isinstance(authz, dict):
        add(blockers, "authz_reason_flags_diagnostic_containment_missing", "$.decisions.candidate_only_diagnostics.authz_reason_flags")
        return
    for key, expected in REQUIRED_AUTHZ_REASON_FLAGS_DIAGNOSTIC.items():
        if authz.get(key) != expected:
            add(
                blockers,
                "authz_reason_flags_containment_field_mismatch",
                f"$.decisions.candidate_only_diagnostics.authz_reason_flags.{key}",
                expected=expected,
                value=authz.get(key),
            )


def validate_bridge_decisions(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    require_equal(payload, "schema", DECISIONS_SCHEMA, "$.decisions", blockers)
    require_equal(payload, "surface", SURFACE, "$.decisions", blockers)
    require_equal(payload, "status", "blocked", "$.decisions", blockers)
    require_equal(payload, "planning_stage", "planning_only_bridge_guardrail", "$.decisions", blockers)
    require_equal(payload, "planning_only", True, "$.decisions", blockers)
    for key in (
        "promotion_ready",
        "public_sdk_ready",
        "public_abi_ready",
        "runtime_ready",
        "public_header_allowed",
        "runtime_wiring_allowed",
        "server_validation_allowed",
    ):
        require_false(payload, key, "$.decisions", blockers)
    if payload.get("public_header_symbols_now") != []:
        add(blockers, "public_header_symbols_now_not_empty", "$.decisions.public_header_symbols_now")
    if payload.get("public_capability_bits_now") != []:
        add(blockers, "public_capability_bits_now_not_empty", "$.decisions.public_capability_bits_now")
    if payload.get("public_response_abi_now") != []:
        add(blockers, "public_response_abi_now_not_empty", "$.decisions.public_response_abi_now")
    if payload.get("depends_on_decision_docs") != DEPENDENCY_DOCS:
        add(blockers, "depends_on_decision_docs_mismatch", "$.decisions.depends_on_decision_docs")
    if payload.get("ordered_dependency_chain") != DEPENDENCY_CHAIN:
        add(blockers, "ordered_dependency_chain_mismatch", "$.decisions.ordered_dependency_chain")

    vocabulary = payload.get("shared_principal_vocabulary")
    if not isinstance(vocabulary, list):
        add(blockers, "shared_principal_vocabulary_not_list", "$.decisions.shared_principal_vocabulary")
    else:
        by_field = {item.get("field"): item for item in vocabulary if isinstance(item, dict)}
        if set(by_field) != set(SHARED_VOCABULARY):
            add(
                blockers,
                "shared_principal_vocabulary_fields_mismatch",
                "$.decisions.shared_principal_vocabulary",
                missing=sorted(set(SHARED_VOCABULARY) - set(by_field)),
                unexpected=sorted(set(by_field) - set(SHARED_VOCABULARY)),
            )
        for field in SHARED_VOCABULARY:
            item = by_field.get(field)
            if not isinstance(item, dict):
                continue
            if item.get("fail_closed_when_missing") is not True:
                add(blockers, "shared_principal_field_not_fail_closed", "$.decisions.shared_principal_vocabulary", field=field)
            meaning = item.get("required_meaning")
            if not isinstance(meaning, str) or field not in meaning:
                add(blockers, "shared_principal_meaning_missing_field", "$.decisions.shared_principal_vocabulary", field=field)

    missing_fail_closed = REQUIRED_FAIL_CLOSED - string_set(payload.get("required_fail_closed_conditions"))
    if missing_fail_closed:
        add(
            blockers,
            "required_fail_closed_conditions_missing",
            "$.decisions.required_fail_closed_conditions",
            missing=sorted(missing_fail_closed),
        )
    missing_behaviors = REQUIRED_BEHAVIORS - string_set(payload.get("required_bridge_behaviors"))
    if missing_behaviors:
        add(blockers, "required_bridge_behaviors_missing", "$.decisions.required_bridge_behaviors", missing=sorted(missing_behaviors))
    ergonomics_flow = payload.get("bridge_ergonomics_flow")
    if not isinstance(ergonomics_flow, list):
        add(blockers, "bridge_ergonomics_flow_not_list", "$.decisions.bridge_ergonomics_flow")
    else:
        by_step = {item.get("step"): item for item in ergonomics_flow if isinstance(item, dict)}
        observed_steps = [item.get("step") for item in ergonomics_flow if isinstance(item, dict)]
        if observed_steps != list(REQUIRED_BRIDGE_ERGONOMICS_STEPS):
            add(
                blockers,
                "bridge_ergonomics_flow_order_mismatch",
                "$.decisions.bridge_ergonomics_flow",
                expected=list(REQUIRED_BRIDGE_ERGONOMICS_STEPS),
                value=observed_steps,
            )
        for step in REQUIRED_BRIDGE_ERGONOMICS_STEPS:
            item = by_step.get(step)
            if not isinstance(item, dict):
                add(blockers, "bridge_ergonomics_flow_step_missing", "$.decisions.bridge_ergonomics_flow", step=step)
                continue
            boundary = item.get("required_boundary")
            if not isinstance(boundary, str) or not boundary:
                add(
                    blockers,
                    "bridge_ergonomics_flow_boundary_missing",
                    "$.decisions.bridge_ergonomics_flow",
                    step=step,
                )
                continue
            missing_fragments = sorted(
                fragment
                for fragment in REQUIRED_BRIDGE_ERGONOMICS_BOUNDARY_FRAGMENTS[step]
                if fragment not in boundary
            )
            if missing_fragments:
                add(
                    blockers,
                    "bridge_ergonomics_flow_boundary_incomplete",
                    "$.decisions.bridge_ergonomics_flow",
                    step=step,
                    missing=missing_fragments,
                )
    missing_forbidden = REQUIRED_FORBIDDEN - string_set(payload.get("forbidden_public_contract"))
    if missing_forbidden:
        add(blockers, "forbidden_public_contract_missing", "$.decisions.forbidden_public_contract", missing=sorted(missing_forbidden))
    forbidden_tokens = string_set(payload.get("public_header_forbidden_tokens"))
    if not forbidden_tokens:
        add(blockers, "public_header_forbidden_tokens_missing", "$.decisions.public_header_forbidden_tokens")
    missing_tokens = REQUIRED_PUBLIC_HEADER_FORBIDDEN_TOKENS - forbidden_tokens
    if missing_tokens:
        add(
            blockers,
            "public_header_forbidden_tokens_incomplete",
            "$.decisions.public_header_forbidden_tokens",
            missing=sorted(missing_tokens),
        )
    validate_candidate_only_diagnostics(payload, blockers)
    collect_reason_flag_terms(payload, blockers, "$.decisions")

    collect_overclaims(payload, blockers, "$.decisions")


def validate_source_doc(label: str, payload: dict[str, Any], expected_surface: str, blockers: list[dict[str, Any]]) -> None:
    expected_schema = SOURCE_SCHEMAS.get(label)
    if expected_schema is not None and payload.get("schema") != expected_schema:
        add(
            blockers,
            "source_doc_schema_mismatch",
            f"$.{label}.schema",
            expected=expected_schema,
            value=payload.get("schema"),
        )
    if payload.get("surface") != expected_surface:
        add(blockers, "source_doc_surface_mismatch", f"$.{label}.surface", expected=expected_surface, value=payload.get("surface"))
    if payload.get("status") in ("promoted", "ready"):
        add(blockers, "source_doc_unexpectedly_promoted", f"$.{label}.status", value=payload.get("status"))
    for key in ("public_header_allowed", "promotion_ready", "public_sdk_ready", "public_abi_ready", "runtime_ready"):
        if key in payload and payload.get(key) is not False:
            add(blockers, "source_doc_public_or_runtime_overclaim", f"$.{label}.{key}", value=payload.get(key))
    if payload.get("public_header_allowed") is not False:
        add(blockers, "source_doc_public_header_allowed_not_false", f"$.{label}.public_header_allowed", value=payload.get("public_header_allowed"))
    if payload.get("public_header_symbols_now") != []:
        add(
            blockers,
            "source_doc_public_header_symbols_now_not_empty",
            f"$.{label}.public_header_symbols_now",
            value=payload.get("public_header_symbols_now"),
        )
    for key in ("public_capability_bits_now", "public_callback_abi_now", "public_response_abi_now"):
        if key in payload and payload.get(key) != []:
            add(blockers, f"source_doc_{key}_not_empty", f"$.{label}.{key}", value=payload.get(key))

    flattened = "\n".join(collect_strings(payload))
    normalized_flattened = " ".join(flattened.split())
    for field in SHARED_VOCABULARY:
        if field not in flattened:
            add(blockers, "source_doc_missing_shared_principal_vocabulary", f"$.{label}", field=field)
    missing_semantics = sorted(
        fragment
        for fragment in REQUIRED_SOURCE_SEMANTICS.get(label, frozenset())
        if fragment not in normalized_flattened
    )
    if missing_semantics:
        add(
            blockers,
            "source_doc_missing_bridge_semantics",
            f"$.{label}",
            missing=missing_semantics,
        )
    collect_overclaims(payload, blockers, f"$.{label}")


def strip_c_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//.*", "", text)


def validate_public_header(path: Path, forbidden_tokens: set[str], blockers: list[dict[str, Any]]) -> None:
    try:
        header = without_native_prototype_symbols(
            strip_c_comments(path.read_text(encoding="utf-8")), header_only=True
        )
    except OSError as exc:
        add(blockers, "public_header_unreadable", "$.public_header", path=str(path), detail=str(exc))
        return
    observed = sorted(token for token in forbidden_tokens if public_header_has_token(header, token))
    if observed:
        add(blockers, "public_header_forbidden_symbols_present", "$.public_header", symbols=observed)


def public_header_has_token(header: str, token: str) -> bool:
    if token.endswith("_"):
        return re.search(rf"\b{re.escape(token)}", header) is not None
    return re.search(rf"\b{re.escape(token)}\b", header) is not None


def build_report(
    *,
    decisions_path: Path,
    source_paths: dict[str, tuple[str, Path]],
    public_header_path: Path,
) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    decisions = load_json(decisions_path, "decisions", blockers)
    source_payloads = {
        label: load_json(path, label, blockers)
        for label, (_, path) in source_paths.items()
    }
    source_hashes = source_artifact_hashes(
        decisions_path=decisions_path,
        source_paths=source_paths,
        public_header_path=public_header_path,
        blockers=blockers,
    )

    if decisions is not None:
        validate_bridge_decisions(decisions, blockers)
    for label, (expected_surface, _) in source_paths.items():
        payload = source_payloads.get(label)
        if payload is not None:
            validate_source_doc(label, payload, expected_surface, blockers)

    forbidden_tokens = REQUIRED_PUBLIC_HEADER_FORBIDDEN_TOKENS | (
        set(strings(decisions.get("public_header_forbidden_tokens"))) if isinstance(decisions, dict) else set()
    )
    validate_public_header(public_header_path, forbidden_tokens, blockers)

    valid = not blockers
    return {
        "schema": REPORT_SCHEMA,
        "valid": valid,
        "accepted_for_planning": valid,
        "planning_only": valid,
        "surface": SURFACE,
        "dependency_chain": DEPENDENCY_CHAIN,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "runtime_ready": False,
        "public_header_allowed": False,
        "public_capability_bits_now": [],
        "public_response_abi_now": [],
        "runtime_wiring_allowed": False,
        "server_validation_allowed": False,
        "bridge_claims_allowed": False,
        "non_claim": (
            "valid bridge output is planning-only and non-claim; it does not count as route acceptance, "
            "public runtime readiness, public ABI, runtime wiring, server validation, SDK readiness, or v1 completion"
        ),
        "decisions_path": str(decisions_path),
        "public_header_path": str(public_header_path),
        "source_decision_paths": {label: str(path) for label, (_, path) in source_paths.items()},
        "source_artifact_hashes": source_hashes,
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
    }


def main() -> int:
    args = parse_args()
    source_paths = {
        "player_identity": ("obelisk.player_identity.v1", args.player_identity),
        "permissions_admin": ("obelisk.permissions_admin.v1", args.permissions_admin),
        "command_response": ("obelisk.command_chat_response_path.v1", args.command_response),
        "commands_replies": ("obelisk.commands_replies.v1", args.commands_replies),
    }
    report = build_report(
        decisions_path=args.decisions,
        source_paths=source_paths,
        public_header_path=args.public_header,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
