#!/usr/bin/env python3
"""Offline stability guardrail for inventory/item copied public signals."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_DECISIONS = REPO_ROOT / "docs" / "inventory_item_copied_signals_public_contract_decisions.json"
DEFAULT_PUBLIC_SDK_SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
DEFAULT_PUBLIC_GAMEPLAY_EVENTS = REPO_ROOT / "docs" / "public_gameplay_events.json"
DEFAULT_PUBLIC_HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"

REPORT_SCHEMA = "obelisk.inventory-item-copied-signals-stability-check.v1"
DECISIONS_SCHEMA = "obelisk.inventory-item-copied-signals-public-contract-decisions.v1"
PUBLIC_SDK_SURFACES_SCHEMA = "obelisk.public-sdk-surfaces.v1"
PUBLIC_GAMEPLAY_EVENTS_SCHEMA = "obelisk.public-gameplay-events.v1"

SURFACE = "obelisk.inventory_item_copied_signals.v1"
GAMEPLAY_POLICY_EVENT_SURFACE = "obelisk.gameplay_policy_event.v1"
GAMEPLAY_POLICY_EVENT = "obelisk.gameplay_policy.v1"
INVENTORY_MUTATION_SURFACE = "obelisk.inventory_items_mutation.v1"
RESOURCE_HANDLE_SURFACE = "obelisk.object_identity_resource_handle.v1"
RESOURCE_KIND = "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM"
ALL_INVENTORY_MASK = "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY"
RETURN_VALUE = "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE"
REQUESTED_BY_PLAYER = "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER"
IGNORE_COOLDOWN = "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN"
EXPECTED_INVENTORY_TARGET_SET = "minimal-second-source-intake"
EXPECTED_ITEM_RETURN_TARGET_SET = "item-return-only-policy-slice"
EXCLUDED_INVENTORY_ACTION_TARGET_SET = "inventory-action-compact-intake"
EXPECTED_INVENTORY_RELEASE_READINESS_TARGET_SETS = (
    EXPECTED_INVENTORY_TARGET_SET,
    EXPECTED_ITEM_RETURN_TARGET_SET,
)
EXPECTED_TARGET_SET_EVIDENCE_SCOPE_TERMS = {
    EXPECTED_INVENTORY_TARGET_SET: (
        "layout-only",
        "no standalone",
        "module-specific",
        "inventory",
    ),
    EXPECTED_ITEM_RETURN_TARGET_SET: (
        "ReturnValue-only",
        "AllowEquipItem",
        "CanRepair",
        "UseItemOntoItem",
        "no standalone item or inventory module surface",
        "no identity",
        "no lookup",
        "no mutation",
        "no return override",
        "ResourceHandle",
    ),
}

EXPECTED_ALLOWED_SIGNALS: tuple[dict[str, Any], ...] = (
    {
        "stable_name": "inventory.remote_add_check",
        "kind": "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK",
        "event_kind_mask": "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_REMOTE_ADD_CHECK",
        "field_mask": [RETURN_VALUE, REQUESTED_BY_PLAYER],
    },
    {
        "stable_name": "inventory.use_check",
        "kind": "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK",
        "event_kind_mask": "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_CHECK",
        "field_mask": [RETURN_VALUE, IGNORE_COOLDOWN],
    },
    {
        "stable_name": "inventory_item.allow_equip_check",
        "kind": "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_ALLOW_EQUIP_ITEM_CHECK",
        "event_kind_mask": "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_ALLOW_EQUIP_ITEM_CHECK",
        "field_mask": [RETURN_VALUE],
    },
    {
        "stable_name": "inventory_item.can_repair_check",
        "kind": "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_CAN_REPAIR_CHECK",
        "event_kind_mask": "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_CAN_REPAIR_CHECK",
        "field_mask": [RETURN_VALUE],
    },
    {
        "stable_name": "inventory_item.use_onto_item_check",
        "kind": "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK",
        "event_kind_mask": "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK",
        "field_mask": [RETURN_VALUE],
    },
)
EXPECTED_SIGNAL_BY_KIND = {signal["kind"]: signal for signal in EXPECTED_ALLOWED_SIGNALS}
EXPECTED_SIGNAL_KINDS = frozenset(EXPECTED_SIGNAL_BY_KIND)
EXPECTED_SIGNAL_MASKS = frozenset(signal["event_kind_mask"] for signal in EXPECTED_ALLOWED_SIGNALS)
EXPECTED_SIGNAL_FIELDS = frozenset(
    field for signal in EXPECTED_ALLOWED_SIGNALS for field in signal["field_mask"]
)
EXPECTED_REQUIRED_FLAGS = frozenset(
    (
        "OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD",
        "OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED",
    )
)
EXPECTED_DECISIONS_PAYLOAD_CONTRACT = "copied POD scalar observation only"
EXPECTED_SURFACE_PAYLOAD_CONTRACT = (
    "copied bool ReturnValue signals only where declared by docs/public_gameplay_events.json",
    "copied bRequestedByPlayer for inventory.remote_add_check",
    "copied bIgnoreCooldown for inventory.use_check",
    "resource_kind remains INVENTORY_ITEM metadata only",
    "post-original observation only; no authority",
)
EXPECTED_PUBLIC_CONTRACT = tuple(
    f"GameplayPolicyEvent {signal['stable_name']}" for signal in EXPECTED_ALLOWED_SIGNALS
)
EXPECTED_HEADER_SYMBOLS = frozenset(
    (
        "OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS",
        "OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS",
        "OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD",
        "OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED",
        "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY",
        "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE",
        "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER",
        "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN",
        "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM",
        "ObeliskGameplayPolicyEvent",
        "ObeliskGameplayPolicyEventDescriptor",
        "ObeliskGameplayPolicyEventCallback",
        "RegisterGameplayPolicyEventWithOwnerTokenHandle",
        "UnregisterGameplayPolicyEventWithOwnerToken",
        "DescribeGameplayPolicyEventKind",
    )
    + tuple(EXPECTED_SIGNAL_KINDS)
    + tuple(EXPECTED_SIGNAL_MASKS)
)
REQUIRED_FORBIDDEN_TERMS = frozenset(
    (
        "Inventory SDK",
        "Items SDK",
        "lookup",
        "mutation",
        "return override",
        "ResourceHandle",
        "AdditionalData",
        "ItemNetID identity",
    )
)
PUBLIC_CLAIM_TERMS = frozenset(
    (
        "Inventory SDK",
        "Items SDK",
        "lookup",
        "mutation",
        "return override",
        "ResourceHandle",
        "AdditionalData",
        "ResourceHandle API",
        "AdditionalData API",
        "Inventory callback API",
        "InventoryComp",
        "ItemId",
        "ItemID1",
        "ItemNetID identity",
        "ServerRequestInventoryUseItem",
        "ServerRequestInventoryUseItemWithActor",
        "action params",
        "anActor",
        "raw params",
    )
)
PUBLIC_SDK_SURFACES_INVENTORY_SIDE_LANE_TERMS = frozenset(("Inventory SDK", "Items SDK"))
CONTRACT_SCAN_KEYS = frozenset(
    (
        "public_contract",
        "payload_contract",
        "scope",
        "resource_contract",
        "public_fields",
        "descriptor_fields",
        "compatibility_statement",
        "inventory_sdk",
        "item_module_sdk",
        "public_name",
        "release_claim",
        "support_tier",
    )
)
CLAIM_TEXT_SCAN_KEYS = CONTRACT_SCAN_KEYS | frozenset(
    (
        "claim",
        "claims",
        "description",
        "evidence_summary",
        "note",
        "notes",
        "rationale",
        "release_note",
        "review_note",
        "review_notes",
        "summary",
    )
)
NEGATIVE_KEYS = frozenset(
    (
        "blockers",
        "exclusions",
        "forbidden_terms",
        "guardrails",
        "must_not_unlock",
        "non_claims",
        "not_promoted",
        "redacted_fields",
    )
)
NEGATED_OR_BOUNDARY_RE = re.compile(
    r"\b(?:"
    r"blocked|cannot|does\s+not|do\s+not|excluded|excludes?|future|metadata-only|"
    r"must\s+not|no|not|only|outside|post-v1|prevent|prevents|remain|remains|"
    r"without"
    r")\b",
    re.IGNORECASE,
)
CLAUSE_SPLIT_RE = re.compile(r"[,.;:\n\r]+")
NEGATION_LIST_SCOPE_SPLIT_RE = re.compile(r"[.;:\n\r]+")
POSITIVE_TERM_SUFFIX_RE = re.compile(
    r"^\s+(?:ready|enabled|public|supported|allowed|live|operational|exposes?|provides?)\b",
    re.IGNORECASE,
)
C_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
CPP_COMMENT_RE = re.compile(r"//.*")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the inventory/item copied-signal public contract remains narrow."
    )
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    parser.add_argument("--public-sdk-surfaces", type=Path, default=DEFAULT_PUBLIC_SDK_SURFACES)
    parser.add_argument("--public-gameplay-events", type=Path, default=DEFAULT_PUBLIC_GAMEPLAY_EVENTS)
    parser.add_argument("--public-header", type=Path, default=DEFAULT_PUBLIC_HEADER)
    parser.add_argument("--json", action="store_true", help="Emit JSON. The checker always emits JSON.")
    return parser.parse_args(argv)


def add(blockers: list[dict[str, Any]], reason: str, label: str, **details: Any) -> None:
    item: dict[str, Any] = {"reason": reason, "path": label}
    item.update(details)
    blockers.append(item)


def load_json(path: Path, label: str, blockers: list[dict[str, Any]]) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        add(blockers, f"{label}_unreadable", f"--{label}", path=str(path), error=str(exc))
        return None
    except json.JSONDecodeError as exc:
        add(blockers, f"{label}_invalid_json", f"--{label}", path=str(path), error=str(exc))
        return None
    if not isinstance(payload, dict):
        add(blockers, f"{label}_not_object", f"--{label}", path=str(path))
        return None
    return payload


def strip_c_comments(text: str) -> str:
    text = C_COMMENT_RE.sub("", text)
    return CPP_COMMENT_RE.sub("", text)


def normalized_signals(signals: Any) -> list[dict[str, Any]]:
    if not isinstance(signals, list):
        return []
    result: list[dict[str, Any]] = []
    for signal in signals:
        if not isinstance(signal, dict):
            continue
        result.append(
            {
                "stable_name": signal.get("stable_name"),
                "kind": signal.get("kind"),
                "event_kind_mask": signal.get("event_kind_mask"),
                "field_mask": list(signal.get("field_mask") or []),
            }
        )
    return sorted(result, key=lambda item: str(item.get("kind")))


def expected_signals_sorted() -> list[dict[str, Any]]:
    return sorted((dict(signal) for signal in EXPECTED_ALLOWED_SIGNALS), key=lambda item: item["kind"])


def string_values(value: Any, trail: str) -> list[tuple[str, str]]:
    if isinstance(value, str):
        return [(trail, value)]
    if isinstance(value, list):
        result: list[tuple[str, str]] = []
        for index, child in enumerate(value):
            result.extend(string_values(child, f"{trail}[{index}]"))
        return result
    if isinstance(value, dict):
        result = []
        for key, child in value.items():
            result.extend(string_values(child, f"{trail}.{key}"))
        return result
    return []


def preceding_clause(text: str, start: int) -> str:
    prefix = text[:start]
    parts = CLAUSE_SPLIT_RE.split(prefix)
    return parts[-1] if parts else prefix


def preceding_negation_list_scope(text: str, start: int) -> str:
    prefix = text[:start]
    parts = NEGATION_LIST_SCOPE_SPLIT_RE.split(prefix)
    return parts[-1] if parts else prefix


def has_positive_term_suffix(text: str, end: int) -> bool:
    return bool(POSITIVE_TERM_SUFFIX_RE.match(text[end:]))


def is_negated_for_match(text: str, start: int, end: int) -> bool:
    if has_positive_term_suffix(text, end):
        return False
    return bool(
        NEGATED_OR_BOUNDARY_RE.search(preceding_clause(text, start))
        or NEGATED_OR_BOUNDARY_RE.search(preceding_negation_list_scope(text, start))
    )


def scan_public_claim_terms(value: Any, blockers: list[dict[str, Any]], trail: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if key in NEGATIVE_KEYS:
                continue
            if key in CLAIM_TEXT_SCAN_KEYS:
                for text_path, text in string_values(child, child_trail):
                    for term in PUBLIC_CLAIM_TERMS:
                        match = re.search(rf"\b{re.escape(term)}\b", text, re.IGNORECASE)
                        if not match:
                            continue
                        if is_negated_for_match(text, match.start(), match.end()):
                            continue
                        add(blockers, "public_claim_forbidden_term", text_path, term=term, value=text)
                continue
            scan_public_claim_terms(child, blockers, child_trail)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            scan_public_claim_terms(child, blockers, f"{trail}[{index}]")


def scan_public_sdk_surfaces_inventory_side_lane_claims(
    value: Any, blockers: list[dict[str, Any]], trail: str = "$"
) -> None:
    if isinstance(value, str):
        for term in PUBLIC_SDK_SURFACES_INVENTORY_SIDE_LANE_TERMS:
            match = re.search(rf"\b{re.escape(term)}\b", value, re.IGNORECASE)
            if not match:
                continue
            if is_negated_for_match(value, match.start(), match.end()):
                continue
            add(
                blockers,
                "public_sdk_surfaces_positive_inventory_side_lane_claim",
                trail,
                term=term,
                value=value,
            )
        return
    if isinstance(value, dict):
        for key, child in value.items():
            if key in NEGATIVE_KEYS:
                continue
            scan_public_sdk_surfaces_inventory_side_lane_claims(child, blockers, f"{trail}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            scan_public_sdk_surfaces_inventory_side_lane_claims(child, blockers, f"{trail}[{index}]")


def require_equal(
    mapping: dict[str, Any], key: str, expected: Any, label: str, blockers: list[dict[str, Any]]
) -> None:
    if mapping.get(key) != expected:
        add(blockers, f"{key}_mismatch", f"{label}.{key}", expected=expected, value=mapping.get(key))


def require_false(mapping: dict[str, Any], key: str, label: str, blockers: list[dict[str, Any]]) -> None:
    if mapping.get(key) is not False:
        add(blockers, f"{key}_not_false", f"{label}.{key}", value=mapping.get(key))


def find_surface(payload: dict[str, Any], surface_id: str) -> dict[str, Any] | None:
    surfaces = payload.get("surfaces")
    if not isinstance(surfaces, list):
        return None
    matches = [item for item in surfaces if isinstance(item, dict) and item.get("id") == surface_id]
    return matches[0] if len(matches) == 1 else None


def find_gameplay_policy_event(payload: dict[str, Any]) -> dict[str, Any] | None:
    events = payload.get("promoted_events")
    if not isinstance(events, list):
        return None
    matches = [item for item in events if isinstance(item, dict) and item.get("event_id") == GAMEPLAY_POLICY_EVENT]
    return matches[0] if len(matches) == 1 else None


def target_set_evidence_names(event: dict[str, Any]) -> set[str]:
    return set(target_set_evidence_by_name(event))


def target_set_evidence_by_name(event: dict[str, Any]) -> dict[str, dict[str, Any]]:
    evidence = event.get("target_set_evidence")
    if not isinstance(evidence, list):
        return {}
    return {
        str(item.get("target_set")): item
        for item in evidence
        if isinstance(item, dict) and item.get("target_set") is not None
    }


def excluded_target_set_names(event: dict[str, Any]) -> set[str]:
    excluded = event.get("excluded_target_sets")
    if not isinstance(excluded, list):
        return set()
    return {
        str(item.get("target_set"))
        for item in excluded
        if isinstance(item, dict) and item.get("target_set") is not None
    }


def find_resource_descriptor(payload: dict[str, Any]) -> dict[str, Any] | None:
    return find_metadata_surface(payload, "obelisk.resource_kind_descriptors.v1")


def find_gameplay_policy_event_descriptor(payload: dict[str, Any]) -> dict[str, Any] | None:
    return find_metadata_surface(payload, "obelisk.gameplay_policy_event_descriptors.v1")


def find_metadata_surface(payload: dict[str, Any], surface_id: str) -> dict[str, Any] | None:
    surfaces = payload.get("metadata_surfaces")
    if not isinstance(surfaces, list):
        return None
    for surface in surfaces:
        if isinstance(surface, dict) and surface.get("surface_id") == surface_id:
            return surface
    return None


def find_inventory_resource_kind(payload: dict[str, Any]) -> dict[str, Any] | None:
    descriptor = find_resource_descriptor(payload)
    if not isinstance(descriptor, dict):
        return None
    resource_kinds = descriptor.get("resource_kinds")
    if not isinstance(resource_kinds, list):
        return None
    for resource_kind in resource_kinds:
        if isinstance(resource_kind, dict) and resource_kind.get("kind") == RESOURCE_KIND:
            return resource_kind
    return None


def validate_decisions(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    label = "$.decisions"
    require_equal(payload, "schema", DECISIONS_SCHEMA, label, blockers)
    require_equal(payload, "surface", SURFACE, label, blockers)
    require_equal(payload, "status", "promoted-experimental-only", label, blockers)
    require_equal(payload, "decision", "copied_signal_only", label, blockers)
    require_equal(payload, "public_header_allowed", True, label, blockers)
    if GAMEPLAY_POLICY_EVENT_SURFACE not in set(payload.get("depends_on") or []):
        add(blockers, "decisions_dependency_missing", f"{label}.depends_on", expected=GAMEPLAY_POLICY_EVENT_SURFACE)

    actual_signals = normalized_signals(payload.get("allowed_signals"))
    expected = expected_signals_sorted()
    if actual_signals != expected:
        add(blockers, "decisions_allowed_signals_mismatch", f"{label}.allowed_signals", expected=expected, value=actual_signals)

    contract = payload.get("public_contract")
    if not isinstance(contract, dict):
        add(blockers, "decisions_public_contract_missing", f"{label}.public_contract")
    else:
        require_equal(contract, "resource_kind", RESOURCE_KIND, f"{label}.public_contract", blockers)
        require_equal(
            contract,
            "payload_contract",
            EXPECTED_DECISIONS_PAYLOAD_CONTRACT,
            f"{label}.public_contract",
            blockers,
        )
        resource_contract = str(contract.get("resource_contract") or "")
        for term in ("category-only", "no identity", "lookup", "handle"):
            if term not in resource_contract:
                add(
                    blockers,
                    "decisions_resource_contract_guardrail_missing",
                    f"{label}.public_contract.resource_contract",
                    term=term,
                    value=resource_contract,
                )
        if set(contract.get("public_fields") or []) != {
            "abi_version",
            "struct_size",
            "event_kind",
            "resource_kind",
            "flags",
            "field_mask",
            "bool_values",
            "int32_values",
        }:
            add(blockers, "decisions_public_fields_mismatch", f"{label}.public_contract.public_fields")
        actual_flags = set(contract.get("required_flags") or [])
        if actual_flags != EXPECTED_REQUIRED_FLAGS:
            add(
                blockers,
                "decisions_required_flags_mismatch",
                f"{label}.public_contract.required_flags",
                expected=sorted(EXPECTED_REQUIRED_FLAGS),
                value=sorted(actual_flags),
            )

    blocked = payload.get("blocked_public_contract")
    if not isinstance(blocked, dict):
        add(blockers, "decisions_blocked_public_contract_missing", f"{label}.blocked_public_contract")
    else:
        require_false(blocked, "standalone_inventory_sdk_allowed", f"{label}.blocked_public_contract", blockers)
        require_false(blocked, "standalone_items_sdk_allowed", f"{label}.blocked_public_contract", blockers)
        forbidden = set(blocked.get("forbidden_terms") or [])
        missing = sorted(REQUIRED_FORBIDDEN_TERMS - forbidden)
        if missing:
            add(blockers, "decisions_forbidden_terms_missing", f"{label}.blocked_public_contract.forbidden_terms", missing=missing)

    v1_contract = payload.get("v1_completion_contract")
    if not isinstance(v1_contract, dict):
        add(blockers, "decisions_v1_completion_contract_missing", f"{label}.v1_completion_contract")
    else:
        require_equal(
            v1_contract,
            "claim_effect",
            "does_not_complete_v1_sdk",
            f"{label}.v1_completion_contract",
            blockers,
        )

    listed_symbols = set(payload.get("public_header_symbols_now") or [])
    missing_symbols = sorted(EXPECTED_HEADER_SYMBOLS - listed_symbols)
    if missing_symbols:
        add(blockers, "decisions_public_header_symbols_missing", f"{label}.public_header_symbols_now", missing=missing_symbols)

    scan_public_claim_terms(payload, blockers, label)
    return {"allowed_signal_count": len(actual_signals), "allowed_kinds": sorted(item["kind"] for item in actual_signals)}


def validate_public_gameplay_events(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    label = "$.public_gameplay_events"
    require_equal(payload, "schema", PUBLIC_GAMEPLAY_EVENTS_SCHEMA, label, blockers)

    event = find_gameplay_policy_event(payload)
    if event is None:
        add(blockers, "gameplay_policy_event_missing", f"{label}.promoted_events")
        return {"inventory_event_kinds": []}

    require_equal(event, "v1_sdk_status", "promoted-experimental-only", f"{label}.{GAMEPLAY_POLICY_EVENT}", blockers)
    require_false(event, "v1_completion_evidence", f"{label}.{GAMEPLAY_POLICY_EVENT}", blockers)
    require_equal(event, "payload", "copied POD scalar fields only", f"{label}.{GAMEPLAY_POLICY_EVENT}", blockers)
    require_equal(
        event,
        "inventory_backing_target_set",
        EXPECTED_INVENTORY_TARGET_SET,
        f"{label}.{GAMEPLAY_POLICY_EVENT}",
        blockers,
    )
    require_equal(
        event,
        "item_return_backing_target_set",
        EXPECTED_ITEM_RETURN_TARGET_SET,
        f"{label}.{GAMEPLAY_POLICY_EVENT}",
        blockers,
    )
    target_sets = set(event.get("target_sets") or [])
    missing_target_sets = sorted(set(EXPECTED_INVENTORY_RELEASE_READINESS_TARGET_SETS) - target_sets)
    if missing_target_sets:
        add(
            blockers,
            "gameplay_policy_inventory_target_sets_missing",
            f"{label}.{GAMEPLAY_POLICY_EVENT}.target_sets",
            missing=missing_target_sets,
            value=sorted(target_sets),
        )
    evidence_by_target_set = target_set_evidence_by_name(event)
    evidence_target_sets = set(evidence_by_target_set)
    missing_evidence_sets = sorted(set(EXPECTED_INVENTORY_RELEASE_READINESS_TARGET_SETS) - evidence_target_sets)
    if missing_evidence_sets:
        add(
            blockers,
            "gameplay_policy_inventory_target_set_evidence_missing",
            f"{label}.{GAMEPLAY_POLICY_EVENT}.target_set_evidence",
            missing=missing_evidence_sets,
            value=sorted(evidence_target_sets),
        )
    for target_set, required_scope_terms in EXPECTED_TARGET_SET_EVIDENCE_SCOPE_TERMS.items():
        evidence = evidence_by_target_set.get(target_set)
        if evidence is None:
            continue
        evidence_label = f"{label}.{GAMEPLAY_POLICY_EVENT}.target_set_evidence[{target_set}]"
        scope = str(evidence.get("scope") or "")
        for term in required_scope_terms:
            if term not in scope:
                add(
                    blockers,
                    "gameplay_policy_inventory_target_set_evidence_scope_guardrail_missing",
                    f"{evidence_label}.scope",
                    target_set=target_set,
                    term=term,
                    value=scope,
                )
        reports = evidence.get("reports")
        if not isinstance(reports, list) or not reports:
            add(
                blockers,
                "gameplay_policy_inventory_target_set_evidence_reports_missing",
                f"{evidence_label}.reports",
                target_set=target_set,
                value=reports,
            )
            continue
        for index, report in enumerate(reports):
            if not isinstance(report, str) or not report:
                add(
                    blockers,
                    "gameplay_policy_inventory_target_set_evidence_report_invalid",
                    f"{evidence_label}.reports[{index}]",
                    target_set=target_set,
                    value=report,
                )
            elif "/servidor/ark" in report:
                add(
                    blockers,
                    "gameplay_policy_inventory_target_set_evidence_report_live_path",
                    f"{evidence_label}.reports[{index}]",
                    target_set=target_set,
                    value=report,
                )
    excluded_target_sets = excluded_target_set_names(event)
    if EXCLUDED_INVENTORY_ACTION_TARGET_SET not in excluded_target_sets:
        add(
            blockers,
            "gameplay_policy_inventory_action_target_set_not_excluded",
            f"{label}.{GAMEPLAY_POLICY_EVENT}.excluded_target_sets",
            expected=EXCLUDED_INVENTORY_ACTION_TARGET_SET,
            value=sorted(excluded_target_sets),
        )
    resource_contract = str(event.get("resource_contract") or "")
    for term in ("kind-only", "no identity", "no lookup", "no persistent handle", "no cross-event correlation"):
        if term not in resource_contract:
            add(
                blockers,
                "gameplay_policy_resource_contract_guardrail_missing",
                f"{label}.{GAMEPLAY_POLICY_EVENT}.resource_contract",
                term=term,
                value=resource_contract,
            )

    event_kinds = event.get("event_kinds")
    if not isinstance(event_kinds, list):
        add(blockers, "gameplay_policy_event_kinds_not_list", f"{label}.{GAMEPLAY_POLICY_EVENT}.event_kinds")
        inventory_events: list[dict[str, Any]] = []
    else:
        inventory_events = [
            item for item in event_kinds if isinstance(item, dict) and item.get("resource_kind") == RESOURCE_KIND
        ]

    actual = normalized_signals(inventory_events)
    expected = expected_signals_sorted()
    if actual != expected:
        add(
            blockers,
            "public_gameplay_inventory_event_kinds_mismatch",
            f"{label}.{GAMEPLAY_POLICY_EVENT}.event_kinds",
            expected=expected,
            value=actual,
        )

    for index, item in enumerate(inventory_events):
        kind = item.get("kind")
        signal = EXPECTED_SIGNAL_BY_KIND.get(str(kind))
        if signal is None:
            continue
        if item.get("stable_name") != signal["stable_name"]:
            add(blockers, "public_gameplay_inventory_stable_name_mismatch", f"{label}.event_kinds[{index}]", kind=kind)
        if item.get("event_kind_mask") != signal["event_kind_mask"]:
            add(blockers, "public_gameplay_inventory_event_mask_mismatch", f"{label}.event_kinds[{index}]", kind=kind)
        if list(item.get("field_mask") or []) != signal["field_mask"]:
            add(blockers, "public_gameplay_inventory_field_mask_mismatch", f"{label}.event_kinds[{index}]", kind=kind)
        actual_flags = set(item.get("required_flags") or [])
        if actual_flags != EXPECTED_REQUIRED_FLAGS:
            add(
                blockers,
                "public_gameplay_inventory_required_flags_mismatch",
                f"{label}.event_kinds[{index}].required_flags",
                kind=kind,
                expected=sorted(EXPECTED_REQUIRED_FLAGS),
                value=sorted(actual_flags),
            )

    event_descriptor = find_gameplay_policy_event_descriptor(payload)
    if not isinstance(event_descriptor, dict):
        add(blockers, "gameplay_policy_event_descriptor_missing", f"{label}.metadata_surfaces")
    else:
        descriptor_flags = set(event_descriptor.get("flags") or [])
        missing_descriptor_flags = sorted(EXPECTED_REQUIRED_FLAGS - descriptor_flags)
        if missing_descriptor_flags:
            add(
                blockers,
                "gameplay_policy_event_descriptor_required_flags_missing",
                f"{label}.metadata_surfaces.gameplay_policy_event_descriptors.flags",
                missing=missing_descriptor_flags,
            )

    resource_descriptor = find_resource_descriptor(payload)
    if not isinstance(resource_descriptor, dict):
        add(blockers, "resource_descriptor_missing", f"{label}.metadata_surfaces")
    else:
        scope = str(resource_descriptor.get("scope") or "")
        for term in ("metadata-only", "no identity", "no lookup", "no handle", "no cross-event correlation", "no mutation"):
            if term not in scope:
                add(blockers, "resource_descriptor_scope_guardrail_missing", f"{label}.metadata_surfaces.resource_kind.scope", term=term, value=scope)
        flags = set(resource_descriptor.get("flags") or [])
        required_flags = {
            "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY",
            "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY",
            "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP",
        }
        if not required_flags.issubset(flags):
            add(
                blockers,
                "resource_descriptor_category_only_flags_missing",
                f"{label}.metadata_surfaces.resource_kind.flags",
                missing=sorted(required_flags - flags),
            )

    inventory_kind = find_inventory_resource_kind(payload)
    if not isinstance(inventory_kind, dict):
        add(blockers, "inventory_resource_kind_descriptor_missing", f"{label}.metadata_surfaces.resource_kinds")
    else:
        require_equal(inventory_kind, "stable_name", "inventory_item", f"{label}.resource_kinds.inventory_item", blockers)
        require_equal(inventory_kind, "supported_gameplay_policy_event_mask", ALL_INVENTORY_MASK, f"{label}.resource_kinds.inventory_item", blockers)
        actual_fields = set(inventory_kind.get("supported_gameplay_policy_field_mask") or [])
        if actual_fields != EXPECTED_SIGNAL_FIELDS:
            add(
                blockers,
                "inventory_resource_kind_supported_fields_mismatch",
                f"{label}.resource_kinds.inventory_item.supported_gameplay_policy_field_mask",
                expected=sorted(EXPECTED_SIGNAL_FIELDS),
                value=sorted(actual_fields),
            )

    scan_public_claim_terms(payload, blockers, label)
    scan_readiness_claims(payload, blockers, label)
    return {"inventory_event_kinds": sorted(item["kind"] for item in actual if item.get("kind"))}


def validate_public_sdk_surfaces(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    label = "$.public_sdk_surfaces"
    require_equal(payload, "schema", PUBLIC_SDK_SURFACES_SCHEMA, label, blockers)
    require_false(payload, "v1_completion_required", label, blockers)
    stable_contract = payload.get("stable_release_contract")
    if not isinstance(stable_contract, dict):
        add(blockers, "stable_release_contract_missing", f"{label}.stable_release_contract")
    else:
        require_false(stable_contract, "claim_allowed", f"{label}.stable_release_contract", blockers)

    promoted = set(payload.get("promoted_surfaces") or [])
    experimental = set(payload.get("experimental_surfaces") or [])
    if SURFACE in promoted:
        add(blockers, "inventory_copied_surface_in_promoted_surfaces", f"{label}.promoted_surfaces")
    if SURFACE not in experimental:
        add(blockers, "inventory_copied_surface_missing_from_experimental_surfaces", f"{label}.experimental_surfaces")

    surface = find_surface(payload, SURFACE)
    if surface is None:
        add(blockers, "inventory_copied_surface_missing", f"{label}.surfaces")
    else:
        require_equal(surface, "status", "promoted-experimental-only", f"{label}.{SURFACE}", blockers)
        require_equal(surface, "support_tier", "promoted-experimental-only copied-data seed", f"{label}.{SURFACE}", blockers)
        if list(surface.get("public_contract") or []) != list(EXPECTED_PUBLIC_CONTRACT):
            add(
                blockers,
                "inventory_copied_surface_public_contract_mismatch",
                f"{label}.{SURFACE}.public_contract",
                expected=list(EXPECTED_PUBLIC_CONTRACT),
                value=surface.get("public_contract"),
            )
        payload_contract = tuple(surface.get("payload_contract") or [])
        if payload_contract != EXPECTED_SURFACE_PAYLOAD_CONTRACT:
            add(
                blockers,
                "inventory_copied_payload_contract_mismatch",
                f"{label}.{SURFACE}.payload_contract",
                expected=list(EXPECTED_SURFACE_PAYLOAD_CONTRACT),
                value=list(payload_contract),
            )
        exclusions = set(surface.get("exclusions") or [])
        missing = sorted(REQUIRED_FORBIDDEN_TERMS - exclusions)
        if missing:
            add(blockers, "inventory_copied_surface_exclusions_missing", f"{label}.{SURFACE}.exclusions", missing=missing)
        evidence = surface.get("evidence")
        if not isinstance(evidence, dict):
            add(blockers, "inventory_copied_surface_evidence_missing", f"{label}.{SURFACE}.evidence")
        else:
            readiness_target_sets = tuple(evidence.get("release_readiness_target_sets") or [])
            if readiness_target_sets != EXPECTED_INVENTORY_RELEASE_READINESS_TARGET_SETS:
                add(
                    blockers,
                    "inventory_copied_release_readiness_target_sets_mismatch",
                    f"{label}.{SURFACE}.evidence.release_readiness_target_sets",
                    expected=list(EXPECTED_INVENTORY_RELEASE_READINESS_TARGET_SETS),
                    value=list(readiness_target_sets),
                )
        scan_public_claim_terms(surface, blockers, f"{label}.{SURFACE}")

    mutation_surface = find_surface(payload, INVENTORY_MUTATION_SURFACE)
    if mutation_surface is None:
        add(blockers, "inventory_mutation_surface_missing", f"{label}.surfaces")
    else:
        require_equal(mutation_surface, "status", "post-v1", f"{label}.{INVENTORY_MUTATION_SURFACE}", blockers)
        if mutation_surface.get("public_contract") not in ([], None):
            add(
                blockers,
                "inventory_mutation_surface_public_contract_not_empty",
                f"{label}.{INVENTORY_MUTATION_SURFACE}.public_contract",
                value=mutation_surface.get("public_contract"),
            )

    resource_handle_surface = find_surface(payload, RESOURCE_HANDLE_SURFACE)
    if resource_handle_surface is None:
        add(blockers, "resource_handle_surface_missing", f"{label}.surfaces")
    else:
        require_equal(resource_handle_surface, "status", "post-v1", f"{label}.{RESOURCE_HANDLE_SURFACE}", blockers)
        if resource_handle_surface.get("public_contract") not in ([], None):
            add(
                blockers,
                "resource_handle_surface_public_contract_not_empty",
                f"{label}.{RESOURCE_HANDLE_SURFACE}.public_contract",
                value=resource_handle_surface.get("public_contract"),
            )

    scan_public_sdk_surfaces_inventory_side_lane_claims(payload, blockers, label)
    scan_readiness_claims(payload, blockers, label)
    return {"inventory_copied_status": surface.get("status") if isinstance(surface, dict) else None}


def scan_readiness_claims(value: Any, blockers: list[dict[str, Any]], trail: str) -> None:
    forbidden_true_keys = {
        "inventory_sdk_ready",
        "items_sdk_ready",
        "promotion_ready",
        "public_abi_ready",
        "public_inventory_sdk_ready",
        "public_items_sdk_ready",
        "public_sdk_ready",
        "release_ready",
        "runtime_ready",
        "stable_sdk_ready",
        "v1_completion_ready",
        "v1_ready",
        "v1_sdk_ready",
    }
    readiness_text_keys = forbidden_true_keys | {
        "inventory_sdk_readiness",
        "items_sdk_readiness",
        "promotion_readiness",
        "public_abi_readiness",
        "public_inventory_sdk_readiness",
        "public_items_sdk_readiness",
        "public_sdk_readiness",
        "release_readiness",
        "runtime_readiness",
        "stable_sdk_readiness",
        "v1_completion_readiness",
        "v1_readiness",
        "v1_sdk_readiness",
    }
    positive_readiness_phrases = (
        "inventory sdk ready",
        "items sdk ready",
        "promotion ready",
        "public abi ready",
        "public sdk ready",
        "release ready",
        "runtime ready",
        "runtime readiness",
        "stable sdk ready",
        "v1 completion ready",
        "v1 ready",
        "v1 sdk ready",
    )
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if key in forbidden_true_keys and child is True:
                add(blockers, "readiness_claim_enabled", child_trail)
            if key in readiness_text_keys and isinstance(child, str):
                normalized = child.lower()
                for phrase in positive_readiness_phrases:
                    start = normalized.find(phrase)
                    if start < 0:
                        continue
                    end = start + len(phrase)
                    if is_negated_for_match(child, start, end):
                        continue
                    add(blockers, "readiness_claim_enabled", child_trail, value=child, term=phrase)
                    break
            scan_readiness_claims(child, blockers, child_trail)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            scan_readiness_claims(child, blockers, f"{trail}[{index}]")


def extract_define_symbols(text: str) -> set[str]:
    return set(re.findall(r"^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\b", text, flags=re.MULTILINE))


def extract_define_body(text: str, symbol: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not re.match(rf"\s*#\s*define\s+{re.escape(symbol)}\b", line):
            continue
        body_lines = [line]
        cursor = index
        while body_lines[-1].rstrip().endswith("\\") and cursor + 1 < len(lines):
            cursor += 1
            body_lines.append(lines[cursor])
        return "\n".join(body_lines)
    return ""


def validate_public_header(path: Path, decisions: dict[str, Any] | None, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    label = "$.public_header"
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        add(blockers, "public_header_unreadable", label, path=str(path), error=str(exc))
        return {"inventory_event_kinds": []}

    code = strip_c_comments(raw_text)
    define_symbols = extract_define_symbols(code)
    event_kinds = set(re.findall(r"\b(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_[A-Z0-9_]+)\b", code))
    event_masks = set(re.findall(r"\b(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_[A-Z0-9_]+)\b", code))

    if event_kinds != EXPECTED_SIGNAL_KINDS:
        add(
            blockers,
            "public_header_inventory_event_kinds_mismatch",
            label,
            expected=sorted(EXPECTED_SIGNAL_KINDS),
            value=sorted(event_kinds),
        )

    if event_masks != set(EXPECTED_SIGNAL_MASKS):
        add(
            blockers,
            "public_header_inventory_event_masks_mismatch",
            label,
            expected=sorted(EXPECTED_SIGNAL_MASKS),
            value=sorted(event_masks),
        )

    all_inventory_body = extract_define_body(code, ALL_INVENTORY_MASK)
    for mask in EXPECTED_SIGNAL_MASKS:
        if mask not in all_inventory_body:
            add(blockers, "public_header_all_inventory_mask_missing_signal", label, mask=mask)
    extra_masks_in_all = sorted(set(re.findall(r"\b(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_[A-Z0-9_]+)\b", all_inventory_body)) - EXPECTED_SIGNAL_MASKS - {ALL_INVENTORY_MASK})
    if extra_masks_in_all:
        add(blockers, "public_header_all_inventory_mask_extra_signal", label, extra=extra_masks_in_all)

    missing_defines = sorted((EXPECTED_SIGNAL_MASKS | {ALL_INVENTORY_MASK}) - define_symbols)
    if missing_defines:
        add(blockers, "public_header_expected_inventory_mask_defines_missing", label, missing=missing_defines)

    for term in REQUIRED_FORBIDDEN_TERMS:
        if re.search(rf"\b{re.escape(term)}\b", code, re.IGNORECASE):
            add(blockers, "public_header_forbidden_inventory_claim_token", label, term=term)

    missing_listed_symbols: list[str] = []
    if decisions is not None:
        for symbol in decisions.get("public_header_symbols_now") or []:
            if not re.search(rf"\b{re.escape(str(symbol))}\b", code):
                missing_listed_symbols.append(str(symbol))
    if missing_listed_symbols:
        add(blockers, "public_header_symbols_now_missing_from_header", label, missing=sorted(missing_listed_symbols))

    return {"inventory_event_kinds": sorted(event_kinds), "inventory_event_masks": sorted(event_masks)}


def build_report(
    decisions_path: Path,
    public_sdk_surfaces_path: Path,
    public_gameplay_events_path: Path,
    public_header_path: Path,
) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    decisions = load_json(decisions_path, "decisions", blockers)
    public_sdk_surfaces = load_json(public_sdk_surfaces_path, "public_sdk_surfaces", blockers)
    public_gameplay_events = load_json(public_gameplay_events_path, "public_gameplay_events", blockers)

    summaries: dict[str, Any] = {}
    if decisions is not None:
        summaries["decisions"] = validate_decisions(decisions, blockers)
    if public_gameplay_events is not None:
        summaries["public_gameplay_events"] = validate_public_gameplay_events(public_gameplay_events, blockers)
    if public_sdk_surfaces is not None:
        summaries["public_sdk_surfaces"] = validate_public_sdk_surfaces(public_sdk_surfaces, blockers)
    summaries["public_header"] = validate_public_header(public_header_path, decisions, blockers)

    return {
        "schema": REPORT_SCHEMA,
        "ready": not blockers,
        "surface": SURFACE,
        "inputs": {
            "decisions": str(decisions_path),
            "public_sdk_surfaces": str(public_sdk_surfaces_path),
            "public_gameplay_events": str(public_gameplay_events_path),
            "public_header": str(public_header_path),
        },
        "summary": {
            "allowed_signal_count": len(EXPECTED_ALLOWED_SIGNALS),
            "allowed_signal_kinds": sorted(EXPECTED_SIGNAL_KINDS),
            "allowed_signal_masks": sorted(EXPECTED_SIGNAL_MASKS),
            "resource_kind_contract": "category-only metadata",
            "public_sdk_ready": False,
            "v1_completion_ready": False,
        },
        "checks": summaries,
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    report = build_report(
        args.decisions,
        args.public_sdk_surfaces,
        args.public_gameplay_events,
        args.public_header,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
