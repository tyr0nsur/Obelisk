#!/usr/bin/env python3
"""Validate that object identity and ResourceHandle stay blocked from the public SDK."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component  # noqa: E402


REPORT_SCHEMA = "obelisk.object-identity-resource-handle-public-contract-readiness-check.v1"
DECISIONS_SCHEMA = "obelisk.object-identity-resource-handle-public-contract-decisions.v1"
SURFACE_ID = "obelisk.object_identity_resource_handle.v1"
DEFAULT_DECISIONS = REPO_ROOT / "docs" / "object_identity_resource_handle_public_contract_decisions.json"
DEFAULT_SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
DEFAULT_PUBLIC_EVENTS = REPO_ROOT / "docs" / "public_gameplay_events.json"
DEFAULT_PUBLIC_HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"

REQUIRED_FALSE_KEYS = (
    "public_header_allowed",
    "public_contract_allowed",
    "promotion_ready",
    "public_sdk_ready",
    "runtime_ready",
    "public_resource_handle_ready",
    "post_callback_resource_handle_ready",
)
REQUIRED_DESCRIPTOR_FLAGS = (
    "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY",
    "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY",
    "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP",
)
REQUIRED_NON_CLAIMS = (
    "no public ResourceHandle ABI",
    "no public object identity ABI",
    "no public object lookup ABI",
    "no post-callback object correlation",
    "category-only resource_kind metadata is not identity",
    "copied events do not imply object identity",
)
FORBIDDEN_HEADER_SYMBOL_RE = re.compile(
    r"\b(?:"
    r"OBELISK_API_CAPABILITY_(?:RESOURCE_HANDLE|OBJECT_IDENTITY|OBJECT_LOOKUP)|"
    r"OBELISK_[A-Z0-9_]*(?:RESOURCE_HANDLE|OBJECT_IDENTITY|OBJECT_LOOKUP)[A-Z0-9_]*|"
    r"Obelisk(?:ResourceHandle|ObjectIdentity|ObjectLookup)[A-Za-z0-9_]*|"
    r"(?:Resolve|Lookup)[A-Za-z0-9_]*(?:Resource|Object|UObject)|"
    r"UObject|FName|GObjects"
    r")\b"
)
FORBIDDEN_PUBLIC_EVENT_TERMS = (
    "ObeliskResourceHandle",
    "ObeliskObjectIdentity",
    "ObeliskObjectLookup",
    "OBELISK_API_CAPABILITY_RESOURCE_HANDLE",
    "post-callback object handle API is included",
    "object lookup API is included",
)
FORBIDDEN_TRUE_KEYS = (
    "promotion_ready",
    "public_abi_ready",
    "public_sdk_ready",
    "release_ready",
    "runtime_ready",
    "stable_claim_allowed",
    "v1_sdk_ready",
    "object_identity_ready",
    "post_callback_resource_handle_ready",
    "public_object_identity_ready",
    "public_object_lookup_ready",
    "public_resource_handle_ready",
    "resource_handle_ready",
)
FORBIDDEN_READY_VALUE_KEYS = {
    "object_identity",
    "object_lookup",
    "resource_handle",
    "ResourceHandle",
}
FORBIDDEN_ALIAS_SUBJECT_RE = re.compile(
    r"(?:resource_?handle|resourcehandle|resource_?lookup|object_?identity|object_?lookup|object_?handle|"
    r"runtime_?object|public_?gobjects|gobjects|static_?globals?|strict_?serial|serial_?policy|"
    r"serial_?reuse|zero_?serial|runtime_?rejection|post_?callback_?rejection|source_?helper|"
    r"weak_?helper|future_?runtime_?observation|runtime_?observation|wraparound)",
    re.IGNORECASE,
)
FORBIDDEN_ALIAS_CONTEXT_RE = re.compile(
    r"(?:public|runtime|v1|sdk|abi|release|promot|ready|readiness|enabled|allowed|available|"
    r"post_?callback|lookup|identity|samples?|safety|policy|proven|complete|completion|satisfied|"
    r"stable|supported|included|blockers?|gates?)",
    re.IGNORECASE,
)
SURFACE_FORBIDDEN_TERM_RE = re.compile(
    r"(?:resourcehandle|resource[_ -]?handle|resource[_ -]?lookup|object[_ -]?identity|object[_ -]?lookup|"
    r"public[_ -]?gobjects|gobjects|static[_ -]?globals?|strict[_ -]?serial|serial[_ -]?policy|"
    r"serial[_ -]?reuse|zero[_ -]?serial|runtime[_ -]?rejection[_ -]?samples?|"
    r"post[_ -]?callback[_ -]?rejection[_ -]?contracts?|source[_ -]?helper[_ -]?flags?|"
    r"weak[_ -]?helper|future[_ -]?runtime[_ -]?observation|runtime[_ -]?observation[_ -]?plans?|"
    r"post[_ -]?callback[_ -]?object[_ -]?(?:correlation|handle|identity)|"
    r"(?:structure|item|inventory|dino|tribe|buff|mission|transfer|economy|mobility|area[_ -]?policy)[_ -]?handle)",
    re.IGNORECASE,
)
SURFACE_POSITIVE_CLAIM_RE = re.compile(
    r"(?:public[_ -]?sdk|ready|readiness|allowed|available|enabled|included|"
    r"includes?|ships?|part[_ -]?of[_ -]?v1|promoted|promotion|supported|stable|accepted|"
    r"complete|completion|satisf(?:y|ies|ied)|prove[ns]?|lookup[_ -]?api|handle[_ -]?api|"
    r"cleared|resolved|unblocked|unlocked|passed)",
    re.IGNORECASE,
)
DESCRIPTOR_SURFACE_IDS = frozenset(
    (
        "obelisk.descriptors.v1",
        "obelisk.resource_kind_descriptors.v1",
        "obelisk.gameplay_policy_event_descriptors.v1",
    )
)
DESCRIPTOR_FORBIDDEN_PUBLIC_CONTRACT_RE = re.compile(
    r"(?:"
    r"\bObelisk(?:ResourceHandle|ObjectIdentity|ObjectLookup)[A-Za-z0-9_]*\b|"
    r"\bOBELISK_API_CAPABILITY_(?:RESOURCE_HANDLE|OBJECT_IDENTITY|OBJECT_LOOKUP)\b|"
    r"\b(?:resourcehandle|resource[_ -]?handle|resource[_ -]?lookup|object[_ -]?identity|object[_ -]?lookup|"
    r"post[_ -]?callback[_ -]?object[_ -]?(?:correlation|handle|identity))\b"
    r")",
    re.IGNORECASE,
)
SURFACE_NEGATED_CLAIM_RE = re.compile(
    r"(?:\bno\b|\bnot\b|must[_ -]?not|cannot|blocked|excluded|post[_ -]?v1|"
    r"without|not[_ -]?included|does[_ -]?not|do[_ -]?not)",
    re.IGNORECASE,
)
SURFACE_UNBLOCKING_NEGATION_RE = re.compile(
    r"(?:not|no[_ -]?longer)\s+(?:blocked|excluded|post[_ -]?v1|deferred)|"
    r"(?:blocked|excluded|post[_ -]?v1)\s*[:=]\s*false",
    re.IGNORECASE,
)
PUBLIC_CONTRACT_FIELD_KEYS = frozenset(
    (
        "public_contract",
        "public_contracts",
        "sdk_contract",
        "sdk_contracts",
        "public_api_contract",
        "public_abi_contract",
        "capability",
        "capabilities",
    )
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    parser.add_argument("--surfaces", type=Path, default=DEFAULT_SURFACES)
    parser.add_argument("--public-events", type=Path, default=DEFAULT_PUBLIC_EVENTS)
    parser.add_argument("--public-header", type=Path, default=DEFAULT_PUBLIC_HEADER)
    parser.add_argument("--json", action="store_true", help="Emit JSON. The checker always emits JSON.")
    return parser.parse_args()


def safe_input_path(path: Path, label: str) -> Path:
    reject_symlink_component(path, label)
    return reject_protected_input_path(path, label)


def load_json(path: Path, label: str) -> Any:
    resolved = safe_input_path(path, label)
    try:
        return json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{label} is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise SystemExit(f"{label} is unreadable: {exc}") from exc


def strip_c_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"//.*", "", text)
    return text


def positive_claim(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return value.casefold() in {
            "accepted",
            "allowed",
            "available",
            "complete",
            "enabled",
            "included",
            "live",
            "promoted",
            "proven",
            "cleared",
            "resolved",
            "ready",
            "satisfied",
            "stable",
            "supported",
            "true",
            "unblocked",
            "unlocked",
            "passed",
            "yes",
        }
    return False


def normalized_claim_key(key: str) -> str:
    key = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key)
    return re.sub(r"[^a-zA-Z0-9]+", "_", key).strip("_").casefold()


def forbidden_positive_alias_key(key: str) -> bool:
    normalized = normalized_claim_key(key)
    return bool(FORBIDDEN_ALIAS_SUBJECT_RE.search(normalized) and FORBIDDEN_ALIAS_CONTEXT_RE.search(normalized))


def walk_claims(value: Any, blockers: list[str], trail: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_TRUE_KEYS and positive_claim(child):
                blockers.append(f"forbidden_positive_resource_handle_claim:{trail}.{key}")
            if key in FORBIDDEN_READY_VALUE_KEYS and positive_claim(child):
                blockers.append(f"forbidden_positive_resource_handle_claim:{trail}.{key}")
            if forbidden_positive_alias_key(str(key)) and positive_claim(child):
                blockers.append(f"forbidden_positive_resource_handle_claim:{trail}.{key}")
            walk_claims(child, blockers, f"{trail}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_claims(child, blockers, f"{trail}[{index}]")


def positive_surface_text_claim(text: str) -> bool:
    if not SURFACE_FORBIDDEN_TERM_RE.search(text):
        return False
    if not SURFACE_POSITIVE_CLAIM_RE.search(text):
        return False
    if SURFACE_NEGATED_CLAIM_RE.search(text) and not SURFACE_UNBLOCKING_NEGATION_RE.search(text):
        return False
    return True


def walk_text_claims(value: Any, blockers: list[str], trail: str, blocker_prefix: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            walk_text_claims(child, blockers, f"{trail}.{key}", blocker_prefix)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_text_claims(child, blockers, f"{trail}[{index}]", blocker_prefix)
    elif isinstance(value, str):
        for clause_index, clause in enumerate(re.split(r"[.;\n]+", value)):
            normalized = clause.strip()
            if normalized and positive_surface_text_claim(normalized):
                blockers.append(f"{blocker_prefix}:{trail}[clause:{clause_index}]")


def walk_surface_text_claims(value: Any, blockers: list[str], trail: str) -> None:
    walk_text_claims(value, blockers, trail, "surface_positive_resource_handle_claim")


def walk_decisions_text_claims(value: Any, blockers: list[str], trail: str) -> None:
    walk_text_claims(value, blockers, trail, "decisions_positive_resource_handle_claim")


def walk_public_event_text_claims(value: Any, blockers: list[str], trail: str) -> None:
    walk_text_claims(value, blockers, trail, "public_events_positive_resource_handle_claim")


def value_contains_forbidden_public_contract(value: Any) -> bool:
    if isinstance(value, str):
        return DESCRIPTOR_FORBIDDEN_PUBLIC_CONTRACT_RE.search(value) is not None
    if isinstance(value, dict):
        return any(value_contains_forbidden_public_contract(child) for child in value.values())
    if isinstance(value, list):
        return any(value_contains_forbidden_public_contract(child) for child in value)
    return False


def walk_public_contract_fields(value: Any, blockers: list[str], trail: str, blocker_prefix: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            if (
                normalized_claim_key(key_text) in PUBLIC_CONTRACT_FIELD_KEYS
                and value_contains_forbidden_public_contract(child)
            ):
                blockers.append(f"{blocker_prefix}:{trail}.{key_text}")
            walk_public_contract_fields(child, blockers, f"{trail}.{key_text}", blocker_prefix)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_public_contract_fields(child, blockers, f"{trail}[{index}]", blocker_prefix)


def surface_entry(surfaces: Any, blockers: list[str]) -> dict[str, Any] | None:
    entries = surfaces.get("surfaces") if isinstance(surfaces, dict) else None
    if not isinstance(entries, list):
        blockers.append("public_sdk_surfaces_missing_surfaces_list")
        return None
    matches = [entry for entry in entries if isinstance(entry, dict) and entry.get("id") == SURFACE_ID]
    if len(matches) != 1:
        blockers.append("object_identity_resource_handle_surface_missing_or_duplicate")
        return None
    return matches[0]


def validate_decisions(decisions: Any, blockers: list[str]) -> None:
    if not isinstance(decisions, dict):
        blockers.append("decisions_not_object")
        return
    if decisions.get("schema") != DECISIONS_SCHEMA:
        blockers.append("decisions_schema_mismatch")
    if decisions.get("surface_id") != SURFACE_ID:
        blockers.append("decisions_surface_id_mismatch")
    if decisions.get("status") != "blocked":
        blockers.append("decisions_status_not_blocked")
    if decisions.get("support_tier") != "blocked":
        blockers.append("decisions_support_tier_not_blocked")
    for key in REQUIRED_FALSE_KEYS:
        if decisions.get(key) is not False:
            blockers.append(f"{key}_not_false")
    if decisions.get("required_public_sdk_surface_status") != "post-v1":
        blockers.append("required_public_sdk_surface_status_not_post_v1")
    if decisions.get("required_public_sdk_surface_support_tier") != "blocked":
        blockers.append("required_public_sdk_surface_support_tier_not_blocked")
    if decisions.get("required_public_contract") != []:
        blockers.append("required_public_contract_not_empty")
    flags = decisions.get("required_resource_kind_descriptor_flags")
    if not isinstance(flags, list) or set(REQUIRED_DESCRIPTOR_FLAGS) - set(flags):
        blockers.append("required_resource_kind_descriptor_flags_missing")
    non_claims = decisions.get("non_claims")
    if not isinstance(non_claims, list):
        blockers.append("non_claims_missing")
    else:
        missing = [claim for claim in REQUIRED_NON_CLAIMS if claim not in non_claims]
        if missing:
            blockers.append("required_non_claims_missing")
    walk_claims(decisions, blockers, "$.decisions")
    walk_decisions_text_claims(decisions, blockers, "$.decisions")
    walk_public_contract_fields(
        decisions,
        blockers,
        "$.decisions",
        "decisions_forbidden_public_contract_field",
    )


def validate_surface(surfaces: Any, blockers: list[str]) -> None:
    entry = surface_entry(surfaces, blockers)
    if entry is None:
        return
    if entry.get("status") != "post-v1":
        blockers.append("surface_status_not_post_v1")
    if entry.get("support_tier") != "blocked":
        blockers.append("surface_support_tier_not_blocked")
    if entry.get("public_contract") != []:
        blockers.append("surface_public_contract_not_empty")
    contract = entry.get("v1_decision_contract")
    if not isinstance(contract, dict):
        blockers.append("surface_v1_decision_contract_missing")
    elif contract.get("must_remain_without_public_contract_until_promotion") is not True:
        blockers.append("surface_must_remain_without_public_contract_missing")
    blockers_text = "\n".join(str(item) for item in entry.get("blockers", []))
    if "No dedicated tested checker" in blockers_text:
        blockers.append("surface_blockers_still_say_dedicated_checker_missing")
    required_terms = ("ResourceHandle", "object identity", "lookup", "post-callback")
    evidence_text = json.dumps(entry.get("evidence", {}), sort_keys=True)
    for term in required_terms:
        if term not in blockers_text and term not in evidence_text:
            blockers.append(f"surface_missing_boundary_term:{term}")
    walk_claims(entry, blockers, f"$.surfaces[{SURFACE_ID}]")
    walk_surface_text_claims(entry, blockers, f"$.surfaces[{SURFACE_ID}]")
    walk_public_contract_fields(
        entry,
        blockers,
        f"$.surfaces[{SURFACE_ID}]",
        "surface_forbidden_public_contract_field",
    )


def validate_promoted_descriptor_surfaces(surfaces: Any, blockers: list[str]) -> None:
    entries = surfaces.get("surfaces") if isinstance(surfaces, dict) else None
    if not isinstance(entries, list):
        return
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        surface_id = entry.get("id")
        is_descriptor_surface = surface_id in DESCRIPTOR_SURFACE_IDS or (
            entry.get("status") == "promoted"
            and entry.get("category") == "metadata"
            and "descriptor" in str(entry.get("public_name", "")).casefold()
        )
        if not is_descriptor_surface:
            continue
        walk_public_contract_fields(
            entry,
            blockers,
            f"$.surfaces[{index}]",
            "surface_forbidden_public_contract_field",
        )
        for key in ("public_contract", "capabilities", "public_name"):
            value = entry.get(key)
            for item_index, item in enumerate(value if isinstance(value, list) else [value]):
                if isinstance(item, str) and DESCRIPTOR_FORBIDDEN_PUBLIC_CONTRACT_RE.search(item):
                    blockers.append(
                        "promoted_descriptor_surface_forbidden_public_contract:"
                        f"$.surfaces[{index}].{key}[{item_index}]"
                    )
        walk_surface_text_claims(entry.get("evidence", {}), blockers, f"$.surfaces[{index}].evidence")


def validate_public_events(events: Any, blockers: list[str]) -> None:
    text = json.dumps(events, sort_keys=True)
    for term in FORBIDDEN_PUBLIC_EVENT_TERMS:
        if term in text:
            blockers.append(f"public_events_forbidden_term:{term}")
    walk_claims(events, blockers)
    walk_public_event_text_claims(events, blockers, "$.public_events")
    walk_public_contract_fields(
        events,
        blockers,
        "$.public_events",
        "public_events_forbidden_public_contract_field",
    )
    if isinstance(events, dict):
        metadata_surfaces = events.get("metadata_surfaces")
        resource_surface = None
        if isinstance(metadata_surfaces, list):
            for item in metadata_surfaces:
                if isinstance(item, dict) and item.get("surface_id") == "obelisk.resource_kind_descriptors.v1":
                    resource_surface = item
                    break
        if resource_surface is None:
            blockers.append("resource_kind_descriptor_surface_missing")
        else:
            flags = resource_surface.get("flags")
            if not isinstance(flags, list) or set(REQUIRED_DESCRIPTOR_FLAGS) - set(flags):
                blockers.append("resource_kind_descriptor_flags_missing")
            fields = resource_surface.get("descriptor_fields")
            if not isinstance(fields, list):
                blockers.append("resource_kind_descriptor_fields_missing")
            else:
                forbidden_fields = {"identity", "object_identity", "lookup", "handle", "resource_handle"}
                if forbidden_fields & set(fields):
                    blockers.append("resource_kind_descriptor_identity_or_lookup_field_present")


def validate_header(path: Path, blockers: list[str]) -> None:
    resolved = safe_input_path(path, "--public-header")
    try:
        header = strip_c_comments(resolved.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"--public-header is unreadable: {exc}") from exc
    matches = sorted(set(FORBIDDEN_HEADER_SYMBOL_RE.findall(header)))
    if matches:
        blockers.append("public_header_contains_object_identity_or_resource_handle_symbol")
    for flag in REQUIRED_DESCRIPTOR_FLAGS:
        if flag not in header:
            blockers.append(f"public_header_missing_descriptor_flag:{flag}")
    descriptor_match = re.search(r"typedef\s+struct\s+ObeliskResourceKindDescriptor\s*\{(?P<body>.*?)\}", header, re.DOTALL)
    if descriptor_match is None:
        blockers.append("public_header_missing_resource_kind_descriptor")
    else:
        body = descriptor_match.group("body")
        if re.search(r"\b(?:identity|object_identity|lookup|handle|resource_handle)\b", body, re.IGNORECASE):
            blockers.append("public_header_resource_kind_descriptor_has_identity_lookup_or_handle_field")


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    blockers: list[str] = []
    decisions = load_json(args.decisions, "--decisions")
    surfaces = load_json(args.surfaces, "--surfaces")
    events = load_json(args.public_events, "--public-events")

    validate_decisions(decisions, blockers)
    validate_surface(surfaces, blockers)
    validate_promoted_descriptor_surfaces(surfaces, blockers)
    validate_public_events(events, blockers)
    validate_header(args.public_header, blockers)
    valid = not blockers

    return {
        "schema": REPORT_SCHEMA,
        "surface_id": SURFACE_ID,
        "valid": valid,
        "accepted_for_planning": valid,
        "planning_only": True,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_resource_handle_ready": False,
        "post_callback_resource_handle_ready": False,
        "blockers": sorted(set(blockers)),
        "non_claim": (
            "ResourceHandle and object identity remain post-v1/blocked; copied events and "
            "category-only resource_kind metadata do not imply lookup, identity, persistent "
            "handles, post-callback object correlation, mutation, return override, runtime "
            "readiness, public SDK readiness, or v1 completion."
        ),
    }


def main() -> int:
    args = parse_args()
    report = build_report(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
