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
SHARED_VOCABULARY = ("principal_handle", "principal_generation", "principal_scope_flags")
REQUIRED_FAIL_CLOSED = frozenset(
    (
        "missing principal_handle",
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
        "unknown permission authority",
        "permission deny result",
        "permission unknown result",
        "missing command_chat_response_path promotion",
        "missing commands_replies promotion",
    )
)
REQUIRED_BEHAVIORS = frozenset(
    (
        "principal_handle, principal_generation, and principal_scope_flags must appear together in any future command, permission, or response payload that consumes player identity",
        "principal_handle alone never authorizes",
        "permissions/admin cannot return allow from command text, operator config, plugin input, or missing runtime principal observation",
        "command/chat response targeting cannot create principal or permission claims",
        "commands/replies cannot dispatch when permission result is deny or unknown",
        "commands/replies cannot imply replies, send-chat, broadcast, moderation, storage, or admin mutation",
        "missing or zero plugin_owner_token fails closed for every future owner-token bridge operation",
        "missing capability fails closed and no capability bit is reserved by this bridge",
        "legacy CallProcessEvent debug access is not a command, reply, response, permission, or principal bridge",
        "ArkServerApi, ArkApi, AseApi, and NextGenPlugins names may inform demand only and cannot provide offsets, layouts, vtables, code, control flow, or ABI semantics",
    )
)
REQUIRED_FORBIDDEN = frozenset(
    (
        "public bridge ABI",
        "public header symbols",
        "public capability bits",
        "response ABI",
        "reply ABI",
        "send-chat ABI",
        "command router",
        "command parser",
        "permission cache ABI",
        "admin mutation",
        "principal or permission claims from command text",
        "principal or permission claims from operator config",
        "raw UE pointers",
        "raw ProcessEvent params",
        "raw FString storage",
        "FName/GObjects indices",
        "ResourceHandle",
        "player lookup",
        "mutation",
        "return override",
    )
)
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
    r"\b(blocked|cannot|does\s+not|fail[s-]?closed|forbidden|missing|must\s+not|no|not|planning|without)\b",
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
    missing_forbidden = REQUIRED_FORBIDDEN - string_set(payload.get("forbidden_public_contract"))
    if missing_forbidden:
        add(blockers, "forbidden_public_contract_missing", "$.decisions.forbidden_public_contract", missing=sorted(missing_forbidden))
    if not string_set(payload.get("public_header_forbidden_tokens")):
        add(blockers, "public_header_forbidden_tokens_missing", "$.decisions.public_header_forbidden_tokens")

    collect_overclaims(payload, blockers, "$.decisions")


def validate_source_doc(label: str, payload: dict[str, Any], expected_surface: str, blockers: list[dict[str, Any]]) -> None:
    if payload.get("surface") != expected_surface:
        add(blockers, "source_doc_surface_mismatch", f"$.{label}.surface", expected=expected_surface, value=payload.get("surface"))
    if payload.get("status") in ("promoted", "ready"):
        add(blockers, "source_doc_unexpectedly_promoted", f"$.{label}.status", value=payload.get("status"))
    for key in ("public_header_allowed", "promotion_ready", "public_sdk_ready", "public_abi_ready", "runtime_ready"):
        if key in payload and payload.get(key) is not False:
            add(blockers, "source_doc_public_or_runtime_overclaim", f"$.{label}.{key}", value=payload.get(key))

    flattened = "\n".join(collect_strings(payload))
    for field in SHARED_VOCABULARY:
        if field not in flattened:
            add(blockers, "source_doc_missing_shared_principal_vocabulary", f"$.{label}", field=field)
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
    observed = sorted(token for token in forbidden_tokens if re.search(rf"\b{re.escape(token)}\b", header))
    if observed:
        add(blockers, "public_header_forbidden_symbols_present", "$.public_header", symbols=observed)


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

    forbidden_tokens = set(strings(decisions.get("public_header_forbidden_tokens"))) if isinstance(decisions, dict) else set()
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
