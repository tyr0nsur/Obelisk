#!/usr/bin/env python3
"""Fail-closed checker for Structure build-policy offline intake accounting."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from artifact_identity import ARTIFACT_IDENTITY_KEYS, complete_artifact_identity, is_sha256
from reflection_target_sets import side_lane_fail_closed_source_artifact_issues
from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
REPORT_SCHEMA = "obelisk.structure-build-policy-offline-intake-check.v1"
READINESS_SCHEMA = "obelisk.reflection-snapshot-readiness.v1"
SNAPSHOT_SCHEMA = "obelisk.ufunction-chain.snapshot.v1"
SURFACE_ID = "obelisk.structure_census.v1"
TARGET_SET = "structure-build-policy-offline-intake"
EXPECTED_SURFACE_STATUSES = {"planning", "excluded"}
EXPECTED_SURFACE_SUPPORT_TIER = "blocked"
EXPECTED_STATUS = "planning-layout-second-source-accepted"
EXPECTED_READINESS_ENVELOPE = {
    "evidence_scope": "second_source_layout_evidence_only",
    "strict_identity_indices": False,
    "target_set_guidance": [],
}
EXPECTED_TOTALS = {
    "targets": 3,
    "comparable": 3,
    "second_source_accepted": 3,
    "blocked": 0,
}
EXPECTED_ZERO_TOTALS = {
    "second_source_rejected": 0,
    "second_source_inconclusive": 0,
    "second_source_missing": 0,
}
EXPECTED_READINESS_FLAGS = {
    "promotion_ready": False,
    "public_sdk_ready": False,
    "runtime_ready": False,
}
EXPECTED_TARGET_FILTERS = {
    "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToBuild",
    "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.BPIsAllowedToBuild",
    "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.BPIsAllowedToBuildEx",
}
EXPECTED_FIELD_SHAPES = {
    "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToBuild": {
        "outer_name": "PrimalStructure",
        "function_name": "IsAllowedToBuild",
        "function_flags": "0x4c20400",
        "num_parms": 8,
        "parms_size": 152,
        "properties": (
            {"name": "PC", "class_name": "ObjectProperty", "offset_internal": 0, "element_size": 8},
            {
                "name": "AtLocation",
                "class_name": "StructProperty",
                "offset_internal": 8,
                "element_size": 12,
                "struct_type": "Vector",
            },
            {
                "name": "AtRotation",
                "class_name": "StructProperty",
                "offset_internal": 20,
                "element_size": 12,
                "struct_type": "Rotator",
            },
            {
                "name": "OutPlacementData",
                "class_name": "StructProperty",
                "offset_internal": 32,
                "element_size": 96,
                "struct_type": "PlacementData",
            },
            {
                "name": "bDontAdjustForMaxRange",
                "class_name": "BoolProperty",
                "offset_internal": 128,
                "element_size": 1,
                "bool_field_size": 1,
                "bool_byte_offset": 0,
                "native_bool": False,
            },
            {
                "name": "PlayerViewRotation",
                "class_name": "StructProperty",
                "offset_internal": 132,
                "element_size": 12,
                "struct_type": "Rotator",
            },
            {
                "name": "bFinalPlacement",
                "class_name": "BoolProperty",
                "offset_internal": 144,
                "element_size": 1,
                "bool_field_size": 1,
                "bool_byte_offset": 0,
                "native_bool": False,
            },
            {"name": "ReturnValue", "class_name": "IntProperty", "offset_internal": 148, "element_size": 4},
        ),
    },
    "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.BPIsAllowedToBuild": {
        "outer_name": "PrimalStructure",
        "function_name": "BPIsAllowedToBuild",
        "function_flags": "0xc420c00",
        "num_parms": 3,
        "parms_size": 104,
        "properties": (
            {
                "name": "OutPlacementData",
                "class_name": "StructProperty",
                "offset_internal": 0,
                "element_size": 96,
                "struct_type": "PlacementData",
            },
            {"name": "CurrentAllowedReason", "class_name": "IntProperty", "offset_internal": 96, "element_size": 4},
            {"name": "ReturnValue", "class_name": "IntProperty", "offset_internal": 100, "element_size": 4},
        ),
    },
    "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.BPIsAllowedToBuildEx": {
        "outer_name": "PrimalStructure",
        "function_name": "BPIsAllowedToBuildEx",
        "function_flags": "0xc420c00",
        "num_parms": 6,
        "parms_size": 120,
        "properties": (
            {
                "name": "OutPlacementData",
                "class_name": "StructProperty",
                "offset_internal": 0,
                "element_size": 96,
                "struct_type": "PlacementData",
            },
            {"name": "CurrentAllowedReason", "class_name": "IntProperty", "offset_internal": 96, "element_size": 4},
            {"name": "PC", "class_name": "ObjectProperty", "offset_internal": 104, "element_size": 8},
            {
                "name": "bFinalPlacement",
                "class_name": "BoolProperty",
                "offset_internal": 112,
                "element_size": 1,
                "bool_field_size": 1,
                "bool_byte_offset": 0,
                "native_bool": False,
            },
            {
                "name": "bChoosingRotation",
                "class_name": "BoolProperty",
                "offset_internal": 113,
                "element_size": 1,
                "bool_field_size": 1,
                "bool_byte_offset": 0,
                "native_bool": False,
            },
            {"name": "ReturnValue", "class_name": "IntProperty", "offset_internal": 116, "element_size": 4},
        ),
    },
}
FIELD_REDACTION_POLICY = {
    "PC": "redacted_player_controller_context",
    "AtLocation": "redacted_location_context",
    "AtRotation": "redacted_rotation_context",
    "OutPlacementData": "redacted_placement_struct",
    "PlayerViewRotation": "redacted_player_view_context",
    "CurrentAllowedReason": "layout_only_reason_code_not_public_payload",
    "bDontAdjustForMaxRange": "layout_only_bool_not_public_payload",
    "bFinalPlacement": "layout_only_bool_not_public_payload",
    "bChoosingRotation": "layout_only_bool_not_public_payload",
    "ReturnValue": "layout_only_return_candidate_no_override",
}
EXPECTED_NON_CLAIM = (
    "planning-layout evidence only; does not promote StructureEvents, Structure SDK, "
    "build-policy SDK, enforcement, identity, lookup, mutation, return override, "
    "runtime hooks, or v1 completion"
)
REQUIRED_NON_CLAIM_TOKENS = (
    "planning-layout evidence only",
    "does not promote",
    "StructureEvents",
    "Structure SDK",
    "build-policy SDK",
    "enforcement",
    "identity",
    "lookup",
    "mutation",
    "return override",
    "runtime hooks",
    "v1 completion",
)
REQUIRED_BOUNDARIES = (
    "candidate-only",
    "sanitized UFunction layout comparison only",
    "no public StructureEvents SDK",
    "no build-policy SDK or enforcement",
    "no structure identity or lookup",
    "no mutation or return override",
    "public_sdk_ready=false",
)
REQUIRED_NOT_PROMOTED_SURFACES = {
    "lookup",
    "mutation",
    "object_identity",
    "public_sdk",
    "raw_params",
    "resource_handle",
    "return_override",
    "runtime_hooks",
}
EXPECTED_SNAPSHOT_ADDRESS_POLICY = "absolute core paths and addresses omitted; use full inspector JSON for local evidence review"
EXPECTED_SNAPSHOT_SOURCE = "offline_core"
EXPECTED_SNAPSHOT_GENERATOR = "scripts/inspect_core_ufunctions.py --snapshot-json"
SNAPSHOT_BASE_DIR = "base"
SNAPSHOT_CANDIDATE_DIR = "candidate"
FORBIDDEN_TRUE_READY_KEYS = {
    "approved_runtime_samples_ready",
    "build_policy_ready",
    "build_policy_sdk_ready",
    "complete_sdk_ready",
    "complete_sdk_readiness",
    "counts_toward_complete_sdk",
    "enforcement_ready",
    "identity_ready",
    "lookup_ready",
    "mutation_ready",
    "promotion_ready",
    "public_sdk_ready",
    "public_lookup_ready",
    "return_override_ready",
    "route_acceptance_ready",
    "route_accepted",
    "runtime_ready",
    "runtime_samples_approved",
    "sdk_progress",
    "sdk_progress_ready",
    "stable",
    "release_supported",
    "structure_events_ready",
    "structure_sdk_ready",
    "support_ready",
    "support_tier_active",
    "support_tier_ready",
    "runtime_support_active",
    "runtime_support_ready",
    "runtime_v1_support_active",
    "runtime_v1_support_ready",
    "umbrella_leaf_promoted",
    "umbrella_leaf_promotion_ready",
    "leaf_promotion_ready",
    "v1_complete",
    "v1_completion",
    "v1_ready",
}
FORBIDDEN_READY_DOMAINS = {
    "api",
    "buildpolicy",
    "callback",
    "collision",
    "completion",
    "dispatch",
    "dispatcher",
    "enforcement",
    "event",
    "events",
    "identity",
    "lookup",
    "mutation",
    "observer",
    "progress",
    "promotion",
    "promote",
    "promoted",
    "public",
    "pin",
    "pincode",
    "placement",
    "release",
    "return",
    "route",
    "routes",
    "runtime",
    "sample",
    "samples",
    "sdk",
    "stable",
    "structure",
    "structureevents",
    "structuresdk",
    "v1",
}
READY_TERMS = {
    "accepted",
    "approved",
    "complete",
    "completion",
    "counts",
    "done",
    "progress",
    "promoted",
    "promotion",
    "readiness",
    "ready",
    "supported",
    "released",
    "active",
    "available",
    "enabled",
}
FORBIDDEN_STRING_DOMAINS = {
    "public sdk": "public_sdk",
    "public sdk support": "public_sdk",
    "structure sdk": "structure_sdk",
    "structure events": "public_structure_events_sdk",
    "structureevents": "public_structure_events_sdk",
    "structureevents sdk": "public_structure_events_sdk",
    "public abi": "public_abi",
    "promotion gate": "promotion_gate",
    "approved runtime samples": "runtime_samples",
    "build placement": "build_placement_policy",
    "build policy": "build_policy",
    "collision policy": "no_collision_policy",
    "complete sdk readiness": "v1_completion",
    "counts toward complete sdk": "v1_completion",
    "enforcement allowed": "enforcement",
    "enforcement ready": "enforcement",
    "no collision": "no_collision_policy",
    "no-collision": "no_collision_policy",
    "owner lookup": "structure_ownership",
    "ownership lookup": "structure_ownership",
    "mutation readiness": "mutation",
    "public lookup": "public_lookup",
    "pin code outcome": "pin_code_policy",
    "pin outcome": "pin_code_policy",
    "pincode outcome": "pin_code_policy",
    "placement policy": "build_placement_policy",
    "release supported": "release_support",
    "release-supported": "release_support",
    "route accepted": "route_acceptance",
    "route acceptance": "route_acceptance",
    "runtime support": "runtime_support",
    "runtime sample": "runtime_samples",
    "runtime samples": "runtime_samples",
    "sdk progress": "sdk_progress",
    "stable sdk": "structure_sdk",
    "support tier": "support_tier",
    "umbrella leaf promoted": "umbrella_leaf_promotion",
    "umbrella leaf promotion": "umbrella_leaf_promotion",
    "leaf promoted": "umbrella_leaf_promotion",
    "leaf promotion": "umbrella_leaf_promotion",
    "v1 support": "v1_completion",
}
POSITIVE_STRING_CLAIM_RE = re.compile(
    r"(?:\baccepted\b|\bapproved\b|\bpromoted\b|\breleased\b|\bcomplete\b|\bdone\b|"
    r"\bactive\b|\bavailable\b|\benabled\b|\bsupported\b|"
    r"\brelease[-_\s]+supported\b|\bstable\b|\bcounts[-_\s]+toward[-_\s]+complete[-_\s]+sdk\b|"
    r"\bpublic[-_\s]+ready\b|\bprogress\b|\bready\b)",
    re.IGNORECASE,
)
NEGATED_TRUE_KEY_PREFIXES = (
    "must_block_",
    "must_remain_",
    "no_",
    "not_",
)
FORBIDDEN_TRUE_CLAIM_KEYS = {
    "enforcement",
    "enforcement_claim",
    "enforcement_ready",
    "exposed_payload",
    "exposes_payload",
    "exposes_public_payload",
    "public_payload",
    "public_payload_ready",
    "return_override",
    "return_override_claim",
    "return_override_ready",
    "runtime",
    "runtime_claim",
    "runtime_ready",
}
FORBIDDEN_RUNTIME_INPUT_KEYS = {
    "copied_payload",
    "dispatch_budget",
    "fname_indices",
    "hook_enabled",
    "observation_budget",
    "return_override",
    "runtime_name_indices",
}
PUBLIC_PAYLOAD_KEY_TOKENS = {
    "field",
    "fields",
    "param",
    "params",
    "parameter",
    "parameters",
    "payload",
    "range",
    "ranges",
}
PUBLIC_EXPOSURE_KEY_TOKENS = {
    "expose",
    "exposed",
    "exposes",
    "public",
}
FORBIDDEN_SNAPSHOT_KEYS = {
    "address",
    "chunks",
    "first_property",
    "fname_table",
    "gobjects",
    "integer_window",
    "native_func_candidate",
    "next_field",
    "next_property",
    "object",
    "pointer_window",
}
FIELD_VALUE_BEARING_KEY_TOKENS = {
    "payload",
    "range",
    "ranges",
    "value",
    "values",
}
FIELD_PUBLIC_KEY_TOKENS = {
    "expose",
    "exposed",
    "exposes",
    "public",
}
ADDRESS_RE = re.compile(r"0x[0-9a-fA-F]{6,}")
HEX_METADATA_KEYS = {"function_flags", "property_flags", "return_value_offset"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the Structure build-policy offline readiness report referenced by "
            "docs/public_sdk_surfaces.json without promoting public SDK or runtime readiness."
        )
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="public_sdk_surfaces.json path.")
    parser.add_argument(
        "--readiness",
        type=Path,
        help="Override readiness report path. The manifest entry is still validated.",
    )
    parser.add_argument("--json", action="store_true", help="Compatibility flag; output is always JSON.")
    return parser.parse_args()


def add(blockers: list[dict[str, Any]], reason: str, **details: Any) -> None:
    blockers.append({"reason": reason, **details})


def read_json(path: Path, blockers: list[dict[str, Any]], label: str) -> dict[str, Any] | None:
    safe_path = safe_read_path(path, blockers, label)
    if safe_path is None:
        return None
    try:
        parsed = json.loads(safe_path.read_text(encoding="utf-8"))
    except OSError as exc:
        add(blockers, f"{label}_unreadable", path=str(path), detail=str(exc))
        return None
    except json.JSONDecodeError as exc:
        add(blockers, f"{label}_malformed", path=str(path), detail=str(exc))
        return None
    if not isinstance(parsed, dict):
        add(blockers, f"{label}_not_object", path=str(path))
        return None
    return parsed


def sha256_file(path: Path, blockers: list[dict[str, Any]]) -> str | None:
    safe_path = safe_read_path(path, blockers, "readiness")
    if safe_path is None:
        return None
    try:
        return hashlib.sha256(safe_path.read_bytes()).hexdigest()
    except OSError as exc:
        add(blockers, "readiness_unreadable_for_sha256", path=str(path), detail=str(exc))
        return None


def safe_read_path(path: Path, blockers: list[dict[str, Any]], label: str) -> Path | None:
    try:
        reject_symlink_component(path, label)
        return reject_protected_input_path(path, label)
    except SystemExit as exc:
        add(blockers, f"{label}_path_rejected", path=str(path), detail=str(exc))
        return None


def find_surface(manifest: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any] | None:
    surfaces = manifest.get("surfaces")
    if not isinstance(surfaces, list):
        add(blockers, "manifest_surfaces_missing")
        return None
    matches = [surface for surface in surfaces if isinstance(surface, dict) and surface.get("id") == SURFACE_ID]
    if len(matches) != 1:
        add(blockers, "surface_id_match_count_mismatch", expected=1, value=len(matches), surface=SURFACE_ID)
        return None
    return matches[0]


def find_report_entry(surface: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any] | None:
    evidence = surface.get("evidence")
    reports = evidence.get("offline_readiness_reports") if isinstance(evidence, dict) else None
    if not isinstance(reports, list):
        add(blockers, "offline_readiness_reports_missing", surface=SURFACE_ID)
        return None
    matches = [report for report in reports if isinstance(report, dict) and report.get("target_set") == TARGET_SET]
    if not matches and len(reports) == 1 and isinstance(reports[0], dict):
        add(
            blockers,
            "manifest_report_target_set_mismatch",
            expected=TARGET_SET,
            value=reports[0].get("target_set"),
        )
        return reports[0]
    if len(matches) != 1:
        add(blockers, "offline_readiness_report_match_count_mismatch", expected=1, value=len(matches))
        return None
    return matches[0]


def manifest_string_list(manifest: dict[str, Any], key: str) -> set[str]:
    value = manifest.get(key)
    if not isinstance(value, list):
        return set()
    return {item for item in value if isinstance(item, str)}


def is_non_empty_posture(value: Any) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, (list, dict, str, tuple, set)):
        return bool(value)
    return value is True


def validate_surface_manifest_posture(
    manifest: dict[str, Any],
    surface: dict[str, Any] | None,
    blockers: list[dict[str, Any]],
) -> None:
    promoted_surfaces = manifest_string_list(manifest, "promoted_surfaces")
    planning_surfaces = manifest_string_list(manifest, "planning_surfaces")
    post_v1_or_excluded_surfaces = manifest_string_list(manifest, "post_v1_or_excluded_surfaces")

    if SURFACE_ID in promoted_surfaces:
        add(blockers, "structure_surface_in_promoted_surfaces", surface=SURFACE_ID)

    if surface is None:
        return

    status = surface.get("status")
    if status not in EXPECTED_SURFACE_STATUSES:
        add(
            blockers,
            "surface_status_mismatch",
            surface=SURFACE_ID,
            expected=sorted(EXPECTED_SURFACE_STATUSES),
            value=status,
        )
    if status == "planning" and SURFACE_ID not in planning_surfaces:
        add(blockers, "structure_surface_missing_from_planning_surfaces", surface=SURFACE_ID)
    if status == "excluded" and SURFACE_ID not in post_v1_or_excluded_surfaces:
        add(blockers, "structure_surface_missing_from_post_v1_or_excluded_surfaces", surface=SURFACE_ID)
    if surface.get("support_tier") != EXPECTED_SURFACE_SUPPORT_TIER:
        add(
            blockers,
            "surface_support_tier_mismatch",
            surface=SURFACE_ID,
            expected=EXPECTED_SURFACE_SUPPORT_TIER,
            value=surface.get("support_tier"),
        )

    public_contract = surface.get("public_contract")
    if is_non_empty_posture(public_contract):
        add(blockers, "surface_public_contract_not_empty", surface=SURFACE_ID, value=public_contract)
    public_abi = surface.get("public_abi")
    if is_non_empty_posture(public_abi):
        add(blockers, "surface_public_abi_not_false", surface=SURFACE_ID, value=public_abi)
    abi_contract = surface.get("abi_contract")
    if is_non_empty_posture(abi_contract):
        add(blockers, "surface_abi_contract_not_empty", surface=SURFACE_ID, value=abi_contract)


def missing_tokens(text: str, tokens: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    return [token for token in tokens if token.lower() not in lowered]


def key_tokens(value: str) -> set[str]:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return {token for token in re.split(r"[^A-Za-z0-9]+", spaced.lower()) if token}


def compact_key_text(value: str) -> str:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return "".join(token for token in re.split(r"[^A-Za-z0-9]+", spaced.lower()) if token)


def is_negative_statement(text: str) -> bool:
    return text.strip().casefold().startswith(("does not", "do not", "no ", "not "))


def has_false_ready_literal(text: str) -> bool:
    return re.search(r"\bready\s*[:=]\s*false\b", text, re.IGNORECASE) is not None


def flexible_phrase_in_text(text: str, phrase: str) -> bool:
    tokens = [token for token in re.split(r"[^A-Za-z0-9]+", phrase) if token]
    if not tokens:
        return False
    pattern = r"(?<![A-Za-z0-9])" + r"[\W_]*".join(re.escape(token) for token in tokens) + r"(?![A-Za-z0-9])"
    return re.search(pattern, text, re.IGNORECASE) is not None


def raw_sanitization_reasons(value: Any, *, key: str | None = None, path: str = "") -> list[str]:
    reasons: list[str] = []
    if key in FORBIDDEN_SNAPSHOT_KEYS:
        reasons.append(f"forbidden_key:{path or key}")
    if isinstance(value, dict):
        for child_key, child in value.items():
            child_path = f"{path}.{child_key}" if path else str(child_key)
            reasons.extend(raw_sanitization_reasons(child, key=str(child_key), path=child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reasons.extend(raw_sanitization_reasons(child, path=f"{path}[{index}]"))
    elif isinstance(value, str) and key not in HEX_METADATA_KEYS and ADDRESS_RE.search(value):
        reasons.append(f"raw_address:{path}")
    return reasons


def has_forbidden_ready_claim(key: str, path: str) -> bool:
    if key.startswith(NEGATED_TRUE_KEY_PREFIXES):
        return False
    if key == "layout_ready":
        return False
    key_token_set = key_tokens(key)
    path_token_set = key_tokens(path)
    compact_key = compact_key_text(key)
    compact_path = compact_key_text(path)
    domain_in_key = bool(key_token_set & FORBIDDEN_READY_DOMAINS) or any(
        domain in compact_key for domain in FORBIDDEN_READY_DOMAINS if len(domain) > 3
    )
    domain_in_path = bool(path_token_set & FORBIDDEN_READY_DOMAINS) or any(
        domain in compact_path for domain in FORBIDDEN_READY_DOMAINS if len(domain) > 3
    )
    readiness_in_key = bool(key_token_set & READY_TERMS)

    if key in FORBIDDEN_TRUE_READY_KEYS:
        return True
    if readiness_in_key and (domain_in_key or domain_in_path):
        return True
    if "ready" in key_token_set and domain_in_path:
        return True
    return False


def has_forbidden_true_claim(key: str) -> bool:
    if key.startswith(NEGATED_TRUE_KEY_PREFIXES):
        return False
    key_token_set = key_tokens(key)
    compact_key = compact_key_text(key)
    if key in FORBIDDEN_TRUE_CLAIM_KEYS:
        return True
    if "override" in key_token_set and "return" in key_token_set:
        return True
    if "runtime" in key_token_set or "enforcement" in key_token_set:
        return True
    has_public_exposure = bool(key_token_set & PUBLIC_EXPOSURE_KEY_TOKENS)
    has_payload = bool(key_token_set & PUBLIC_PAYLOAD_KEY_TOKENS)
    if has_public_exposure and has_payload:
        return True
    if any(term in compact_key for term in ("publicpayload", "exposedpayload", "exposespayload")):
        return True
    return False


def expected_struct_type(expected: dict[str, Any]) -> str | None:
    value = expected.get("struct_type")
    return value if isinstance(value, str) else None


def actual_struct_type(prop: dict[str, Any]) -> str | None:
    candidate = prop.get("struct_type_candidate")
    if not isinstance(candidate, dict):
        return None
    struct_type = candidate.get("struct_type")
    if not isinstance(struct_type, dict):
        return None
    value = struct_type.get("name")
    return value if isinstance(value, str) else None


def validate_bool_shape(prop: dict[str, Any], expected: dict[str, Any], blockers: list[dict[str, Any]], path: str) -> None:
    for key in ("bool_field_size", "bool_byte_offset", "native_bool"):
        if key in expected and prop.get(key) != expected[key]:
            add(blockers, "snapshot_bool_shape_mismatch", path=path, key=key, expected=expected[key], value=prop.get(key))
    semantics = prop.get("bool_property_semantics")
    if not isinstance(semantics, dict):
        add(blockers, "snapshot_bool_semantics_missing", path=path)
        return
    for key in ("bool_field_size", "bool_byte_offset"):
        if key in expected and semantics.get(key) != expected[key]:
            add(
                blockers,
                "snapshot_bool_semantics_mismatch",
                path=path,
                key=key,
                expected=expected[key],
                value=semantics.get(key),
            )
    if semantics.get("status") != "candidate":
        add(blockers, "snapshot_bool_semantics_status_mismatch", path=path, expected="candidate", value=semantics.get("status"))


def target_snapshot_filename(target_filter: str) -> str:
    _, _, qualified = target_filter.partition(":")
    return f"{qualified}.snapshot.json"


def validate_snapshot_path(
    target_filter: str,
    snapshot_path: Path,
    readiness_path: Path,
    blockers: list[dict[str, Any]],
) -> Path | None:
    expected_path = readiness_path.parent / SNAPSHOT_BASE_DIR / target_snapshot_filename(target_filter)
    if not snapshot_path.is_absolute():
        add(blockers, "readiness_target_detail_path_not_absolute", target=target_filter, value=str(snapshot_path))
        return None
    if snapshot_path != expected_path:
        add(
            blockers,
            "readiness_target_detail_path_mismatch",
            target=target_filter,
            expected=str(expected_path),
            value=str(snapshot_path),
        )
        return None
    if safe_read_path(snapshot_path, blockers, "snapshot") is None:
        return None
    return snapshot_path


def candidate_snapshot_path(readiness_path: Path, base_snapshot_path: Path) -> Path:
    return readiness_path.parent / SNAPSHOT_CANDIDATE_DIR / base_snapshot_path.name


def snapshot_artifact_identity(snapshot: dict[str, Any], blockers: list[dict[str, Any]], path: str) -> dict[str, str] | None:
    evidence = snapshot.get("evidence")
    if not isinstance(evidence, dict):
        add(blockers, "snapshot_evidence_missing", path=path)
        return None
    identity_payload = {"artifact_identity": {key: evidence.get(key) for key in ARTIFACT_IDENTITY_KEYS}}
    identity, errors = complete_artifact_identity(
        identity_payload, container_key="artifact_identity", expected_artifact_kind=EXPECTED_SNAPSHOT_SOURCE
    )
    for error in errors:
        add(blockers, "snapshot_artifact_identity_invalid", path=path, detail=error)
    return identity


def validate_snapshot_envelope(snapshot: dict[str, Any], blockers: list[dict[str, Any]], path: str) -> dict[str, str] | None:
    if snapshot.get("address_policy") != EXPECTED_SNAPSHOT_ADDRESS_POLICY:
        add(
            blockers,
            "snapshot_address_policy_mismatch",
            path=path,
            expected=EXPECTED_SNAPSHOT_ADDRESS_POLICY,
            value=snapshot.get("address_policy"),
        )
    sanitization_reasons = raw_sanitization_reasons(snapshot)
    for reason in sanitization_reasons:
        add(blockers, "snapshot_raw_sanitization_mismatch", path=path, detail=reason)

    evidence = snapshot.get("evidence")
    if not isinstance(evidence, dict):
        add(blockers, "snapshot_evidence_missing", path=path)
        return None
    if evidence.get("source") != EXPECTED_SNAPSHOT_SOURCE:
        add(blockers, "snapshot_evidence_source_mismatch", path=path, expected=EXPECTED_SNAPSHOT_SOURCE, value=evidence.get("source"))
    if evidence.get("status") != "candidate-only":
        add(blockers, "snapshot_evidence_status_mismatch", path=path, expected="candidate-only", value=evidence.get("status"))
    if evidence.get("generated_by") != EXPECTED_SNAPSHOT_GENERATOR:
        add(blockers, "snapshot_evidence_generator_mismatch", path=path, expected=EXPECTED_SNAPSHOT_GENERATOR, value=evidence.get("generated_by"))
    if not is_sha256(evidence.get("ark_binary_sha256")):
        add(blockers, "snapshot_ark_binary_sha256_invalid", path=path, value=evidence.get("ark_binary_sha256"))
    return snapshot_artifact_identity(snapshot, blockers, path)


def validate_distinct_snapshot_identity(
    target_filter: str,
    base_identity: dict[str, str] | None,
    candidate_identity: dict[str, str] | None,
    base_snapshot: dict[str, Any],
    candidate_snapshot: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    base_evidence = base_snapshot.get("evidence") if isinstance(base_snapshot.get("evidence"), dict) else {}
    candidate_evidence = candidate_snapshot.get("evidence") if isinstance(candidate_snapshot.get("evidence"), dict) else {}
    if base_evidence.get("ark_binary_sha256") != candidate_evidence.get("ark_binary_sha256"):
        add(
            blockers,
            "snapshot_ark_binary_sha256_mismatch",
            target=target_filter,
            base=base_evidence.get("ark_binary_sha256"),
            candidate=candidate_evidence.get("ark_binary_sha256"),
        )
    if base_identity is None or candidate_identity is None:
        return
    if tuple(base_identity[key] for key in ARTIFACT_IDENTITY_KEYS) == tuple(
        candidate_identity[key] for key in ARTIFACT_IDENTITY_KEYS
    ):
        add(blockers, "snapshot_same_evidence_artifact_identity", target=target_filter)
    for key in ("artifact_sha256", "capture_id", "evidence_pack_id"):
        if base_identity[key] == candidate_identity[key]:
            add(blockers, f"snapshot_same_evidence_{key}", target=target_filter, value=base_identity[key])


def validate_snapshot_shape(target_filter: str, snapshot_path: Path, blockers: list[dict[str, Any]]) -> dict[str, Any] | None:
    expected = EXPECTED_FIELD_SHAPES[target_filter]
    snapshot = read_json(snapshot_path, blockers, "snapshot")
    if snapshot is None:
        return None
    scan_for_forbidden_runtime_inputs(snapshot, blockers, f"$.snapshot[{target_filter}]")
    scan_for_forbidden_true_ready(snapshot, blockers, f"$.snapshot[{target_filter}]")
    scan_for_forbidden_true_claims(snapshot, blockers, f"$.snapshot[{target_filter}]")
    scan_for_forbidden_string_claims(snapshot, blockers, f"$.snapshot[{target_filter}]")
    validate_snapshot_envelope(snapshot, blockers, str(snapshot_path))
    if snapshot.get("schema") != SNAPSHOT_SCHEMA:
        add(blockers, "snapshot_schema_mismatch", path=str(snapshot_path), expected=SNAPSHOT_SCHEMA, value=snapshot.get("schema"))
    for section in ("evidence", "interpretation"):
        value = snapshot.get(section)
        if not isinstance(value, dict) or value.get("status") != "candidate-only":
            add(blockers, "snapshot_candidate_only_status_mismatch", path=str(snapshot_path), section=section)

    targets = snapshot.get("targets")
    if not isinstance(targets, list) or len(targets) != 1 or not isinstance(targets[0], dict):
        add(blockers, "snapshot_target_count_mismatch", path=str(snapshot_path), expected=1, value=len(targets) if isinstance(targets, list) else None)
        return snapshot
    target = targets[0]
    target_meta = target.get("target")
    if not isinstance(target_meta, dict):
        add(blockers, "snapshot_target_metadata_missing", path=str(snapshot_path))
        return snapshot

    target_checks = {
        "outer_name": expected["outer_name"],
        "name": expected["function_name"],
        "class_name": "Function",
        "outer_class_name": "Class",
    }
    for key, expected_value in target_checks.items():
        if target_meta.get(key) != expected_value:
            add(
                blockers,
                "snapshot_target_metadata_mismatch",
                path=str(snapshot_path),
                key=key,
                expected=expected_value,
                value=target_meta.get(key),
            )
    for key in ("function_flags", "num_parms", "parms_size"):
        if target.get(key) != expected[key]:
            add(blockers, "snapshot_function_shape_mismatch", path=str(snapshot_path), key=key, expected=expected[key], value=target.get(key))
    if target.get("status") != "candidate":
        add(blockers, "snapshot_target_status_mismatch", path=str(snapshot_path), expected="candidate", value=target.get("status"))

    property_chain = target.get("property_chain")
    if not isinstance(property_chain, dict):
        add(blockers, "snapshot_property_chain_missing", path=str(snapshot_path))
        return snapshot
    expected_properties = expected["properties"]
    chain_checks = {
        "status": "candidate",
        "expected_count": len(expected_properties),
        "observed_count": len(expected_properties),
        "parms_size": expected["parms_size"],
    }
    for key, expected_value in chain_checks.items():
        if property_chain.get(key) != expected_value:
            add(blockers, "snapshot_property_chain_mismatch", path=str(snapshot_path), key=key, expected=expected_value, value=property_chain.get(key))
    properties = property_chain.get("properties")
    if not isinstance(properties, list) or len(properties) != len(expected_properties):
        add(
            blockers,
            "snapshot_property_count_mismatch",
            path=str(snapshot_path),
            expected=len(expected_properties),
            value=len(properties) if isinstance(properties, list) else None,
        )
        return snapshot

    for index, (prop, expected_prop) in enumerate(zip(properties, expected_properties, strict=True)):
        prop_path = f"{snapshot_path}#properties[{index}]"
        if not isinstance(prop, dict):
            add(blockers, "snapshot_property_not_object", path=prop_path)
            continue
        expected_base = {
            "depth": index,
            "array_dim": 1,
            "name": expected_prop["name"],
            "class_name": expected_prop["class_name"],
            "offset_internal": expected_prop["offset_internal"],
            "element_size": expected_prop["element_size"],
            "membership_status": "candidate-uobject",
            "class_membership_status": "candidate-uobject",
            "outer_membership_status": "candidate-uobject",
            "status": "candidate",
        }
        for key, expected_value in expected_base.items():
            if prop.get(key) != expected_value:
                add(blockers, "snapshot_property_shape_mismatch", path=prop_path, key=key, expected=expected_value, value=prop.get(key))
        struct_type = expected_struct_type(expected_prop)
        if struct_type is not None and actual_struct_type(prop) != struct_type:
            add(blockers, "snapshot_struct_type_mismatch", path=prop_path, expected=struct_type, value=actual_struct_type(prop))
        if expected_prop["class_name"] == "BoolProperty":
            validate_bool_shape(prop, expected_prop, blockers, prop_path)
        if prop.get("name") not in FIELD_REDACTION_POLICY:
            add(blockers, "snapshot_field_redaction_policy_missing", path=prop_path, field=prop.get("name"))
        redaction = FIELD_REDACTION_POLICY.get(str(prop.get("name")))
        if redaction is None:
            continue
        forbidden_keys = field_policy_forbidden_keys(prop, redaction)
        for key in forbidden_keys:
            add(blockers, "snapshot_field_value_bearing_key", path=prop_path, field=prop.get("name"), key=key)
        if redaction.startswith("redacted_") and prop.get("exposes_range") is True:
            add(blockers, "snapshot_redacted_field_exposes_range", path=prop_path, field=prop.get("name"))
        if redaction.startswith("layout_only_") and prop.get("exposes_public_payload") is True:
            add(blockers, "snapshot_layout_only_field_public_payload", path=prop_path, field=prop.get("name"))
    return snapshot


def field_policy_forbidden_keys(prop: dict[str, Any], redaction: str) -> list[str]:
    if not redaction.startswith(("redacted_", "layout_only_")):
        return []
    forbidden: list[str] = []
    for key in prop:
        tokens = key_tokens(str(key))
        if tokens & FIELD_VALUE_BEARING_KEY_TOKENS:
            forbidden.append(str(key))
            continue
        if (tokens & FIELD_PUBLIC_KEY_TOKENS) and (tokens & PUBLIC_PAYLOAD_KEY_TOKENS):
            forbidden.append(str(key))
    return forbidden


def validate_readiness_snapshot_shapes(readiness: dict[str, Any], readiness_path: Path, blockers: list[dict[str, Any]]) -> None:
    modules = readiness.get("modules")
    if not isinstance(modules, list):
        add(blockers, "readiness_modules_missing")
        return
    target_details: dict[str, dict[str, Any]] = {}
    for module_index, module in enumerate(modules):
        if not isinstance(module, dict):
            add(blockers, "readiness_module_not_object", path=f"$.modules[{module_index}]")
            continue
        details = module.get("target_details")
        if not isinstance(details, list):
            add(blockers, "readiness_module_target_details_missing", path=f"$.modules[{module_index}]")
            continue
        for detail_index, detail in enumerate(details):
            if not isinstance(detail, dict):
                add(blockers, "readiness_target_detail_not_object", path=f"$.modules[{module_index}].target_details[{detail_index}]")
                continue
            target = detail.get("target")
            if target in EXPECTED_TARGET_FILTERS:
                if target in target_details:
                    add(blockers, "readiness_target_detail_duplicate", target=target)
                target_details[target] = detail

    actual_targets = set(target_details)
    if actual_targets != EXPECTED_TARGET_FILTERS:
        add(
            blockers,
            "readiness_target_details_mismatch",
            missing=sorted(EXPECTED_TARGET_FILTERS - actual_targets),
            unexpected=sorted(actual_targets - EXPECTED_TARGET_FILTERS),
        )
        return

    for target_filter in sorted(EXPECTED_TARGET_FILTERS):
        detail = target_details[target_filter]
        if detail.get("comparable") is not True:
            add(blockers, "readiness_target_detail_comparable_mismatch", target=target_filter, expected=True, value=detail.get("comparable"))
        if detail.get("second_source_status") != "accepted":
            add(
                blockers,
                "readiness_target_detail_second_source_status_mismatch",
                target=target_filter,
                expected="accepted",
                value=detail.get("second_source_status"),
            )
        if detail.get("block_reasons") != []:
            add(blockers, "readiness_target_detail_block_reasons_mismatch", target=target_filter, expected=[], value=detail.get("block_reasons"))
        path_value = detail.get("path")
        if not isinstance(path_value, str) or not path_value:
            add(blockers, "readiness_target_detail_path_missing", target=target_filter, value=path_value)
            continue
        base_path = validate_snapshot_path(target_filter, Path(path_value), readiness_path, blockers)
        if base_path is None:
            continue
        candidate_path = candidate_snapshot_path(readiness_path, base_path)
        if safe_read_path(candidate_path, blockers, "snapshot") is None:
            continue
        base_snapshot = validate_snapshot_shape(target_filter, base_path, blockers)
        candidate_snapshot = validate_snapshot_shape(target_filter, candidate_path, blockers)
        if base_snapshot is None or candidate_snapshot is None:
            continue
        base_identity = snapshot_artifact_identity(base_snapshot, blockers, str(base_path))
        candidate_identity = snapshot_artifact_identity(candidate_snapshot, blockers, str(candidate_path))
        validate_distinct_snapshot_identity(
            target_filter,
            base_identity,
            candidate_identity,
            base_snapshot,
            candidate_snapshot,
            blockers,
        )


def validate_manifest_entry(entry: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    expected_values = {
        "target_set": TARGET_SET,
        "schema": READINESS_SCHEMA,
        "status": EXPECTED_STATUS,
        "non_claim": EXPECTED_NON_CLAIM,
    }
    for key, expected in expected_values.items():
        if entry.get(key) != expected:
            add(blockers, f"manifest_report_{key}_mismatch", expected=expected, value=entry.get(key))

    totals = entry.get("totals")
    if totals != EXPECTED_TOTALS:
        add(blockers, "manifest_report_totals_mismatch", expected=EXPECTED_TOTALS, value=totals)

    flags = entry.get("readiness_flags")
    if flags != EXPECTED_READINESS_FLAGS:
        add(blockers, "manifest_report_readiness_flags_mismatch", expected=EXPECTED_READINESS_FLAGS, value=flags)

    non_claim = entry.get("non_claim")
    if isinstance(non_claim, str):
        missing = missing_tokens(non_claim, REQUIRED_NON_CLAIM_TOKENS)
        if missing:
            add(blockers, "manifest_report_non_claim_missing_tokens", missing=missing)
    else:
        add(blockers, "manifest_report_non_claim_not_string", value=non_claim)


def validate_candidate_manifest(surface: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    candidate = surface.get("build_policy_offline_intake_candidate")
    if not isinstance(candidate, dict):
        add(blockers, "build_policy_offline_intake_candidate_missing")
        return
    expected_values = {
        "status": "candidate-only",
        "scope": "offline structure build-policy planning-layout audit only",
        "target_set": TARGET_SET,
        "target_count": 3,
        "target_names_redacted": True,
        "public_sdk_ready": False,
        "promotion_ready": False,
        "runtime_ready": False,
        "enforcement_ready": False,
        "must_remain_planning_only": True,
    }
    for key, expected in expected_values.items():
        if candidate.get(key) != expected:
            add(blockers, f"candidate_{key}_mismatch", expected=expected, value=candidate.get(key))

    boundaries = candidate.get("required_boundaries")
    if not isinstance(boundaries, list):
        add(blockers, "candidate_required_boundaries_missing")
        return
    missing = [boundary for boundary in REQUIRED_BOUNDARIES if boundary not in boundaries]
    if missing:
        add(blockers, "candidate_required_boundaries_missing_values", missing=missing)


def validate_referenced_sha(entry: dict[str, Any], readiness_path: Path, blockers: list[dict[str, Any]]) -> str | None:
    expected_sha = entry.get("sha256")
    actual_sha = sha256_file(readiness_path, blockers)
    if not isinstance(expected_sha, str) or len(expected_sha) != 64:
        add(blockers, "manifest_report_sha256_missing_or_invalid", value=expected_sha)
    elif actual_sha is not None and actual_sha != expected_sha:
        add(blockers, "manifest_report_sha256_mismatch", expected=expected_sha, value=actual_sha)
    return actual_sha


def validate_readiness(readiness: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if readiness.get("schema") != READINESS_SCHEMA:
        add(blockers, "readiness_schema_mismatch", expected=READINESS_SCHEMA, value=readiness.get("schema"))
    for key, expected in EXPECTED_READINESS_ENVELOPE.items():
        if readiness.get(key) != expected:
            add(blockers, f"readiness_{key}_mismatch", expected=expected, value=readiness.get(key))
    if readiness.get("gate_mode") != "planning_layout_intake":
        add(blockers, "readiness_gate_mode_mismatch", expected="planning_layout_intake", value=readiness.get("gate_mode"))
    if readiness.get("second_source_status") != "compared":
        add(blockers, "readiness_second_source_status_mismatch", expected="compared", value=readiness.get("second_source_status"))
    not_promoted = readiness.get("not_promoted_surfaces")
    if not isinstance(not_promoted, list) or not all(isinstance(item, str) for item in not_promoted):
        add(blockers, "readiness_not_promoted_surfaces_missing")
    else:
        missing_not_promoted = sorted(REQUIRED_NOT_PROMOTED_SURFACES - set(not_promoted))
        if missing_not_promoted:
            add(blockers, "readiness_not_promoted_surfaces_missing_values", missing=missing_not_promoted)

    target_sets = readiness.get("target_sets")
    if target_sets != [TARGET_SET]:
        add(blockers, "readiness_target_sets_mismatch", expected=[TARGET_SET], value=target_sets)

    target_filters = readiness.get("target_filters")
    actual_filters = set(target_filters) if isinstance(target_filters, list) else set()
    if actual_filters != EXPECTED_TARGET_FILTERS:
        add(
            blockers,
            "readiness_target_filters_mismatch",
            missing=sorted(EXPECTED_TARGET_FILTERS - actual_filters),
            unexpected=sorted(actual_filters - EXPECTED_TARGET_FILTERS),
        )

    totals = readiness.get("totals")
    if not isinstance(totals, dict):
        add(blockers, "readiness_totals_missing")
    else:
        for key, expected in {**EXPECTED_TOTALS, **EXPECTED_ZERO_TOTALS}.items():
            if totals.get(key) != expected:
                add(blockers, "readiness_total_mismatch", key=key, expected=expected, value=totals.get(key))

    planning_gate = readiness.get("planning_layout_gate")
    if not isinstance(planning_gate, dict):
        add(blockers, "planning_layout_gate_missing")
    else:
        expected_gate_values = {
            "ready": True,
            "layout_ready": True,
            "ready_scope": "planning_only",
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "blockers": [],
        }
        for key, expected in expected_gate_values.items():
            if planning_gate.get(key) != expected:
                add(blockers, f"planning_layout_gate_{key}_mismatch", expected=expected, value=planning_gate.get(key))

    promotion_gate = readiness.get("promotion_gate")
    if not isinstance(promotion_gate, dict):
        add(blockers, "promotion_gate_missing")
    else:
        expected_promotion_values = {
            "ready": False,
            "layout_ready": True,
            "promotion_ready": False,
            "ready_scope": "planning_only",
        }
        for key, expected in expected_promotion_values.items():
            if promotion_gate.get(key) != expected:
                add(blockers, f"promotion_gate_{key}_mismatch", expected=expected, value=promotion_gate.get(key))
        blocker_reasons = {
            blocker.get("reason")
            for blocker in promotion_gate.get("blockers", [])
            if isinstance(blocker, dict)
        }
        if "planning_layout_intake_not_promotion_gate" not in blocker_reasons:
            add(blockers, "promotion_gate_blocker_missing", expected="planning_layout_intake_not_promotion_gate")

    non_claims = readiness.get("non_claims")
    if not isinstance(non_claims, list) or not all(isinstance(item, str) for item in non_claims):
        add(blockers, "readiness_non_claims_missing")
    else:
        joined = " ".join(non_claims)
        for token in (
            "layout evidence only",
            "does not promote public SDK",
            "Structure SDK",
            "StructureEvents",
            "object identity",
            "lookup",
            "mutation",
            "return override",
            "runtime hooks",
        ):
            if token.lower() not in joined.lower():
                add(blockers, "readiness_non_claims_missing_token", token=token)


def scan_for_forbidden_true_ready(payload: Any, blockers: list[dict[str, Any]], path: str) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            child_path = f"{path}.{key}"
            if value is True and has_forbidden_ready_claim(key, path):
                add(blockers, "forbidden_readiness_true", path=child_path, key=key)
            scan_for_forbidden_true_ready(value, blockers, child_path)
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            scan_for_forbidden_true_ready(value, blockers, f"{path}[{index}]")


def scan_for_forbidden_true_claims(payload: Any, blockers: list[dict[str, Any]], path: str) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            child_path = f"{path}.{key}"
            if value is True and has_forbidden_true_claim(key):
                add(blockers, "forbidden_true_claim", path=child_path, key=key)
            scan_for_forbidden_true_claims(value, blockers, child_path)
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            scan_for_forbidden_true_claims(value, blockers, f"{path}[{index}]")


def forbidden_string_claim_surface(key: str, path: str, value: str) -> str | None:
    text = value.casefold().strip()
    if is_negative_statement(text) or has_false_ready_literal(text):
        return None
    normalized = normalized_key(key)
    value_tokens = key_tokens(value)
    key_path_tokens = key_tokens(key) | key_tokens(path)
    value_public_ready = "public" in value_tokens and "ready" in value_tokens
    if normalized == "status" and (value_public_ready or text in {"promoted", "public-ready", "public_ready"}):
        return "status"
    if normalized.endswith("_status"):
        domain_tokens = key_path_tokens & FORBIDDEN_READY_DOMAINS
        if domain_tokens and value_tokens & {"accepted", "promoted", "ready", "released"}:
            return "_".join(sorted(domain_tokens))
    if POSITIVE_STRING_CLAIM_RE.search(text) is None:
        return None
    key_context = f"{key} {value}"
    for phrase, surface in FORBIDDEN_STRING_DOMAINS.items():
        if flexible_phrase_in_text(value, phrase):
            return surface
    for phrase, surface in FORBIDDEN_STRING_DOMAINS.items():
        if flexible_phrase_in_text(key_context, phrase):
            return surface
    return None


def scan_for_forbidden_string_claims(payload: Any, blockers: list[dict[str, Any]], path: str) -> None:
    if isinstance(payload, str):
        if ".promotion_requires[" in path or ".exclusion_requires[" in path:
            return
        key = path.rsplit(".", 1)[-1]
        surface = forbidden_string_claim_surface(key, path, payload)
        if surface is not None:
            add(blockers, "forbidden_string_claim", path=path, key=key, surface=surface)
    elif isinstance(payload, dict):
        for key, value in payload.items():
            child_path = f"{path}.{key}"
            scan_for_forbidden_string_claims(value, blockers, child_path)
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            scan_for_forbidden_string_claims(value, blockers, f"{path}[{index}]")


def normalized_key(key: object) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(key))
    return separated.casefold().replace("-", "_").replace(" ", "_")


def scan_for_forbidden_runtime_inputs(payload: Any, blockers: list[dict[str, Any]], path: str) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            child_path = f"{path}.{key}"
            if normalized_key(key) in FORBIDDEN_RUNTIME_INPUT_KEYS:
                add(blockers, "forbidden_runtime_input_key", path=child_path, key=key)
            scan_for_forbidden_runtime_inputs(value, blockers, child_path)
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            scan_for_forbidden_runtime_inputs(value, blockers, f"{path}[{index}]")


def add_side_lane_source_artifact_guardrails(payload: Any, blockers: list[dict[str, Any]], path: str) -> None:
    for issue in side_lane_fail_closed_source_artifact_issues(
        payload,
        expected_target_sets=(TARGET_SET,),
        path=path,
    ):
        # Structure build-policy reports intentionally contain layout-only readiness
        # fields such as planning_layout_gate.ready=true and second_source.accepted
        # counts. Keep generic status alias scanning in the structure-specific checks.
        if issue.get("reason") == "positive_status_alias_source_not_allowed":
            continue
        blockers.append(issue)


def surface_source_artifact_guardrail_payload(surface: dict[str, Any]) -> dict[str, Any]:
    payload = dict(surface)
    # This checker owns only the build-policy intake lane. The legacy aggregate/census
    # checker candidate can coexist on the same surface with its own target set without
    # becoming a stale alias for build-policy evidence.
    payload.pop("readiness_checker_candidate", None)
    return payload


def build_report(
    blockers: list[dict[str, Any]],
    *,
    readiness_path: Path | None,
    readiness_sha256: str | None,
) -> dict[str, Any]:
    ready = not blockers
    return {
        "schema": REPORT_SCHEMA,
        "target_set": TARGET_SET,
        "status": "accepted_planning_only" if ready else "blocked",
        "ready": ready,
        "accepted_for_offline_planning": ready,
        "planning_only": True,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "enforcement_ready": False,
        "readiness_flags": {
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "enforcement_ready": False,
        },
        "expected_status": EXPECTED_STATUS,
        "expected_totals": EXPECTED_TOTALS,
        "readiness_path": str(readiness_path) if readiness_path is not None else None,
        "readiness_sha256": readiness_sha256,
        "non_claim": EXPECTED_NON_CLAIM,
        "non_claim_matrix": {
            "public_structure_events_sdk": "not_claimed",
            "structure_sdk": "not_claimed",
            "build_policy_sdk": "not_claimed",
            "enforcement": "not_claimed",
            "identity_lookup": "not_claimed",
            "mutation": "not_claimed",
            "return_override": "not_claimed",
            "runtime_hooks": "not_claimed",
            "route_acceptance": "not_claimed",
            "approved_runtime_samples": "not_claimed",
            "public_lookup": "not_claimed",
            "sdk_progress": "not_claimed",
            "v1_completion": "not_claimed",
        },
        "field_shape_contract": {
            target: {
                "num_parms": shape["num_parms"],
                "parms_size": shape["parms_size"],
                "properties": [
                    {
                        "name": prop["name"],
                        "class_name": prop["class_name"],
                        "offset_internal": prop["offset_internal"],
                        "element_size": prop["element_size"],
                        "struct_type": prop.get("struct_type"),
                        "redaction": FIELD_REDACTION_POLICY[prop["name"]],
                    }
                    for prop in shape["properties"]
                ],
            }
            for target, shape in sorted(EXPECTED_FIELD_SHAPES.items())
        },
        "field_redaction": {
            "public_payload": "not_claimed",
            "payload_exposure": "none",
            "runtime_param_read": "not_claimed",
            "return_override": "not_claimed",
            "policy": FIELD_REDACTION_POLICY,
        },
        "blockers": blockers,
    }


def main() -> int:
    args = parse_args()
    blockers: list[dict[str, Any]] = []

    manifest = read_json(args.manifest, blockers, "manifest")
    surface: dict[str, Any] | None = None
    entry: dict[str, Any] | None = None
    readiness_path: Path | None = None
    readiness_sha256: str | None = None

    if manifest is not None:
        surface = find_surface(manifest, blockers)
        validate_surface_manifest_posture(manifest, surface, blockers)
    if surface is not None:
        entry = find_report_entry(surface, blockers)
        validate_candidate_manifest(surface, blockers)
    if entry is not None:
        validate_manifest_entry(entry, blockers)
        entry_path = entry.get("path")
        if not isinstance(entry_path, str) or not entry_path:
            add(blockers, "manifest_report_path_missing", value=entry_path)
        readiness_path = args.readiness if args.readiness is not None else Path(entry_path) if isinstance(entry_path, str) else None

    readiness: dict[str, Any] | None = None
    if entry is not None and readiness_path is not None:
        readiness_sha256 = validate_referenced_sha(entry, readiness_path, blockers)
        readiness = read_json(readiness_path, blockers, "readiness")
    if readiness is not None:
        validate_readiness(readiness, blockers)
        validate_readiness_snapshot_shapes(readiness, readiness_path, blockers)
        add_side_lane_source_artifact_guardrails(readiness, blockers, "$.readiness")
        scan_for_forbidden_runtime_inputs(readiness, blockers, "$.readiness")
        scan_for_forbidden_true_ready(readiness, blockers, "$.readiness")
        scan_for_forbidden_true_claims(readiness, blockers, "$.readiness")
        scan_for_forbidden_string_claims(readiness, blockers, "$.readiness")
    if surface is not None:
        surface_path = "$.manifest.surfaces[obelisk.structure_census.v1]"
        add_side_lane_source_artifact_guardrails(
            surface_source_artifact_guardrail_payload(surface),
            blockers,
            surface_path,
        )
        scan_for_forbidden_runtime_inputs(surface, blockers, surface_path)
        scan_for_forbidden_true_ready(surface, blockers, surface_path)
        scan_for_forbidden_true_claims(surface, blockers, surface_path)
        scan_for_forbidden_string_claims(surface, blockers, surface_path)

    report = build_report(blockers, readiness_path=readiness_path, readiness_sha256=readiness_sha256)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
