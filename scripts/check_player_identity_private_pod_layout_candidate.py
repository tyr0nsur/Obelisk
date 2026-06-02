#!/usr/bin/env python3
"""Validate candidate-only private POD layout evidence for player identity."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SCHEMA = "obelisk.player-identity-private-pod-layout-candidate.v1"
REPORT_SCHEMA = "obelisk.player-identity-private-pod-layout-candidate-check.v1"
SURFACE = "obelisk.player_identity.v1"
RESOLVED_INPUT = "abi.public_pod_contract.private_layout_candidate"
DEFAULT_MANIFEST = Path("docs/research/player-identity-planning-sources/player-identity-private-pod-layout-candidate.json")
DEFAULT_PRIVATE_CONTRACT = Path("docs/research/2026-06-01-player-identity-private-candidate-contract.json")

EVENT_FIELDS = [
    ("abi_version", "uint32", 0, 4),
    ("struct_size", "uint32", 4, 4),
    ("event_kind", "uint64", 8, 8),
    ("principal_handle", "uint64", 16, 8),
    ("principal_generation", "uint64", 24, 8),
    ("principal_scope_flags", "uint64", 32, 8),
    ("principal_state_flags", "uint64", 40, 8),
    ("invalidation_reason_flags", "uint64", 48, 8),
    ("event_sequence", "uint64", 56, 8),
    ("server_process_epoch", "uint64", 64, 8),
    ("reserved", "uint64", 72, 8),
]
DESCRIPTOR_FIELDS = [
    ("abi_version", "uint32", 0, 4),
    ("struct_size", "uint32", 4, 4),
    ("supported_event_kind_mask", "uint64", 8, 8),
    ("supported_scope_flags", "uint64", 16, 8),
    ("supported_state_flags", "uint64", 24, 8),
    ("supported_invalidation_reason_flags", "uint64", 32, 8),
    ("contract_flags", "uint64", 40, 8),
]
REQUIRED_NON_CLAIMS = {
    "candidate-only private POD layout review input",
    "does not add public header symbols",
    "does not promote obelisk.player_identity.v1",
    "does not satisfy abi.layout public-header tests",
    "does not satisfy installed SDK consumer tests",
    "runtime evidence and public ABI promotion remain separate gates",
}
FORBIDDEN_POSITIVE_RE = re.compile(
    r"steam|eos|unique[_ -]?net|player[_ -]?data|player[_ -]?name|ipaddress|"
    r"tribe|resourcehandle|fname|gobjects|uobject|lookup|persist|mutat|return[_ -]?override",
    re.IGNORECASE,
)
NEGATIVE_RE = re.compile(r"does not|do not|no |not |forbidden|redact|without|remain separate", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--private-candidate-contract", type=Path, default=DEFAULT_PRIVATE_CONTRACT)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def add(blockers: list[dict[str, Any]], reason: str, label: str, **details: Any) -> None:
    item = {"reason": reason, "label": label}
    item.update(details)
    blockers.append(item)


def validate_false_flags(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    for key in (
        "promotion_ready",
        "public_sdk_ready",
        "runtime_ready",
        "public_header_allowed",
    ):
        if payload.get(key) is not False:
            add(blockers, f"{key}_not_false", f"$.{key}", value=payload.get(key))
    for key in ("public_header_symbols_now", "public_capability_bits_now", "public_callback_abi_now"):
        if payload.get(key) != []:
            add(blockers, f"{key}_not_empty", f"$.{key}", value=payload.get(key))


def field_tuples(layout: dict[str, Any]) -> list[tuple[Any, Any, Any, Any]]:
    fields = layout.get("fields")
    if not isinstance(fields, list):
        return []
    return [
        (
            field.get("name"),
            field.get("type"),
            field.get("offset"),
            field.get("size"),
        )
        for field in fields
        if isinstance(field, dict)
    ]


def validate_layout(
    payload: dict[str, Any],
    key: str,
    expected: list[tuple[str, str, int, int]],
    expected_size: int,
    blockers: list[dict[str, Any]],
    *,
    reserved_tail_required: bool,
) -> list[str]:
    layout = payload.get(key)
    if not isinstance(layout, dict):
        add(blockers, f"{key}_missing", f"$.{key}")
        return []
    if layout.get("candidate_only") is not True:
        add(blockers, f"{key}_candidate_only_not_true", f"$.{key}.candidate_only", value=layout.get("candidate_only"))
    if layout.get("struct_size") != expected_size:
        add(blockers, f"{key}_struct_size_mismatch", f"$.{key}.struct_size", value=layout.get("struct_size"))
    if layout.get("alignment") != 8:
        add(blockers, f"{key}_alignment_mismatch", f"$.{key}.alignment", value=layout.get("alignment"))
    observed = field_tuples(layout)
    if observed != expected:
        add(blockers, f"{key}_fields_mismatch", f"$.{key}.fields", expected=expected, observed=observed)
    names = [field[0] for field in observed]
    if names[:2] != ["abi_version", "struct_size"]:
        add(blockers, f"{key}_version_size_not_front_loaded", f"$.{key}.fields")
    if reserved_tail_required and (not names or names[-1] != "reserved"):
        add(blockers, f"{key}_reserved_tail_missing", f"$.{key}.fields")
    if reserved_tail_required:
        fields = layout.get("fields") if isinstance(layout.get("fields"), list) else []
        reserved = next((field for field in fields if isinstance(field, dict) and field.get("name") == "reserved"), None)
        if not isinstance(reserved, dict) or reserved.get("zero_required") is not True:
            add(blockers, f"{key}_reserved_zero_required_missing", f"$.{key}.fields")
    if len(names) != len(set(names)):
        add(blockers, f"{key}_duplicate_fields", f"$.{key}.fields")
    return [str(name) for name in names]


def validate_against_private_contract(
    event_names: list[str],
    descriptor_names: list[str],
    private_contract: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    if event_names != private_contract.get("candidate_event_payload_fields_or_equivalent"):
        add(blockers, "event_layout_private_contract_fields_mismatch", "$.event_payload_layout.fields")
    if descriptor_names != private_contract.get("candidate_descriptor_fields_or_equivalent"):
        add(blockers, "descriptor_layout_private_contract_fields_mismatch", "$.descriptor_layout.fields")


def walk_strings(value: Any, path: str = "$") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, str):
        found.append((path, value))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(walk_strings(item, f"{path}[{index}]"))
    elif isinstance(value, dict):
        for key, item in value.items():
            found.extend(walk_strings(key, f"{path}.{key}:key"))
            found.extend(walk_strings(item, f"{path}.{key}"))
    return found


def validate_no_positive_forbidden_terms(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    exposures = []
    for path, value in walk_strings(payload):
        if path.startswith("$.required_non_claims") or path.startswith("$.forbidden_public_terms"):
            continue
        if FORBIDDEN_POSITIVE_RE.search(value) and not NEGATIVE_RE.search(value):
            exposures.append({"path": path, "value": value})
    if exposures:
        add(blockers, "forbidden_public_term_exposure", "$", exposures=exposures)


def validate_manifest(payload: dict[str, Any], private_contract: dict[str, Any]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    if payload.get("schema") != SCHEMA:
        add(blockers, "schema_mismatch", "$.schema", value=payload.get("schema"))
    if payload.get("surface") != SURFACE:
        add(blockers, "surface_mismatch", "$.surface", value=payload.get("surface"))
    if payload.get("artifact_status") != "candidate_only":
        add(blockers, "artifact_status_not_candidate_only", "$.artifact_status")
    if payload.get("visibility") != "private_planning_contract":
        add(blockers, "visibility_mismatch", "$.visibility")
    if payload.get("candidate_only") is not True:
        add(blockers, "candidate_only_not_true", "$.candidate_only")
    if payload.get("accepted_for_contract_review") is not True:
        add(blockers, "accepted_for_contract_review_not_true", "$.accepted_for_contract_review")
    if payload.get("resolved_input") != RESOLVED_INPUT:
        add(blockers, "resolved_input_mismatch", "$.resolved_input", value=payload.get("resolved_input"))
    if payload.get("private_candidate_contract") != str(DEFAULT_PRIVATE_CONTRACT):
        add(blockers, "private_candidate_contract_path_mismatch", "$.private_candidate_contract")
    validate_false_flags(payload, blockers)
    model = payload.get("layout_model")
    if not isinstance(model, dict):
        add(blockers, "layout_model_missing", "$.layout_model")
    else:
        required_model = {
            "endianness": "little",
            "pointer_width": "none",
            "packing": "natural_c_abi_fixed_width_scalars",
            "max_alignment": 8,
            "append_only_after_promotion": True,
            "front_loaded_version_size": True,
            "reserved_tail_required": True,
            "reserved_zero_required": True,
        }
        for key, expected in required_model.items():
            if model.get(key) != expected:
                add(blockers, "layout_model_value_mismatch", f"$.layout_model.{key}", expected=expected, value=model.get(key))
    event_names = validate_layout(
        payload,
        "event_payload_layout",
        EVENT_FIELDS,
        80,
        blockers,
        reserved_tail_required=True,
    )
    descriptor_names = validate_layout(
        payload,
        "descriptor_layout",
        DESCRIPTOR_FIELDS,
        48,
        blockers,
        reserved_tail_required=False,
    )
    validate_against_private_contract(event_names, descriptor_names, private_contract, blockers)
    non_claims = payload.get("required_non_claims")
    if not isinstance(non_claims, list) or not REQUIRED_NON_CLAIMS.issubset(set(non_claims)):
        add(blockers, "required_non_claims_missing", "$.required_non_claims")
    forbidden_terms = payload.get("forbidden_public_terms")
    if not isinstance(forbidden_terms, list) or not forbidden_terms:
        add(blockers, "forbidden_public_terms_missing", "$.forbidden_public_terms")
    validate_no_positive_forbidden_terms(payload, blockers)
    if "reserved" not in event_names:
        add(blockers, "reserved_field_missing", "$.fields")
    return blockers


def build_report(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": REPORT_SCHEMA,
        "surface": SURFACE,
        "ready": not blockers,
        "accepted_for_contract_review": not blockers,
        "resolved_input": RESOLVED_INPUT if not blockers else None,
        "candidate_only": True,
        "layout_candidate_ready": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_header_allowed": False,
        "event_payload": {
            "struct_size": payload.get("event_payload_layout", {}).get("struct_size") if isinstance(payload.get("event_payload_layout"), dict) else None,
            "alignment": payload.get("event_payload_layout", {}).get("alignment") if isinstance(payload.get("event_payload_layout"), dict) else None,
            "fields": [field[0] for field in EVENT_FIELDS],
        },
        "descriptor": {
            "struct_size": payload.get("descriptor_layout", {}).get("struct_size") if isinstance(payload.get("descriptor_layout"), dict) else None,
            "alignment": payload.get("descriptor_layout", {}).get("alignment") if isinstance(payload.get("descriptor_layout"), dict) else None,
            "fields": [field[0] for field in DESCRIPTOR_FIELDS],
        },
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
        "non_claims": [
            "private POD layout candidate is review input only",
            "does not satisfy public abi.layout or SDK consumer coverage",
            "does not authorize runtime, public SDK, public header, permissions/admin, command response, lookup, persistence, mutation, or return override",
        ],
    }


def main() -> int:
    args = parse_args()
    payload = load_json(args.manifest)
    private_contract = load_json(args.private_candidate_contract)
    blockers = validate_manifest(payload, private_contract)
    report = build_report(payload, blockers)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif blockers:
        for blocker in blockers:
            print(f"{blocker['reason']}: {blocker['label']}", file=sys.stderr)
    else:
        print("player identity private POD layout candidate valid: review-only")
    return 0 if not blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
