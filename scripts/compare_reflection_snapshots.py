#!/usr/bin/env python3
"""Compare sanitized UFunction/ScriptStruct snapshot layouts from two evidence roots."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
import re

from artifact_identity import ARTIFACT_IDENTITY_KEYS, is_safe_artifact_id, is_sha256
import protected_paths
from reflection_target_sets import (
    INTERNAL_LAYOUT_ONLY_TARGET_SETS,
    PLANNING_ONLY_TARGET_SETS,
    RELEASE_READINESS_TARGET_SETS,
    TARGET_SETS,
    target_set_readiness_classification,
)


SUPPORTED_SCHEMAS = {
    "obelisk.ufunction-chain.snapshot.v1",
    "obelisk.scriptstruct-chain.snapshot.v1",
}
FORBIDDEN_KEYS = {
    "object",
    "address",
    "first_property",
    "next_field",
    "next_property",
    "pointer_window",
    "integer_window",
    "gobjects",
    "fname_table",
    "chunks",
    "native_func_candidate",
}
ADDRESS_RE = re.compile(r"0x[0-9a-fA-F]{8,}")
BOOL_MASK_RE = re.compile(r"^0x[0-9a-fA-F]{1,2}$")
HEX_METADATA_KEYS = {"property_flags", "return_value_offset", "function_flags"}
EVIDENCE_ARTIFACT_IDENTITY_KEYS = ARTIFACT_IDENTITY_KEYS
ALLOWED_ARTIFACT_KINDS = {"offline_core"}
PROTECTED_SERVER_ROOT = Path("/servidor/ark")
APPROVED_OFFLINE_WORKSPACE_ROOTS = (Path("/servidor/ark/workspace-offline"),)
READINESS_EVIDENCE_SCOPE = "second_source_layout_evidence_only"
READINESS_NOT_PROMOTED_SURFACES = {
    "class_identity",
    "cross_binary_portability",
    "inventory_identity",
    "item_identity",
    "lookup",
    "mutation",
    "object_identity",
    "public_sdk",
    "raw_params",
    "resource_handle",
    "return_override",
    "runtime_hooks",
}
READINESS_NON_CLAIMS = [
    "accepted second-source readiness is layout evidence only",
    "does not promote public SDK, object identity, lookup, mutation, return override, ResourceHandle, or runtime hooks",
]
MISSION_COPIED_BOOL_POLICY_ARTIFACT = (
    "/home/flowcommunity-ark/obelisk-artifacts/"
    "mission-copied-bool-tail-policy-slice-20260530T090211Z/"
)
MISSION_COPIED_BOOL_POLICY_ARTIFACT_SHA256 = (
    "f56a191aaecbd52d042efd81423d4a86f4e5a29674660aab9d65bbf496416945"
)
MISSION_COPIED_BOOL_POLICY_MANIFEST_SHA256 = (
    "b47f0497c92ae3e8f9a006fb5be87cfbcc1d1dd5f15d78267ad186073e4c26fb"
)
MISSION_CONSUME_ONLY_TARGET_SETS = frozenset(
    (
        "mission-copied-bool-policy-slice",
    )
)
TARGET_BLOCKER_GUIDANCE = {
    "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToBuild": {
        "classification": "second_wave_structure_build_policy_candidate",
        "why_blocked": [
            "missing_committed_sanitized_snapshot",
            "missing_distinct_second_source_layout",
            "placement_struct_redaction_policy_unproven",
            "build_denial_return_override_policy_blocked",
        ],
        "next_offline_input": (
            "approved non-protected copied/offline core or complete core evidence-pack manifest "
            "with FName root, GObjects, binary hash, and artifact identity; use core inputs "
            "with inspect_core_ufunctions.py --snapshot-json, but route evidence-pack manifests "
            "through the snapshot regeneration consumer instead of passing a manifest to --core; "
            "do not repeat fixture-only missing_base_snapshot checks as discovery"
        ),
        "snapshot_prep_checks": [
            "emit exact schema-qualified target obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToBuild",
            "generate one sanitized candidate snapshot for this exact target only before adding any target set",
            "never pass an evidence-pack manifest path to inspect_core_ufunctions.py --core",
            "record distinct offline artifact identity fields: artifact_sha256, capture_id, evidence_pack_id",
            "require target, class, outer, every property, and nested struct/array candidates to be candidate-uobject",
            "keep placement structs, location vectors, player/controller context, object refs, arrays, and raw params redacted or recognition-only",
            "compare only against a distinct sanitized second-source snapshot before any readiness claim",
        ],
        "non_claim": (
            "does not promote StructureEvents, build-policy SDK, identity, lookup, mutation, "
            "return override, runtime hooks, or target-set coverage"
        ),
    },
    "obelisk.ufunction-chain.snapshot.v1:APrimalStructure.IsAllowedToBuild": {
        "classification": "second_wave_structure_build_policy_candidate",
        "why_blocked": [
            "missing_committed_sanitized_snapshot",
            "missing_distinct_second_source_layout",
            "reflected_owner_unproven",
            "placement_struct_redaction_policy_unproven",
            "build_denial_return_override_policy_blocked",
        ],
        "next_offline_input": (
            "approved non-protected copied/offline core or complete core evidence-pack manifest "
            "that proves whether APrimalStructure is a reflected owner; use core inputs with "
            "inspect_core_ufunctions.py --snapshot-json, but route evidence-pack manifests "
            "through the snapshot regeneration consumer instead of passing a manifest to --core; "
            "do not repeat fixture-only missing_base_snapshot checks as discovery"
        ),
        "snapshot_prep_checks": [
            "treat APrimalStructure as an ArkApi dictionary seed until a sanitized snapshot proves the reflected owner",
            "emit exact schema-qualified target obelisk.ufunction-chain.snapshot.v1:APrimalStructure.IsAllowedToBuild only if that owner is observed",
            "generate one sanitized candidate snapshot for this exact target only before adding any target set",
            "never pass an evidence-pack manifest path to inspect_core_ufunctions.py --core",
            "record distinct offline artifact identity fields: artifact_sha256, capture_id, evidence_pack_id",
            "require target, class, outer, every property, and nested struct/array candidates to be candidate-uobject",
            "keep placement structs, location vectors, player/controller context, object refs, arrays, and raw params redacted or recognition-only",
        ],
        "non_claim": (
            "does not promote StructureEvents, build-policy SDK, identity, lookup, mutation, "
            "return override, runtime hooks, or target-set coverage"
        ),
    },
}
TARGET_SET_BLOCKER_GUIDANCE = {
    "players-identity-lifecycle-intake": {
        "classification": "players_identity_lifecycle_guidance_only_candidate",
        "why_blocked": [
            "planning_guidance_only",
            "not_release_readiness_target",
            "identity_privacy_policy_unproven",
            "lifecycle_cleanup_policy_unproven",
            "public_player_sdk_blocked",
            "runtime_observation_requires_separate_approval",
        ],
        "next_offline_input": (
            "docs-only review or sanitized offline snapshots from distinct non-protected "
            "artifacts with complete artifact identity"
        ),
        "snapshot_prep_checks": [
            "compare schema-qualified targets through --target-set players-identity-lifecycle-intake for coverage review only",
            "keep player ids, platform ids, names, IPs, tribe ids, transfer ids, online-list values, object refs, arrays, strings, raw params, and UE pointers redacted",
            "classify copied-scalar candidates separately from redacted identity and lifecycle risks",
            "require distinct artifact identity before any second-source layout claim",
            "do not use this target set for release/readiness or public SDK promotion gates",
        ],
        "non_claim": (
            "does not promote Player Identity/Lifecycle SDK, public player identity, lookup, "
            "ResourceHandle, mutation, return override, runtime hooks, or release readiness"
        ),
    },
    "mission-copied-bool-policy-slice": {
        "classification": "internal_mission_copied_bool_policy_candidate",
        "why_blocked": [
            "policy_slice_evidence_only",
            "consume_mode_only",
            "promote_mode_blocked",
            "not_release_readiness_target",
            "mission_payload_decoding_blocked",
            "public_mission_sdk_blocked",
            "runtime_observation_requires_separate_approval",
        ],
        "next_offline_input": (
            "consume existing offline artifact "
            f"{MISSION_COPIED_BOOL_POLICY_ARTIFACT} "
            f"(pack_sha256={MISSION_COPIED_BOOL_POLICY_ARTIFACT_SHA256}, "
            f"manifest_sha256={MISSION_COPIED_BOOL_POLICY_MANIFEST_SHA256}) "
            "or refresh sanitized mission UFunction snapshots from distinct non-protected "
            "copied/offline artifacts with complete artifact identity"
        ),
        "snapshot_prep_checks": [
            "compare schema-qualified targets through --target-set mission-copied-bool-policy-slice",
            "require AddPlayerToMission, BPAllowPlayerToLeaveMission, and BPOnPlayerRemovedFromMission layouts to be comparable",
            "keep GetPlayerUsableItems in mission-compact-intake as recognition-only; do not add it to the copied-bool policy slice",
            "keep player/controller/character object refs, item arrays, mission payload identity, and raw params redacted or recognition-only",
            "require distinct artifact identity before any second-source readiness claim",
            "consume-only means offline artifact or sanitized snapshot reads; do not substitute runtime probes, live /servidor/ark inputs, or public SDK layouts",
            "do not use this target set for release/readiness or public SDK promotion gates",
        ],
        "non_claim": (
            "does not promote Mission SDK, mission payload decoding, identity, lookup, mutation, "
            "return override, runtime hooks, or target-set expansion"
        ),
    },
    "transfer-baccept-only-policy-slice": {
        "classification": "internal_transfer_baccept_policy_candidate",
        "why_blocked": [
            "policy_slice_evidence_only",
            "not_release_readiness_target",
            "missing_distinct_second_source_layout",
            "transfer_payload_decoding_blocked",
            "public_transfer_sdk_blocked",
            "runtime_observation_requires_separate_approval",
        ],
        "next_offline_input": (
            "sanitized ServerTransferredPlayerConfirmationResult snapshots from distinct "
            "non-protected copied/offline artifacts with complete artifact identity"
        ),
        "snapshot_prep_checks": [
            "compare schema-qualified targets through --target-set transfer-baccept-only-policy-slice",
            "require the bAccept bool layout to be comparable and backed by candidate-uobject membership",
            "keep transferred player payloads, inventory/dino data, object refs, arrays, and raw params redacted or recognition-only",
            "require distinct artifact identity before any second-source readiness claim",
            "do not use this target set for release/readiness or public SDK promotion gates",
        ],
        "non_claim": (
            "does not promote Transfer SDK, transfer payload decoding, identity, lookup, mutation, "
            "return override, runtime hooks, or target-set expansion"
        ),
    },
}

INTERNAL_TARGET_SET_MODULE_GUIDANCE = {
    "buff-breadth-intake": {
        "classification": "internal_buff_layout_only_candidate",
        "module": "Buff",
        "redactions": "buff payloads, inventory/add/prevent context, object refs, strings, arrays, raw params, and UE pointers",
    },
    "buff-compact-intake": {
        "classification": "internal_buff_layout_only_candidate",
        "module": "Buff",
        "redactions": "buff payloads, inventory context, object refs, strings, arrays, raw params, and UE pointers",
    },
    "dino-compact-intake": {
        "classification": "internal_dino_layout_only_candidate",
        "module": "Dino",
        "redactions": "rider/passenger identity, carried actor identity, object refs, strings, arrays, raw params, and UE pointers",
    },
    "inventory-action-compact-intake": {
        "classification": "internal_inventory_action_layout_only_candidate",
        "module": "Inventory",
        "redactions": "inventory item identity, actor identity, object refs, strings, arrays, raw params, and UE pointers",
    },
    "item-compact-intake": {
        "classification": "internal_item_layout_only_candidate",
        "module": "Item",
        "redactions": "item identity, inventory identity, object refs, strings, arrays, raw params, and UE pointers",
    },
    "mission-compact-intake": {
        "classification": "internal_mission_layout_only_candidate",
        "module": "Mission",
        "redactions": "player/controller/character object refs, item arrays, mission payload identity, raw params, and UE pointers",
    },
    "structure-nonpin-copied-scalar-policy-slice": {
        "classification": "internal_structure_scalar_layout_only_candidate",
        "module": "Structure",
        "redactions": "pin codes, player context, structure identity, object refs, strings, arrays, raw params, and UE pointers",
    },
    "structure-return-only-policy-slice": {
        "classification": "internal_structure_return_layout_only_candidate",
        "module": "Structure",
        "redactions": "player context, structure identity, object refs, strings, arrays, raw params, and UE pointers",
    },
    "transfer-scriptstruct": {
        "classification": "internal_transfer_scriptstruct_layout_only_candidate",
        "module": "Transfer",
        "redactions": "transferred player/dino payloads, inventory data, object refs, strings, arrays, raw params, and UE pointers",
    },
    "transfer-ufunction-intake": {
        "classification": "internal_transfer_layout_only_candidate",
        "module": "Transfer",
        "redactions": "transferred player/dino payloads, inventory data, object refs, strings, arrays, raw params, and UE pointers",
    },
    "tribe-compact-intake": {
        "classification": "internal_tribe_layout_only_candidate",
        "module": "Tribe",
        "redactions": "player ids, platform ids, names, tribe ids, online-list values, object refs, arrays, strings, raw params, and UE pointers",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare two sanitized reflection snapshot roots without reading cores or touching servers."
    )
    parser.add_argument("--base-root", type=Path, help="Baseline snapshot root or single snapshot file.")
    parser.add_argument("--candidate-root", type=Path, help="Second-source snapshot root or file.")
    parser.add_argument(
        "--allow-ark-sha-mismatch",
        action="store_true",
        help="Do not mark targets inconclusive when evidence.ark_binary_sha256 differs.",
    )
    parser.add_argument(
        "--strict-identity-indices",
        action="store_true",
        help="Also require FName/object identity indices to match where snapshots carry them.",
    )
    parser.add_argument(
        "--target",
        action="append",
        default=[],
        help=(
            "Only compare an exact target. Accepts Outer.Name or schema:Outer.Name. "
            "Repeatable."
        ),
    )
    parser.add_argument(
        "--target-set",
        action="append",
        default=[],
        choices=sorted(TARGET_SETS),
        help="Add a named target group. Repeatable.",
    )
    parser.add_argument(
        "--readiness-report",
        action="store_true",
        help="Summarize current snapshot coverage and second-source readiness by module.",
    )
    parser.add_argument(
        "--fail-on-readiness-gaps",
        action="store_true",
        help=(
            "With --readiness-report, return non-zero when requested targets are blocked, "
            "missing, inconclusive, or rejected. Use this for promotion gates."
        ),
    )
    parser.add_argument(
        "--fail-on-base-readiness-gaps",
        action="store_true",
        help=(
            "With --readiness-report, return non-zero when requested base target sets are "
            "empty or have blocked/missing/non-comparable committed snapshots. Does not "
            "require candidate second-source evidence."
        ),
    )
    parser.add_argument(
        "--list-target-sets",
        action="store_true",
        help="List named target sets and exit without reading snapshot roots.",
    )
    parser.add_argument(
        "--list-target-guidance",
        action="store_true",
        help=(
            "List deferred-target blocker guidance and exit without reading snapshot roots. "
            "Use --target to filter."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser.parse_args()


def expand_target_filters(targets: list[str], target_sets: list[str]) -> set[str]:
    filters = set(targets)
    for target_set in target_sets:
        filters.update(TARGET_SETS[target_set])
    validate_target_filters(filters)
    return filters


def validate_target_filters(filters: set[str]) -> None:
    for target in sorted(filters):
        if ":" not in target:
            continue
        schema, _, short_key = target.partition(":")
        if schema not in SUPPORTED_SCHEMAS:
            raise SystemExit(f"unsupported target filter schema: {schema}")
        if not short_key:
            raise SystemExit(f"schema-qualified target filter missing target: {target}")


def is_under_path(path: Path, root: Path) -> bool:
    return protected_paths.is_under_path(path, root)


def is_approved_offline_workspace_path(path: Path) -> bool:
    return protected_paths.is_approved_offline_workspace_path(
        path,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )


def reject_protected_input_path(label: str, path: Path) -> None:
    protected_paths.reject_protected_input_path(
        path,
        label,
        protected_root=PROTECTED_SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
        message=f"{label} must not read from protected live-server path: {path}",
    )


def target_set_report() -> dict[str, Any]:
    return {
        "schema": "obelisk.reflection-snapshot-target-sets.v1",
        "target_sets": [
            {
                "name": name,
                "readiness_classification": target_set_readiness_classification(name),
                "release_readiness": name in RELEASE_READINESS_TARGET_SETS,
                "targets": list(targets),
            }
            for name, targets in sorted(TARGET_SETS.items())
        ],
    }


def target_guidance_report(target_filters: set[str]) -> dict[str, Any]:
    guidance = []
    for target in sorted(TARGET_BLOCKER_GUIDANCE):
        if matches_target_filter(target, target_filters):
            guidance.append({"target": target, **(target_blocker_guidance(target) or {})})
    return {
        "schema": "obelisk.reflection-target-guidance.v1",
        "guidance_scope": "offline_planning_only",
        "target_filters": sorted(target_filters),
        "not_promoted_surfaces": sorted(READINESS_NOT_PROMOTED_SURFACES),
        "non_claims": list(READINESS_NON_CLAIMS),
        "target_set_guidance": [],
        "targets": guidance,
    }


def target_set_blocker_guidance(target_set: str) -> dict[str, Any] | None:
    guidance = TARGET_SET_BLOCKER_GUIDANCE.get(target_set)
    if guidance is None:
        if target_set not in INTERNAL_LAYOUT_ONLY_TARGET_SETS:
            return None
        internal_guidance = INTERNAL_TARGET_SET_MODULE_GUIDANCE.get(target_set)
        if internal_guidance is None:
            return None
        module = internal_guidance["module"]
        return {
            "classification": internal_guidance["classification"],
            "why_blocked": [
                "internal_layout_evidence_only",
                "not_release_readiness_target",
                f"public_{module.lower()}_sdk_blocked",
                "runtime_observation_requires_separate_approval",
            ],
            "next_offline_input": (
                "sanitized offline snapshots from distinct non-protected artifacts with "
                "complete artifact identity"
            ),
            "snapshot_prep_checks": [
                f"compare schema-qualified targets through --target-set {target_set} for internal coverage review only",
                f"keep {internal_guidance['redactions']} redacted or recognition-only",
                "require target, class, outer, every property, and nested struct/array candidates to be candidate-uobject",
                "require distinct artifact identity before any second-source layout claim",
                "do not use this target set for release/readiness or public SDK promotion gates",
            ],
            "non_claim": (
                f"does not promote {module} SDK, identity, lookup, mutation, return override, "
                "runtime hooks, or release readiness"
            ),
        }
    copied: dict[str, Any] = {}
    for key, value in guidance.items():
        copied[key] = list(value) if isinstance(value, list) else value
    return copied


def target_set_guidance_report(target_sets: list[str]) -> list[dict[str, Any]]:
    guidance = []
    for target_set in sorted(target_sets):
        item = target_set_blocker_guidance(target_set)
        if item is not None:
            guidance.append({"target_set": target_set, **item})
    return guidance


def duplicate_values(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def reject_duplicate_target_set_guidance_filters(target_sets: list[str]) -> None:
    duplicates = duplicate_values(target_sets)
    if duplicates:
        raise SystemExit("duplicate target-set guidance filter(s): " + ", ".join(duplicates))


def reject_duplicate_target_guidance_filters(targets: list[str]) -> None:
    duplicates = duplicate_values(targets)
    if duplicates:
        raise SystemExit("duplicate target guidance filter(s): " + ", ".join(duplicates))


def unmatched_target_guidance_filters(targets: list[str]) -> list[str]:
    return [
        target
        for target in targets
        if not any(
            matches_target_filter(guidance_target, {target})
            for guidance_target in TARGET_BLOCKER_GUIDANCE
        )
    ]


def target_blocker_guidance(target: str) -> dict[str, Any] | None:
    guidance = TARGET_BLOCKER_GUIDANCE.get(target)
    if guidance is None:
        return None
    copied: dict[str, Any] = {}
    for key, value in guidance.items():
        copied[key] = list(value) if isinstance(value, list) else value
    return copied


def snapshot_paths(root: Path) -> list[Path]:
    reject_protected_input_path("snapshot root", root)
    if root.is_symlink():
        reject_protected_input_path("snapshot", root)
    if root.is_file():
        return [root]
    if not root.exists():
        raise SystemExit(f"snapshot root does not exist: {root}")
    paths = []
    for path in root.rglob("*.snapshot.json"):
        reject_protected_input_path("snapshot", path)
        if path.is_file():
            paths.append(path)
    return sorted(paths)


def load_snapshot(path: Path) -> dict[str, Any]:
    reject_protected_input_path("snapshot", path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}") from exc
    if payload.get("schema") not in SUPPORTED_SCHEMAS:
        raise SystemExit(f"{path}: unsupported snapshot schema: {payload.get('schema')!r}")
    targets = payload.get("targets")
    if not isinstance(targets, list) or len(targets) != 1 or not isinstance(targets[0], dict):
        raise SystemExit(f"{path}: expected exactly one target")
    return payload


def target_key(payload: dict[str, Any]) -> str:
    target = payload["targets"][0]
    identity = target.get("target")
    if not isinstance(identity, dict):
        raise SystemExit("snapshot target missing identity object")
    schema = payload.get("schema")
    outer = identity.get("outer_name")
    name = identity.get("name")
    if not isinstance(outer, str) or not isinstance(name, str):
        raise SystemExit("snapshot target missing string outer_name/name")
    return f"{schema}:{outer}.{name}"


def load_snapshot_set(root: Path) -> dict[str, dict[str, Any]]:
    snapshots: dict[str, dict[str, Any]] = {}
    for path in snapshot_paths(root):
        payload = load_snapshot(path)
        key = target_key(payload)
        if key in snapshots:
            raise SystemExit(f"duplicate snapshot target {key}: {snapshots[key]['path']} and {path}")
        snapshots[key] = {"path": str(path), "payload": payload}
    return snapshots


def schema_label(schema: str) -> str:
    if schema == "obelisk.ufunction-chain.snapshot.v1":
        return "ufunction"
    if schema == "obelisk.scriptstruct-chain.snapshot.v1":
        return "scriptstruct"
    return schema


def module_from_path(path: str) -> str:
    parts = Path(path).parts
    if len(parts) >= 2:
        return parts[-2]
    return "<unknown>"


def raw_sanitization_reasons(value: Any, *, key: str | None = None, path: str = "") -> list[str]:
    reasons: list[str] = []
    if key in FORBIDDEN_KEYS:
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


def property_layout(prop: dict[str, Any], *, strict_identity_indices: bool) -> dict[str, Any]:
    result = {
        "name": prop.get("name"),
        "class_name": prop.get("class_name"),
        "offset_internal": prop.get("offset_internal"),
        "element_size": prop.get("element_size"),
        "array_dim": prop.get("array_dim"),
        "property_flags": prop.get("property_flags"),
        "bool_field_size": prop.get("bool_field_size"),
        "bool_byte_offset": prop.get("bool_byte_offset"),
        "native_bool": prop.get("native_bool"),
        "byte_mask": prop.get("byte_mask"),
        "field_mask": prop.get("field_mask"),
        "status": prop.get("status"),
        "reject_reasons": prop.get("reject_reasons", []),
        "membership_status": prop.get("membership_status"),
        "class_membership_status": prop.get("class_membership_status"),
        "outer_membership_status": prop.get("outer_membership_status"),
    }
    if strict_identity_indices:
        result.update(
            {
                "object_index": prop.get("object_index"),
                "name_index": prop.get("name_index"),
                "class_name_index": prop.get("class_name_index"),
                "class_object_index": prop.get("class_object_index"),
            }
        )
    for nested_key in ("array_inner_candidate", "struct_type_candidate"):
        nested = prop.get(nested_key)
        if not isinstance(nested, dict):
            continue
        nested_identity_key = "inner_property" if nested_key == "array_inner_candidate" else "struct_type"
        nested_identity = nested.get(nested_identity_key)
        if not isinstance(nested_identity, dict):
            continue
        result[nested_key] = {
            "status": nested.get("status"),
            "reject_reasons": nested.get("reject_reasons", []),
            "membership_status": nested.get("membership_status"),
            nested_identity_key: {
                "name": nested_identity.get("name"),
                "class_name": nested_identity.get("class_name"),
            },
        }
        if strict_identity_indices:
            result[nested_key][nested_identity_key]["object_index"] = nested_identity.get("object_index")
            result[nested_key][nested_identity_key]["name_index"] = nested_identity.get("name_index")
            result[nested_key][nested_identity_key]["class_name_index"] = nested_identity.get("class_name_index")
            result[nested_key][nested_identity_key]["class_object_index"] = nested_identity.get("class_object_index")
    return result


def property_block_reasons(prop: dict[str, Any], *, index: int) -> list[str]:
    reasons: list[str] = []
    prefix = f"property[{index}]"
    if prop.get("status") != "candidate":
        reasons.append(f"{prefix}_status_{prop.get('status')}")
    if prop.get("reject_reasons", []):
        reasons.append(f"{prefix}_has_reject_reasons")
    if prop.get("class_name") == "BoolProperty":
        bool_semantics = prop.get("bool_property_semantics")
        if not isinstance(bool_semantics, dict):
            reasons.append(f"{prefix}_bool_property_semantics_missing")
        else:
            if bool_semantics.get("status") != "candidate":
                reasons.append(f"{prefix}_bool_property_semantics_status_{bool_semantics.get('status')}")
            if bool_semantics.get("reject_reasons", []):
                reasons.append(f"{prefix}_bool_property_semantics_has_reject_reasons")
            for tail_key in ("bool_field_size", "bool_byte_offset"):
                if not isinstance(bool_semantics.get(tail_key), int):
                    reasons.append(f"{prefix}_bool_property_semantics_{tail_key}_missing")
        for tail_key in ("bool_field_size", "bool_byte_offset"):
            if not isinstance(prop.get(tail_key), int):
                reasons.append(f"{prefix}_{tail_key}_missing")
            elif (
                isinstance(bool_semantics, dict)
                and isinstance(bool_semantics.get(tail_key), int)
                and prop.get(tail_key) != bool_semantics.get(tail_key)
            ):
                reasons.append(f"{prefix}_{tail_key}_mismatches_bool_property_semantics")
        if prop.get("native_bool") not in (True, False):
            reasons.append(f"{prefix}_native_bool_missing")
        for mask_key in ("byte_mask", "field_mask"):
            mask = prop.get(mask_key)
            if not isinstance(mask, str) or BOOL_MASK_RE.fullmatch(mask) is None or int(mask, 16) == 0:
                reasons.append(f"{prefix}_{mask_key}_missing_or_zero")
    for membership_key in ("membership_status", "class_membership_status", "outer_membership_status"):
        membership = prop.get(membership_key)
        if membership != "candidate-uobject":
            reasons.append(f"{prefix}_{membership_key}_{membership if membership is not None else 'missing'}")
    for nested_key in ("array_inner_candidate", "struct_type_candidate"):
        nested = prop.get(nested_key)
        if not isinstance(nested, dict):
            continue
        nested_prefix = f"{prefix}_{nested_key}"
        nested_identity_key = "inner_property" if nested_key == "array_inner_candidate" else "struct_type"
        if nested.get("status") != "candidate":
            reasons.append(f"{nested_prefix}_status_{nested.get('status')}")
        if nested.get("reject_reasons", []):
            reasons.append(f"{nested_prefix}_has_reject_reasons")
        membership = nested.get("membership_status")
        if membership != "candidate-uobject":
            reasons.append(f"{nested_prefix}_membership_status_{membership if membership is not None else 'missing'}")
        if not isinstance(nested.get(nested_identity_key), dict):
            reasons.append(f"{nested_prefix}_missing_{nested_identity_key}")
    return reasons


def evidence_reasons(payload: dict[str, Any]) -> list[str]:
    evidence = payload.get("evidence")
    if not isinstance(evidence, dict):
        return ["missing_evidence"]
    reasons: list[str] = []
    ark_binary_sha256 = evidence.get("ark_binary_sha256")
    if not isinstance(ark_binary_sha256, str):
        reasons.append("missing_ark_binary_sha256")
    elif not is_sha256(ark_binary_sha256):
        reasons.append("invalid_ark_binary_sha256")
    artifact_kind = evidence.get("artifact_kind")
    if artifact_kind is not None and artifact_kind not in ALLOWED_ARTIFACT_KINDS:
        reasons.append(f"invalid_artifact_kind_{artifact_kind}")
    artifact_sha256 = evidence.get("artifact_sha256")
    if artifact_sha256 is not None:
        if not is_sha256(artifact_sha256):
            reasons.append("invalid_artifact_sha256")
    for field in ("capture_id", "evidence_pack_id"):
        value = evidence.get(field)
        if value is not None:
            if not is_safe_artifact_id(value):
                reasons.append(f"invalid_{field}")
    if evidence.get("source") != "offline_core":
        reasons.append(f"evidence_source_{evidence.get('source')}")
    if evidence.get("status") != "candidate-only":
        reasons.append(f"evidence_status_{evidence.get('status')}")
    generated_by = evidence.get("generated_by")
    if generated_by != "scripts/inspect_core_ufunctions.py --snapshot-json":
        reasons.append(f"evidence_generated_by_{generated_by}")
    return reasons


def comparable_layout(payload: dict[str, Any], *, strict_identity_indices: bool) -> tuple[dict[str, Any] | None, list[str]]:
    raw_reasons = raw_sanitization_reasons(payload)
    if raw_reasons:
        return None, raw_reasons
    invalid_evidence = evidence_reasons(payload)
    if invalid_evidence:
        return None, invalid_evidence
    target = payload["targets"][0]
    identity = target.get("target")
    chain = target.get("property_chain")
    if not isinstance(identity, dict) or not isinstance(chain, dict):
        return None, ["missing_target_identity_or_property_chain"]
    if target.get("status") != "candidate":
        return None, [f"target_status_{target.get('status')}"]
    membership = target.get("membership")
    if membership != {"target": "candidate-uobject", "class": "candidate-uobject", "outer": "candidate-uobject"}:
        return None, ["target_membership_not_candidate"]
    if chain.get("status") != "candidate":
        return None, [f"property_chain_status_{chain.get('status')}"]
    if chain.get("reject_reasons", []):
        return None, ["property_chain_has_reject_reasons"]
    properties = chain.get("properties")
    if not isinstance(properties, list):
        return None, ["missing_property_list"]
    property_reasons: list[str] = []
    for index, prop in enumerate(properties):
        if not isinstance(prop, dict):
            property_reasons.append(f"property[{index}]_not_object")
            continue
        property_reasons.extend(property_block_reasons(prop, index=index))
    if property_reasons:
        return None, property_reasons

    layout = {
        "schema": payload.get("schema"),
        "inspection_mode": target.get("inspection_mode"),
        "status": target.get("status"),
        "reject_reasons": target.get("reject_reasons", []),
        "membership": membership,
        "target": {
            "name": identity.get("name"),
            "class_name": identity.get("class_name"),
            "outer_name": identity.get("outer_name"),
            "outer_class_name": identity.get("outer_class_name"),
        },
        "property_chain": {
            "status": chain.get("status"),
            "reject_reasons": chain.get("reject_reasons", []),
            "expected_count": chain.get("expected_count"),
            "observed_count": chain.get("observed_count"),
            "properties": [
                property_layout(prop, strict_identity_indices=strict_identity_indices)
                for prop in properties
            ],
        },
    }
    if strict_identity_indices:
        layout["target"].update(
            {
                "object_index": identity.get("object_index"),
                "name_index": identity.get("name_index"),
                "class_name_index": identity.get("class_name_index"),
                "class_object_index": identity.get("class_object_index"),
                "outer_name_index": identity.get("outer_name_index"),
                "outer_object_index": identity.get("outer_object_index"),
            }
        )
    if payload.get("schema") == "obelisk.ufunction-chain.snapshot.v1":
        layout.update(
            {
                "num_parms": target.get("num_parms"),
                "parms_size": target.get("parms_size"),
                "function_flags": target.get("function_flags"),
                "return_value_offset": target.get("return_value_offset"),
            }
        )
        layout["property_chain"]["parms_size"] = chain.get("parms_size")
    else:
        layout.update(
            {
                "properties_size": target.get("properties_size"),
                "min_alignment": target.get("min_alignment"),
            }
        )
        layout["property_chain"]["properties_size"] = chain.get("properties_size")
    return layout, []


def diff_layout(base: Any, candidate: Any, path: str = "") -> list[dict[str, Any]]:
    if type(base) is not type(candidate):
        return [{"path": path or ".", "base": base, "candidate": candidate}]
    if isinstance(base, dict):
        diffs: list[dict[str, Any]] = []
        for key in sorted(set(base) | set(candidate)):
            diffs.extend(diff_layout(base.get(key), candidate.get(key), f"{path}.{key}" if path else key))
        return diffs
    if isinstance(base, list):
        diffs = []
        if len(base) != len(candidate):
            diffs.append({"path": f"{path}.length" if path else "length", "base": len(base), "candidate": len(candidate)})
        for index, (left, right) in enumerate(zip(base, candidate)):
            diffs.extend(diff_layout(left, right, f"{path}[{index}]"))
        return diffs
    if base != candidate:
        return [{"path": path or ".", "base": base, "candidate": candidate}]
    return []


def evidence_sha(payload: dict[str, Any]) -> Any:
    evidence = payload.get("evidence")
    return evidence.get("ark_binary_sha256") if isinstance(evidence, dict) else None


def evidence_artifact_identity(payload: dict[str, Any]) -> tuple[Any, ...] | None:
    identity = evidence_artifact_identity_dict(payload)
    if identity is None:
        return None
    return tuple(identity[key] for key in EVIDENCE_ARTIFACT_IDENTITY_KEYS)


def evidence_artifact_identity_dict(payload: dict[str, Any]) -> dict[str, str] | None:
    evidence = payload.get("evidence")
    if not isinstance(evidence, dict):
        return None
    values = {key: evidence.get(key) for key in EVIDENCE_ARTIFACT_IDENTITY_KEYS}
    if not all(isinstance(value, str) and value for value in values.values()):
        return None
    return values  # type: ignore[return-value]


def shared_artifact_identity_reasons(base_payload: dict[str, Any], candidate_payload: dict[str, Any]) -> list[str]:
    base_identity = evidence_artifact_identity_dict(base_payload)
    candidate_identity = evidence_artifact_identity_dict(candidate_payload)
    if base_identity is None or candidate_identity is None:
        return []
    if tuple(base_identity[key] for key in EVIDENCE_ARTIFACT_IDENTITY_KEYS) == tuple(
        candidate_identity[key] for key in EVIDENCE_ARTIFACT_IDENTITY_KEYS
    ):
        return ["same_evidence_artifact_identity"]
    reasons: list[str] = []
    for key in ("artifact_sha256", "capture_id", "evidence_pack_id"):
        if base_identity[key] == candidate_identity[key]:
            reasons.append(f"same_evidence_{key}")
    return reasons


def matches_target_filter(key: str, filters: set[str]) -> bool:
    if not filters:
        return True
    _, _, short_key = key.partition(":")
    return key in filters or short_key in filters


def filtered_keys(
    base: dict[str, dict[str, Any]],
    candidate: dict[str, dict[str, Any]],
    *,
    target_filters: set[str],
) -> list[str]:
    available_keys = set(base) | set(candidate)
    keys = {key for key in available_keys if matches_target_filter(key, target_filters)}
    schema_qualified_filters = {target for target in target_filters if ":" in target}
    keys.update(schema_qualified_filters)
    if target_filters and not keys:
        raise SystemExit(f"target filter did not match snapshots: {', '.join(sorted(target_filters))}")
    unmatched_short_filters = []
    for target in target_filters:
        if ":" in target:
            continue
        if not any(key.partition(":")[2] == target for key in available_keys):
            unmatched_short_filters.append(target)
    if unmatched_short_filters:
        raise SystemExit(f"target filter did not match snapshots: {', '.join(sorted(unmatched_short_filters))}")
    return sorted(keys)


def compare_sets(
    base: dict[str, dict[str, Any]],
    candidate: dict[str, dict[str, Any]],
    *,
    strict_identity_indices: bool,
    allow_ark_sha_mismatch: bool,
    target_filters: set[str],
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for key in filtered_keys(base, candidate, target_filters=target_filters):
        missing_reasons = []
        if key not in base:
            missing_reasons.append("missing_base_snapshot")
        if key not in candidate:
            missing_reasons.append("missing_candidate_snapshot")
        if missing_reasons:
            results.append({"target": key, "status": "inconclusive", "reasons": missing_reasons})
            continue
        if not allow_ark_sha_mismatch and evidence_sha(base[key]["payload"]) != evidence_sha(candidate[key]["payload"]):
            results.append(
                {
                    "target": key,
                    "status": "inconclusive",
                    "reasons": ["ark_binary_sha256_mismatch"],
                }
            )
            continue
        base_artifact = evidence_artifact_identity(base[key]["payload"])
        candidate_artifact = evidence_artifact_identity(candidate[key]["payload"])
        artifact_reasons = []
        if base_artifact is None:
            artifact_reasons.append("missing_base_evidence_artifact_identity")
        if candidate_artifact is None:
            artifact_reasons.append("missing_candidate_evidence_artifact_identity")
        artifact_reasons.extend(shared_artifact_identity_reasons(base[key]["payload"], candidate[key]["payload"]))
        if artifact_reasons:
            results.append({"target": key, "status": "inconclusive", "reasons": artifact_reasons})
            continue
        base_layout, base_reasons = comparable_layout(base[key]["payload"], strict_identity_indices=strict_identity_indices)
        candidate_layout, candidate_reasons = comparable_layout(
            candidate[key]["payload"],
            strict_identity_indices=strict_identity_indices,
        )
        if base_reasons or candidate_reasons or base_layout is None or candidate_layout is None:
            results.append(
                {
                    "target": key,
                    "status": "inconclusive",
                    "reasons": [f"base:{reason}" for reason in base_reasons]
                    + [f"candidate:{reason}" for reason in candidate_reasons],
                }
            )
            continue
        diffs = diff_layout(base_layout, candidate_layout)
        if diffs:
            results.append({"target": key, "status": "rejected", "diffs": diffs})
        else:
            results.append({"target": key, "status": "accepted"})
    counts = {"accepted": 0, "rejected": 0, "inconclusive": 0}
    for result in results:
        counts[result["status"]] += 1
    return {
        "schema": "obelisk.reflection-snapshot-comparison.v1",
        "strict_identity_indices": strict_identity_indices,
        "allow_ark_sha_mismatch": allow_ark_sha_mismatch,
        "target_filters": sorted(target_filters),
        "counts": counts,
        "results": results,
    }


def readiness_report(
    snapshots: dict[str, dict[str, Any]],
    *,
    strict_identity_indices: bool,
    allow_ark_sha_mismatch: bool,
    target_filters: set[str],
    candidate: dict[str, dict[str, Any]] | None,
) -> dict[str, Any]:
    if candidate is None:
        keys = filtered_keys(snapshots, {}, target_filters=target_filters)
        if target_filters and not keys:
            raise SystemExit(f"target filter did not match snapshots: {', '.join(sorted(target_filters))}")
        comparison_by_target: dict[str, dict[str, Any]] = {}
    else:
        keys = filtered_keys(snapshots, candidate, target_filters=target_filters)
        comparison = compare_sets(
            snapshots,
            candidate,
            strict_identity_indices=strict_identity_indices,
            allow_ark_sha_mismatch=allow_ark_sha_mismatch,
            target_filters=target_filters,
        )
        comparison_by_target = {result["target"]: result for result in comparison["results"]}

    modules: dict[str, dict[str, Any]] = {}
    totals = {
        "targets": 0,
        "comparable": 0,
        "blocked": 0,
        "second_source_accepted": 0,
        "second_source_rejected": 0,
        "second_source_inconclusive": 0,
        "second_source_missing": 0,
    }

    def promotion_gate_summary() -> dict[str, Any]:
        blockers = []
        if totals["targets"] == 0:
            blockers.append({"reason": "no_targets", "count": 1})
        if totals["blocked"]:
            blockers.append({"reason": "blocked_base_targets", "count": totals["blocked"]})
        if totals["second_source_rejected"]:
            blockers.append({"reason": "rejected_second_source", "count": totals["second_source_rejected"]})
        if totals["second_source_inconclusive"]:
            blockers.append({"reason": "inconclusive_second_source", "count": totals["second_source_inconclusive"]})
        if totals["second_source_missing"]:
            blockers.append({"reason": "missing_second_source", "count": totals["second_source_missing"]})
        return {
            "ready": not blockers,
            "ready_scope": "layout_only" if not blockers else "not_ready",
            "layout_ready": not blockers,
            "promotion_ready": False,
            "blockers": blockers,
        }

    def module_bucket(module_key: str, *, schema: str, module: str) -> dict[str, Any]:
        return modules.setdefault(
            module_key,
            {
                "schema": schema,
                "module": module,
                "targets": 0,
                "comparable": 0,
                "blocked": 0,
                "block_reasons": {},
                "second_source": {"accepted": 0, "rejected": 0, "inconclusive": 0, "missing": 0},
                "target_details": [],
            },
        )

    for key in keys:
        entry = snapshots.get(key)
        if entry is None:
            schema_name, _, _ = key.partition(":")
            schema = schema_label(schema_name)
            bucket = module_bucket(f"{schema}:<missing>", schema=schema, module="<missing>")
            target_detail = {
                "target": key,
                "path": None,
                "comparable": False,
                "block_reasons": ["missing_base_snapshot"],
                "second_source_status": "not_applicable",
            }
            guidance = target_blocker_guidance(key)
            if guidance is not None:
                target_detail["guidance"] = guidance
            bucket["targets"] += 1
            bucket["blocked"] += 1
            bucket["block_reasons"]["missing_base_snapshot"] = (
                bucket["block_reasons"].get("missing_base_snapshot", 0) + 1
            )
            bucket["second_source"]["missing"] += 1
            bucket["target_details"].append(target_detail)
            totals["targets"] += 1
            totals["blocked"] += 1
            continue
        payload = entry["payload"]
        schema = schema_label(payload.get("schema", ""))
        module = module_from_path(entry["path"])
        module_key = f"{schema}:{module}"
        bucket = module_bucket(module_key, schema=schema, module=module)

        bucket["targets"] += 1
        totals["targets"] += 1
        _, reasons = comparable_layout(payload, strict_identity_indices=strict_identity_indices)
        target_detail = {
            "target": key,
            "path": entry["path"],
            "comparable": not bool(reasons),
            "block_reasons": reasons,
            "second_source_status": "missing",
        }
        guidance = target_blocker_guidance(key)
        if guidance is not None:
            target_detail["guidance"] = guidance
        if reasons:
            bucket["blocked"] += 1
            totals["blocked"] += 1
            for reason in reasons:
                bucket["block_reasons"][reason] = bucket["block_reasons"].get(reason, 0) + 1
        else:
            bucket["comparable"] += 1
            totals["comparable"] += 1

        comparison_result = comparison_by_target.get(key)
        if comparison_result is None:
            bucket["second_source"]["missing"] += 1
            totals["second_source_missing"] += 1
            bucket["target_details"].append(target_detail)
            continue
        status = comparison_result["status"]
        target_detail["second_source_status"] = status
        if status == "inconclusive":
            target_detail["second_source_reasons"] = comparison_result.get("reasons", [])
        elif status == "rejected":
            target_detail["diff_count"] = len(comparison_result.get("diffs", []))
            first_diff = comparison_result.get("diffs", [{}])[0]
            target_detail["first_diff"] = first_diff.get("path")
        bucket["second_source"][status] += 1
        totals[f"second_source_{status}"] += 1
        bucket["target_details"].append(target_detail)

    return {
        "schema": "obelisk.reflection-snapshot-readiness.v1",
        "strict_identity_indices": strict_identity_indices,
        "target_filters": sorted(target_filters),
        "second_source_status": "compared" if candidate is not None else "missing_candidate_root",
        "evidence_scope": READINESS_EVIDENCE_SCOPE,
        "not_promoted_surfaces": sorted(READINESS_NOT_PROMOTED_SURFACES),
        "non_claims": list(READINESS_NON_CLAIMS),
        "totals": totals,
        "promotion_gate": promotion_gate_summary(),
        "modules": [modules[key] for key in sorted(modules)],
    }


def print_text(report: dict[str, Any]) -> None:
    if report["schema"] == "obelisk.reflection-snapshot-target-sets.v1":
        for item in report["target_sets"]:
            print(f"{item['name']}: readiness_classification={item['readiness_classification']}")
            for target in item["targets"]:
                print(f"  {target}")
        return

    if report["schema"] == "obelisk.reflection-target-guidance.v1":
        print(
            "target_guidance count={count} scope={scope} target_set_guidance={set_count}".format(
                count=len(report["targets"]),
                scope=report["guidance_scope"],
                set_count=len(report.get("target_set_guidance", [])),
            )
        )
        for item in report.get("target_set_guidance", []):
            parts = [
                f"target_set={item['target_set']}",
                f"classification={item.get('classification')}",
            ]
            why_blocked = item.get("why_blocked")
            if isinstance(why_blocked, list) and why_blocked:
                parts.append(f"why_blocked={','.join(str(reason) for reason in why_blocked)}")
            next_offline_input = item.get("next_offline_input")
            if isinstance(next_offline_input, str) and next_offline_input:
                parts.append(f"next_offline_input={next_offline_input}")
            snapshot_prep_checks = item.get("snapshot_prep_checks")
            if isinstance(snapshot_prep_checks, list) and snapshot_prep_checks:
                parts.append(f"snapshot_prep_checks={len(snapshot_prep_checks)}")
            non_claim = item.get("non_claim")
            if isinstance(non_claim, str) and non_claim:
                parts.append(f"non_claim={non_claim}")
            print("  " + " ".join(parts))
        for item in report["targets"]:
            parts = [
                f"target={item['target']}",
                f"classification={item.get('classification')}",
            ]
            why_blocked = item.get("why_blocked")
            if isinstance(why_blocked, list) and why_blocked:
                parts.append(f"why_blocked={','.join(str(reason) for reason in why_blocked)}")
            next_offline_input = item.get("next_offline_input")
            if isinstance(next_offline_input, str) and next_offline_input:
                parts.append(f"next_offline_input={next_offline_input}")
            snapshot_prep_checks = item.get("snapshot_prep_checks")
            if isinstance(snapshot_prep_checks, list) and snapshot_prep_checks:
                parts.append(f"snapshot_prep_checks={len(snapshot_prep_checks)}")
            non_claim = item.get("non_claim")
            if isinstance(non_claim, str) and non_claim:
                parts.append(f"non_claim={non_claim}")
            print("  " + " ".join(parts))
        return

    if report["schema"] == "obelisk.reflection-snapshot-readiness.v1":
        totals = report["totals"]
        print(
            "readiness targets={targets} comparable={comparable} blocked={blocked} "
            "second_source_status={second_source_status} gate_mode={gate_mode}".format(
                second_source_status=report["second_source_status"],
                gate_mode=report.get("gate_mode", "unknown"),
                **totals,
            )
        )
        promotion_gate = report["promotion_gate"]
        blocker_reasons = [
            f"{blocker.get('reason')}:{blocker.get('count')}"
            for blocker in promotion_gate.get("blockers", [])
            if isinstance(blocker, dict)
        ]
        blockers = ",".join(blocker_reasons) if blocker_reasons else "none"
        print(f"promotion_gate ready={str(promotion_gate['ready']).lower()} blockers={blockers}")
        for module in report["modules"]:
            second_source = module["second_source"]
            print(
                "{schema}:{module_name} targets={targets} comparable={comparable} "
                "blocked={blocked} second_source=accepted:{accepted},rejected:{rejected},"
                "inconclusive:{inconclusive},missing:{missing}".format(
                    schema=module["schema"],
                    module_name=module["module"],
                    targets=module["targets"],
                    comparable=module["comparable"],
                    blocked=module["blocked"],
                    accepted=second_source["accepted"],
                    rejected=second_source["rejected"],
                    inconclusive=second_source["inconclusive"],
                    missing=second_source["missing"],
                )
            )
            for detail in module["target_details"]:
                second_source_status = detail["second_source_status"]
                if detail["comparable"] and second_source_status == "accepted":
                    continue

                parts = [
                    f"target={detail['target']}",
                    f"comparable={str(detail['comparable']).lower()}",
                    f"second_source={second_source_status}",
                ]
                block_reasons = detail.get("block_reasons", [])
                if block_reasons:
                    parts.append(f"block_reasons={','.join(block_reasons)}")
                second_source_reasons = detail.get("second_source_reasons", [])
                if second_source_reasons:
                    parts.append(f"second_source_reasons={','.join(second_source_reasons)}")
                guidance = detail.get("guidance")
                if isinstance(guidance, dict):
                    classification = guidance.get("classification")
                    why_blocked = guidance.get("why_blocked")
                    if isinstance(classification, str) and classification:
                        parts.append(f"guidance={classification}")
                    if isinstance(why_blocked, list) and why_blocked:
                        parts.append(f"why_blocked={','.join(str(reason) for reason in why_blocked)}")
                    next_offline_input = guidance.get("next_offline_input")
                    if isinstance(next_offline_input, str) and next_offline_input:
                        parts.append(f"next_offline_input={next_offline_input}")
                    snapshot_prep_checks = guidance.get("snapshot_prep_checks")
                    if isinstance(snapshot_prep_checks, list) and snapshot_prep_checks:
                        parts.append(f"snapshot_prep_checks={len(snapshot_prep_checks)}")
                    non_claim = guidance.get("non_claim")
                    if isinstance(non_claim, str) and non_claim:
                        parts.append(f"non_claim={non_claim}")
                if "first_diff" in detail:
                    parts.append(f"first_diff={detail['first_diff']}")
                print(f"  {' '.join(parts)}")
        return

    counts = report["counts"]
    print(
        "summary accepted={accepted} rejected={rejected} inconclusive={inconclusive}".format(
            **counts,
        )
    )
    for result in report["results"]:
        line = f"{result['status']} {result['target']}"
        if result["status"] == "rejected":
            first = result.get("diffs", [{}])[0]
            line += f" first_diff={first.get('path')} base={first.get('base')!r} candidate={first.get('candidate')!r}"
        elif result["status"] == "inconclusive":
            line += " reasons=" + ",".join(result.get("reasons", []))
        print(line)


def apply_readiness_gate_mode(report: dict[str, Any]) -> None:
    if report.get("schema") != "obelisk.reflection-snapshot-readiness.v1":
        return
    if report.get("gate_mode") == "second_source_promotion":
        return
    promotion_gate = report.get("promotion_gate")
    if not isinstance(promotion_gate, dict) or not promotion_gate.get("ready"):
        return
    promotion_gate["ready"] = False
    blockers = promotion_gate.setdefault("blockers", [])
    if isinstance(blockers, list):
        blockers.append({"reason": "not_second_source_promotion_gate", "count": 1})


def require_target_set_for_promotion(report: dict[str, Any], target_sets: list[str]) -> None:
    if report.get("schema") != "obelisk.reflection-snapshot-readiness.v1":
        return
    if report.get("gate_mode") != "second_source_promotion":
        return
    if target_sets:
        return
    promotion_gate = report.get("promotion_gate")
    if not isinstance(promotion_gate, dict):
        return
    promotion_gate["ready"] = False
    blockers = promotion_gate.setdefault("blockers", [])
    if isinstance(blockers, list):
        blockers.append({"reason": "promotion_requires_target_set", "count": 1})


def block_non_release_target_set_promotion(report: dict[str, Any], target_sets: list[str]) -> None:
    if report.get("schema") != "obelisk.reflection-snapshot-readiness.v1":
        return
    if report.get("gate_mode") != "second_source_promotion":
        return
    requested = set(target_sets)
    non_release = sorted(requested - RELEASE_READINESS_TARGET_SETS)
    if not non_release:
        return
    promotion_gate = report.get("promotion_gate")
    if not isinstance(promotion_gate, dict):
        return
    promotion_gate["ready"] = False
    planning_only = sorted(requested & (PLANNING_ONLY_TARGET_SETS | MISSION_CONSUME_ONLY_TARGET_SETS))
    promotion_gate["ready_scope"] = (
        "planning_only" if planning_only and set(non_release) == set(planning_only) else "internal_layout_only"
    )
    blockers = promotion_gate.setdefault("blockers", [])
    if isinstance(blockers, list):
        blockers.append({"reason": "target_set_not_release_readiness", "count": len(non_release)})


def main() -> int:
    args = parse_args()
    if args.list_target_sets:
        report = target_set_report()
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print_text(report)
        return 0
    target_filters = expand_target_filters(args.target, args.target_set)
    if args.list_target_guidance:
        reject_duplicate_target_set_guidance_filters(args.target_set)
        reject_duplicate_target_guidance_filters(args.target)
        unmatched_guidance = unmatched_target_guidance_filters(args.target)
        if unmatched_guidance:
            raise SystemExit(
                "target guidance filter did not match known guidance: "
                + ", ".join(sorted(unmatched_guidance))
            )
        report = target_guidance_report(target_filters)
        report["target_sets"] = sorted(args.target_set)
        report["target_set_guidance"] = target_set_guidance_report(args.target_set)
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print_text(report)
        return 0

    if args.base_root is None:
        raise SystemExit("--base-root is required unless --list-target-sets or --list-target-guidance is used")
    if args.fail_on_readiness_gaps and args.allow_ark_sha_mismatch:
        raise SystemExit("--allow-ark-sha-mismatch is incompatible with --fail-on-readiness-gaps")
    reject_protected_input_path("--base-root", args.base_root)
    if args.candidate_root:
        reject_protected_input_path("--candidate-root", args.candidate_root)
    base = load_snapshot_set(args.base_root)
    candidate = load_snapshot_set(args.candidate_root) if args.candidate_root else None
    if args.readiness_report:
        report = readiness_report(
            base,
            strict_identity_indices=args.strict_identity_indices,
            allow_ark_sha_mismatch=args.allow_ark_sha_mismatch,
            target_filters=target_filters,
            candidate=candidate,
        )
        if args.fail_on_readiness_gaps:
            report["gate_mode"] = "second_source_promotion"
        elif args.fail_on_base_readiness_gaps:
            report["gate_mode"] = "base_fixture_readiness"
        else:
            report["gate_mode"] = "informational_gap_report"
        apply_readiness_gate_mode(report)
        require_target_set_for_promotion(report, args.target_set)
        block_non_release_target_set_promotion(report, args.target_set)
    else:
        if candidate is None:
            raise SystemExit("--candidate-root is required unless --readiness-report is used")
        report = compare_sets(
            base,
            candidate,
            strict_identity_indices=args.strict_identity_indices,
            allow_ark_sha_mismatch=args.allow_ark_sha_mismatch,
            target_filters=target_filters,
        )
    report["target_sets"] = sorted(args.target_set)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_text(report)
    if report["schema"] == "obelisk.reflection-snapshot-readiness.v1":
        if args.fail_on_base_readiness_gaps:
            totals = report["totals"]
            if totals["targets"] == 0 or totals["blocked"]:
                return 1
        if args.fail_on_readiness_gaps:
            totals = report["totals"]
            if totals["targets"] == 0:
                return 1
            if totals["blocked"] or totals["second_source_rejected"]:
                return 1
            if totals["second_source_inconclusive"] or totals["second_source_missing"]:
                return 2
            if not report["promotion_gate"].get("ready"):
                return 1
        return 0
    if report["counts"]["rejected"]:
        return 1
    if report["counts"]["inconclusive"]:
        return 2
    if sum(report["counts"].values()) == 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
