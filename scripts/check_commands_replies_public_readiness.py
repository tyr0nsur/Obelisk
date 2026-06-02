#!/usr/bin/env python3
"""Validate commands/replies public-readiness stays candidate/planning-only."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import check_command_chat_response_public_readiness as response_path_readiness
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
DEPENDENCY_CHAIN = (
    "obelisk.player_identity.v1",
    "obelisk.permissions_admin.v1",
    RESPONSE_PATH_SURFACE,
    SURFACE,
)
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
        "plugin input",
        "command text",
        "operator config",
        "reply request",
        "send-chat request",
        "router metadata",
        "passive ChatMessageEvent",
        "raw ProcessEvent",
        "legacy CallProcessEvent",
    )
)
REQUIRED_NOT_SUFFICIENT = frozenset(
    (
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
REQUIRED_HEADER_ABSENT_TOKENS = frozenset(
    (
        "OBELISK_API_CAPABILITY_COMMANDS_REPLIES",
        "OBELISK_API_CAPABILITY_COMMAND_ROUTER",
        "OBELISK_API_CAPABILITY_CHAT_REPLIES",
        "OBELISK_API_CAPABILITY_SEND_CHAT",
        "OBELISK_API_CAPABILITY_COMMAND_CHAT_RESPONSE_PATH",
        "OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT_RESPONSE",
        "OBELISK_COMMANDS_REPLIES_ABI_VERSION",
        "OBELISK_COMMAND_ROUTER_ABI_VERSION",
        "OBELISK_COMMAND_CHAT_RESPONSE_ABI_VERSION",
        "ObeliskCommandRegistration",
        "ObeliskCommandCallback",
        "ObeliskCommandPayload",
        "ObeliskCommandParser",
        "ObeliskArkApiCommandParser",
        "ObeliskAseApiCommandParser",
        "ObeliskCommandReply",
        "ObeliskChatReply",
        "ObeliskSendChat",
        "RegisterCommandWithOwnerToken",
        "UnregisterCommandWithOwnerToken",
        "ReplyToCommandWithOwnerToken",
        "SendChatWithOwnerToken",
        "CallProcessEventCommandResponse",
        "CallProcessEventReply",
    )
)
FALSE_ONLY_KEYS = frozenset(
    (
        "arkapi_parser_copy_allowed",
        "aseapi_parser_copy_allowed",
        "call_process_event_response_allowed",
        "command_parser_allowed",
        "command_router_allowed",
        "commands_replies_ready",
        "parser_allowed",
        "promotion_ready",
        "public_abi_allowed",
        "public_abi_ready",
        "public_command_parser_allowed",
        "public_command_router_allowed",
        "public_header_allowed",
        "public_reply_api",
        "public_readiness_ready",
        "public_reply_abi_allowed",
        "public_reply_or_send_chat_abi_allowed",
        "public_response_path_allowed",
        "public_sdk_ready",
        "public_send_chat_api",
        "reply_send_chat_router_claims_allowed",
        "reply_api_allowed",
        "public_send_chat_abi_allowed",
        "reply_allowed",
        "runtime_delivery_allowed",
        "runtime_readiness_allowed",
        "runtime_ready",
        "send_chat_api_allowed",
        "send_chat_allowed",
        "v1_completion_evidence",
    )
)
NEGATIVE_CONTEXT_TOKENS = (
    "blocker",
    "blockers",
    "blocked",
    "decision_required",
    "exclusion",
    "exclusions",
    "forbidden",
    "not_sufficient",
    "non_claim",
    "promotion_requires",
    "required_evidence",
    "release_guardrails",
    "required_exclusions",
    "why_blocked",
)
NEGATED_CLAIM_RE = re.compile(
    r"\b(before|blocked|cannot|does\s+not|fail[s-]?closed|forbidden|future|must|must\s+be|must\s+not|"
    r"never|no|not|only|planning|post-v1|require[sd]?|unresolved|until|without)\b",
    re.IGNORECASE,
)
CLAIM_SCOPE_SPLIT_RE = re.compile(r"[.;:\n\r]|\s+\b(?:and|but|then|however|unless)\b\s+", re.IGNORECASE)
NEGATED_CLAIM_SUFFIX_RE = re.compile(
    r"^\s+(?:remains?|stays?|is|are)?\s*(?:blocked|not\s+(?:ready|enabled|authorized|allowed)|"
    r"unauthorized|unsupported|unresolved|.*\b(?:before|only|never|until|requires?)\b)",
    re.IGNORECASE,
)
POSITIVE_CLAIM_RE = re.compile(
    r"\b("
    r"arkapi\s+(?:command\s+)?parser|aseapi\s+(?:command\s+)?parser|"
    r"callprocessevent\s+(?:command|reply|response)|"
    r"command[_ -]?chat[_ -]?response[_ -]?path|"
    r"command[_ -]?parser|command[_ -]?rout(?:e|er|ing)|chat[_ -]?rout(?:e|er|ing)|router|"
    r"public\s+command\s+sdk|"
    r"repl(?:y|ies)(?:[_ -]?(?:abi|api|path|request))?|send[_ -]?chat(?:[_ -]?(?:abi|api|path|request))?"
    r")\b.{0,100}\b(allowed|available|copied|enabled|established|implemented|promoted|public|ready|supported)\b",
    re.IGNORECASE,
)
POSITIVE_CLAIM_REVERSED_RE = re.compile(
    r"\b(allowed|available|copied|enabled|established|implemented|promoted|public|ready|supported)\b"
    r".{0,100}\b("
    r"arkapi\s+(?:command\s+)?parser|aseapi\s+(?:command\s+)?parser|"
    r"callprocessevent\s+(?:command|reply|response)|"
    r"command[_ -]?chat[_ -]?response[_ -]?path|"
    r"command[_ -]?parser|command[_ -]?rout(?:e|er|ing)|chat[_ -]?rout(?:e|er|ing)|router|"
    r"public\s+command\s+sdk|"
    r"repl(?:y|ies)(?:[_ -]?(?:abi|api|path|request))?|send[_ -]?chat(?:[_ -]?(?:abi|api|path|request))?"
    r")\b",
    re.IGNORECASE,
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


def normalized_key(key: Any) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(key))
    return separated.casefold().replace("-", "_").replace(" ", "_")


def is_negative_context(trail: str) -> bool:
    lowered = trail.casefold()
    return any(token in lowered for token in NEGATIVE_CONTEXT_TOKENS)


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


def has_unnegated_positive_claim(text: str) -> bool:
    for clause in CLAIM_SCOPE_SPLIT_RE.split(text):
        for regex in (POSITIVE_CLAIM_RE, POSITIVE_CLAIM_REVERSED_RE):
            for match in regex.finditer(clause):
                if not claim_match_is_negated(clause, match):
                    return True
    return False


def collect_overclaims(value: Any, blockers: list[dict[str, Any]], trail: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if normalized_key(key) in FALSE_ONLY_KEYS and child is not False:
                add(blockers, "public_surface_overclaim", child_trail, field=str(key), value=child)
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
    if has_unnegated_positive_claim(value):
        add(blockers, "positive_public_surface_claim", trail, value=value)


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

    response_dep = by_id.get("dependency.promoted_command_chat_response_path", {})
    if response_dep.get("required_dependency") != RESPONSE_PATH_SURFACE:
        add(blockers, "response_path_dependency_mismatch", "$.decisions.required_before_public_header", value=response_dep.get("required_dependency"))
    response_behaviors = string_set(response_dep.get("required_behavior"))
    for required in (
        "commands/replies remains blocked while command_chat_response_path is unpromoted or unresolved",
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
    if RESPONSE_PATH_SURFACE in promoted:
        add(blockers, "response_path_planning_evidence_treated_as_promoted", "$.surfaces.promoted_surfaces")
        add(blockers, "command_chat_response_manifest_promotion_without_evidence", "$.surfaces.promoted_surfaces")
    if DEPENDENCY_CHAIN[0] in promoted:
        add(blockers, "player_identity_manifest_promotion_without_evidence", "$.surfaces.promoted_surfaces")
    if DEPENDENCY_CHAIN[1] in promoted:
        add(blockers, "permissions_admin_manifest_promotion_without_evidence", "$.surfaces.promoted_surfaces")

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
    if isinstance(identity, dict) and identity.get("status") in MANIFEST_PROMOTION_STATUSES:
        add(blockers, "player_identity_evidence_not_approved", "$.surfaces.surfaces[player_identity].status", status=identity.get("status"))
    if isinstance(permissions, dict) and permissions.get("status") in MANIFEST_PROMOTION_STATUSES:
        add(blockers, "permissions_admin_evidence_not_approved", "$.surfaces.surfaces[permissions_admin].status", status=permissions.get("status"))
    if isinstance(response_path, dict) and response_path.get("status") in MANIFEST_PROMOTION_STATUSES:
        add(
            blockers,
            "command_chat_response_evidence_not_approved",
            "$.surfaces.surfaces[command_chat_response_path].status",
            status=response_path.get("status"),
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
        if response_path.get("status") not in {"planning", "post-v1"}:
            add(
                blockers,
                "response_path_planning_evidence_treated_as_promoted",
                "$.surfaces.surfaces.status",
                expected=["planning", "post-v1"],
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
        header = strip_c_comments(resolved.read_text(encoding="utf-8"))
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
) -> None:
    schema = payload.get("schema")
    if schema == RESPONSE_PATH_REPORT_SCHEMA:
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
        resolved_source_artifacts: dict[str, Path] = {}
        if not missing_source_artifacts and not unverifiable_source_artifacts:
            for key in RESPONSE_PATH_SOURCE_ARTIFACT_KEYS:
                resolved = resolve_source_artifact_path(Path(payload[key]), key, blockers)
                if resolved is not None:
                    resolved_source_artifacts[key] = resolved
        if expected_root is None:
            add(blockers, "response_path_report_expected_root_required", "$.response_path_root")
        else:
            resolved_expected_root = resolve_expected_path(expected_root, "response_path_root", blockers)
            if resolved_expected_root is not None and payload.get("readiness_root") != str(resolved_expected_root):
                add(
                    blockers,
                    "response_path_report_readiness_root_mismatch",
                    "$.response_path_report.readiness_root",
                    expected=str(resolved_expected_root),
                    value=payload.get("readiness_root"),
                )
        if expected_readiness is None:
            add(blockers, "response_path_report_expected_readiness_required", "$.response_path_readiness")
        else:
            resolved_expected_readiness = resolve_expected_path(expected_readiness, "response_path_readiness", blockers)
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
        ):
            if payload.get(key) is not False:
                add(
                    blockers,
                    f"response_path_report_{key}_not_false",
                    f"$.response_path_report.{key}",
                    value=payload.get(key),
                )
        if len(resolved_source_artifacts) == len(RESPONSE_PATH_SOURCE_ARTIFACT_KEYS):
            if resolved_source_artifacts["decisions_path"] != response_path_readiness.DEFAULT_DECISIONS.resolve():
                add(
                    blockers,
                    "response_path_report_decisions_path_mismatch",
                    "$.response_path_report.decisions_path",
                    expected=str(response_path_readiness.DEFAULT_DECISIONS),
                    value=str(resolved_source_artifacts["decisions_path"]),
                )
            readiness_root = resolved_source_artifacts["readiness_path"].parent
            rebuilt = response_path_readiness.build_report(
                readiness_root,
                resolved_source_artifacts["readiness_path"],
                resolved_source_artifacts["decisions_path"],
                resolved_source_artifacts["public_header_path"],
                resolved_source_artifacts["surfaces_path"],
            )
            if rebuilt.get("valid") is not True or rebuilt.get("accepted_for_planning") is not True:
                add(
                    blockers,
                    "response_path_report_source_artifact_revalidation_failed",
                    "$.response_path_report",
                    rebuilt_blockers=rebuilt.get("blockers"),
                )
            for key in (
                "valid",
                "accepted_for_planning",
                "planning_only",
                "surface",
                "target_set",
                "target_filters",
                "readiness_root",
                "readiness_status",
                "decisions_status",
                "surfaces_status",
                "public_readiness_ready",
                "public_header_allowed",
                "promotion_ready",
                "public_sdk_ready",
                "public_abi_ready",
                "runtime_ready",
                "blockers",
            ):
                if payload.get(key) != rebuilt.get(key):
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
) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
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
    if surfaces is not None:
        validate_surfaces(surfaces, blockers)
    validate_public_header(public_header_path, blockers)
    if response_path_report is not None:
        validate_response_path_report(
            response_path_report,
            blockers,
            expected_root=response_path_root,
            expected_readiness=response_path_readiness,
            expected_surfaces=surfaces_path,
            expected_public_header=public_header_path,
        )

    valid = not blockers
    return {
        "schema": REPORT_SCHEMA,
        "valid": valid,
        "accepted_for_planning": valid,
        "planning_only": valid,
        "surface": SURFACE,
        "dependency_chain": list(DEPENDENCY_CHAIN),
        "public_readiness_ready": False,
        "public_abi_ready": False,
        "runtime_ready": False,
        "public_command_router_allowed": False,
        "public_reply_or_send_chat_abi_allowed": False,
        "public_response_path_allowed": False,
        "public_header_allowed": False,
        "decisions_path": str(decisions_path),
        "surfaces_path": str(surfaces_path),
        "public_header_path": str(public_header_path),
        "response_path_report_path": str(response_path_report_path) if response_path_report_path is not None else None,
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
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
