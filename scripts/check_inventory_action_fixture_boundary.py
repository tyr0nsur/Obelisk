#!/usr/bin/env python3
"""Fixture-only guardrail for inventory action redacted signatures.

This check intentionally consumes committed sanitized snapshots only. It is a narrow
mutation blocker: the inventory action artifact may stay useful as candidate planning
evidence, but it must not become a public Inventory SDK, lookup, mutation, return
override, ResourceHandle, or public action-parameter contract.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

import build_redacted_ufunction_signatures as redacted_signatures  # noqa: E402


REPORT_SCHEMA = "obelisk.inventory-action-fixture-boundary-check.v1"
TARGET_SET = "inventory-action-compact-intake"
DEFAULT_SNAPSHOT_ROOT = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"
PUBLIC_SDK_SURFACES_MANIFEST = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
EXPECTED_TARGETS = (
    "ShooterPlayerController.ServerRequestInventoryUseItem",
    "ShooterPlayerController.ServerRequestInventoryUseItemWithActor",
)
EXPECTED_SAFETY_VALUES = {
    "artifact_status": "candidate_only",
    "promotion_ready": False,
    "copied_scalar_count_total": 1,
    "redacted_count_total": 5,
    "signature_count": 2,
    "snapshot_count": 2,
}
EXPECTED_COPIED_SCALAR_BY_KIND = {"integer": 1}
EXPECTED_REDACTED_BY_REASON = {"object_ref": 3, "struct": 2}
EXPECTED_PARAM_BOUNDARY = {
    "ShooterPlayerController.ServerRequestInventoryUseItem": {
        "InventoryComp": ("redacted_uobject_ref", "ObjectProperty"),
        "ItemId": ("redacted_struct", "StructProperty"),
    },
    "ShooterPlayerController.ServerRequestInventoryUseItemWithActor": {
        "anActor": ("redacted_uobject_ref", "ObjectProperty"),
        "InventoryComp": ("redacted_uobject_ref", "ObjectProperty"),
        "ItemID1": ("redacted_struct", "StructProperty"),
        "AdditionalData": ("int32", "IntProperty"),
    },
}
PUBLIC_CONTRACT_KEYS = ("public_contract", "payload_contract")
FORBIDDEN_PUBLIC_CONTRACT_TOKENS = (
    "ItemId",
    "ItemID1",
    "AdditionalData",
    "ServerRequestInventoryUseItem",
    "ServerRequestInventoryUseItemWithActor",
    "inventory-action-compact-intake",
)
INVENTORY_COPIED_SIGNALS_SURFACE = "obelisk.inventory_item_copied_signals.v1"
INVENTORY_MUTATION_SURFACE = "obelisk.inventory_items_mutation.v1"
EXPECTED_INVENTORY_COPIED_PUBLIC_CONTRACT = [
    "GameplayPolicyEvent inventory.remote_add_check",
    "GameplayPolicyEvent inventory.use_check",
    "GameplayPolicyEvent inventory_item.allow_equip_check",
    "GameplayPolicyEvent inventory_item.can_repair_check",
    "GameplayPolicyEvent inventory_item.use_onto_item_check",
]
REQUIRED_INVENTORY_COPIED_EXCLUSIONS = (
    "Inventory SDK",
    "Items SDK",
    "item identity",
    "inventory identity",
    "lookup",
    "mutation",
    "return override",
    "ResourceHandle",
    "AdditionalData",
    "UObject pointers",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate inventory action fixture-only redacted signatures stay candidate-only."
    )
    parser.add_argument(
        "--snapshot-root",
        type=Path,
        default=DEFAULT_SNAPSHOT_ROOT,
        help="Committed sanitized UFunction snapshot root.",
    )
    parser.add_argument(
        "--public-sdk-surfaces",
        type=Path,
        default=PUBLIC_SDK_SURFACES_MANIFEST,
        help="Public SDK surfaces manifest to scan for action parameter contract leaks.",
    )
    parser.add_argument("--json", action="store_true", help="Compatibility flag; output is always JSON.")
    return parser.parse_args()


def append_blocker(blockers: list[dict[str, Any]], reason: str, **details: Any) -> None:
    blockers.append({"reason": reason, **details})


def build_fixture_report(snapshot_root: Path = DEFAULT_SNAPSHOT_ROOT) -> dict[str, Any]:
    return redacted_signatures.build_report(snapshot_root=snapshot_root, target_sets=[TARGET_SET])


def signatures_by_target(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    signatures = report.get("signatures")
    if not isinstance(signatures, list):
        return {}
    by_target: dict[str, dict[str, Any]] = {}
    for signature in signatures:
        if isinstance(signature, dict) and isinstance(signature.get("target"), str):
            by_target[signature["target"]] = signature
    return by_target


def validate_report(report: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    if report.get("schema") != redacted_signatures.OUTPUT_SCHEMA:
        append_blocker(blockers, "schema_mismatch", value=report.get("schema"))
    if report.get("snapshot_root") != "redacted":
        append_blocker(blockers, "snapshot_root_not_redacted", value=report.get("snapshot_root"))
    if report.get("target_sets") != [TARGET_SET]:
        append_blocker(blockers, "target_sets_mismatch", value=report.get("target_sets"))
    if report.get("source_target_sets") != []:
        append_blocker(blockers, "source_target_sets_not_empty", value=report.get("source_target_sets"))
    if report.get("missing_targets") != []:
        append_blocker(blockers, "missing_targets_not_empty", value=report.get("missing_targets"))
    if report.get("signature_count") != 2:
        append_blocker(blockers, "signature_count_mismatch", expected=2, value=report.get("signature_count"))

    coverage = report.get("target_set_coverage")
    if not isinstance(coverage, dict):
        append_blocker(blockers, "target_set_coverage_missing")
        coverage = {}
    if coverage.get("status") != "complete":
        append_blocker(blockers, "target_set_coverage_status_mismatch", expected="complete", value=coverage.get("status"))
    if coverage.get("complete") is not True:
        append_blocker(blockers, "target_set_coverage_not_complete", value=coverage.get("complete"))

    by_target = signatures_by_target(report)
    actual_targets = tuple(by_target)
    if actual_targets != EXPECTED_TARGETS:
        append_blocker(
            blockers,
            "target_order_mismatch",
            expected=list(EXPECTED_TARGETS),
            value=list(actual_targets),
        )

    safety = report.get("safety_summary")
    if not isinstance(safety, dict):
        append_blocker(blockers, "safety_summary_missing")
        safety = {}
    for key, expected in EXPECTED_SAFETY_VALUES.items():
        if safety.get(key) != expected:
            append_blocker(blockers, "safety_value_mismatch", field=key, expected=expected, value=safety.get(key))
    if safety.get("copied_scalar_by_kind") != EXPECTED_COPIED_SCALAR_BY_KIND:
        append_blocker(
            blockers,
            "copied_scalar_by_kind_mismatch",
            expected=EXPECTED_COPIED_SCALAR_BY_KIND,
            value=safety.get("copied_scalar_by_kind"),
        )
    if safety.get("redacted_by_reason") != EXPECTED_REDACTED_BY_REASON:
        append_blocker(
            blockers,
            "redacted_by_reason_mismatch",
            expected=EXPECTED_REDACTED_BY_REASON,
            value=safety.get("redacted_by_reason"),
        )

    copied_integer_fields: list[str] = []
    redacted_struct_fields: list[str] = []
    redacted_object_fields: list[str] = []
    for target, expected_params in EXPECTED_PARAM_BOUNDARY.items():
        signature = by_target.get(target)
        if not isinstance(signature, dict):
            append_blocker(blockers, "expected_signature_missing", target=target)
            continue
        params = signature.get("params")
        if not isinstance(params, list):
            append_blocker(blockers, "params_missing", target=target)
            continue
        params_by_name = {param.get("name"): param for param in params if isinstance(param, dict)}
        if tuple(params_by_name) != tuple(expected_params):
            append_blocker(
                blockers,
                "param_order_mismatch",
                target=target,
                expected=list(expected_params),
                value=list(params_by_name),
            )
        for name, (expected_type, expected_class) in expected_params.items():
            param = params_by_name.get(name)
            if not isinstance(param, dict):
                append_blocker(blockers, "expected_param_missing", target=target, param=name)
                continue
            if param.get("type") != expected_type:
                append_blocker(
                    blockers,
                    "param_type_mismatch",
                    target=target,
                    param=name,
                    expected=expected_type,
                    value=param.get("type"),
                )
            if param.get("source_property_class") != expected_class:
                append_blocker(
                    blockers,
                    "param_property_class_mismatch",
                    target=target,
                    param=name,
                    expected=expected_class,
                    value=param.get("source_property_class"),
                )
            if param.get("status") != "candidate":
                append_blocker(blockers, "param_status_not_candidate", target=target, param=name, value=param.get("status"))
            field = f"{target}.{name}"
            if expected_type == "int32":
                copied_integer_fields.append(field)
                if param.get("redaction") != "copied scalar candidate":
                    append_blocker(
                        blockers,
                        "copied_scalar_redaction_mismatch",
                        target=target,
                        param=name,
                        value=param.get("redaction"),
                    )
            elif expected_type == "redacted_struct":
                redacted_struct_fields.append(field)
                if param.get("redaction") != "StructProperty identity/payload redacted":
                    append_blocker(
                        blockers,
                        "redacted_struct_redaction_mismatch",
                        target=target,
                        param=name,
                        value=param.get("redaction"),
                    )
            elif expected_type == "redacted_uobject_ref":
                redacted_object_fields.append(field)
                if param.get("redaction") != "ObjectProperty identity/payload redacted":
                    append_blocker(
                        blockers,
                        "redacted_object_ref_redaction_mismatch",
                        target=target,
                        param=name,
                        value=param.get("redaction"),
                    )

    serialized = json.dumps(report, sort_keys=True)
    for forbidden in ("ItemNetID", "UPrimalInventoryComponent", "struct_type", "struct_type_candidate"):
        if forbidden in serialized:
            append_blocker(blockers, "redacted_identity_leaked", token=forbidden)

    return {
        "signature_count": report.get("signature_count"),
        "target_set_coverage_status": coverage.get("status"),
        "artifact_status": safety.get("artifact_status"),
        "promotion_ready": safety.get("promotion_ready"),
        "copied_scalar_by_kind": safety.get("copied_scalar_by_kind"),
        "redacted_by_reason": safety.get("redacted_by_reason"),
        "copied_integer_fields": copied_integer_fields,
        "redacted_struct_fields": redacted_struct_fields,
        "redacted_object_fields": redacted_object_fields,
    }


def scan_public_contract_manifest(path: Path, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        append_blocker(blockers, "public_sdk_surfaces_unreadable", path=str(path), detail=str(exc))
        return {"path": str(path), "offenders": []}
    except json.JSONDecodeError as exc:
        append_blocker(blockers, "public_sdk_surfaces_malformed", path=str(path), detail=str(exc))
        return {"path": str(path), "offenders": []}

    surfaces = manifest.get("surfaces")
    if not isinstance(surfaces, list):
        append_blocker(blockers, "public_sdk_surfaces_missing")
        return {"path": str(path), "offenders": []}

    offenders: list[dict[str, str]] = []
    surfaces_by_id = {surface.get("id"): surface for surface in surfaces if isinstance(surface, dict)}
    for surface in surfaces:
        if not isinstance(surface, dict):
            continue
        surface_id = str(surface.get("id", "<unknown>"))
        for key in PUBLIC_CONTRACT_KEYS:
            value = surface.get(key, [])
            text = json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
            for token in FORBIDDEN_PUBLIC_CONTRACT_TOKENS:
                if token in text:
                    offenders.append({"surface": surface_id, "field": key, "token": token})

    if offenders:
        append_blocker(blockers, "inventory_action_public_contract_leak", offenders=offenders)

    inventory_copied = surfaces_by_id.get(INVENTORY_COPIED_SIGNALS_SURFACE)
    inventory_mutation = surfaces_by_id.get(INVENTORY_MUTATION_SURFACE)
    surface_summary: dict[str, Any] = {}
    if not isinstance(inventory_copied, dict):
        append_blocker(blockers, "inventory_copied_signals_surface_missing")
    else:
        copied_status = inventory_copied.get("status")
        copied_contract = inventory_copied.get("public_contract")
        copied_exclusions = inventory_copied.get("exclusions")
        surface_summary[INVENTORY_COPIED_SIGNALS_SURFACE] = {
            "status": copied_status,
            "public_contract_count": len(copied_contract) if isinstance(copied_contract, list) else None,
        }
        if copied_status != "promoted-experimental-only":
            append_blocker(
                blockers,
                "inventory_copied_signals_status_mismatch",
                expected="promoted-experimental-only",
                value=copied_status,
            )
        if copied_contract != EXPECTED_INVENTORY_COPIED_PUBLIC_CONTRACT:
            append_blocker(
                blockers,
                "inventory_copied_signals_public_contract_mismatch",
                expected=EXPECTED_INVENTORY_COPIED_PUBLIC_CONTRACT,
                value=copied_contract,
            )
        if not isinstance(copied_exclusions, list):
            append_blocker(blockers, "inventory_copied_signals_exclusions_missing")
        else:
            missing_exclusions = [
                exclusion for exclusion in REQUIRED_INVENTORY_COPIED_EXCLUSIONS if exclusion not in copied_exclusions
            ]
            if missing_exclusions:
                append_blocker(
                    blockers,
                    "inventory_copied_signals_exclusions_incomplete",
                    missing=missing_exclusions,
                )

    if not isinstance(inventory_mutation, dict):
        append_blocker(blockers, "inventory_mutation_surface_missing")
    else:
        mutation_status = inventory_mutation.get("status")
        mutation_contract = inventory_mutation.get("public_contract")
        surface_summary[INVENTORY_MUTATION_SURFACE] = {
            "status": mutation_status,
            "public_contract_count": len(mutation_contract) if isinstance(mutation_contract, list) else None,
        }
        if mutation_status != "post-v1":
            append_blocker(
                blockers,
                "inventory_mutation_status_mismatch",
                expected="post-v1",
                value=mutation_status,
            )
        if mutation_contract != []:
            append_blocker(
                blockers,
                "inventory_mutation_public_contract_present",
                value=mutation_contract,
            )

    return {"path": str(path), "offenders": offenders, "surface_summary": surface_summary}


def build_check(snapshot_root: Path, public_sdk_surfaces: Path) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    try:
        source_report = build_fixture_report(snapshot_root)
    except Exception as exc:  # pragma: no cover - defensive CLI reporting
        append_blocker(blockers, "fixture_report_build_failed", detail=str(exc))
        source_report = {}

    summary = validate_report(source_report, blockers) if source_report else {}
    public_contract_scan = scan_public_contract_manifest(public_sdk_surfaces, blockers)
    ready = not blockers
    return {
        "schema": REPORT_SCHEMA,
        "status": "accepted_fixture_boundary" if ready else "blocked",
        "ready": ready,
        "fixture_only": True,
        "snapshot_root": str(snapshot_root),
        "target_set": TARGET_SET,
        "public_inventory_sdk_ready": False,
        "inventory_action_sdk_ready": False,
        "lookup_ready": False,
        "mutation_ready": False,
        "resource_handle_ready": False,
        "return_override_ready": False,
        "runtime_ready": False,
        "promotion_ready": False,
        "summary": summary,
        "public_contract_scan": public_contract_scan,
        "blockers": blockers,
        "non_claims": [
            "fixture-only redacted signature boundary; no core, runtime, or server path evidence",
            "does not promote Inventory SDK, mutation, lookup, ResourceHandle, or return override",
            "ItemId, ItemID1, and AdditionalData do not cross public_contract or payload_contract",
        ],
    }


def main() -> int:
    args = parse_args()
    report = build_check(args.snapshot_root, args.public_sdk_surfaces)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
