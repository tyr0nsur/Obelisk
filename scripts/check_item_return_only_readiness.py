#!/usr/bin/env python3
"""Read-only readiness check for the internal item return-only lane."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_ROOT = Path("/home/flowcommunity-ark/obelisk-artifacts/item-return-only-policy-slice-20260530T072255Z")
DEFAULT_MANIFEST_NAME = "item-return-only-policy-slice.json"
EXPECTED_MANIFEST_SHA256 = "242d7506703d0164cfd5c2722690d4d865ca4063f4db1c26be4374da133f3f42"
REPORT_SCHEMA = "obelisk.item-return-only-readiness-check.v1"
POLICY_SCHEMA = "obelisk.item-return-only-policy-slice.v1"
INPUT_TARGET_SET = "item-compact-intake"
OUTPUT_TARGET_SET = "item-return-only-policy-slice"
PUBLIC_GAMEPLAY_EVENTS = REPO_ROOT / "docs" / "public_gameplay_events.json"
PUBLIC_GAMEPLAY_EVENTS_SCHEMA = "obelisk.public-gameplay-events.v1"
GAMEPLAY_POLICY_EVENT_ID = "obelisk.gameplay_policy.v1"
ITEM_RETURN_BACKING_REPORT = "docs/research/2026-05-30-item-return-only-policy-slice.md"
INVENTORY_ITEM_RESOURCE_KIND = "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM"
RETURN_VALUE_FIELD_MASK = "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE"
REQUESTED_BY_PLAYER_FIELD_MASK = "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER"
IGNORE_COOLDOWN_FIELD_MASK = "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN"
EXPECTED_METADATA_SURFACE_IDS = {
    "obelisk.resource_kind_descriptors.v1",
    "obelisk.gameplay_policy_event_descriptors.v1",
}
EXPECTED_DESCRIPTOR_SURFACES = {
    "obelisk.resource_kind_descriptors.v1": {
        "public_name": "DescribeResourceKind",
        "descriptor_struct": "ObeliskResourceKindDescriptor",
        "descriptor": "DescribeResourceKind",
        "descriptor_fields": [
            "abi_version",
            "struct_size",
            "resource_kind",
            "reserved0",
            "flags",
            "supported_gameplay_policy_event_mask",
            "supported_gameplay_policy_field_mask",
            "stable_name",
            "display_name",
        ],
        "scope_terms": [
            "metadata-only",
            "no identity",
            "no lookup",
            "no handle",
            "no cross-event correlation",
            "no mutation",
            "no UE object access",
        ],
        "not_promoted": {
            "ResourceHandle",
            "object identity",
            "lookup",
            "cross-event correlation",
            "persistent handles",
            "UE pointers",
            "mutation",
            "return override",
        },
    },
    "obelisk.gameplay_policy_event_descriptors.v1": {
        "public_name": "DescribeGameplayPolicyEventKind",
        "descriptor_struct": "ObeliskGameplayPolicyEventDescriptor",
        "descriptor": "DescribeGameplayPolicyEventKind",
        "descriptor_fields": [
            "abi_version",
            "struct_size",
            "event_kind",
            "resource_kind",
            "flags",
            "event_kind_mask",
            "field_mask",
            "stable_name",
            "display_name",
        ],
        "scope_terms": [
            "metadata-only",
            "no identity",
            "no lookup",
            "no cross-event correlation",
            "no mutation",
            "no return override",
            "no UE object access",
        ],
        "not_promoted": {
            "module-specific SDK",
            "ResourceHandle",
            "persistent handles",
            "object identity",
            "lookup",
            "cross-event correlation",
            "UE pointers",
            "mutation",
            "return override",
        },
    },
}
FORBIDDEN_DESCRIPTOR_FIELD_NAMES = {
    "handle",
    "resource_handle",
    "resource_id",
    "object_id",
    "player_id",
    "tribe_id",
    "inventory_id",
    "item_id",
    "lookup_key",
    "uobject",
    "gobject",
    "gobjects",
    "fname_index",
    "coordinates",
    "location",
    "mutation",
    "return_override",
}
EXPECTED_INPUT_TARGETS = {
    "PrimalItem.AllowEquipItem",
    "PrimalItem.CanRepair",
    "PrimalItem.CraftBlueprint",
    "PrimalItem.UseItemOntoItem",
}
EXPECTED_COPIED_TARGETS = {
    "PrimalItem.AllowEquipItem",
    "PrimalItem.CanRepair",
    "PrimalItem.UseItemOntoItem",
}
EXPECTED_COPIED_FIELDS = {
    "PrimalItem.AllowEquipItem.ReturnValue",
    "PrimalItem.CanRepair.ReturnValue",
    "PrimalItem.UseItemOntoItem.ReturnValue",
}
EXPECTED_PUBLIC_ITEM_RETURN_EVENT_KINDS = {
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_ALLOW_EQUIP_ITEM_CHECK",
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_CAN_REPAIR_CHECK",
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK",
}
EXPECTED_PUBLIC_ITEM_RETURN_STABLE_NAMES = {
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_ALLOW_EQUIP_ITEM_CHECK": "inventory_item.allow_equip_check",
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_CAN_REPAIR_CHECK": "inventory_item.can_repair_check",
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK": "inventory_item.use_onto_item_check",
}
EXPECTED_PUBLIC_ITEM_RETURN_EVENT_KIND_MASKS = {
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_ALLOW_EQUIP_ITEM_CHECK": (
        "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_ALLOW_EQUIP_ITEM_CHECK"
    ),
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_CAN_REPAIR_CHECK": (
        "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_CAN_REPAIR_CHECK"
    ),
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK": (
        "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK"
    ),
}
EXPECTED_PUBLIC_INVENTORY_POLICY_EVENT_KINDS = {
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK",
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK",
}
EXPECTED_PUBLIC_INVENTORY_POLICY_STABLE_NAMES = {
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK": "inventory.remote_add_check",
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK": "inventory.use_check",
}
EXPECTED_PUBLIC_INVENTORY_POLICY_FIELD_MASKS = {
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK": [
        RETURN_VALUE_FIELD_MASK,
        REQUESTED_BY_PLAYER_FIELD_MASK,
    ],
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK": [
        RETURN_VALUE_FIELD_MASK,
        IGNORE_COOLDOWN_FIELD_MASK,
    ],
}
EXPECTED_PUBLIC_EVENT_REQUIRED_FLAGS = {
    "OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD",
    "OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED",
}
ITEM_RETURN_EVENT_KIND_ALLOWED_KEYS = {
    "kind",
    "stable_name",
    "resource_kind",
    "event_kind_mask",
    "field_mask",
    "required_flags",
}
POLICY_TOP_LEVEL_ALLOWED_KEYS = {
    "schema",
    "input_target_set",
    "output_target_set",
    "policy_status",
    "coverage",
    "copied_return_bools",
    "excluded_fields",
    "safety_summary",
    "non_claims",
    "descriptor_preflight",
    "generated_from",
    "missing_targets",
    "snapshot_root",
}
COPIED_RETURN_BOOL_ALLOWED_KEYS = {
    "bool_masks",
    "copied_field",
    "direction",
    "element_size",
    "evidence_status",
    "field",
    "offset",
    "source_snapshot",
    "source_snapshot_sha256",
    "target",
    "type",
}
EXCLUDED_FIELD_ALLOWED_KEYS = {
    "excluded_field",
    "field",
    "reason",
    "source_snapshot",
    "target",
}
COVERAGE_ALLOWED_KEYS = {
    "status",
    "input_targets",
    "copied_targets",
    "copied_fields",
    "excluded_fields",
}
SAFETY_SUMMARY_ALLOWED_KEYS = {
    "artifact_status",
    "copied_bool_count",
    "descriptor_preflight_count",
    "excluded_field_count",
    "explicitly_excluded",
    "intended_use",
    "promotion_ready",
}
DESCRIPTOR_PREFLIGHT_ALLOWED_KEYS = {
    "assigned_event_kind",
    "assigned_event_kind_mask",
    "descriptor_count",
    "descriptors",
    "explicitly_not_assigned",
    "payload_policy",
    "promotion_ready",
    "public_promotion",
    "public_surface",
    "resource_backing",
    "resource_kind",
    "return_value_only",
    "scope",
    "status",
}
DESCRIPTOR_PREFLIGHT_DESCRIPTOR_ALLOWED_KEYS = {
    "assigned_event_kind",
    "assigned_event_kind_mask",
    "copied_field",
    "descriptor",
    "direction",
    "evidence_status",
    "field",
    "payload_policy",
    "promotion_ready",
    "public_promotion",
    "resource_backing",
    "resource_kind",
    "source_snapshot",
    "source_snapshot_sha256",
    "target",
    "type",
}
EXPECTED_EXCLUDED_FIELDS = {
    "PrimalItem.AllowEquipItem.toInventory",
    "PrimalItem.CanRepair.bIgnoreInventoryRequirement",
    "PrimalItem.CraftBlueprint.bConsumeResources",
    "PrimalItem.UseItemOntoItem.DestinationItem",
    "PrimalItem.UseItemOntoItem.AdditionalData",
}
EXPECTED_SOURCE_TARGETS = {
    "snapshot-0001": "PrimalItem.AllowEquipItem",
    "snapshot-0002": "PrimalItem.CanRepair",
    "snapshot-0003": "PrimalItem.CraftBlueprint",
    "snapshot-0004": "PrimalItem.UseItemOntoItem",
}
REQUIRED_NON_CLAIM_TOKENS = (
    "does not promote public SDK callbacks",
    "does not expose UE pointers",
    "does not copy CraftBlueprint",
)
FORBIDDEN_COPIED_RE = re.compile(
    r"(?:CraftBlueprint|toInventory|DestinationItem|AdditionalData|bIgnoreInventoryRequirement|"
    r"bConsumeResources|identity|lookup|mutation|object_refs|public_sdk|resource_handle|return_override|"
    r"runtime|ue_pointer)",
    re.IGNORECASE,
)
FORBIDDEN_CLAIM_FIELD_RE = re.compile(
    r"(?:inventory_sdk|items_sdk|item_sdk|public_sdk|identity|lookup|mutation|resource_handle|"
    r"return_overrides?|runtime_(?:ready|validated|validation)|v1(?:_completion|_complete|_stable)?|"
    r"completion)",
    re.IGNORECASE,
)
PUBLIC_GAMEPLAY_EVENTS_READINESS_KEYS = {
    "inventory_sdk_ready",
    "items_sdk_ready",
    "promotion_ready",
    "public_inventory_sdk_ready",
    "public_items_sdk_ready",
    "public_sdk_ready",
    "runtime_ready",
    "stable_sdk_ready",
    "v1_completion_ready",
    "v1_ready",
}
PUBLIC_GAMEPLAY_EVENTS_READINESS_TEXT_KEYS = PUBLIC_GAMEPLAY_EVENTS_READINESS_KEYS | {
    "inventory_sdk_readiness",
    "inventory_sdk_status",
    "items_sdk_readiness",
    "items_sdk_status",
    "promotion_status",
    "promotion_readiness",
    "public_inventory_sdk_readiness",
    "public_inventory_sdk_status",
    "public_items_sdk_readiness",
    "public_items_sdk_status",
    "public_sdk_readiness",
    "public_sdk_status",
    "runtime_readiness",
    "runtime_status",
    "stable_sdk_readiness",
    "stable_sdk_status",
    "v1_completion_readiness",
    "v1_completion_status",
    "v1_sdk_status",
    "v1_readiness",
    "v1_status",
}
PUBLIC_GAMEPLAY_EVENTS_POSITIVE_READINESS_PHRASES = (
    "inventory sdk ready",
    "items sdk ready",
    "promotion ready",
    "public sdk ready",
    "runtime ready",
    "runtime readiness",
    "stable sdk ready",
    "v1 completion ready",
    "v1 ready",
)
PUBLIC_GAMEPLAY_EVENTS_POSITIVE_READINESS_VALUES = {
    "allowed",
    "available",
    "complete",
    "enabled",
    "live",
    "promoted",
    "ready",
    "stable",
    "supported",
    "true",
    "validated",
    "yes",
}
PUBLIC_GAMEPLAY_EVENTS_STATUS_CLAIM_KEY_RE = re.compile(
    r"(?:inventory_sdk|items_sdk|public_(?:inventory_sdk|items_sdk|sdk)|stable_sdk|"
    r"v1(?:_sdk|_completion)?|runtime|promotion|identity|lookup|mutation|"
    r"resource_handle|return_override).*(?:status|readiness|ready|promotion)$",
    re.IGNORECASE,
)
POSITIVE_POLICY_CLAIM_SUBJECT_RE = re.compile(
    r"(?:"
    r"Inventory\s+SDK|Items\s+SDK|item\s+SDK|public\s+(?:SDK|API|ABI|contract|module)|"
    r"runtime(?:\s+hook)?|approved\s+runtime\s+evidence|complete\s+SDK|stable\s+SDK|"
    r"v1\s+(?:completion|SDK|release)|P0|dependency\s+chain|package\s+shape|plugin\s+hub|"
    r"item\s+identity|inventory\s+identity|object\s+identity|class\s+identity|identity|lookup|"
    r"mutation|return\s+overrides?|ResourceHandle|resource\s+handle"
    r")",
    re.IGNORECASE,
)
POSITIVE_POLICY_CLAIM_CONTEXT_RE = re.compile(
    r"(?:"
    r"ready|readiness|available|enabled|promoted|promotion|complete|"
    r"completion|supported|validated|claim|counts|allowed|unblocked|unlocked|"
    r"clears?|resolves?|replaces?|satisfies|stable|accepted|approved"
    r")",
    re.IGNORECASE,
)
NEGATIVE_POLICY_CLAIM_RE = re.compile(
    r"\b(?:does\s+not|do\s+not|must\s+not|not\s+promote|not\s+expose|not\s+copy|no\s+|excluded)\b",
    re.IGNORECASE,
)
POLICY_CLAIM_CLAUSE_SPLIT_RE = re.compile(r"(?:[.;\n]|\bbut\b|\bhowever\b)", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate item return-only candidate readiness without promoting an Inventory/Items SDK."
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Offline artifact root.")
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Item return-only policy-slice manifest. Defaults to --root/item-return-only-policy-slice.json.",
    )
    parser.add_argument(
        "--expected-manifest-sha256",
        default=EXPECTED_MANIFEST_SHA256,
        help="Expected direct manifest SHA256. Defaults to the reviewed durable artifact.",
    )
    parser.add_argument(
        "--skip-artifact-gates",
        action="store_true",
        help="Skip consume/promote gate subprocesses for hermetic policy-fixture tests.",
    )
    parser.add_argument("--json", action="store_true", help="Compatibility flag; output is always JSON.")
    return parser.parse_args()


def append_blocker(blockers: list[dict[str, Any]], reason: str, **details: Any) -> None:
    blockers.append({"reason": reason, **details})


def safe_path(path: Path, label: str, blockers: list[dict[str, Any]]) -> Path | None:
    try:
        reject_symlink_component(path, label)
        return reject_protected_input_path(path, label)
    except SystemExit as exc:
        append_blocker(blockers, "path_rejected", label=label, path=str(path), detail=str(exc))
        return None


def run_gate(root: Path, manifest: Path, mode: str) -> tuple[int, dict[str, Any] | None, str]:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_DIR / "validate_offline_artifact_gate.py"),
            "--root",
            str(root),
            "--manifest",
            str(manifest),
            "--mode",
            mode,
            "--json",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    payload: dict[str, Any] | None = None
    if result.stdout.strip():
        try:
            parsed = json.loads(result.stdout)
            if isinstance(parsed, dict):
                payload = parsed
        except json.JSONDecodeError:
            payload = None
    return result.returncode, payload, result.stderr.strip()


def read_policy(manifest: Path, blockers: list[dict[str, Any]], expected_sha256: str) -> dict[str, Any] | None:
    try:
        content = manifest.read_bytes()
        manifest_sha256 = hashlib.sha256(content).hexdigest()
        parsed = json.loads(content.decode("utf-8"))
    except OSError as exc:
        append_blocker(blockers, "manifest_unreadable", path=str(manifest), detail=str(exc))
        return None
    except json.JSONDecodeError as exc:
        append_blocker(blockers, "manifest_malformed", path=str(manifest), detail=str(exc))
        return None
    if not isinstance(parsed, dict):
        append_blocker(blockers, "manifest_not_object", path=str(manifest))
        return None
    if manifest_sha256 != expected_sha256:
        append_blocker(blockers, "manifest_sha256_mismatch", expected=expected_sha256, value=manifest_sha256)
    return parsed


def read_json_object(path: Path, blockers: list[dict[str, Any]], *, label: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        append_blocker(blockers, f"{label}_unreadable", path=str(path), detail=str(exc))
        return None
    except json.JSONDecodeError as exc:
        append_blocker(blockers, f"{label}_malformed", path=str(path), detail=str(exc))
        return None
    if not isinstance(parsed, dict):
        append_blocker(blockers, f"{label}_not_object", path=str(path))
        return None
    return parsed


def require_set(blockers: list[dict[str, Any]], *, reason: str, actual: Any, expected: set[str]) -> set[str]:
    actual_set = set(actual) if isinstance(actual, list) and all(isinstance(item, str) for item in actual) else set()
    if actual_set != expected:
        append_blocker(blockers, reason, missing=sorted(expected - actual_set), unexpected=sorted(actual_set - expected))
    return actual_set


def reject_forbidden_claim_fields(
    blockers: list[dict[str, Any]],
    *,
    reason: str,
    mapping: dict[str, Any],
    path: str,
    allowed_keys: set[str] | None = None,
) -> None:
    for key in mapping:
        if allowed_keys is not None and key not in allowed_keys:
            append_blocker(blockers, reason, path=path, field=key, detail="unexpected_field")
        elif FORBIDDEN_CLAIM_FIELD_RE.search(key):
            append_blocker(blockers, reason, path=path, field=key, detail="forbidden_claim_field")


def require_not_promoted_claim(
    blockers: list[dict[str, Any]], *, reason: str, value: Any, required_token: str = "GameplayPolicyEvent"
) -> None:
    if not isinstance(value, str):
        append_blocker(blockers, reason, value=value)
        return
    if "not promoted" not in value.lower() or required_token not in value:
        append_blocker(blockers, reason, value=value)


def scan_public_gameplay_event_readiness_claims(
    value: Any,
    blockers: list[dict[str, Any]],
    path: str,
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in PUBLIC_GAMEPLAY_EVENTS_READINESS_KEYS and child is True:
                append_blocker(
                    blockers,
                    "public_gameplay_events_readiness_claim_enabled",
                    path=child_path,
                    field=key,
                    value=child,
                )
            if key in PUBLIC_GAMEPLAY_EVENTS_READINESS_TEXT_KEYS and isinstance(child, str):
                lowered = child.casefold()
                if lowered in PUBLIC_GAMEPLAY_EVENTS_POSITIVE_READINESS_VALUES:
                    append_blocker(
                        blockers,
                        "public_gameplay_events_readiness_claim_enabled",
                        path=child_path,
                        field=key,
                        value=child,
                    )
                    scan_public_gameplay_event_readiness_claims(child, blockers, child_path)
                    continue
                for phrase in PUBLIC_GAMEPLAY_EVENTS_POSITIVE_READINESS_PHRASES:
                    if phrase in lowered:
                        append_blocker(
                            blockers,
                            "public_gameplay_events_readiness_claim_enabled",
                            path=child_path,
                            field=key,
                            term=phrase,
                            value=child,
                        )
                        break
            if (
                key not in PUBLIC_GAMEPLAY_EVENTS_READINESS_TEXT_KEYS
                and isinstance(child, str)
                and PUBLIC_GAMEPLAY_EVENTS_STATUS_CLAIM_KEY_RE.search(key)
                and child.casefold() in PUBLIC_GAMEPLAY_EVENTS_POSITIVE_READINESS_VALUES
            ):
                append_blocker(
                    blockers,
                    "public_gameplay_events_readiness_claim_enabled",
                    path=child_path,
                    field=key,
                    value=child,
                )
            scan_public_gameplay_event_readiness_claims(child, blockers, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            scan_public_gameplay_event_readiness_claims(child, blockers, f"{path}[{index}]")


def reject_positive_policy_claim_values(value: Any, blockers: list[dict[str, Any]], *, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            reject_positive_policy_claim_values(child, blockers, path=f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            reject_positive_policy_claim_values(child, blockers, path=f"{path}[{index}]")
        return
    if not isinstance(value, str):
        return
    for clause in POLICY_CLAIM_CLAUSE_SPLIT_RE.split(value):
        if NEGATIVE_POLICY_CLAIM_RE.search(clause):
            continue
        if POSITIVE_POLICY_CLAIM_SUBJECT_RE.search(clause) is None:
            continue
        if POSITIVE_POLICY_CLAIM_CONTEXT_RE.search(clause) is None:
            continue
        break
    else:
        return
    append_blocker(blockers, "forbidden_positive_policy_claim_value", path=path, value=value)


def validate_generated_from(policy: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    generated_from = policy.get("generated_from")
    if not isinstance(generated_from, dict):
        append_blocker(blockers, "generated_from_missing")
        return {}
    reject_forbidden_claim_fields(
        blockers,
        reason="generated_from_unexpected_field",
        mapping=generated_from,
        path="generated_from",
        allowed_keys={"snapshot_schema", "input_snapshots"},
    )
    if generated_from.get("snapshot_schema") != "obelisk.ufunction-chain.snapshot.v1":
        append_blocker(blockers, "snapshot_schema_mismatch", value=generated_from.get("snapshot_schema"))
    snapshots = generated_from.get("input_snapshots")
    if not isinstance(snapshots, list) or len(snapshots) != len(EXPECTED_SOURCE_TARGETS):
        append_blocker(
            blockers,
            "input_snapshot_count_mismatch",
            expected=len(EXPECTED_SOURCE_TARGETS),
            value=len(snapshots) if isinstance(snapshots, list) else None,
        )
        return {}

    sources: dict[str, dict[str, str]] = {}
    for index, snapshot in enumerate(snapshots):
        if not isinstance(snapshot, dict):
            append_blocker(blockers, "input_snapshot_entry_invalid", index=index)
            continue
        reject_forbidden_claim_fields(
            blockers,
            reason="input_snapshot_unexpected_field",
            mapping=snapshot,
            path=f"generated_from.input_snapshots[{index}]",
            allowed_keys={"id", "sha256"},
        )
        snapshot_id = snapshot.get("id")
        snapshot_sha256 = snapshot.get("sha256")
        if not isinstance(snapshot_id, str) or not snapshot_id:
            append_blocker(blockers, "input_snapshot_id_invalid", index=index)
            continue
        if snapshot_id in sources:
            append_blocker(blockers, "input_snapshot_id_duplicate", index=index, snapshot_id=snapshot_id)
        if snapshot_id not in EXPECTED_SOURCE_TARGETS:
            append_blocker(blockers, "input_snapshot_id_unexpected", index=index, snapshot_id=snapshot_id)
        if not isinstance(snapshot_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", snapshot_sha256):
            append_blocker(blockers, "input_snapshot_sha256_invalid", index=index, snapshot_id=snapshot_id)
            continue
        sources[snapshot_id] = {
            "sha256": snapshot_sha256,
            "target": EXPECTED_SOURCE_TARGETS.get(snapshot_id, ""),
        }
    if set(sources) != set(EXPECTED_SOURCE_TARGETS):
        append_blocker(
            blockers,
            "input_snapshot_ids_mismatch",
            missing=sorted(set(EXPECTED_SOURCE_TARGETS) - set(sources)),
            unexpected=sorted(set(sources) - set(EXPECTED_SOURCE_TARGETS)),
        )
    return sources


def validate_source_snapshot(
    entry: dict[str, Any],
    *,
    index: int,
    field_key: str,
    reason_prefix: str,
    sources: dict[str, dict[str, str]],
    blockers: list[dict[str, Any]],
    require_sha256: bool,
) -> None:
    source_snapshot = entry.get("source_snapshot")
    source_snapshot_sha256 = entry.get("source_snapshot_sha256")
    if not isinstance(source_snapshot, str) or source_snapshot not in sources:
        append_blocker(blockers, f"{reason_prefix}_source_snapshot_unknown", index=index, field=entry.get(field_key))
        return
    source = sources[source_snapshot]
    if require_sha256 and source_snapshot_sha256 != source["sha256"]:
        append_blocker(
            blockers,
            f"{reason_prefix}_source_snapshot_sha256_mismatch",
            index=index,
            field=entry.get(field_key),
            expected=source["sha256"],
            value=source_snapshot_sha256,
        )
    if entry.get("target") != source["target"]:
        append_blocker(
            blockers,
            f"{reason_prefix}_source_snapshot_target_mismatch",
            index=index,
            field=entry.get(field_key),
            expected=source["target"],
            value=entry.get("target"),
        )


def find_gameplay_policy_event(public_events: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    promoted_events = public_events.get("promoted_events")
    if not isinstance(promoted_events, list):
        append_blocker(blockers, "public_gameplay_events_promoted_events_missing")
        return {}
    matches = [
        event
        for event in promoted_events
        if isinstance(event, dict) and event.get("event_id") == GAMEPLAY_POLICY_EVENT_ID
    ]
    if len(matches) != 1:
        append_blocker(blockers, "public_gameplay_policy_event_count_mismatch", expected=1, value=len(matches))
        return matches[0] if matches else {}
    return matches[0]


def validate_descriptor_surfaces(public_events: dict[str, Any], blockers: list[dict[str, Any]]) -> list[str]:
    metadata_surfaces = public_events.get("metadata_surfaces")
    if not isinstance(metadata_surfaces, list):
        append_blocker(blockers, "public_metadata_surfaces_missing")
        return []

    surfaces = {
        surface.get("surface_id"): surface
        for surface in metadata_surfaces
        if isinstance(surface, dict) and isinstance(surface.get("surface_id"), str)
    }
    surface_ids = set(surfaces)
    if surface_ids != EXPECTED_METADATA_SURFACE_IDS:
        append_blocker(
            blockers,
            "public_metadata_surface_ids_mismatch",
            missing=sorted(EXPECTED_METADATA_SURFACE_IDS - surface_ids),
            unexpected=sorted(surface_ids - EXPECTED_METADATA_SURFACE_IDS),
        )

    for surface_id, expected in EXPECTED_DESCRIPTOR_SURFACES.items():
        surface = surfaces.get(surface_id)
        if not isinstance(surface, dict):
            append_blocker(blockers, "public_descriptor_surface_missing", surface_id=surface_id)
            continue
        for key in ("public_name", "descriptor_struct", "descriptor"):
            if surface.get(key) != expected[key]:
                append_blocker(
                    blockers,
                    "public_descriptor_surface_metadata_mismatch",
                    surface_id=surface_id,
                    field=key,
                    expected=expected[key],
                    value=surface.get(key),
                )
        descriptor_fields = surface.get("descriptor_fields")
        if descriptor_fields != expected["descriptor_fields"]:
            append_blocker(
                blockers,
                "public_descriptor_fields_mismatch",
                surface_id=surface_id,
                expected=expected["descriptor_fields"],
                value=descriptor_fields,
            )
        if isinstance(descriptor_fields, list):
            forbidden_fields = [
                field
                for field in descriptor_fields
                if isinstance(field, str) and field.lower() in FORBIDDEN_DESCRIPTOR_FIELD_NAMES
            ]
            if forbidden_fields:
                append_blocker(
                    blockers,
                    "public_descriptor_forbidden_field",
                    surface_id=surface_id,
                    fields=forbidden_fields,
                )
        else:
            append_blocker(blockers, "public_descriptor_fields_not_list", surface_id=surface_id)

        scope = surface.get("scope")
        scope_text = scope.lower() if isinstance(scope, str) else ""
        for term in expected["scope_terms"]:
            if term.lower() not in scope_text:
                append_blocker(
                    blockers,
                    "public_descriptor_scope_missing_guardrail",
                    surface_id=surface_id,
                    term=term,
                    value=scope,
                )
        not_promoted = surface.get("not_promoted")
        promoted_exclusions = set(not_promoted) if isinstance(not_promoted, list) else set()
        missing_exclusions = expected["not_promoted"] - promoted_exclusions
        if missing_exclusions:
            append_blocker(
                blockers,
                "public_descriptor_not_promoted_missing",
                surface_id=surface_id,
                missing=sorted(missing_exclusions),
            )

    return sorted(surface_ids)


def validate_public_gameplay_events(public_events: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    if public_events.get("schema") != PUBLIC_GAMEPLAY_EVENTS_SCHEMA:
        append_blocker(blockers, "public_gameplay_events_schema_mismatch", value=public_events.get("schema"))

    descriptor_surface_ids = validate_descriptor_surfaces(public_events, blockers)
    event = find_gameplay_policy_event(public_events, blockers)
    if not event:
        return {
            "descriptor_surface_ids": descriptor_surface_ids,
            "item_return_event_kinds": [],
            "item_return_backing_target_set": None,
            "item_return_event_descriptors": [],
            "inventory_policy_event_kinds": [],
            "inventory_policy_event_descriptors": [],
        }

    item_return_backing = event.get("item_return_backing_target_set")
    if item_return_backing != OUTPUT_TARGET_SET:
        append_blocker(
            blockers,
            "public_item_return_backing_target_set_mismatch",
            expected=OUTPUT_TARGET_SET,
            value=item_return_backing,
        )

    target_sets_raw = event.get("target_sets")
    target_sets = (
        set(target_sets_raw)
        if isinstance(target_sets_raw, list) and all(isinstance(item, str) for item in target_sets_raw)
        else set()
    )
    if not target_sets:
        append_blocker(blockers, "public_target_sets_missing_or_invalid")
    if OUTPUT_TARGET_SET in target_sets:
        append_blocker(
            blockers,
            "public_item_return_target_set_listed_as_public_scope",
            value=OUTPUT_TARGET_SET,
        )

    evidence = event.get("target_set_evidence")
    if not isinstance(evidence, list):
        append_blocker(blockers, "public_target_set_evidence_missing")
    else:
        item_return_evidence_matches = [
            entry
            for entry in evidence
            if isinstance(entry, dict) and entry.get("target_set") == OUTPUT_TARGET_SET
        ]
        if item_return_evidence_matches:
            append_blocker(
                blockers,
                "public_item_return_target_set_evidence_misclassified_as_public_scope",
                value=len(item_return_evidence_matches),
            )

    second_source_reports = event.get("second_source_reports")
    if not isinstance(second_source_reports, list) or ITEM_RETURN_BACKING_REPORT not in second_source_reports:
        append_blocker(
            blockers,
            "public_item_return_second_source_report_missing",
            expected=ITEM_RETURN_BACKING_REPORT,
            value=second_source_reports,
        )

    require_not_promoted_claim(
        blockers,
        reason="public_inventory_sdk_non_claim_missing",
        value=event.get("inventory_sdk"),
    )
    require_not_promoted_claim(
        blockers,
        reason="public_item_module_sdk_non_claim_missing",
        value=event.get("item_module_sdk"),
    )
    scan_public_gameplay_event_readiness_claims(event, blockers, "$.promoted_events[0]")
    for key in event:
        if key in {"inventory_sdk", "item_module_sdk"}:
            continue
        if key.startswith("item_return_") and FORBIDDEN_CLAIM_FIELD_RE.search(key):
            append_blocker(blockers, "public_item_return_forbidden_claim_field", field=key)

    event_kinds = event.get("event_kinds")
    if not isinstance(event_kinds, list):
        append_blocker(blockers, "public_gameplay_event_kinds_missing")
        return {
            "descriptor_surface_ids": descriptor_surface_ids,
            "item_return_event_kinds": [],
            "item_return_backing_target_set": item_return_backing,
            "item_return_event_descriptors": [],
            "inventory_policy_event_kinds": [],
            "inventory_policy_event_descriptors": [],
        }

    item_return_kinds: list[str] = []
    item_return_event_descriptors: list[dict[str, Any]] = []
    inventory_policy_event_kinds: list[str] = []
    inventory_policy_event_descriptors: list[dict[str, Any]] = []
    for index, event_kind in enumerate(event_kinds):
        if not isinstance(event_kind, dict):
            append_blocker(blockers, "public_gameplay_event_kind_not_object", index=index)
            continue
        kind = event_kind.get("kind")
        stable_name = event_kind.get("stable_name")
        if kind in EXPECTED_PUBLIC_INVENTORY_POLICY_EVENT_KINDS:
            inventory_policy_event_kinds.append(kind)
            inventory_policy_event_descriptors.append(
                {
                    "kind": kind,
                    "stable_name": stable_name,
                    "field_mask": event_kind.get("field_mask"),
                    "resource_kind": event_kind.get("resource_kind"),
                }
            )
            if stable_name != EXPECTED_PUBLIC_INVENTORY_POLICY_STABLE_NAMES[kind]:
                append_blocker(
                    blockers,
                    "public_inventory_policy_stable_name_mismatch",
                    index=index,
                    kind=kind,
                    expected=EXPECTED_PUBLIC_INVENTORY_POLICY_STABLE_NAMES[kind],
                    value=stable_name,
                )
            if event_kind.get("field_mask") != EXPECTED_PUBLIC_INVENTORY_POLICY_FIELD_MASKS[kind]:
                append_blocker(
                    blockers,
                    "public_inventory_policy_field_mask_mismatch",
                    index=index,
                    kind=kind,
                    expected=EXPECTED_PUBLIC_INVENTORY_POLICY_FIELD_MASKS[kind],
                    value=event_kind.get("field_mask"),
                )
            if isinstance(stable_name, str) and stable_name.startswith("inventory_item."):
                append_blocker(
                    blockers,
                    "public_inventory_policy_stable_name_crosses_item_return_boundary",
                    index=index,
                    kind=kind,
                    value=stable_name,
                )
        is_item_return_kind = kind in EXPECTED_PUBLIC_ITEM_RETURN_EVENT_KINDS or (
            isinstance(stable_name, str) and stable_name.startswith("inventory_item.")
        )
        if not is_item_return_kind:
            continue
        reject_forbidden_claim_fields(
            blockers,
            reason="public_item_return_unexpected_field",
            mapping=event_kind,
            path=f"event_kinds[{index}]",
            allowed_keys=ITEM_RETURN_EVENT_KIND_ALLOWED_KEYS,
        )
        if isinstance(kind, str):
            item_return_kinds.append(kind)
            item_return_event_descriptors.append(
                {
                    "kind": kind,
                    "stable_name": stable_name,
                    "field_mask": event_kind.get("field_mask"),
                    "resource_kind": event_kind.get("resource_kind"),
                }
            )
        else:
            append_blocker(blockers, "public_item_return_kind_missing", index=index, value=kind)
        if event_kind.get("stable_name") != EXPECTED_PUBLIC_ITEM_RETURN_STABLE_NAMES.get(kind):
            append_blocker(
                blockers,
                "public_item_return_stable_name_mismatch",
                index=index,
                kind=kind,
                expected=EXPECTED_PUBLIC_ITEM_RETURN_STABLE_NAMES.get(kind),
                value=event_kind.get("stable_name"),
            )
        if event_kind.get("event_kind_mask") != EXPECTED_PUBLIC_ITEM_RETURN_EVENT_KIND_MASKS.get(kind):
            append_blocker(
                blockers,
                "public_item_return_event_kind_mask_mismatch",
                index=index,
                kind=kind,
                expected=EXPECTED_PUBLIC_ITEM_RETURN_EVENT_KIND_MASKS.get(kind),
                value=event_kind.get("event_kind_mask"),
            )
        if event_kind.get("resource_kind") != INVENTORY_ITEM_RESOURCE_KIND:
            append_blocker(
                blockers,
                "public_item_return_resource_kind_mismatch",
                index=index,
                kind=kind,
                expected=INVENTORY_ITEM_RESOURCE_KIND,
                value=event_kind.get("resource_kind"),
            )
        if event_kind.get("field_mask") != [RETURN_VALUE_FIELD_MASK]:
            append_blocker(
                blockers,
                "public_item_return_field_mask_not_return_value_only",
                index=index,
                kind=kind,
                expected=[RETURN_VALUE_FIELD_MASK],
                value=event_kind.get("field_mask"),
            )
        required_flags = event_kind.get("required_flags")
        if required_flags is not None and set(required_flags if isinstance(required_flags, list) else []) != EXPECTED_PUBLIC_EVENT_REQUIRED_FLAGS:
            append_blocker(
                blockers,
                "public_item_return_required_flags_mismatch",
                index=index,
                kind=kind,
                expected=sorted(EXPECTED_PUBLIC_EVENT_REQUIRED_FLAGS),
                value=required_flags,
            )
        if isinstance(stable_name, str) and not stable_name.startswith("inventory_item."):
            append_blocker(
                blockers,
                "public_item_return_stable_name_crosses_inventory_policy_boundary",
                index=index,
                kind=kind,
                value=stable_name,
            )

    item_return_kind_set = set(item_return_kinds)
    inventory_policy_kind_set = set(inventory_policy_event_kinds)
    if item_return_kind_set != EXPECTED_PUBLIC_ITEM_RETURN_EVENT_KINDS:
        append_blocker(
            blockers,
            "public_item_return_event_kind_coverage_mismatch",
            missing=sorted(EXPECTED_PUBLIC_ITEM_RETURN_EVENT_KINDS - item_return_kind_set),
            unexpected=sorted(item_return_kind_set - EXPECTED_PUBLIC_ITEM_RETURN_EVENT_KINDS),
        )
    if len(item_return_kinds) != 3:
        append_blocker(blockers, "public_item_return_event_kind_count_mismatch", expected=3, value=len(item_return_kinds))
    if inventory_policy_kind_set != EXPECTED_PUBLIC_INVENTORY_POLICY_EVENT_KINDS:
        append_blocker(
            blockers,
            "public_inventory_policy_event_kind_coverage_mismatch",
            missing=sorted(EXPECTED_PUBLIC_INVENTORY_POLICY_EVENT_KINDS - inventory_policy_kind_set),
            unexpected=sorted(inventory_policy_kind_set - EXPECTED_PUBLIC_INVENTORY_POLICY_EVENT_KINDS),
        )
    if item_return_kind_set & inventory_policy_kind_set:
        append_blocker(
            blockers,
            "public_item_return_inventory_policy_event_kind_overlap",
            overlap=sorted(item_return_kind_set & inventory_policy_kind_set),
        )

    return {
        "descriptor_surface_ids": descriptor_surface_ids,
        "item_return_event_kinds": sorted(item_return_kind_set),
        "item_return_backing_target_set": item_return_backing,
        "item_return_event_descriptors": sorted(item_return_event_descriptors, key=lambda item: str(item.get("kind"))),
        "inventory_policy_event_kinds": sorted(inventory_policy_kind_set),
        "inventory_policy_event_descriptors": sorted(
            inventory_policy_event_descriptors,
            key=lambda item: str(item.get("kind")),
        ),
    }


def validate_return_bool_entries(
    policy: dict[str, Any],
    copied_fields: set[str],
    sources: dict[str, dict[str, str]],
    blockers: list[dict[str, Any]],
) -> None:
    entries = policy.get("copied_return_bools")
    if not isinstance(entries, list):
        append_blocker(blockers, "copied_return_bools_missing")
        return
    if len(entries) != 3:
        append_blocker(blockers, "copied_return_bool_count_mismatch", expected=3, value=len(entries))

    entry_fields: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            append_blocker(blockers, "copied_return_bool_entry_not_object", index=index)
            continue
        reject_forbidden_claim_fields(
            blockers,
            reason="copied_return_bool_entry_unexpected_field",
            mapping=entry,
            path=f"copied_return_bools[{index}]",
            allowed_keys=COPIED_RETURN_BOOL_ALLOWED_KEYS,
        )
        copied_field = entry.get("copied_field")
        if isinstance(copied_field, str):
            entry_fields.add(copied_field)
        if copied_field not in copied_fields:
            append_blocker(blockers, "copied_return_bool_entry_field_unexpected", index=index, copied_field=copied_field)
        for key, expected in {
            "type": "bool",
            "field": "ReturnValue",
            "direction": "return",
            "property_class": None,
            "evidence_status": "copied-return-bool-only",
            "element_size": 1,
        }.items():
            if key == "property_class":
                continue
            if entry.get(key) != expected:
                append_blocker(
                    blockers,
                    "copied_return_bool_entry_metadata_mismatch",
                    index=index,
                    copied_field=copied_field,
                    field=key,
                    expected=expected,
                    value=entry.get(key),
                )
        bool_masks = entry.get("bool_masks")
        if not isinstance(bool_masks, dict):
            append_blocker(blockers, "copied_return_bool_masks_missing", index=index, copied_field=copied_field)
        else:
            if bool_masks.get("byte_mask") != "0x01":
                append_blocker(blockers, "copied_return_bool_mask_mismatch", index=index, field="byte_mask")
            if bool_masks.get("field_mask") != "0xff":
                append_blocker(blockers, "copied_return_bool_mask_mismatch", index=index, field="field_mask")
        validate_source_snapshot(
            entry,
            index=index,
            field_key="copied_field",
            reason_prefix="copied_return_bool_entry",
            sources=sources,
            blockers=blockers,
            require_sha256=True,
        )
    if entry_fields != copied_fields:
        append_blocker(
            blockers,
            "copied_return_bool_entry_coverage_mismatch",
            missing=sorted(copied_fields - entry_fields),
            unexpected=sorted(entry_fields - copied_fields),
        )


def validate_excluded_field_entries(
    policy: dict[str, Any],
    sources: dict[str, dict[str, str]],
    blockers: list[dict[str, Any]],
) -> None:
    entries = policy.get("excluded_fields")
    if not isinstance(entries, list):
        append_blocker(blockers, "excluded_fields_missing")
        return
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            append_blocker(blockers, "excluded_field_entry_not_object", index=index)
            continue
        reject_forbidden_claim_fields(
            blockers,
            reason="excluded_field_entry_unexpected_field",
            mapping=entry,
            path=f"excluded_fields[{index}]",
            allowed_keys=EXCLUDED_FIELD_ALLOWED_KEYS,
        )
        validate_source_snapshot(
            entry,
            index=index,
            field_key="excluded_field",
            reason_prefix="excluded_field_entry",
            sources=sources,
            blockers=blockers,
            require_sha256=False,
        )


def validate_descriptor_preflight(
    policy: dict[str, Any],
    copied_fields: set[str],
    sources: dict[str, dict[str, str]],
    blockers: list[dict[str, Any]],
) -> None:
    preflight = policy.get("descriptor_preflight")
    if preflight is None:
        return
    if not isinstance(preflight, dict):
        append_blocker(blockers, "descriptor_preflight_not_object")
        return
    reject_forbidden_claim_fields(
        blockers,
        reason="descriptor_preflight_unexpected_field",
        mapping=preflight,
        path="descriptor_preflight",
        allowed_keys=DESCRIPTOR_PREFLIGHT_ALLOWED_KEYS,
    )
    for key, expected in {
        "assigned_event_kind": None,
        "assigned_event_kind_mask": None,
        "descriptor_count": 3,
        "payload_policy": "copied_return_value_only",
        "promotion_ready": False,
        "public_promotion": False,
        "public_surface": False,
        "return_value_only": True,
        "scope": OUTPUT_TARGET_SET,
        "status": "internal-evidence-only",
    }.items():
        if preflight.get(key) != expected:
            append_blocker(
                blockers,
                "descriptor_preflight_metadata_mismatch",
                field=key,
                expected=expected,
                value=preflight.get(key),
            )

    descriptors = preflight.get("descriptors")
    if not isinstance(descriptors, list):
        append_blocker(blockers, "descriptor_preflight_descriptors_missing")
        return
    if len(descriptors) != 3:
        append_blocker(blockers, "descriptor_preflight_descriptor_count_mismatch", expected=3, value=len(descriptors))

    descriptor_fields: set[str] = set()
    for index, descriptor in enumerate(descriptors):
        if not isinstance(descriptor, dict):
            append_blocker(blockers, "descriptor_preflight_descriptor_not_object", index=index)
            continue
        reject_forbidden_claim_fields(
            blockers,
            reason="descriptor_preflight_descriptor_unexpected_field",
            mapping=descriptor,
            path=f"descriptor_preflight.descriptors[{index}]",
            allowed_keys=DESCRIPTOR_PREFLIGHT_DESCRIPTOR_ALLOWED_KEYS,
        )
        copied_field = descriptor.get("copied_field")
        if isinstance(copied_field, str):
            descriptor_fields.add(copied_field)
        if copied_field not in copied_fields:
            append_blocker(
                blockers,
                "descriptor_preflight_descriptor_field_unexpected",
                index=index,
                copied_field=copied_field,
            )
        for key, expected in {
            "assigned_event_kind": None,
            "assigned_event_kind_mask": None,
            "direction": "return",
            "field": "ReturnValue",
            "payload_policy": "copied_return_value_only",
            "promotion_ready": False,
            "public_promotion": False,
            "type": "bool",
        }.items():
            if descriptor.get(key) != expected:
                append_blocker(
                    blockers,
                    "descriptor_preflight_descriptor_metadata_mismatch",
                    index=index,
                    copied_field=copied_field,
                    field=key,
                    expected=expected,
                    value=descriptor.get(key),
                )
        validate_source_snapshot(
            descriptor,
            index=index,
            field_key="copied_field",
            reason_prefix="descriptor_preflight_descriptor",
            sources=sources,
            blockers=blockers,
            require_sha256=True,
        )
    if descriptor_fields != copied_fields:
        append_blocker(
            blockers,
            "descriptor_preflight_descriptor_coverage_mismatch",
            missing=sorted(copied_fields - descriptor_fields),
            unexpected=sorted(descriptor_fields - copied_fields),
        )


def validate_policy(policy: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    reject_forbidden_claim_fields(
        blockers,
        reason="policy_unexpected_field",
        mapping=policy,
        path="policy",
        allowed_keys=POLICY_TOP_LEVEL_ALLOWED_KEYS,
    )
    if policy.get("schema") != POLICY_SCHEMA:
        append_blocker(blockers, "schema_mismatch", value=policy.get("schema"))
    if policy.get("input_target_set") != INPUT_TARGET_SET:
        append_blocker(blockers, "input_target_set_mismatch", value=policy.get("input_target_set"))
    if policy.get("output_target_set") != OUTPUT_TARGET_SET:
        append_blocker(blockers, "output_target_set_mismatch", value=policy.get("output_target_set"))
    if policy.get("policy_status") != "evidence-only":
        append_blocker(blockers, "policy_status_not_evidence_only", value=policy.get("policy_status"))

    coverage = policy.get("coverage")
    if not isinstance(coverage, dict):
        append_blocker(blockers, "coverage_missing")
        coverage = {}
    else:
        reject_forbidden_claim_fields(
            blockers,
            reason="coverage_unexpected_field",
            mapping=coverage,
            path="coverage",
            allowed_keys=COVERAGE_ALLOWED_KEYS,
        )
    input_targets = require_set(
        blockers, reason="input_target_coverage_mismatch", actual=coverage.get("input_targets"), expected=EXPECTED_INPUT_TARGETS
    )
    copied_targets = require_set(
        blockers, reason="copied_target_coverage_mismatch", actual=coverage.get("copied_targets"), expected=EXPECTED_COPIED_TARGETS
    )
    copied_fields = require_set(
        blockers, reason="copied_field_coverage_mismatch", actual=coverage.get("copied_fields"), expected=EXPECTED_COPIED_FIELDS
    )
    excluded_fields = require_set(
        blockers, reason="excluded_field_coverage_mismatch", actual=coverage.get("excluded_fields"), expected=EXPECTED_EXCLUDED_FIELDS
    )
    if coverage.get("status") != "complete":
        append_blocker(blockers, "coverage_status_not_complete", value=coverage.get("status"))

    for copied_field in copied_fields:
        if FORBIDDEN_COPIED_RE.search(copied_field):
            append_blocker(blockers, "forbidden_copied_field", copied_field=copied_field)
    for forbidden_prefix in ("PrimalItem.CraftBlueprint.",):
        if any(field.startswith(forbidden_prefix) for field in copied_fields):
            append_blocker(blockers, "craftblueprint_copied_field_not_allowed")

    sources = validate_generated_from(policy, blockers)
    validate_return_bool_entries(policy, copied_fields, sources, blockers)
    validate_excluded_field_entries(policy, sources, blockers)
    validate_descriptor_preflight(policy, copied_fields, sources, blockers)

    safety = policy.get("safety_summary")
    if not isinstance(safety, dict):
        append_blocker(blockers, "safety_summary_missing")
        safety = {}
    else:
        reject_forbidden_claim_fields(
            blockers,
            reason="safety_summary_unexpected_field",
            mapping=safety,
            path="safety_summary",
            allowed_keys=SAFETY_SUMMARY_ALLOWED_KEYS,
        )
    if safety.get("artifact_status") != "evidence_only":
        append_blocker(blockers, "safety_artifact_status_invalid", value=safety.get("artifact_status"))
    if safety.get("promotion_ready") is not False:
        append_blocker(blockers, "safety_promotion_ready_not_false", value=safety.get("promotion_ready"))
    if safety.get("intended_use") != "offline_review_only":
        append_blocker(blockers, "safety_intended_use_invalid", value=safety.get("intended_use"))
    if safety.get("copied_bool_count") != 3:
        append_blocker(blockers, "safety_copied_bool_count_mismatch", value=safety.get("copied_bool_count"))
    if safety.get("excluded_field_count") != 5:
        append_blocker(blockers, "safety_excluded_field_count_mismatch", value=safety.get("excluded_field_count"))

    non_claims = policy.get("non_claims")
    if not isinstance(non_claims, list):
        append_blocker(blockers, "non_claims_missing")
        non_claims_text = ""
    else:
        non_claims_text = "\n".join(str(item) for item in non_claims)
    for token in REQUIRED_NON_CLAIM_TOKENS:
        if token not in non_claims_text:
            append_blocker(blockers, "required_non_claim_missing", token=token)
    reject_positive_policy_claim_values(policy, blockers)

    return {
        "input_targets": sorted(input_targets),
        "copied_targets": sorted(copied_targets),
        "copied_fields": sorted(copied_fields),
        "excluded_fields": sorted(excluded_fields),
        "copied_return_bool_count": len(policy.get("copied_return_bools", []))
        if isinstance(policy.get("copied_return_bools"), list)
        else 0,
    }


def build_descriptor_reconciliation(
    policy: dict[str, Any],
    public_gameplay_events_summary: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    local_blockers_before = len(blockers)
    preflight = policy.get("descriptor_preflight")
    preflight_summary: dict[str, Any] = {
        "policy_status": policy.get("policy_status"),
        "status": None,
        "assigned_event_kind": None,
        "assigned_event_kind_mask": None,
        "return_value_only": None,
        "public_surface": None,
        "promotion_ready": None,
        "descriptor_count": 0,
        "copied_fields": [],
        "explicitly_not_assigned": [],
    }

    if policy.get("policy_status") != "evidence-only":
        append_blocker(
            blockers,
            "descriptor_reconciliation_policy_status_drift",
            expected="evidence-only",
            value=policy.get("policy_status"),
        )

    if not isinstance(preflight, dict):
        append_blocker(blockers, "descriptor_reconciliation_preflight_missing")
    else:
        descriptors = preflight.get("descriptors")
        copied_fields = (
            sorted(
                descriptor["copied_field"]
                for descriptor in descriptors
                if isinstance(descriptor, dict) and isinstance(descriptor.get("copied_field"), str)
            )
            if isinstance(descriptors, list)
            else []
        )
        explicitly_not_assigned = preflight.get("explicitly_not_assigned")
        preflight_summary = {
            "policy_status": policy.get("policy_status"),
            "status": preflight.get("status"),
            "assigned_event_kind": preflight.get("assigned_event_kind"),
            "assigned_event_kind_mask": preflight.get("assigned_event_kind_mask"),
            "return_value_only": preflight.get("return_value_only"),
            "public_surface": preflight.get("public_surface"),
            "promotion_ready": preflight.get("promotion_ready"),
            "descriptor_count": preflight.get("descriptor_count"),
            "copied_fields": copied_fields,
            "explicitly_not_assigned": explicitly_not_assigned
            if isinstance(explicitly_not_assigned, list)
            else [],
        }
        for key, expected in {
            "status": "internal-evidence-only",
            "assigned_event_kind": None,
            "assigned_event_kind_mask": None,
            "return_value_only": True,
            "public_surface": False,
            "promotion_ready": False,
        }.items():
            if preflight.get(key) != expected:
                append_blocker(
                    blockers,
                    "descriptor_reconciliation_preflight_assignment_drift",
                    field=key,
                    expected=expected,
                    value=preflight.get(key),
                )
        required_unassigned = {
            "event_kind",
            "event_kind_mask",
            "public_metadata_json",
            "runtime_dispatcher_tables",
            "plugin_callbacks",
        }
        recorded_unassigned = set(explicitly_not_assigned) if isinstance(explicitly_not_assigned, list) else set()
        if not required_unassigned.issubset(recorded_unassigned):
            append_blocker(
                blockers,
                "descriptor_reconciliation_preflight_not_assigned_incomplete",
                missing=sorted(required_unassigned - recorded_unassigned),
            )

    item_return_descriptors = public_gameplay_events_summary.get("item_return_event_descriptors")
    if not isinstance(item_return_descriptors, list):
        item_return_descriptors = []
    inventory_policy_descriptors = public_gameplay_events_summary.get("inventory_policy_event_descriptors")
    if not isinstance(inventory_policy_descriptors, list):
        inventory_policy_descriptors = []

    for descriptor in item_return_descriptors:
        if not isinstance(descriptor, dict):
            continue
        if descriptor.get("field_mask") != [RETURN_VALUE_FIELD_MASK]:
            append_blocker(
                blockers,
                "descriptor_reconciliation_public_item_return_not_return_value_only",
                kind=descriptor.get("kind"),
                value=descriptor.get("field_mask"),
            )
    if len(item_return_descriptors) != 3:
        append_blocker(
            blockers,
            "descriptor_reconciliation_public_item_return_descriptor_count_mismatch",
            expected=3,
            value=len(item_return_descriptors),
        )
    for descriptor in inventory_policy_descriptors:
        if not isinstance(descriptor, dict):
            continue
        kind = descriptor.get("kind")
        if kind in EXPECTED_PUBLIC_INVENTORY_POLICY_FIELD_MASKS and (
            descriptor.get("field_mask") != EXPECTED_PUBLIC_INVENTORY_POLICY_FIELD_MASKS[kind]
        ):
            append_blocker(
                blockers,
                "descriptor_reconciliation_inventory_policy_field_mask_drift",
                kind=kind,
                expected=EXPECTED_PUBLIC_INVENTORY_POLICY_FIELD_MASKS[kind],
                value=descriptor.get("field_mask"),
            )

    item_return_kinds = set(public_gameplay_events_summary.get("item_return_event_kinds", []))
    inventory_policy_kinds = set(public_gameplay_events_summary.get("inventory_policy_event_kinds", []))
    if item_return_kinds & inventory_policy_kinds:
        append_blocker(
            blockers,
            "descriptor_reconciliation_dispatcher_boundary_overlap",
            overlap=sorted(item_return_kinds & inventory_policy_kinds),
        )
    item_return_field_masks = {
        str(descriptor.get("kind")): descriptor.get("field_mask")
        for descriptor in item_return_descriptors
        if isinstance(descriptor, dict)
    }
    inventory_policy_field_masks = {
        str(descriptor.get("kind")): descriptor.get("field_mask")
        for descriptor in inventory_policy_descriptors
        if isinstance(descriptor, dict)
    }
    item_return_masks_preserved = all(
        item_return_field_masks.get(kind) == [RETURN_VALUE_FIELD_MASK]
        for kind in EXPECTED_PUBLIC_ITEM_RETURN_EVENT_KINDS
    )
    inventory_policy_masks_preserved = all(
        inventory_policy_field_masks.get(kind) == expected
        for kind, expected in EXPECTED_PUBLIC_INVENTORY_POLICY_FIELD_MASKS.items()
    )

    return {
        "status": "accepted" if len(blockers) == local_blockers_before else "blocked",
        "item_return_only_preflight": preflight_summary,
        "public_gameplay_policy_item_return_descriptors": item_return_descriptors,
        "dispatcher_boundary": {
            "InventoryPolicyEventDispatcher": {
                "stable_name_prefix": "inventory.",
                "event_kinds": sorted(inventory_policy_kinds),
                "field_masks": inventory_policy_field_masks,
            },
            "ItemReturnEventDispatcher": {
                "stable_name_prefix": "inventory_item.",
                "event_kinds": sorted(item_return_kinds),
                "field_masks": item_return_field_masks,
            },
            "preserved": not bool(item_return_kinds & inventory_policy_kinds)
            and item_return_kinds == EXPECTED_PUBLIC_ITEM_RETURN_EVENT_KINDS
            and inventory_policy_kinds == EXPECTED_PUBLIC_INVENTORY_POLICY_EVENT_KINDS
            and item_return_masks_preserved
            and inventory_policy_masks_preserved,
        },
        "non_claims": [
            "reconciles descriptors only; does not promote Inventory SDK, Items SDK, ABI expansion, runtime readiness, identity, mutation, or return override",
            "offline descriptor preflight remains unassigned while public GameplayPolicyEvent descriptors remain ReturnValue-only",
        ],
    }


def build_report(
    root_arg: Path, manifest_arg: Path | None, expected_manifest_sha256: str, skip_artifact_gates: bool = False
) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    root = safe_path(root_arg, "--root", blockers)
    manifest_path = manifest_arg if manifest_arg is not None else root_arg / DEFAULT_MANIFEST_NAME
    manifest = safe_path(manifest_path, "--manifest", blockers)

    summary: dict[str, Any] = {}
    public_gameplay_events_summary: dict[str, Any] = {}
    descriptor_reconciliation: dict[str, Any] = {}
    consume_gate: dict[str, Any] = {"returncode": None, "status": None}
    promote_gate: dict[str, Any] = {"returncode": None, "status": None}
    public_events_path = safe_path(PUBLIC_GAMEPLAY_EVENTS, "docs/public_gameplay_events.json", blockers)
    if public_events_path is not None:
        public_events = read_json_object(public_events_path, blockers, label="public_gameplay_events")
        if public_events is not None:
            public_gameplay_events_summary = validate_public_gameplay_events(public_events, blockers)
    if root is not None and manifest is not None:
        policy = read_policy(manifest, blockers, expected_manifest_sha256)
        if policy is not None:
            summary = validate_policy(policy, blockers)
            descriptor_reconciliation = build_descriptor_reconciliation(policy, public_gameplay_events_summary, blockers)
        if skip_artifact_gates:
            consume_gate = {"returncode": None, "status": "skipped"}
            promote_gate = {"returncode": None, "status": "skipped", "blocker_reasons": []}
        else:
            consume_rc, consume_payload, consume_stderr = run_gate(root, manifest, "consume")
            consume_gate = {
                "returncode": consume_rc,
                "status": consume_payload.get("status") if isinstance(consume_payload, dict) else None,
                "stderr": consume_stderr,
            }
            if consume_rc != 0 or consume_gate["status"] != "accepted":
                append_blocker(blockers, "consume_gate_not_accepted", returncode=consume_rc, status=consume_gate["status"])
            promote_rc, promote_payload, promote_stderr = run_gate(root, manifest, "promote")
            promote_blockers = (
                promote_payload.get("blockers")
                if isinstance(promote_payload, dict) and isinstance(promote_payload.get("blockers"), list)
                else []
            )
            promote_reasons = sorted(
                blocker.get("reason")
                for blocker in promote_blockers
                if isinstance(blocker, dict) and isinstance(blocker.get("reason"), str)
            )
            promote_gate = {
                "returncode": promote_rc,
                "status": promote_payload.get("status") if isinstance(promote_payload, dict) else None,
                "blocker_reasons": promote_reasons,
                "stderr": promote_stderr,
            }
            required_promote_reasons = {
                "promote_mode_item_return_policy_slice_evidence_only",
                "promote_mode_manifest_has_non_claims",
            }
            if promote_rc == 0 or promote_gate["status"] != "blocked":
                append_blocker(blockers, "promote_gate_not_blocked", returncode=promote_rc, status=promote_gate["status"])
            if not required_promote_reasons.issubset(set(promote_reasons)):
                append_blocker(
                    blockers,
                    "promote_gate_missing_required_blockers",
                    missing=sorted(required_promote_reasons - set(promote_reasons)),
                )

    ready = not blockers
    return {
        "schema": REPORT_SCHEMA,
        "status": "candidate_ready" if ready else "blocked",
        "ready": ready,
        "accepted_for_internal_planning": ready,
        "not_artifact_gate": True,
        "public_inventory_sdk_ready": False,
        "public_items_sdk_ready": False,
        "runtime_ready": False,
        "promotion_ready": False,
        "root": str(root if root is not None else root_arg),
        "manifest": str(manifest if manifest is not None else manifest_path),
        "expected_manifest_sha256": expected_manifest_sha256,
        "consume_gate": consume_gate,
        "promote_gate": promote_gate,
        "summary": summary,
        "public_gameplay_events": public_gameplay_events_summary,
        "descriptor_reconciliation": descriptor_reconciliation,
        "blockers": blockers,
        "non_claims": [
            "candidate readiness is internal planning evidence only",
            "does not promote Inventory SDK, Items SDK, item identity, inventory identity, lookup, mutation, return override, ResourceHandle, runtime hooks, or public module callbacks",
            "does not replace public ABI, SDK consumer, lifecycle, privacy, second-source, or live-ops promotion gates",
        ],
    }


def main() -> int:
    args = parse_args()
    report = build_report(args.root, args.manifest, args.expected_manifest_sha256, args.skip_artifact_gates)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
