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


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_DECISIONS = REPO_ROOT / "docs" / "commands_replies_public_contract_decisions.json"
DEFAULT_SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
DEFAULT_PUBLIC_HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"

REPORT_SCHEMA = "obelisk.commands-replies-public-readiness-check.v1"
DECISIONS_SCHEMA = "obelisk.commands-replies-public-contract-decisions.v1"
SURFACES_SCHEMA = "obelisk.public-sdk-surfaces.v1"
RESPONSE_PATH_REPORT_SCHEMA = "obelisk.command-chat-response-public-readiness-check.v1"
RESPONSE_PATH_READINESS_SCHEMA = "obelisk.reflection-snapshot-readiness.v1"
SURFACE = "obelisk.commands_replies.v1"
RESPONSE_PATH_SURFACE = "obelisk.command_chat_response_path.v1"
DEPENDENCY_CHAIN = (
    "obelisk.player_identity.v1",
    "obelisk.permissions_admin.v1",
    RESPONSE_PATH_SURFACE,
    SURFACE,
)
REQUIRED_DEPENDS_ON = list(DEPENDENCY_CHAIN[:-1])
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
        "public command_chat_response_path ABI",
        "reply ABI",
        "send-chat ABI",
        "principal or permission claims from command text",
        "principal or permission claims from operator config",
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
        "principal_handle, principal_generation, and principal_scope_flags must appear together in any future command payload that consumes player identity",
        "principal_handle alone never authorizes command dispatch",
        "missing principal fails closed",
        "missing principal_handle fails closed",
        "missing principal_generation fails closed",
        "missing principal_scope_flags fails closed",
        "stale principal fails closed",
        "unsupported principal_scope_flags fails closed",
        "missing permission policy provenance fails closed",
        "permission denial or unknown result never dispatches a command",
        "command text remains copied request data only and cannot establish identity, permission authority, or policy provenance",
        "operator config remains policy input only and cannot establish command identity, principal identity, permission authority, or policy provenance",
        "command callbacks cannot self-attest permission authority",
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
        "public_abi_ready",
        "public_command_parser_allowed",
        "public_command_router_allowed",
        "public_header_allowed",
        "public_readiness_ready",
        "public_reply_abi_allowed",
        "public_reply_or_send_chat_abi_allowed",
        "public_response_path_allowed",
        "public_sdk_ready",
        "public_send_chat_abi_allowed",
        "reply_allowed",
        "runtime_ready",
        "send_chat_allowed",
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
    "release_guardrails",
    "required",
    "required_behavior",
    "required_exclusions",
    "why_blocked",
)
NEGATED_CLAIM_RE = re.compile(
    r"\b(blocked|cannot|does\s+not|fail[s-]?closed|forbidden|must\s+not|no|not|planning|"
    r"post-v1|require[sd]?|unresolved|until|without)\b",
    re.IGNORECASE,
)
POSITIVE_CLAIM_RE = re.compile(
    r"\b("
    r"arkapi\s+(?:command\s+)?parser|aseapi\s+(?:command\s+)?parser|"
    r"callprocessevent\s+(?:command|reply|response)|"
    r"command[_ -]?chat[_ -]?response[_ -]?path|"
    r"command[_ -]?parser|command[_ -]?router|public\s+command\s+sdk|"
    r"repl(?:y|ies)(?:[_ -]?abi|[_ -]?api)?|send[_ -]?chat(?:[_ -]?abi|[_ -]?api)?"
    r")\b.{0,100}\b(allowed|available|copied|enabled|established|implemented|promoted|public|ready|supported)\b",
    re.IGNORECASE,
)
POSITIVE_CLAIM_REVERSED_RE = re.compile(
    r"\b(allowed|available|copied|enabled|established|implemented|promoted|public|ready|supported)\b"
    r".{0,100}\b("
    r"arkapi\s+(?:command\s+)?parser|aseapi\s+(?:command\s+)?parser|"
    r"callprocessevent\s+(?:command|reply|response)|"
    r"command[_ -]?chat[_ -]?response[_ -]?path|"
    r"command[_ -]?parser|command[_ -]?router|public\s+command\s+sdk|"
    r"repl(?:y|ies)(?:[_ -]?abi|[_ -]?api)?|send[_ -]?chat(?:[_ -]?abi|[_ -]?api)?"
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
        help="Optional command/chat response readiness report or raw planning-readiness JSON.",
    )
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


def normalized_key(key: Any) -> str:
    return str(key).casefold().replace("-", "_").replace(" ", "_")


def is_negative_context(trail: str) -> bool:
    lowered = trail.casefold()
    return any(token in lowered for token in NEGATIVE_CONTEXT_TOKENS)


def strip_c_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//.*", "", text)


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
    if (POSITIVE_CLAIM_RE.search(value) or POSITIVE_CLAIM_REVERSED_RE.search(value)) and not NEGATED_CLAIM_RE.search(value):
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


def validate_decisions(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    require_equal(payload, "schema", DECISIONS_SCHEMA, "$.decisions", blockers)
    require_equal(payload, "surface", SURFACE, "$.decisions", blockers)
    require_equal(payload, "status", "blocked", "$.decisions", blockers)
    require_equal(payload, "planning_stage", "v1_completion_blocker", "$.decisions", blockers)
    require_equal(payload, "not_sufficient_for_v1", True, "$.decisions", blockers)
    require_false(payload, "public_header_allowed", "$.decisions", blockers)
    require_false(payload, "public_command_router_allowed", "$.decisions", blockers)
    require_false(payload, "public_reply_or_send_chat_abi_allowed", "$.decisions", blockers)
    require_false(payload, "public_response_path_allowed", "$.decisions", blockers)
    if payload.get("public_header") != "include/obelisk/ObeliskApi.h":
        add(blockers, "public_header_mismatch", "$.decisions.public_header", value=payload.get("public_header"))
    if payload.get("public_header_symbols_now") != []:
        add(
            blockers,
            "public_header_symbols_now_not_empty",
            "$.decisions.public_header_symbols_now",
            value=payload.get("public_header_symbols_now"),
        )
    if payload.get("public_contract", []) != []:
        add(blockers, "public_contract_not_empty", "$.decisions.public_contract", value=payload.get("public_contract"))

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

    post_v1_or_excluded = string_set(payload.get("post_v1_or_excluded_surfaces"))
    if SURFACE not in post_v1_or_excluded:
        add(blockers, "commands_replies_missing_from_post_v1_or_excluded", "$.surfaces.post_v1_or_excluded_surfaces")
    if RESPONSE_PATH_SURFACE not in post_v1_or_excluded:
        add(blockers, "response_path_missing_from_post_v1_or_excluded", "$.surfaces.post_v1_or_excluded_surfaces")

    blockers_set = string_set(payload.get("v1_sdk_completion_blockers"))
    for surface in DEPENDENCY_CHAIN:
        if surface not in blockers_set and surface not in post_v1_or_excluded:
            add(blockers, "dependency_chain_surface_missing_from_blockers_or_post_v1", "$.surfaces", surface=surface)

    surfaces = payload.get("surfaces")
    if not isinstance(surfaces, list):
        add(blockers, "surfaces_not_list", "$.surfaces.surfaces")
        collect_overclaims(payload, blockers, "$.surfaces")
        return
    by_id = {item.get("id"): item for item in surfaces if isinstance(item, dict) and isinstance(item.get("id"), str)}
    commands = by_id.get(SURFACE)
    response_path = by_id.get(RESPONSE_PATH_SURFACE)
    if not isinstance(commands, dict):
        add(blockers, "commands_replies_surface_missing", "$.surfaces.surfaces")
    else:
        if commands.get("status") != "post-v1":
            add(blockers, "commands_replies_status_mismatch", "$.surfaces.surfaces", value=commands.get("status"))
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
        if response_path.get("status") != "post-v1":
            add(blockers, "response_path_planning_evidence_treated_as_promoted", "$.surfaces.surfaces.status")
        if response_path.get("public_contract") not in ([], None) and response_path.get("status") != "promoted":
            add(blockers, "response_path_public_contract_not_empty_while_unpromoted", "$.surfaces.surfaces.public_contract")

    guardrails = "\n".join(strings(payload.get("release_guardrails")))
    for fragment in (
        "Identity/principal, permissions/admin, command/chat response path, and commands/replies are an ordered v1 dependency chain",
        "Commands/replies also depend on obelisk.command_chat_response_path.v1",
        "command/chat response path is post-v1, no reply, send-chat, broadcast/notices, moderation, or public CallProcessEvent path may be documented as promoted",
        "legacy CallProcessEvent debug access are not public response-path or command/reply promotion evidence",
    ):
        if fragment not in guardrails:
            add(blockers, "release_guardrail_missing", "$.surfaces.release_guardrails", fragment=fragment)

    collect_overclaims(payload, blockers, "$.surfaces")


def validate_public_header(path: Path, blockers: list[dict[str, Any]]) -> None:
    try:
        header = strip_c_comments(path.read_text(encoding="utf-8"))
    except OSError as exc:
        add(blockers, "public_header_unreadable", "$.public_header", path=str(path), detail=str(exc))
        return
    observed = sorted(token for token in REQUIRED_HEADER_ABSENT_TOKENS if re.search(rf"\b{re.escape(token)}\b", header))
    if observed:
        add(blockers, "public_header_forbidden_symbols_present", "$.public_header", symbols=observed)


def validate_response_path_report(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    schema = payload.get("schema")
    if schema == RESPONSE_PATH_REPORT_SCHEMA:
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
    elif schema == RESPONSE_PATH_READINESS_SCHEMA:
        response_path_readiness.validate_readiness(payload, blockers)
    else:
        add(blockers, "response_path_report_schema_mismatch", "$.response_path_report.schema", value=schema)
    collect_overclaims(payload, blockers, "$.response_path_report")


def build_report(
    *,
    decisions_path: Path,
    surfaces_path: Path,
    public_header_path: Path,
    response_path_report_path: Path | None,
) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    decisions = load_json(decisions_path, "decisions", blockers)
    surfaces = load_json(surfaces_path, "surfaces", blockers)
    response_path_report = (
        load_json(response_path_report_path, "response_path_report", blockers)
        if response_path_report_path is not None
        else None
    )

    if decisions is not None:
        validate_decisions(decisions, blockers)
    if surfaces is not None:
        validate_surfaces(surfaces, blockers)
    validate_public_header(public_header_path, blockers)
    if response_path_report is not None:
        validate_response_path_report(response_path_report, blockers)

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
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
