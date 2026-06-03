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
CURRENT_ROUTE_BLOCKER = "approved_runtime_evidence_missing"
ALLOWED_ROUTE_BLOCKERS = (
    "approved_runtime_evidence_missing",
)
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
        "plugin input",
        "command text",
        "operator config",
        "reply request",
        "send-chat request",
        "router metadata",
        "passive ChatMessageEvent",
        "raw ProcessEvent",
        "legacy CallProcessEvent",
        "static thunk orientation",
    )
)
REQUIRED_LAYOUT_RUNTIME_SDK_NOT_SUFFICIENT = frozenset(
    (
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
        "static thunk orientation",
        "minimal ChatMessageEvent callback registration",
        "generic chat routing",
        "raw ProcessEvent callbacks",
        "legacy CallProcessEvent debug gate",
    )
)
REQUIRED_PUBLIC_HEADER_FORBIDDEN_TOKENS = frozenset(
    (
        "OBELISK_API_CAPABILITY_COMMAND_CHAT_RESPONSE_PATH",
        "OBELISK_API_CAPABILITY_COMMAND_RESPONSE",
        "OBELISK_API_CAPABILITY_CHAT_RESPONSE",
        "OBELISK_API_CAPABILITY_CHAT_REPLIES",
        "OBELISK_API_CAPABILITY_CHAT_ROUTING",
        "OBELISK_API_CAPABILITY_CHAT_LOCAL_ROUTING",
        "OBELISK_API_CAPABILITY_COMMAND_REPLIES",
        "OBELISK_API_CAPABILITY_SEND_CHAT",
        "OBELISK_API_CAPABILITY_BROADCAST",
        "OBELISK_API_CAPABILITY_NOTICES",
        "OBELISK_API_CAPABILITY_MODERATION",
        "OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT_RESPONSE",
        "OBELISK_COMMAND_CHAT_RESPONSE_ABI_VERSION",
        "OBELISK_COMMAND_RESPONSE_ABI_VERSION",
        "OBELISK_CHAT_RESPONSE_ABI_VERSION",
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
        "command_router",
        "command_router_allowed",
        "broadcast_abi_allowed",
        "broadcast_allowed",
        "broadcast_api",
        "broadcast_api_allowed",
        "broadcast_ready",
        "chat_router",
        "chat_routing",
        "command_route_ready",
        "complete_sdk_claim_allowed",
        "complete_sdk_ready",
        "counts_toward_public_sdk",
        "counts_toward_runtime",
        "counts_toward_v1_completion",
        "accepted_runtime_evidence_ready",
        "admin_authority_ready",
        "capability_advertised",
        "capability_allowed",
        "capability_ready",
        "commands_unlocked",
        "full_sdk_claim_allowed",
        "full_sdk_ready",
        "generic_chat_router",
        "generic_chat_routing",
        "identity_contract_reviewed",
        "identity_public_contract_allowed",
        "identity_public_contract_ready",
        "identity_public_contract_reviewed",
        "identity_ready",
        "permission_admin_contract",
        "permission_header_allowed",
        "permission_ready",
        "permissions_admin_ready",
        "permissions_query_ready",
        "permissions_ready",
        "permissions_unlocked",
        "player_identity_contract",
        "player_identity_public_contract_ready",
        "player_identity_promotion_certificate_ready",
        "player_identity_ready",
        "principal_identity_ready",
        "principal_ready",
        "operator_approval_granted",
        "permissions_admin_route_ready",
        "production_sdk_claim_allowed",
        "production_sdk_ready",
        "promotion_certificate_ready",
        "promotion_ready",
        "public_or_runtime_accounting_allowed",
        "public_abi_allowed",
        "public_abi_ready",
        "public_bridge_abi_allowed",
        "public_capability_advertised",
        "public_capability_allowed",
        "public_capability_ready",
        "public_broadcast_abi_allowed",
        "public_broadcast_api",
        "public_broadcast_api_allowed",
        "public_chat_router",
        "public_chat_routing",
        "public_command_router",
        "public_command_router_allowed",
        "public_contract_allowed",
        "public_contract_ready",
        "public_contract_reviewed",
        "public_readiness_ready",
        "public_reply_or_send_chat_abi_allowed",
        "public_header_allowed",
        "public_header_ready",
        "public_headers_ready",
        "public_moderation_api",
        "public_moderation_api_allowed",
        "public_moderation_ready",
        "public_notice_abi_allowed",
        "public_notice_api",
        "public_notice_api_allowed",
        "public_notices_abi_allowed",
        "public_notices_api",
        "public_notices_api_allowed",
        "public_route_gate_ready",
        "public_route_ready",
        "public_response_path_allowed",
        "public_reply_abi_ready",
        "public_reply_abi_allowed",
        "public_reply_api",
        "public_response_abi_allowed",
        "reply_path_ready",
        "release_readiness_ready",
        "response_header_allowed",
        "generic_chat_routing_public_response_allowed",
        "minimal_chat_message_event_public_response_allowed",
        "raw_process_event_public_response_allowed",
        "static_thunk_orientation_public_response_allowed",
        "commands_replies_shortcut_public_response_allowed",
        "public_response_path_ready",
        "public_sdk",
        "public_sdk_ready",
        "public_send_chat_abi_allowed",
        "public_send_chat_api",
        "reply_send_chat_router_claims_allowed",
        "reply_allowed",
        "reply_api",
        "reply_api_allowed",
        "reply_abi_allowed",
        "route_ready",
        "route_gate_ready",
        "route_gate_unlocked",
        "route_readiness_ready",
        "router_ready",
        "moderation_allowed",
        "moderation_api",
        "moderation_api_allowed",
        "moderation_ready",
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
        "send_chat_allowed",
        "send_chat_api",
        "send_chat_api_allowed",
        "send_chat_ready",
        "server_operations_authorized",
        "stable_claim_allowed",
        "stable_sdk_claim_allowed",
        "stable_sdk_ready",
        "v1_0_stable_ready",
        "v1_completion_evidence",
        "v1_completion_ready",
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
    )
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
    "promotion_requires",
    "required_exclusions",
    "required_evidence",
    "stable_release_contract",
    "snapshot_prep_checks",
    "why_blocked",
)
POSITIVE_SURFACE_RE = re.compile(
    r"\b("
    r"accepted\s+runtime\s+evidence|admin\s+authority|"
    r"identity\s+(?:public\s+)?contract|player\s+identity\s+public\s+contract|promotion\s+certificate|"
    r"capability\s+bits?|public\s+(?:abi|capabilit(?:y|ies)|contract)|permission\s+headers?|"
    r"permissions?\s+quer(?:y|ies)|"
    r"public\s+headers?|runtime\s+(?:delivery|readiness|response\s+path|hooks?)|"
    r"(?:complete|full|production|stable)\s+sdk|public\s+(?:command\s+)?sdk(?:\s+readiness)?|"
    r"release\s+readiness|v1(?:\.0)?\s+stable|v1\s+(?:sdk\s+)?completion|"
    r"repl(?:y|ies)(?:\s+(?:api|abi|endpoint|path|request))?|send[- ]?chat(?:\s+(?:api|abi|endpoint|path|request))?|"
    r"broadcast(?:/notices?|[- ]?notices?)?(?:\s+(?:api|abi|endpoint|path|request|scheduler|service))?|"
    r"notices?(?:\s+(?:api|abi|endpoint|path|request|scheduler|service))?|moderation(?:\s+(?:api|abi|endpoint|path|request|authority))?|"
    r"command\s+response\s+path|command\s+rout(?:e|er|ing)|chat\s+rout(?:e|er|ing)|generic\s+chat\s+rout(?:e|er|ing)|router|"
    r"route\s+gate|"
    r"player\s+identity|principal\s+identity|permissions?(?:/admin)?"
    r")\b.{0,80}\b(accepted|advertised|allowed|available|enabled|established|live|opened|operational|promoted|public|ready|reviewed|supported|unlocked)\b",
    re.IGNORECASE,
)
POSITIVE_SURFACE_REVERSED = re.compile(
    r"\b(accepted|advertised|allowed|available|enabled|established|live|opened|operational|promoted|public|ready|reviewed|supported|unlocked)\b"
    r".{0,80}\b("
    r"accepted\s+runtime\s+evidence|admin\s+authority|"
    r"identity\s+(?:public\s+)?contract|player\s+identity\s+public\s+contract|promotion\s+certificate|"
    r"capability\s+bits?|public\s+(?:abi|capabilit(?:y|ies)|contract|headers?|sdk)|permission\s+headers?|"
    r"permissions?\s+quer(?:y|ies)|runtime\s+(?:delivery|readiness|response\s+path|hooks?)|"
    r"(?:complete|full|production|stable)\s+sdk|release\s+readiness|v1(?:\.0)?\s+stable|"
    r"v1\s+(?:sdk\s+)?completion|repl(?:y|ies)(?:\s+(?:api|abi|endpoint|path|request))?|"
    r"send[- ]?chat(?:\s+(?:api|abi|endpoint|path|request))?|"
    r"broadcast(?:/notices?|[- ]?notices?)?(?:\s+(?:api|abi|endpoint|path|request|scheduler|service))?|"
    r"notices?(?:\s+(?:api|abi|endpoint|path|request|scheduler|service))?|"
    r"moderation(?:\s+(?:api|abi|endpoint|path|request|authority))?|"
    r"command\s+response\s+path|command\s+rout(?:e|er|ing)|chat\s+rout(?:e|er|ing)|generic\s+chat\s+rout(?:e|er|ing)|"
    r"router|route\s+gate|player\s+identity|principal\s+identity|permissions?(?:/admin)?"
    r")\b",
    re.IGNORECASE,
)
NEGATED_CLAIM_RE = re.compile(
    r"\b(before|blocked|cannot|candidate|does\s+not|fail[s-]?closed|forbidden|future|must|must\s+be|need[s]?|"
    r"never|no|not|only|planning|require[sd]?|until|without)\b",
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


def contains_fragment(haystack: str, needle: str) -> bool:
    return needle.casefold() in haystack.casefold()


def normalized_key(key: Any) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(key))
    return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")


def is_positive_claim_value(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        normalized = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
        return normalized in {
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


def negative_context(trail: str) -> bool:
    lowered = trail.casefold()
    return any(token in lowered for token in NEGATIVE_CONTEXT_TOKENS)


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


def preceding_claim_scope(text: str, start: int) -> str:
    parts = CLAIM_SCOPE_SPLIT_RE.split(text[:start])
    return parts[-1] if parts else text[:start]


def claim_match_is_negated(text: str, match: re.Match[str]) -> bool:
    if NEGATED_CLAIM_RE.search(match.group(0)):
        return True
    if NEGATED_CLAIM_RE.search(preceding_claim_scope(text, match.start())):
        return True
    return bool(NEGATED_CLAIM_SUFFIX_RE.match(text[match.end() :]))


def has_unnegated_positive_surface_claim(text: str) -> bool:
    for clause in CLAIM_SCOPE_SPLIT_RE.split(text):
        for regex in (POSITIVE_SURFACE_RE, POSITIVE_SURFACE_REVERSED):
            for match in regex.finditer(clause):
                if not claim_match_is_negated(clause, match):
                    return True
    return False


def c_identifier_exact_re(token: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9_]){re.escape(token)}(?![A-Za-z0-9_])")


def c_identifier_prefix_re(prefix: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9_]){re.escape(prefix)}[A-Za-z0-9_]*")


def collect_surface_overclaims(value: Any, blockers: list[dict[str, Any]], trail: str = "$") -> None:
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
            if claim_key in FALSE_ONLY_KEYS and any(is_positive_claim_value(item) for item in declared_claim_values):
                add(blockers, "public_surface_overclaim", trail, field=claim_name, value=value)
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if normalized_key(key) in FALSE_ONLY_KEYS and child is not False:
                add(blockers, "public_surface_overclaim", child_trail, field=str(key), value=child)
            collect_surface_overclaims(child, blockers, child_trail)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            collect_surface_overclaims(child, blockers, f"{trail}[{index}]")
        return
    if not isinstance(value, str) or (negative_context(trail) and not is_claim_container_context(trail)):
        return
    if has_unnegated_positive_surface_claim(value):
        add(blockers, "positive_public_surface_claim", trail, value=value)


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


def source_artifact_hashes(paths: dict[str, Path]) -> dict[str, str | None]:
    return {key: sha256_file(path) for key, path in paths.items()}


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
    for required in (
        "command text cannot establish principal identity",
        "operator config enables surfaces only and cannot establish principal identity",
        "response delivery never creates identity or permission claims",
        "minimal ChatMessageEvent, raw ProcessEvent, legacy CallProcessEvent, and static thunk orientation cannot establish principal identity",
        "generic chat routing cannot establish principal identity",
        "chat intake, send mode, passive parsing, command text, and chat snapshots cannot establish principal identity or roadmap priority",
        "commands/replies planning cannot bypass identity promotion",
    ):
        if required not in behaviors:
            add(blockers, "identity_dependency_behavior_missing", "$.decisions.required_before_public_header", behavior=required)

    permissions = by_id.get("dependency.promoted_permissions_admin", {})
    permission_behaviors = string_set(permissions.get("required_behavior"))
    for required in (
        "permissions/admin must be promoted before any reply, send-chat, broadcast, or moderation delivery is public",
        "minimal ChatMessageEvent, raw ProcessEvent, legacy CallProcessEvent, and static thunk orientation cannot establish permissions or admin authority",
        "generic chat routing cannot establish permissions or admin authority",
        "chat intake, send mode, passive parsing, command text, and chat snapshots cannot establish permissions, targeting, command authority, moderation authority, or roadmap priority",
        "commands/replies planning cannot bypass permissions/admin promotion",
        "runtime-owned permissions/admin allow for the same runtime-owned principal tuple is required before any reply, send-chat, broadcast, moderation, or router response path is public",
    ):
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
        text = strip_c_comments(resolved.read_text(encoding="utf-8"))
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


def validate_surfaces(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    require_equal(payload, "schema", SURFACES_SCHEMA, "$.surfaces", blockers)
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
    if set(response.get("depends_on", [])) != {IDENTITY_SURFACE, PERMISSIONS_SURFACE}:
        add(
            blockers,
            "command_chat_response_surface_dependencies_mismatch",
            "$.surfaces.command_chat_response_path.depends_on",
            value=response.get("depends_on"),
        )
    promoted = string_set(payload.get("promoted_surfaces"))
    if IDENTITY_SURFACE in promoted:
        add(blockers, "player_identity_manifest_promotion_without_evidence", "$.surfaces.promoted_surfaces")
    if PERMISSIONS_SURFACE in promoted:
        add(blockers, "permissions_admin_manifest_promotion_without_evidence", "$.surfaces.promoted_surfaces")
    if isinstance(identity, dict) and identity.get("status") in MANIFEST_PROMOTION_STATUSES:
        add(blockers, "player_identity_evidence_not_approved", "$.surfaces.player_identity.status", status=identity.get("status"))
    if isinstance(permissions, dict) and permissions.get("status") in MANIFEST_PROMOTION_STATUSES:
        add(blockers, "permissions_admin_evidence_not_approved", "$.surfaces.permissions_admin.status", status=permissions.get("status"))
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
    if surfaces is not None:
        validate_surfaces(surfaces, blockers)
    validate_public_header(public_header_path, blockers)
    if current_route_blocker != CURRENT_ROUTE_BLOCKER:
        add(
            blockers,
            "current_route_blocker_mismatch",
            "$.current_route_blocker",
            expected=CURRENT_ROUTE_BLOCKER,
            value=current_route_blocker,
        )

    valid = not blockers
    return {
        "schema": REPORT_SCHEMA,
        "valid": valid,
        "accepted_for_planning": valid,
        "planning_only": valid,
        "dependency_chain": DEPENDENCY_CHAIN,
        "dependency_chain_locked": True,
        "current_route_blocker": CURRENT_ROUTE_BLOCKER,
        "remaining_route_blockers": [CURRENT_ROUTE_BLOCKER],
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "public_or_runtime_accounting_allowed": False,
        "public_readiness_ready": False,
        "public_header_allowed": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "runtime_ready": False,
        "non_claim": (
            "valid planning output does not count command/chat response while player identity remains "
            f"blocked on {CURRENT_ROUTE_BLOCKER}"
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
