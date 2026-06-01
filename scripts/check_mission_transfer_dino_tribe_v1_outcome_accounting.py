#!/usr/bin/env python3
"""Validate v1 outcome accounting for mission/transfer/dino/tribe/buff.

This is an accounting guardrail, not a promotion checker.  The current repository
state is allowed to remain candidate-only/planning.  A v1 release statement that
uses this umbrella blocker must either exclude the umbrella and name every leaf as
excluded, or rely on a future manifest where every leaf is promoted with concrete
evidence.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
DEFAULT_SPLIT_NOTE = REPO_ROOT / "docs" / "research" / "2026-06-01-mission-transfer-dino-tribe-v1-split.md"
REPORT_SCHEMA = "obelisk.mission-transfer-dino-tribe-v1-outcome-accounting-check.v1"
SURFACE_ID = "obelisk.mission_transfer_dino_tribe.v1"
REQUIRED_LEAVES = ("mission", "transfer", "dino_policy", "tribe_policy", "buff_status")
LEAF_ALIASES = {
    "mission": ("mission",),
    "transfer": ("transfer",),
    "dino_policy": ("dino_policy", "dino policy", "dino"),
    "tribe_policy": ("tribe_policy", "tribe policy", "tribe"),
    "buff_status": ("buff_status", "buff/status", "buff status", "buff"),
}
PROMOTED_LEAF_EVIDENCE_KEYS = ("abi_tests", "sdk_consumer_tests", "second_source_evidence")
LEAF_MISSING_PUBLIC_GATES = {
    "mission": (
        "public_mission_sdk_abi",
        "runtime_observer_approval",
        "mission_identity_state_reward_authority",
        "dispatcher_lifecycle",
        "installed_sdk_consumer_tests",
        "mutation_return_override_policy",
    ),
    "transfer": (
        "public_transfer_sdk_abi",
        "transfer_payload_ownership",
        "downloaded_character_payload_contract",
        "dino_payload_contract",
        "player_identity",
        "cross_map_state_correlation",
        "ownership_policy",
        "teleport_spawn_authority",
        "runtime_wiring",
        "mutation_return_override_policy",
    ),
    "dino_policy": (
        "public_dino_sdk_abi",
        "dino_player_passenger_identity",
        "lookup_ownership_lifetime",
        "postcall_return_policy",
        "dispatcher_lifecycle",
        "runtime_observation",
        "privacy_contract",
        "resource_handle_policy",
        "mutation_return_override_policy",
    ),
    "tribe_policy": (
        "public_tribe_sdk_abi",
        "tribe_player_identity",
        "permission_semantics",
        "log_string_array_payload_policy",
        "online_list_payload_policy",
        "mission_tag_payload_policy",
        "dispatcher_lifecycle",
        "runtime_observation",
        "privacy_redaction_contract",
        "mutation_return_override_policy",
    ),
    "buff_status": (
        "public_buff_status_sdk_abi",
        "buff_class_object_redaction_contract",
        "copied_payload_policy",
        "lifecycle_stacking_invalidation_semantics",
        "refreshed_compact_evidence",
        "dispatcher_lifecycle",
        "runtime_observation",
        "resource_handle_policy",
        "mutation_return_override_policy",
    ),
}
NEGATIVE_EVIDENCE_RE = re.compile(
    r"\b(?:candidate[- ]?only|consume[- ]?only|planning[- ]?only|not promoted|"
    r"promotion[_ -]?ready\s*[:=]\s*false|public[_ -]?sdk[_ -]?ready\s*[:=]\s*false|"
    r"runtime[_ -]?ready\s*[:=]\s*false)\b",
    re.IGNORECASE,
)
FORBIDDEN_CLAIM_PATTERNS = (
    r"\b(?:Mission|Transfer|Dino|Tribe|Buff(?:/status| status)?|BuffStatus)\s+(?:SDK|API)\b",
    r"\bidentity\b",
    r"\blookup\b",
    r"\bmutation\b",
    r"\breturn[- ]override\b",
    r"\bruntime\s+hook\b",
    r"\bResourceHandle\b",
    r"\bteleport\s*/\s*spawn\b",
    r"\bteleport[- ]spawn\b",
    r"\bteleport\b",
    r"\bspawn\b",
    r"\bownership\s+lookup\b",
    r"\bcross[- ]map\s+correlation\b",
)
FORBIDDEN_CLAIM_RE = re.compile("|".join(f"(?:{pattern})" for pattern in FORBIDDEN_CLAIM_PATTERNS), re.IGNORECASE)
NEGATOR_RE = re.compile(
    r"\b(?:cannot|does\s+not|do\s+not|is\s+not|are\s+not|"
    r"must\s+not|no|not|without)\b",
    re.IGNORECASE,
)
AFTER_NEGATOR_RE = re.compile(
    r"\b(?:blocked|excluded|not\s+included|post-v1|post v1)\b",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="docs/public_sdk_surfaces.json path.")
    parser.add_argument("--split-note", type=Path, default=DEFAULT_SPLIT_NOTE, help="Leaf split research note path.")
    parser.add_argument("--release-statement", type=Path, help="Optional reviewed v1 release statement.")
    parser.add_argument("--json", action="store_true", help="Emit a JSON report.")
    return parser.parse_args()


def add(blockers: list[dict[str, Any]], reason: str, label: str, **extra: Any) -> None:
    item = {"reason": reason, "label": label}
    item.update(extra)
    blockers.append(item)


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"{label}: unreadable: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{label}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{label}: top-level JSON must be an object")
    return payload


def surface_by_id(manifest: dict[str, Any], surface_id: str) -> dict[str, Any] | None:
    surfaces = manifest.get("surfaces")
    if not isinstance(surfaces, list):
        return None
    for surface in surfaces:
        if isinstance(surface, dict) and surface.get("id") == surface_id:
            return surface
    return None


def read_optional(path: Path | None, label: str) -> str:
    if path is None:
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"{label}: unreadable: {exc}") from exc


def leaf_map(surface: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    units = surface.get("leaf_decision_units")
    if not isinstance(units, list):
        add(blockers, "leaf_decision_units_missing", "$.surfaces[mission_transfer_dino_tribe].leaf_decision_units")
        return {}
    leaves: dict[str, dict[str, Any]] = {}
    duplicate_ids: list[str] = []
    for index, leaf in enumerate(units):
        if not isinstance(leaf, dict):
            add(blockers, "leaf_decision_unit_not_object", f"$.leaf_decision_units[{index}]")
            continue
        leaf_id = leaf.get("id")
        if not isinstance(leaf_id, str):
            add(blockers, "leaf_decision_unit_id_missing", f"$.leaf_decision_units[{index}].id")
            continue
        if leaf_id in leaves:
            duplicate_ids.append(leaf_id)
        leaves[leaf_id] = leaf
    if duplicate_ids:
        add(blockers, "leaf_decision_units_duplicate", "$.leaf_decision_units", duplicate_ids=sorted(duplicate_ids))
    observed = set(leaves)
    required = set(REQUIRED_LEAVES)
    if observed != required:
        add(
            blockers,
            "leaf_decision_units_mismatch",
            "$.leaf_decision_units",
            expected=list(REQUIRED_LEAVES),
            observed=[leaf_id for leaf_id in REQUIRED_LEAVES if leaf_id in observed]
            + sorted(observed - required),
            missing=sorted(required - observed),
            extra=sorted(observed - required),
        )
    return leaves


def flattened_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        items: list[str] = []
        for child in value.values():
            items.extend(flattened_strings(child))
        return items
    if isinstance(value, list):
        items = []
        for child in value:
            items.extend(flattened_strings(child))
        return items
    return []


def string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    if isinstance(value, str):
        return [value]
    return []


def public_contract(surface_or_leaf: dict[str, Any]) -> list[str]:
    contract = surface_or_leaf.get("public_contract", [])
    return contract if isinstance(contract, list) else ["<public_contract is not a list>"]


def claim_is_negated(text: str, start: int, end: int) -> bool:
    clause_start = max(text.rfind(".", 0, start), text.rfind("\n", 0, start), text.rfind(";", 0, start)) + 1
    clause_prefix = text[clause_start:start]
    if re.match(r"\s*No\b", clause_prefix, re.IGNORECASE):
        return True
    before = text[max(0, start - 40) : start]
    after = text[end : min(len(text), end + 80)]
    return bool(NEGATOR_RE.search(before) or AFTER_NEGATOR_RE.search(after))


def forbidden_claims(text: str) -> list[str]:
    claims: list[str] = []
    for match in FORBIDDEN_CLAIM_RE.finditer(text):
        if claim_is_negated(text, match.start(), match.end()):
            continue
        claims.append(match.group(0))
    return claims


def validate_split_note(text: str, blockers: list[dict[str, Any]]) -> None:
    if SURFACE_ID not in text:
        add(blockers, "split_note_surface_missing", "$.split_note")
    for leaf in REQUIRED_LEAVES:
        if leaf not in text:
            add(blockers, "split_note_leaf_missing", "$.split_note", leaf=leaf)
    required_non_claims = (
        "does not promote a public SDK",
        "Public SDK promotion remains blocked for all five leaves",
    )
    for phrase in required_non_claims:
        if phrase not in text:
            add(blockers, "split_note_non_claim_missing", "$.split_note", phrase=phrase)


def release_statement_outcome(text: str) -> dict[str, Any]:
    if not text:
        return {
            "present": False,
            "umbrella_excluded": False,
            "leaf_exclusions": {},
            "leaf_promotions": {},
            "forbidden_claims": [],
        }
    surface_line = next((line for line in text.splitlines() if SURFACE_ID in line), "")
    leaf_exclusions = {}
    leaf_promotions = {}
    for leaf, aliases in LEAF_ALIASES.items():
        alias_excluded = False
        alias_promoted = False
        for alias in aliases:
            pattern_excluded = re.compile(
                rf"\b{re.escape(alias)}\b.{{0,100}}\bexcluded\b",
                re.IGNORECASE,
            )
            pattern_promoted = re.compile(
                rf"\b{re.escape(alias)}\b.{{0,100}}\bpromoted\b",
                re.IGNORECASE,
            )
            alias_excluded = alias_excluded or bool(pattern_excluded.search(text))
            alias_promoted = alias_promoted or bool(pattern_promoted.search(text))
        leaf_exclusions[leaf] = alias_excluded
        leaf_promotions[leaf] = alias_promoted
    return {
        "present": True,
        "umbrella_excluded": SURFACE_ID in text and bool(re.search(r"\bexcluded\b", surface_line, re.IGNORECASE)),
        "leaf_exclusions": leaf_exclusions,
        "leaf_promotions": leaf_promotions,
        "forbidden_claims": sorted(set(forbidden_claims(text))),
    }


def evidence_for_leaf(surface: dict[str, Any], leaf: dict[str, Any]) -> dict[str, Any]:
    evidence = leaf.get("evidence")
    if isinstance(evidence, dict):
        return evidence
    per_leaf = surface.get("promotion_evidence_by_leaf")
    leaf_id = leaf.get("id")
    if isinstance(per_leaf, dict) and isinstance(per_leaf.get(leaf_id), dict):
        return per_leaf[leaf_id]
    return {}


def validate_promoted_leaf_evidence(surface: dict[str, Any], leaves: dict[str, dict[str, Any]], blockers: list[dict[str, Any]]) -> bool:
    all_promoted = bool(leaves) and all(leaf.get("status") == "promoted" for leaf in leaves.values())
    any_promoted = any(leaf.get("status") == "promoted" for leaf in leaves.values())
    if any_promoted and not all_promoted:
        add(blockers, "partial_leaf_promotion_not_allowed", "$.leaf_decision_units")
        return False
    if not all_promoted:
        return False
    for leaf_id in REQUIRED_LEAVES:
        leaf = leaves[leaf_id]
        evidence = evidence_for_leaf(surface, leaf)
        label = f"$.leaf_decision_units[{leaf_id}].evidence"
        if not evidence:
            add(blockers, "promoted_leaf_evidence_missing", label, leaf=leaf_id)
            continue
        for key in ("promotion_status", "public_sdk_ready", "promotion_ready", "runtime_ready"):
            expected: Any = "promoted" if key == "promotion_status" else True
            if evidence.get(key) != expected:
                add(blockers, f"promoted_leaf_{key}_mismatch", f"{label}.{key}", leaf=leaf_id)
        for key in PROMOTED_LEAF_EVIDENCE_KEYS:
            values = evidence.get(key)
            if not isinstance(values, list) or not values:
                add(blockers, "promoted_leaf_real_evidence_missing", f"{label}.{key}", leaf=leaf_id)
        joined = "\n".join(flattened_strings(evidence))
        if NEGATIVE_EVIDENCE_RE.search(joined):
            add(blockers, "promoted_leaf_evidence_contains_candidate_only_markers", label, leaf=leaf_id)
    return True


def validate_public_contracts(
    surface: dict[str, Any],
    leaves: dict[str, dict[str, Any]],
    blockers: list[dict[str, Any]],
    excluded_route: bool,
) -> None:
    surface_contract = public_contract(surface)
    if excluded_route and surface_contract:
        add(blockers, "excluded_surface_public_contract_not_empty", "$.surface.public_contract")
    for claim in forbidden_claims("\n".join(surface_contract)):
        add(blockers, "public_contract_forbidden_claim", "$.surface.public_contract", claim=claim)
    for leaf_id, leaf in leaves.items():
        contract = public_contract(leaf)
        if excluded_route and contract:
            add(blockers, "excluded_leaf_public_contract_not_empty", f"$.leaf_decision_units[{leaf_id}].public_contract", leaf=leaf_id)
        for claim in forbidden_claims("\n".join(contract)):
            add(blockers, "leaf_public_contract_forbidden_claim", f"$.leaf_decision_units[{leaf_id}].public_contract", leaf=leaf_id, claim=claim)


def leaf_accounted_by(route: str, leaf_id: str, leaf: dict[str, Any], outcome: dict[str, Any]) -> str | None:
    if route == "per_leaf_promoted" and leaf.get("status") == "promoted":
        return "promoted_leaf_evidence"
    if route == "manifest_umbrella_excluded" and leaf.get("status") == "excluded":
        return "manifest_leaf_exclusion"
    if route == "release_statement_umbrella_excluded" and outcome["leaf_exclusions"].get(leaf_id):
        return "release_statement_leaf_exclusion"
    if leaf.get("status") == "excluded":
        return "manifest_leaf_exclusion_pending_acceptance"
    if outcome["leaf_exclusions"].get(leaf_id):
        return "release_statement_leaf_exclusion_pending_acceptance"
    return None


def build_leaf_family_accounting(
    surface: dict[str, Any],
    leaves: dict[str, dict[str, Any]],
    outcome: dict[str, Any],
    route: str,
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    gaps: dict[str, Any] = {}
    missing_leaf_families: list[str] = []
    non_promoted_leaf_families: list[str] = []
    missing_public_gate_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}

    surface_evidence = surface.get("evidence") if isinstance(surface.get("evidence"), dict) else {}
    planning_target_sets = string_list(surface_evidence.get("planning_target_sets") if isinstance(surface_evidence, dict) else None)

    for leaf_id in REQUIRED_LEAVES:
        leaf = leaves.get(leaf_id, {})
        status = leaf.get("status") if isinstance(leaf.get("status"), str) else "missing"
        status_counts[status] = status_counts.get(status, 0) + 1
        accounted_by = leaf_accounted_by(route, leaf_id, leaf, outcome)
        missing_public_gates = list(LEAF_MISSING_PUBLIC_GATES.get(leaf_id, ()))
        if not accounted_by:
            missing_leaf_families.append(leaf_id)
        if status != "promoted":
            non_promoted_leaf_families.append(leaf_id)
        missing_public_gate_counts[leaf_id] = 0 if accounted_by == "promoted_leaf_evidence" else len(missing_public_gates)
        gaps[leaf_id] = {
            "status": status,
            "v1_accounted": accounted_by is not None,
            "accounted_by": accounted_by,
            "release_statement_excluded": bool(outcome["leaf_exclusions"].get(leaf_id)),
            "release_statement_promoted": bool(outcome["leaf_promotions"].get(leaf_id)),
            "current_evidence": string_list(leaf.get("current_evidence")),
            "current_blocker": leaf.get("current_blocker") if isinstance(leaf.get("current_blocker"), str) else None,
            "allowed_v1_outcome": leaf.get("allowed_v1_outcome") if isinstance(leaf.get("allowed_v1_outcome"), str) else None,
            "missing_public_gates": [] if accounted_by == "promoted_leaf_evidence" else missing_public_gates,
        }

    missing_gate_catalog = sorted(set(REQUIRED_LEAVES) - set(LEAF_MISSING_PUBLIC_GATES))
    if missing_gate_catalog:
        add(blockers, "leaf_family_missing_gate_catalog", "$.checker.leaf_family_accounting", missing=missing_gate_catalog)

    return {
        "mode": route,
        "result": "all_leaf_families_accounted" if not missing_leaf_families else "leaf_families_missing_v1_outcomes",
        "accepted_for_internal_planning": route == "candidate_only" and not blockers,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "promotion_ready": route == "per_leaf_promoted" and not blockers,
        "planning_target_sets": planning_target_sets,
        "missing_leaf_families": missing_leaf_families,
        "non_promoted_leaf_families": non_promoted_leaf_families,
        "missing_public_gate_counts": missing_public_gate_counts,
        "status_counts": status_counts,
        "leaf_family_gaps": gaps,
        "guardrail": (
            "candidate-only accounting names missing leaf outcomes and public gates; "
            "it does not promote public SDK, runtime, identity, lookup, mutation, return override, ResourceHandle, or teleport/spawn"
        ),
    }


def build_report(manifest_path: Path, split_note_path: Path, release_statement_path: Path | None = None) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    manifest = load_json(manifest_path, "manifest")
    split_note = read_optional(split_note_path, "split_note")
    release_statement = read_optional(release_statement_path, "release_statement")
    validate_split_note(split_note, blockers)

    if manifest.get("schema") != "obelisk.public-sdk-surfaces.v1":
        add(blockers, "manifest_schema_mismatch", "$.schema")
    surface = surface_by_id(manifest, SURFACE_ID)
    if surface is None:
        add(blockers, "surface_missing", "$.surfaces")
        surface = {"id": SURFACE_ID, "leaf_decision_units": []}
    leaves = leaf_map(surface, blockers)
    outcome = release_statement_outcome(release_statement)

    manifest_umbrella_excluded = surface.get("status") == "excluded" and all(
        leaves.get(leaf_id, {}).get("status") == "excluded" for leaf_id in REQUIRED_LEAVES
    )
    statement_umbrella_excluded = outcome["present"] and outcome["umbrella_excluded"] and all(
        outcome["leaf_exclusions"].get(leaf_id) for leaf_id in REQUIRED_LEAVES
    )
    all_promoted = validate_promoted_leaf_evidence(surface, leaves, blockers)

    if outcome["forbidden_claims"]:
        add(
            blockers,
            "release_statement_forbidden_claims",
            "$.release_statement",
            claims=outcome["forbidden_claims"],
        )
    if outcome["present"] and not statement_umbrella_excluded and not all_promoted:
        missing = [leaf_id for leaf_id in REQUIRED_LEAVES if not outcome["leaf_exclusions"].get(leaf_id)]
        if not outcome["umbrella_excluded"]:
            add(blockers, "release_statement_umbrella_exclusion_missing", "$.release_statement", surface=SURFACE_ID)
        if missing:
            add(blockers, "release_statement_leaf_exclusions_missing", "$.release_statement", missing=missing)
    if surface.get("status") == "excluded" and not manifest_umbrella_excluded:
        add(blockers, "manifest_excluded_route_missing_leaf_exclusions", "$.leaf_decision_units")

    excluded_route = manifest_umbrella_excluded or statement_umbrella_excluded
    validate_public_contracts(surface, leaves, blockers, excluded_route=excluded_route)

    if all_promoted:
        route = "per_leaf_promoted"
    elif statement_umbrella_excluded:
        route = "release_statement_umbrella_excluded"
    elif manifest_umbrella_excluded:
        route = "manifest_umbrella_excluded"
    else:
        route = "candidate_only"
    leaf_family_accounting = build_leaf_family_accounting(surface, leaves, outcome, route, blockers)

    return {
        "schema": REPORT_SCHEMA,
        "surface": SURFACE_ID,
        "ready": not blockers,
        "accounting_route": route,
        "v1_accounted": route in {"release_statement_umbrella_excluded", "manifest_umbrella_excluded", "per_leaf_promoted"},
        "candidate_only": route == "candidate_only",
        "promotion_ready": all_promoted and not blockers,
        "public_sdk_ready": all_promoted and not blockers,
        "runtime_ready": all_promoted and not blockers,
        "required_leaves": list(REQUIRED_LEAVES),
        "observed_leaves": [leaf_id for leaf_id in REQUIRED_LEAVES if leaf_id in leaves],
        "leaf_statuses": {leaf_id: leaves.get(leaf_id, {}).get("status") for leaf_id in REQUIRED_LEAVES},
        "candidate_only_accounting": leaf_family_accounting,
        "missing_leaf_families": leaf_family_accounting["missing_leaf_families"],
        "release_statement": outcome,
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
        "non_claims": [
            "candidate-only accounting does not add Mission, Transfer, Dino, Tribe, or Buff APIs",
            "candidate-only accounting does not add identity, lookup, mutation, return override, runtime hook, ResourceHandle, teleport/spawn, ownership lookup, or cross-map correlation",
        ],
    }


def main() -> int:
    args = parse_args()
    report = build_report(args.manifest, args.split_note, args.release_statement)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif report["ready"]:
        print(f"{SURFACE_ID}: {report['accounting_route']} accounting accepted")
    else:
        for blocker in report["blocker_details"]:
            print(f"{blocker['reason']}: {blocker['label']}", file=sys.stderr)
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
