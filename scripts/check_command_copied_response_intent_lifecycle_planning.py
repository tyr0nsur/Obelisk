#!/usr/bin/env python3
"""Validate command copied-response-intent lifecycle planning stays non-public."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_DECISIONS = REPO_ROOT / "docs" / "command_copied_response_intent_lifecycle_planning_decisions.json"
DEFAULT_PUBLIC_HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"

REPORT_SCHEMA = "obelisk.command-copied-response-intent-lifecycle-planning-check.v1"
DECISIONS_SCHEMA = "obelisk.command-copied-response-intent-lifecycle-planning-decisions.v1"
SURFACE = "obelisk.command_copied_response_intent_lifecycle.planning.v1"
IDENTITY_SURFACE = "obelisk.player_identity.v1"
PERMISSIONS_SURFACE = "obelisk.permissions_admin.v1"
COMMAND_RESPONSE_SURFACE = "obelisk.command_chat_response_path.v1"
COMMANDS_REPLIES_SURFACE = "obelisk.commands_replies.v1"

FALSE_KEYS = (
    "promotion_ready",
    "public_sdk_ready",
    "public_abi_ready",
    "runtime_ready",
    "public_header_allowed",
    "reply_abi_allowed",
    "send_chat_api_allowed",
    "command_router_allowed",
    "runtime_delivery_allowed",
    "runtime_readiness_allowed",
    "public_response_path_allowed",
    "v1_completion_evidence",
)
EMPTY_ARRAY_KEYS = (
    "public_header_symbols_now",
    "public_capability_bits_now",
    "public_response_abi_now",
    "public_lifecycle_abi_now",
)
REQUIRED_DEPENDS_ON = (
    IDENTITY_SURFACE,
    PERMISSIONS_SURFACE,
    COMMAND_RESPONSE_SURFACE,
)
REQUIRED_ROUTE_ORDER = (
    IDENTITY_SURFACE,
    PERMISSIONS_SURFACE,
    COMMAND_RESPONSE_SURFACE,
    COMMANDS_REPLIES_SURFACE,
)
REQUIRED_DECISION_DOCS = frozenset(
    (
        "docs/command_chat_response_public_contract_decisions.json",
        "docs/command_copied_response_intent_planning_decisions.json",
        "docs/commands_replies_public_contract_decisions.json",
        "docs/permissions_admin_public_contract_decisions.json",
        "docs/player_identity_public_contract_decisions.json",
    )
)
REQUIRED_LIFECYCLE_VOCABULARY = (
    "create",
    "cancel",
    "drain",
    "expire",
    "unload cleanup",
)
REQUIRED_LIFECYCLE_PROPERTIES = frozenset(
    (
        "create is owner-scoped and process-local",
        "cancel is owner-scoped and idempotent",
        "drain is owner-scoped and required before owner teardown completes",
        "expire is owner-scoped and invalidates stale copied response intent handles",
        "unload cleanup is owner-scoped and cancels or drains all copied response intents for the unloading owner",
        "lifecycle vocabulary is planning-only and does not define a public struct, public callback, or runtime dispatch path",
        "principal_handle, principal_generation, principal_scope_flags, permission_policy_epoch, and policy provenance must remain attached to any future lifecycle state",
        "commands/replies may consume this only after promoted identity, permissions/admin, and command response contracts exist",
    )
)
REQUIRED_FAIL_CLOSED = frozenset(
    (
        "promotion flag true",
        "runtime flag true",
        "public ABI flag true",
        "public header symbols non-empty",
        "public capability bits non-empty",
        "public response ABI non-empty",
        "public lifecycle ABI non-empty",
        "missing owner token",
        "zero owner token",
        "unknown owner token",
        "unloading owner token",
        "create without owner scope",
        "cancel without owner scope",
        "drain without owner scope",
        "expire without owner scope",
        "unload cleanup without owner scope",
        "create treated as runtime delivery",
        "cancel treated as reply ABI",
        "drain treated as send-chat authorization",
        "expire treated as runtime readiness",
        "unload cleanup treated as public header readiness",
        "lifecycle state inferred from raw FString",
        "lifecycle state inferred from CallProcessEvent",
        "lifecycle state inferred from command text",
        "lifecycle state inferred from operator config",
        "missing principal_handle",
        "missing principal_generation",
        "missing principal_scope_flags",
        "stale principal",
        "permission deny",
        "permission unknown",
        "missing permission_policy_epoch",
        "missing policy provenance",
        "commands/replies planning treated as lifecycle promotion",
    )
)
REQUIRED_NON_CLAIMS = frozenset(
    (
        "planning-only copied response intent lifecycle vocabulary",
        "send-chat, reply ABI, raw FString, CallProcessEvent, public header, and runtime readiness are forbidden positive claims",
        "does not add public headers, capability bits, response ABI, lifecycle ABI, reply ABI, send-chat API, command router, chat router, runtime delivery, runtime readiness, storage, mutation, return override, ResourceHandle, UE pointers, raw params, raw FString, or public SDK readiness",
        "does not authorize runtime observation, server operations, Discord updates, GitHub publication, tags, release claims, or v1 SDK completion",
        "does not bypass promoted player identity, permissions/admin, command_chat_response_path, or commands/replies gates",
    )
)
FORBIDDEN_POSITIVE_CLAIM_TERMS = frozenset(
    (
        "send-chat",
        "reply ABI",
        "raw FString",
        "CallProcessEvent",
        "public header",
        "runtime readiness",
    )
)
ALLOWED_FORBIDDEN_TERM_PATH_PARTS = ("non_claim", "forbidden", "fail_closed")
POSITIVE_TERM_PATH_PARTS = ("abi", "capability", "vocabulary")
FORBIDDEN_HEADER_TOKENS = frozenset(
    (
        "OBELISK_COMMAND_COPIED_RESPONSE_INTENT_LIFECYCLE_ABI_VERSION",
        "OBELISK_API_CAPABILITY_COMMAND_COPIED_RESPONSE_INTENT_LIFECYCLE",
        "ObeliskCommandCopiedResponseIntentLifecycle",
        "RegisterCommandCopiedResponseIntentLifecycle",
    )
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
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


def contains_forbidden_term(value: str) -> str | None:
    value_folded = value.casefold()
    for term in sorted(FORBIDDEN_POSITIVE_CLAIM_TERMS):
        if term.casefold() in value_folded:
            return term
    return None


def path_allows_forbidden_term(trail: str) -> bool:
    trail_folded = trail.casefold()
    return any(part in trail_folded for part in ALLOWED_FORBIDDEN_TERM_PATH_PARTS)


def path_is_positive_contract_area(trail: str) -> bool:
    trail_folded = trail.casefold()
    return any(part in trail_folded for part in POSITIVE_TERM_PATH_PARTS)


def find_forbidden_term_misuse(value: Any, trail: str = "$") -> tuple[str, str, str] | None:
    if isinstance(value, dict):
        for key, child in value.items():
            found = find_forbidden_term_misuse(child, f"{trail}.{key}")
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = find_forbidden_term_misuse(child, f"{trail}[{index}]")
            if found is not None:
                return found
    elif isinstance(value, str):
        term = contains_forbidden_term(value)
        if term is not None and not path_allows_forbidden_term(trail):
            return term, trail, value
        if term is not None and path_is_positive_contract_area(trail):
            return term, trail, value
    return None


def validate_main_decisions(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if payload.get("schema") != DECISIONS_SCHEMA:
        add(blockers, "decisions_schema_mismatch", "$.schema")
    if payload.get("surface") != SURFACE:
        add(blockers, "decisions_surface_mismatch", "$.surface")
    if payload.get("status") != "blocked":
        add(blockers, "decisions_status_not_blocked", "$.status")
    if payload.get("planning_stage") != "planning_only_copied_response_intent_lifecycle":
        add(blockers, "planning_stage_mismatch", "$.planning_stage")
    if payload.get("planning_only") is not True:
        add(blockers, "planning_only_not_true", "$.planning_only")
    for key in FALSE_KEYS:
        if payload.get(key) is not False:
            add(blockers, f"{key}_not_false", f"$.{key}")
    for key in EMPTY_ARRAY_KEYS:
        if payload.get(key) != []:
            add(blockers, f"{key}_not_empty", f"$.{key}")

    depends_on = tuple(string_list(payload.get("depends_on")))
    if depends_on != REQUIRED_DEPENDS_ON:
        add(
            blockers,
            "depends_on_chain_mismatch",
            "$.depends_on",
            expected=list(REQUIRED_DEPENDS_ON),
            observed=list(depends_on),
        )
    route_order = tuple(string_list(payload.get("route_order")))
    if route_order != REQUIRED_ROUTE_ORDER:
        add(
            blockers,
            "route_order_mismatch",
            "$.route_order",
            expected=list(REQUIRED_ROUTE_ORDER),
            observed=list(route_order),
        )
    decision_docs = set(string_list(payload.get("depends_on_decision_docs")))
    if not REQUIRED_DECISION_DOCS.issubset(decision_docs):
        add(
            blockers,
            "depends_on_decision_docs_missing_required",
            "$.depends_on_decision_docs",
            missing=sorted(REQUIRED_DECISION_DOCS - decision_docs),
        )

    lifecycle_vocabulary = tuple(string_list(payload.get("lifecycle_vocabulary")))
    if lifecycle_vocabulary != REQUIRED_LIFECYCLE_VOCABULARY:
        add(
            blockers,
            "lifecycle_vocabulary_mismatch",
            "$.lifecycle_vocabulary",
            expected=list(REQUIRED_LIFECYCLE_VOCABULARY),
            observed=list(lifecycle_vocabulary),
        )
    lifecycle_properties = set(string_list(payload.get("lifecycle_properties")))
    if not REQUIRED_LIFECYCLE_PROPERTIES.issubset(lifecycle_properties):
        add(
            blockers,
            "lifecycle_properties_missing_required",
            "$.lifecycle_properties",
            missing=sorted(REQUIRED_LIFECYCLE_PROPERTIES - lifecycle_properties),
        )
    for term in REQUIRED_LIFECYCLE_VOCABULARY:
        matching_properties = [item for item in lifecycle_properties if item.startswith(term)]
        if not matching_properties or not all("owner-scoped" in item for item in matching_properties):
            add(blockers, "lifecycle_term_not_owner_scoped", "$.lifecycle_properties", term=term)

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
    forbidden_terms = set(string_list(payload.get("forbidden_positive_claim_terms")))
    if forbidden_terms != FORBIDDEN_POSITIVE_CLAIM_TERMS:
        add(
            blockers,
            "forbidden_positive_claim_terms_mismatch",
            "$.forbidden_positive_claim_terms",
            expected=sorted(FORBIDDEN_POSITIVE_CLAIM_TERMS),
            observed=sorted(forbidden_terms),
        )

    misuse = find_forbidden_term_misuse(payload)
    if misuse is not None:
        term, trail, value = misuse
        add(blockers, "forbidden_positive_claim_term_outside_allowed_sections", trail, term=term, value=value)


def validate_public_header(path: Path, blockers: list[dict[str, Any]]) -> None:
    text = path.read_text(encoding="utf-8")
    present = sorted(token for token in FORBIDDEN_HEADER_TOKENS if token in text)
    if present:
        add(blockers, "public_header_contains_lifecycle_symbol", str(path), tokens=present)


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    decisions = load_json(args.decisions, "decisions")

    validate_main_decisions(decisions, blockers)
    validate_public_header(args.public_header, blockers)

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
        "public_header_allowed": False,
        "reply_abi_allowed": False,
        "send_chat_api_allowed": False,
        "command_router_allowed": False,
        "runtime_delivery_allowed": False,
        "runtime_readiness_allowed": False,
        "public_response_path_allowed": False,
        "v1_completion_evidence": False,
        "dependency_chain": list(REQUIRED_DEPENDS_ON),
        "route_order": list(REQUIRED_ROUTE_ORDER),
        "lifecycle_vocabulary": list(REQUIRED_LIFECYCLE_VOCABULARY),
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
