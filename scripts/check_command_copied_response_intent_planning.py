#!/usr/bin/env python3
"""Validate command copied-response-intent planning stays non-public and fail-closed."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import check_permissions_admin_public_readiness as permissions_readiness
import check_permissions_admin_query_failclosed_contract as query_failclosed_contract
from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_DECISIONS = REPO_ROOT / "docs" / "command_copied_response_intent_planning_decisions.json"
DEFAULT_COMMAND_RESPONSE_DECISIONS = REPO_ROOT / "docs" / "command_chat_response_public_contract_decisions.json"
DEFAULT_BRIDGE_DECISIONS = REPO_ROOT / "docs" / "command_principal_authz_response_bridge_decisions.json"
DEFAULT_COMMANDS_REPLIES_DECISIONS = REPO_ROOT / "docs" / "commands_replies_public_contract_decisions.json"
DEFAULT_PERMISSIONS_DECISIONS = REPO_ROOT / "docs" / "permissions_admin_public_contract_decisions.json"
DEFAULT_SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
DEFAULT_PUBLIC_HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"

REPORT_SCHEMA = "obelisk.command-copied-response-intent-planning-check.v1"
DECISIONS_SCHEMA = "obelisk.command-copied-response-intent-planning-decisions.v1"
COMMAND_RESPONSE_SCHEMA = "obelisk.command-chat-response-public-contract-decisions.v1"
BRIDGE_SCHEMA = "obelisk.command-principal-authz-response-bridge-decisions.v1"
COMMANDS_REPLIES_SCHEMA = "obelisk.commands-replies-public-contract-decisions.v1"
PERMISSIONS_SCHEMA = "obelisk.permissions-admin-public-contract-decisions.v1"
SURFACES_SCHEMA = "obelisk.public-sdk-surfaces.v1"
QUERY_CONTRACT_SCHEMA = "obelisk.permissions-admin-query-failclosed-contract.v1"
QUERY_CONTRACT_REPORT_SCHEMA = "obelisk.permissions-admin-query-failclosed-contract-check.v1"
SURFACE = "obelisk.command_copied_response_intent.planning.v1"
COMMAND_RESPONSE_SURFACE = "obelisk.command_chat_response_path.v1"
COMMANDS_REPLIES_SURFACE = "obelisk.commands_replies.v1"
PERMISSIONS_SURFACE = "obelisk.permissions_admin.v1"
IDENTITY_SURFACE = "obelisk.player_identity.v1"

FALSE_KEYS = (
    "promotion_ready",
    "public_sdk_ready",
    "public_abi_ready",
    "runtime_ready",
    "public_header_allowed",
    "reply_api_allowed",
    "send_chat_api_allowed",
    "command_router_allowed",
    "runtime_delivery_allowed",
)
EMPTY_ARRAY_KEYS = (
    "public_header_symbols_now",
    "public_capability_bits_now",
    "public_response_abi_now",
)
REQUIRED_DEPENDS_ON = frozenset(
    (IDENTITY_SURFACE, PERMISSIONS_SURFACE, COMMAND_RESPONSE_SURFACE)
)
REQUIRED_DECISION_DOCS = frozenset(
    (
        "docs/command_chat_response_public_contract_decisions.json",
        "docs/command_principal_authz_response_bridge_decisions.json",
        "docs/commands_replies_public_contract_decisions.json",
        "docs/permissions_admin_public_contract_decisions.json",
    )
)
REQUIRED_INTENT_FIELDS = (
    "intent_version",
    "intent_size",
    "plugin_owner_token",
    "response_intent_handle",
    "principal_handle",
    "principal_generation",
    "principal_scope_flags",
    "permission_policy_epoch",
    "policy_source_id",
    "policy_source_generation",
    "authority_kind",
    "authority_generation",
    "source_kind",
    "response_intent_kind",
    "message_utf8",
    "message_size",
    "message_encoding",
    "intent_scope_flags",
    "intent_flags",
    "rate_limit_class",
    "audit_correlation_id",
    "redaction_flags",
)
REQUIRED_INTENT_PROPERTIES = frozenset(
    (
        "intent field names are planning vocabulary only and are not a public struct",
        "message_utf8 is copied plugin intent text only",
        "message_utf8 is not FString storage, not raw UE text, not ChatMessageEvent storage, and not a delivery request",
        "principal_handle, principal_generation, and principal_scope_flags must appear together",
        "permission allow requires policy_source_id, policy_source_generation, authority_kind, authority_generation, and permission_policy_epoch provenance",
        "plugin_owner_token must be nonzero and owner-scoped",
        "response_intent_handle is process-local and owner-scoped",
        "redaction_flags and audit_correlation_id are required before any future delivery contract",
        "this planning contract cannot reserve a public capability bit or ABI version",
    )
)
REQUIRED_FAIL_CLOSED = frozenset(
    (
        "missing plugin_owner_token",
        "zero plugin_owner_token",
        "missing principal_handle",
        "missing principal_generation",
        "missing principal_scope_flags",
        "stale principal",
        "principal_generation mismatch",
        "principal_scope_flags mismatch",
        "process mismatch",
        "identity inferred from command text",
        "identity inferred from operator config",
        "identity inferred from passive chat",
        "identity inferred from raw ProcessEvent",
        "identity inferred from static thunk orientation",
        "identity inferred from legacy CallProcessEvent",
        "permission deny",
        "permission unknown",
        "missing permission_policy_epoch",
        "missing policy_source_id",
        "missing policy_source_generation",
        "missing authority_kind",
        "missing authority_generation",
        "policy provenance supplied by plugin",
        "policy provenance supplied by command text",
        "malformed message_utf8",
        "message contains NUL",
        "message_size mismatch",
        "message_size exceeds limit",
        "unknown source_kind",
        "unknown response_intent_kind",
        "unknown intent_scope_flags",
        "unknown intent_flags",
        "rate limit exceeded",
        "audit records missing",
        "redaction flags missing",
        "audit or logs expose player names",
        "audit or logs expose platform ids",
        "audit or logs expose UE pointers",
        "audit or logs expose FName/GObjects",
        "audit or logs expose raw params",
        "audit or logs expose raw FString",
        "ChatMessageEvent treated as delivery authorization",
        "generic chat routing treated as delivery authorization",
        "commands/replies planning treated as delivery authorization",
        "static thunk orientation treated as delivery authorization",
        "legacy CallProcessEvent treated as delivery authorization",
        "reply API claim",
        "send-chat API claim",
        "broadcast API claim",
        "moderation API claim",
        "storage claim",
        "mutation claim",
        "return override claim",
    )
)
REQUIRED_NON_CLAIMS = frozenset(
    (
        "planning-only copied response intent vocabulary",
        "does not add public headers, capability bits, response ABI, reply API, send-chat API, command router, chat router, runtime delivery, moderation, storage, mutation, return override, ResourceHandle, UE pointers, raw params, raw FString, or public SDK readiness",
        "does not authorize runtime observation, server operations, Discord updates, GitHub publication, tags, release claims, or v1 SDK completion",
        "does not bypass promoted player identity, permissions/admin, or command_chat_response_path",
    )
)
DEFAULT_FORBIDDEN_HEADER_TOKENS = frozenset(
    (
        "OBELISK_API_CAPABILITY_COMMAND_COPIED_RESPONSE_INTENT",
        "OBELISK_COMMAND_COPIED_RESPONSE_INTENT_ABI_VERSION",
        "ObeliskCommandCopiedResponseIntent",
        "RegisterCommandCopiedResponseIntent",
    )
)
POSITIVE_CLAIM_RE = re.compile(
    r"\b(reply|send[- ]?chat|command router|chat router|runtime delivery|public abi|public sdk|promotion|moderation|broadcast)\b"
    r".{0,80}\b(allowed|enabled|promoted|ready|public|supported)\b",
    re.IGNORECASE,
)
NEGATED_RE = re.compile(r"\b(blocked|cannot|does not|forbidden|no|not|planning|without|until)\b", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    parser.add_argument("--command-response-decisions", type=Path, default=DEFAULT_COMMAND_RESPONSE_DECISIONS)
    parser.add_argument("--bridge-decisions", type=Path, default=DEFAULT_BRIDGE_DECISIONS)
    parser.add_argument("--commands-replies-decisions", type=Path, default=DEFAULT_COMMANDS_REPLIES_DECISIONS)
    parser.add_argument("--permissions-decisions", type=Path, default=DEFAULT_PERMISSIONS_DECISIONS)
    parser.add_argument(
        "--query-failclosed-artifact",
        type=Path,
        help="Candidate-only permissions/admin query manifest or consume-mode checker report.",
    )
    parser.add_argument("--surfaces", type=Path, default=DEFAULT_SURFACES)
    parser.add_argument("--public-header", type=Path, default=DEFAULT_PUBLIC_HEADER)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def add(blockers: list[dict[str, Any]], reason: str, label: str, **extra: Any) -> None:
    blocker = {"reason": reason, "label": label}
    blocker.update(extra)
    blockers.append(blocker)


def load_json(path: Path, label: str) -> dict[str, Any]:
    reject_symlink_component(path, label)
    path = reject_protected_input_path(path, label)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path}: expected JSON object")
    return payload


def string_list(value: Any) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def validate_main_decisions(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> list[str]:
    if payload.get("schema") != DECISIONS_SCHEMA:
        add(blockers, "decisions_schema_mismatch", "$.schema")
    if payload.get("surface") != SURFACE:
        add(blockers, "decisions_surface_mismatch", "$.surface")
    if payload.get("status") != "blocked":
        add(blockers, "decisions_status_not_blocked", "$.status")
    if payload.get("planning_stage") != "planning_only_copied_response_intent":
        add(blockers, "planning_stage_mismatch", "$.planning_stage")
    if payload.get("planning_only") is not True:
        add(blockers, "planning_only_not_true", "$.planning_only")
    for key in FALSE_KEYS:
        if payload.get(key) is not False:
            add(blockers, f"{key}_not_false", f"$.{key}")
    for key in EMPTY_ARRAY_KEYS:
        if payload.get(key) != []:
            add(blockers, f"{key}_not_empty", f"$.{key}")

    depends_on = set(string_list(payload.get("depends_on")))
    if not REQUIRED_DEPENDS_ON.issubset(depends_on):
        add(blockers, "depends_on_missing_required", "$.depends_on", missing=sorted(REQUIRED_DEPENDS_ON - depends_on))
    decision_docs = set(string_list(payload.get("depends_on_decision_docs")))
    if not REQUIRED_DECISION_DOCS.issubset(decision_docs):
        add(
            blockers,
            "depends_on_decision_docs_missing_required",
            "$.depends_on_decision_docs",
            missing=sorted(REQUIRED_DECISION_DOCS - decision_docs),
        )

    fields = string_list(payload.get("intent_field_vocabulary"))
    if tuple(fields) != REQUIRED_INTENT_FIELDS:
        add(
            blockers,
            "intent_field_vocabulary_mismatch",
            "$.intent_field_vocabulary",
            expected=list(REQUIRED_INTENT_FIELDS),
            observed=fields,
        )
    properties = set(string_list(payload.get("intent_properties")))
    if not REQUIRED_INTENT_PROPERTIES.issubset(properties):
        add(
            blockers,
            "intent_properties_missing_required",
            "$.intent_properties",
            missing=sorted(REQUIRED_INTENT_PROPERTIES - properties),
        )
    fail_closed = set(string_list(payload.get("fail_closed_cases")))
    if not REQUIRED_FAIL_CLOSED.issubset(fail_closed):
        add(
            blockers,
            "fail_closed_cases_missing_required",
            "$.fail_closed_cases",
            missing=sorted(REQUIRED_FAIL_CLOSED - fail_closed),
        )
    non_claims = set(string_list(payload.get("non_claims")))
    if not REQUIRED_NON_CLAIMS.issubset(non_claims):
        add(blockers, "non_claims_missing_required", "$.non_claims")

    for token in DEFAULT_FORBIDDEN_HEADER_TOKENS:
        if token not in string_list(payload.get("public_header_forbidden_tokens")):
            add(blockers, "public_header_forbidden_token_missing", "$.public_header_forbidden_tokens", token=token)
    return string_list(payload.get("public_header_forbidden_tokens"))


def validate_dependency_docs(
    command_response: dict[str, Any],
    bridge: dict[str, Any],
    commands_replies: dict[str, Any],
    permissions: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    expected = (
        (command_response, COMMAND_RESPONSE_SCHEMA, COMMAND_RESPONSE_SURFACE, "command_response"),
        (bridge, BRIDGE_SCHEMA, "obelisk.command_principal_authz_response_bridge.v1", "bridge"),
        (commands_replies, COMMANDS_REPLIES_SCHEMA, COMMANDS_REPLIES_SURFACE, "commands_replies"),
        (permissions, PERMISSIONS_SCHEMA, PERMISSIONS_SURFACE, "permissions"),
    )
    for payload, schema, surface, label in expected:
        if payload.get("schema") != schema:
            add(blockers, f"{label}_schema_mismatch", f"{label}.schema")
        if payload.get("surface") != surface:
            add(blockers, f"{label}_surface_mismatch", f"{label}.surface")
        if payload.get("status") != "blocked":
            add(blockers, f"{label}_status_not_blocked", f"{label}.status")
        for key in ("promotion_ready", "public_sdk_ready", "runtime_ready"):
            if payload.get(key) is True:
                add(blockers, f"{label}_{key}_overclaim", f"{label}.{key}")

    if bridge.get("public_response_abi_now") != []:
        add(blockers, "bridge_public_response_abi_now_not_empty", "bridge.public_response_abi_now")
    if bridge.get("public_capability_bits_now") != []:
        add(blockers, "bridge_public_capability_bits_now_not_empty", "bridge.public_capability_bits_now")
    if commands_replies.get("public_response_path_allowed") is not False:
        add(blockers, "commands_replies_public_response_path_allowed_not_false", "commands_replies.public_response_path_allowed")
    if permissions.get("public_header_allowed") is not False:
        add(blockers, "permissions_public_header_allowed_not_false", "permissions.public_header_allowed")


def validate_surfaces(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if payload.get("schema") != SURFACES_SCHEMA:
        add(blockers, "surfaces_schema_mismatch", "$.schema")
        return
    surfaces = payload.get("surfaces")
    if not isinstance(surfaces, list):
        add(blockers, "surfaces_not_list", "$.surfaces")
        return
    by_id = {item.get("id"): item for item in surfaces if isinstance(item, dict)}
    for surface_id in (IDENTITY_SURFACE, PERMISSIONS_SURFACE, COMMAND_RESPONSE_SURFACE, COMMANDS_REPLIES_SURFACE):
        surface = by_id.get(surface_id)
        if not isinstance(surface, dict):
            add(blockers, "surface_missing", "$.surfaces", surface=surface_id)
            continue
        if surface.get("status") == "promoted":
            add(blockers, "dependency_surface_unexpectedly_promoted", f"$.surfaces[{surface_id}]", surface=surface_id)
    command_response = by_id.get(COMMAND_RESPONSE_SURFACE)
    commands_replies = by_id.get(COMMANDS_REPLIES_SURFACE)
    if isinstance(commands_replies, dict) and COMMAND_RESPONSE_SURFACE not in commands_replies.get("depends_on", []):
        add(blockers, "commands_replies_missing_command_response_dependency", "$.surfaces[commands_replies].depends_on")
    if isinstance(command_response, dict) and command_response.get("public_contract") != []:
        add(blockers, "command_response_public_contract_not_empty", "$.surfaces[command_response].public_contract")


def validate_public_header(path: Path, tokens: list[str], blockers: list[dict[str, Any]]) -> None:
    text = path.read_text(encoding="utf-8")
    present = sorted(token for token in set(tokens) | DEFAULT_FORBIDDEN_HEADER_TOKENS if token in text)
    if present:
        add(blockers, "public_header_contains_command_response_intent_symbol", str(path), tokens=present)


def validate_query_failclosed_artifact(path: Path | None, blockers: list[dict[str, Any]]) -> str | None:
    if path is None:
        add(blockers, "query_failclosed_artifact_missing", "--query-failclosed-artifact")
        return None
    payload = load_json(path, "query-failclosed-artifact")
    schema = payload.get("schema")
    if schema not in {QUERY_CONTRACT_SCHEMA, QUERY_CONTRACT_REPORT_SCHEMA}:
        add(blockers, "query_failclosed_artifact_schema_mismatch", str(path), schema=schema)
        return None
    if schema == QUERY_CONTRACT_REPORT_SCHEMA:
        if payload.get("mode") != "consume" or payload.get("ready") is not True:
            add(blockers, "query_failclosed_report_not_consume_ready", str(path))
    else:
        validation = query_failclosed_contract.validate_manifest(payload, check_mode="consume")
        if validation.blockers:
            add(
                blockers,
                "query_failclosed_manifest_invalid",
                str(path),
                reasons=[blocker["reason"] for blocker in validation.blockers],
            )
    return str(schema)


def validate_permissions_public_readiness(
    args: argparse.Namespace,
    query_artifact_schema: str | None,
    blockers: list[dict[str, Any]],
) -> None:
    if query_artifact_schema is None:
        add(blockers, "response_intent_accepts_without_query_failclosed_planning", "--query-failclosed-artifact")
        return
    report = permissions_readiness.build_report(
        argparse.Namespace(
            decisions=args.permissions_decisions,
            surfaces=args.surfaces,
            public_header=args.public_header,
            query_failclosed_artifact=args.query_failclosed_artifact,
        )
    )
    if report.get("valid") is not True or report.get("accepted_for_planning") is not True:
        add(
            blockers,
            "permissions_admin_public_readiness_not_accepted_for_planning",
            "--query-failclosed-artifact",
            readiness_blockers=report.get("blockers"),
        )


def find_positive_claim(value: Any, trail: str = "$") -> tuple[str, str] | None:
    if isinstance(value, dict):
        for key, child in value.items():
            found = find_positive_claim(child, f"{trail}.{key}")
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = find_positive_claim(child, f"{trail}[{index}]")
            if found is not None:
                return found
    elif isinstance(value, str):
        for match in POSITIVE_CLAIM_RE.finditer(value):
            prefix = value[max(0, match.start() - 80) : match.start()]
            if not NEGATED_RE.search(prefix):
                return value, trail
    return None


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    decisions = load_json(args.decisions, "decisions")
    command_response = load_json(args.command_response_decisions, "command-response-decisions")
    bridge = load_json(args.bridge_decisions, "bridge-decisions")
    commands_replies = load_json(args.commands_replies_decisions, "commands-replies-decisions")
    permissions = load_json(args.permissions_decisions, "permissions-decisions")
    surfaces = load_json(args.surfaces, "surfaces")

    forbidden_tokens = validate_main_decisions(decisions, blockers)
    validate_dependency_docs(command_response, bridge, commands_replies, permissions, blockers)
    validate_surfaces(surfaces, blockers)
    validate_public_header(args.public_header, forbidden_tokens, blockers)
    query_artifact_schema = validate_query_failclosed_artifact(args.query_failclosed_artifact, blockers)
    validate_permissions_public_readiness(args, query_artifact_schema, blockers)
    positive_claim = find_positive_claim(decisions)
    if positive_claim is not None:
        value, trail = positive_claim
        add(blockers, "positive_public_response_claim", trail, value=value)

    valid = not blockers
    return {
        "schema": REPORT_SCHEMA,
        "surface": SURFACE,
        "valid": valid,
        "accepted_for_planning": valid,
        "planning_only": True,
        "public_readiness_ready": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "runtime_ready": False,
        "intent_fields": list(REQUIRED_INTENT_FIELDS),
        "dependency_chain": [IDENTITY_SURFACE, PERMISSIONS_SURFACE, COMMAND_RESPONSE_SURFACE, COMMANDS_REPLIES_SURFACE],
        "query_failclosed_artifact_schema": query_artifact_schema,
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
    }


def main() -> int:
    args = parse_args()
    report = build_report(args)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif report["blockers"]:
        for blocker in report["blocker_details"]:
            print(f"{blocker['reason']}: {blocker['label']}", file=sys.stderr)
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
