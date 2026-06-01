#!/usr/bin/env python3
"""Validate the command/principal/authz/response bridge stays planning-only."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


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
        "promotion_ready",
        "public_sdk_ready",
        "public_abi_ready",
        "runtime_ready",
        "public_header_allowed",
        "runtime_wiring_allowed",
        "server_validation_allowed",
        "public_bridge_abi_allowed",
        "public_command_router_allowed",
        "public_reply_or_send_chat_abi_allowed",
        "public_response_path_allowed",
        "public_response_abi_allowed",
        "response_abi_allowed",
        "capability_bit_allowed",
    )
)
NEGATIVE_CONTEXT_TOKENS = (
    "blocked",
    "fail_closed",
    "forbidden",
    "non_claim",
    "required",
    "public_header_forbidden_tokens",
)
POSITIVE_CLAIM_RE = re.compile(
    r"\b("
    r"bridge|capability|command[_ -]?router|commands?/replies|permissions?/admin|"
    r"player[_ -]?identity|principal|reply|response|send[_ -]?chat"
    r")\b.{0,90}\b(allowed|available|enabled|implemented|promoted|public|ready|runtime)\b",
    re.IGNORECASE,
)
NEGATED_CLAIM_RE = re.compile(
    r"\b(blocked|cannot|does\s+not|fail[s-]?closed|forbidden|missing|must\s+not|never|no|not|planning|until|without)\b",
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
        payload = json.loads(path.read_text(encoding="utf-8"))
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


def strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def string_set(value: Any) -> set[str]:
    return set(strings(value))


def normalized_key(value: Any) -> str:
    return str(value).casefold().replace("-", "_").replace(" ", "_")


def is_negative_context(trail: str) -> bool:
    lowered = trail.casefold()
    return any(token in lowered for token in NEGATIVE_CONTEXT_TOKENS)


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


def collect_overclaims(value: Any, blockers: list[dict[str, Any]], trail: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if normalized_key(key) in FALSE_ONLY_KEYS and child is not False:
                add(blockers, "public_or_runtime_overclaim", child_trail, field=str(key), value=child)
            collect_overclaims(child, blockers, child_trail)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            collect_overclaims(child, blockers, f"{trail}[{index}]")
        return
    if (
        not isinstance(value, str)
        or is_negative_context(trail)
        or trail.endswith(".schema")
        or trail.endswith(".surface")
        or trail.endswith(".id")
    ):
        return
    if POSITIVE_CLAIM_RE.search(value) and NEGATED_CLAIM_RE.search(value) is None:
        add(blockers, "positive_public_or_runtime_claim", trail, value=value)


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
        header = strip_c_comments(path.read_text(encoding="utf-8"))
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
        "decisions_path": str(decisions_path),
        "public_header_path": str(public_header_path),
        "source_decision_paths": {label: str(path) for label, (_, path) in source_paths.items()},
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
