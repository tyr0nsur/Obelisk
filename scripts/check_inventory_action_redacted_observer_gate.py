#!/usr/bin/env python3
"""Candidate-only offline gate for inventory-action redacted observer readiness.

This checker is intentionally not a runtime implementation. It consumes the committed
inventory-action redacted fixture boundary and sanitized UFunction snapshots, then checks
the fail-closed preconditions a future observer must satisfy before any server-backed
work is proposed.
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

import check_inventory_action_fixture_boundary as fixture_boundary  # noqa: E402


REPORT_SCHEMA = "obelisk.inventory-action-redacted-observer-gate-check.v1"
TARGET_SET = fixture_boundary.TARGET_SET
EXPECTED_TARGETS = fixture_boundary.EXPECTED_TARGETS
EXPECTED_COPIED_INTEGER_FIELDS = (
    "ShooterPlayerController.ServerRequestInventoryUseItemWithActor.AdditionalData",
)
EXPECTED_REDACTED_STRUCT_FIELDS = (
    "ShooterPlayerController.ServerRequestInventoryUseItem.ItemId",
    "ShooterPlayerController.ServerRequestInventoryUseItemWithActor.ItemID1",
)
EXPECTED_REDACTED_OBJECT_FIELDS = (
    "ShooterPlayerController.ServerRequestInventoryUseItem.InventoryComp",
    "ShooterPlayerController.ServerRequestInventoryUseItemWithActor.anActor",
    "ShooterPlayerController.ServerRequestInventoryUseItemWithActor.InventoryComp",
)
DECISION_MANIFEST = REPO_ROOT / "docs" / "inventory_item_copied_signals_public_contract_decisions.json"
DECISION_MANIFEST_SCHEMA = "obelisk.inventory-item-copied-signals-public-contract-decisions.v1"
EXPECTED_DECISION_SURFACE = "obelisk.inventory_item_copied_signals.v1"
EXPECTED_DECISION_STATUS = "promoted-experimental-only"
EXPECTED_PUBLIC_CONTRACT: dict[str, Any] = {
    "event_family": "GameplayPolicyEvent",
    "capability": "OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS",
    "descriptor_capability": "OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS",
    "registration": "RegisterGameplayPolicyEventWithOwnerTokenHandle",
    "unregister": "UnregisterGameplayPolicyEventWithOwnerToken",
    "resource_kind": "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM",
    "resource_contract": "category-only metadata; no identity, lookup, handle, persistence, or cross-event correlation",
    "payload_contract": "copied POD scalar observation only",
    "public_fields": [
        "abi_version",
        "struct_size",
        "event_kind",
        "resource_kind",
        "flags",
        "field_mask",
        "bool_values",
        "int32_values",
    ],
    "required_flags": [
        "OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD",
        "OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED",
    ],
}
REQUIRED_BLOCKED_CONTRACT_FLAGS = {
    "standalone_inventory_sdk_allowed": False,
    "standalone_items_sdk_allowed": False,
}
REQUIRED_BLOCKED_CONTRACT_TERMS = (
    "Inventory SDK",
    "Items SDK",
    "item identity",
    "inventory identity",
    "ItemNetID identity",
    "lookup",
    "mutation",
    "return override",
    "ResourceHandle",
    "CraftBlueprint",
    "AdditionalData",
    "ItemId",
    "ItemID1",
    "InventoryComp",
    "anActor",
    "action params",
    "raw params",
    "UObject pointers",
    "UFunction pointers",
    "FName/GObjects indices",
)
FORBIDDEN_DECISION_PUBLIC_CONTRACT_TOKENS = (
    "Inventory SDK",
    "Items SDK",
    "item identity",
    "inventory identity",
    "ItemNetID",
    "lookup",
    "mutation",
    "return override",
    "ResourceHandle",
    "CraftBlueprint",
    "AdditionalData",
    "ServerRequestInventoryUseItem",
    "ServerRequestInventoryUseItemWithActor",
    "ItemId",
    "ItemID1",
    "InventoryComp",
    "anActor",
    "action params",
    "raw params",
    "UObject",
    "UFunction",
    "FName/GObjects",
)
REQUIRED_PROMOTION_BLOCKERS: dict[str, dict[str, Any]] = {
    "copied_signal_stability_wording": {
        "status": "blocked",
        "required_tokens": (
            "Inventory SDK",
            "Items SDK",
            "item identity",
            "inventory identity",
            "lookup",
            "mutation",
            "return override",
            "ResourceHandle",
        ),
    },
    "inventory_items_mutation_surface": {
        "status": "blocked",
        "required_tokens": (
            "identity semantics",
            "copied signal sequence",
            "append-only POD C ABI",
            "owner-scoped cleanup",
            "rollback",
            "resource_kind as identity",
            "lookup",
            "mutation",
            "return override",
            "ResourceHandle",
        ),
    },
    "inventory_action_redacted_observer": {
        "status": "candidate-only-blocked",
        "required_tokens": (
            "dispatch budget exactly 0",
            "no-read/no-budget",
            "copied output cleared",
            "public callbacks",
            "raw params",
            "AdditionalData stable semantics",
            "ItemId or ItemID1 identity",
            "InventoryComp or anActor identity",
        ),
    },
    "resource_handle_identity": {
        "status": "blocked",
        "required_tokens": (
            "runtime object rejection samples",
            "serial reuse",
            "UObject flag",
            "ResourceHandle",
            "object lookup",
            "persistent handles",
            "cross-event correlation",
        ),
    },
}
EXPECTED_ALLOWED_SIGNALS: tuple[dict[str, Any], ...] = (
    {
        "stable_name": "inventory.remote_add_check",
        "kind": "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK",
        "event_kind_mask": "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_REMOTE_ADD_CHECK",
        "field_mask": [
            "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE",
            "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER",
        ],
    },
    {
        "stable_name": "inventory.use_check",
        "kind": "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK",
        "event_kind_mask": "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_CHECK",
        "field_mask": [
            "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE",
            "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN",
        ],
    },
    {
        "stable_name": "inventory_item.allow_equip_check",
        "kind": "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_ALLOW_EQUIP_ITEM_CHECK",
        "event_kind_mask": "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_ALLOW_EQUIP_ITEM_CHECK",
        "field_mask": [
            "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE",
        ],
    },
    {
        "stable_name": "inventory_item.can_repair_check",
        "kind": "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_CAN_REPAIR_CHECK",
        "event_kind_mask": "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_CAN_REPAIR_CHECK",
        "field_mask": [
            "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE",
        ],
    },
    {
        "stable_name": "inventory_item.use_onto_item_check",
        "kind": "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK",
        "event_kind_mask": "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK",
        "field_mask": [
            "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE",
        ],
    },
)
SUPPORTED_SNAPSHOT_SCHEMA = "obelisk.ufunction-chain.snapshot.v1"
REQUIRED_PROFILE = "observer-debug"
MAX_OBSERVATION_BUDGET = 10
REQUIRED_MARKERS = (
    "allow-observer-debug-window",
    "allow-experimental-observers",
    "enable-inventory-action-redacted-observer",
    "enable-process-event-hook",
    "disable-plugins",
)
FALSE_PUBLIC_RUNTIME_FLAGS = (
    "public_inventory_sdk_ready",
    "inventory_action_sdk_ready",
    "lookup_ready",
    "mutation_ready",
    "resource_handle_ready",
    "return_override_ready",
    "runtime_ready",
    "promotion_ready",
)
PUBLIC_CONTRACT_LEAK_REASONS = {"inventory_action_public_contract_leak"}


def parse_int(value: str) -> int:
    try:
        return int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer: {value}") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Offline candidate-only preflight for a future inventory-action redacted observer."
    )
    parser.add_argument("--snapshot-root", type=Path, default=fixture_boundary.DEFAULT_SNAPSHOT_ROOT)
    parser.add_argument("--public-sdk-surfaces", type=Path, default=fixture_boundary.PUBLIC_SDK_SURFACES_MANIFEST)
    parser.add_argument("--public-gameplay-events", type=Path, default=fixture_boundary.PUBLIC_GAMEPLAY_EVENTS_MANIFEST)
    parser.add_argument("--decision-manifest", type=Path, default=DECISION_MANIFEST)
    parser.add_argument(
        "--gate-enabled",
        action="store_true",
        help="Model the future observer gate as explicitly enabled for this offline check.",
    )
    parser.add_argument(
        "--observer-profile",
        default="stable",
        help="Modeled wrapper profile. Must be observer-debug for a candidate observer window.",
    )
    parser.add_argument(
        "--marker",
        action="append",
        default=[],
        help="Model a present same-instance marker. Repeat for each marker.",
    )
    parser.add_argument(
        "--ark-binary-sha256",
        help="Modeled ARK binary SHA256. Must match the committed supported snapshot SHA.",
    )
    parser.add_argument(
        "--fname-index",
        type=parse_int,
        help="Modeled ProcessEvent FName ComparisonIndex for the cheap exact prefilter.",
    )
    parser.add_argument(
        "--dispatch-budget",
        type=int,
        help="Modeled dispatch budget. Must be explicitly 0 for this redacted observer.",
    )
    parser.add_argument(
        "--observation-budget",
        type=int,
        help=(
            "Modeled log/observation budget. Must be between 1 and "
            f"{MAX_OBSERVATION_BUDGET}, and reserved only after cheap gates pass."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Compatibility flag; output is always JSON.")
    return parser.parse_args()


def append_blocker(blockers: list[dict[str, Any]], reason: str, **details: Any) -> None:
    blockers.append({"reason": reason, **details})


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def snapshot_paths_for_targets(snapshot_root: Path, blockers: list[dict[str, Any]]) -> dict[str, Path]:
    manifest = load_json(snapshot_root / "manifest.json")
    if manifest is None:
        append_blocker(blockers, "snapshot_manifest_unreadable", path=str(snapshot_root / "manifest.json"))
        return {}
    sha_prefix = manifest.get("sha_prefix")
    entries = manifest.get("targets")
    if not isinstance(sha_prefix, str) or not sha_prefix:
        append_blocker(blockers, "snapshot_manifest_sha_prefix_missing")
        return {}
    if not isinstance(entries, list):
        append_blocker(blockers, "snapshot_manifest_targets_missing")
        return {}

    expected = set(EXPECTED_TARGETS)
    paths: dict[str, Path] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        outer = entry.get("outer")
        name = entry.get("name")
        module = entry.get("module")
        filename = entry.get("file")
        target = f"{outer}.{name}" if isinstance(outer, str) and isinstance(name, str) else None
        if target not in expected:
            continue
        if not all(isinstance(value, str) and value for value in (module, filename)):
            append_blocker(blockers, "snapshot_manifest_target_entry_malformed", target=target)
            continue
        paths[target] = snapshot_root / sha_prefix / module / filename

    missing = sorted(expected - set(paths))
    if missing:
        append_blocker(blockers, "target_snapshot_missing", missing=missing)
    return paths


def read_supported_snapshot_identity(snapshot_root: Path, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    paths = snapshot_paths_for_targets(snapshot_root, blockers)
    supported_shas: set[str] = set()
    fname_indices: dict[str, int] = {}
    snapshot_targets: list[str] = []

    for expected_target in EXPECTED_TARGETS:
        path = paths.get(expected_target)
        if path is None:
            continue
        payload = load_json(path)
        if payload is None:
            append_blocker(blockers, "target_snapshot_unreadable", target=expected_target, path=str(path))
            continue
        if payload.get("schema") != SUPPORTED_SNAPSHOT_SCHEMA:
            append_blocker(
                blockers,
                "target_snapshot_schema_mismatch",
                target=expected_target,
                expected=SUPPORTED_SNAPSHOT_SCHEMA,
                value=payload.get("schema"),
            )
        evidence = payload.get("evidence")
        if isinstance(evidence, dict) and isinstance(evidence.get("ark_binary_sha256"), str):
            supported_shas.add(evidence["ark_binary_sha256"])
        else:
            append_blocker(blockers, "target_snapshot_sha_missing", target=expected_target)

        targets = payload.get("targets")
        if not isinstance(targets, list) or len(targets) != 1 or not isinstance(targets[0], dict):
            append_blocker(blockers, "target_snapshot_target_shape_mismatch", target=expected_target)
            continue
        target_info = targets[0].get("target")
        if not isinstance(target_info, dict):
            append_blocker(blockers, "target_snapshot_function_identity_missing", target=expected_target)
            continue
        outer = target_info.get("outer_name")
        name = target_info.get("name")
        actual_target = f"{outer}.{name}" if isinstance(outer, str) and isinstance(name, str) else None
        snapshot_targets.append(str(actual_target))
        if actual_target != expected_target:
            append_blocker(
                blockers,
                "target_snapshot_identity_mismatch",
                expected=expected_target,
                value=actual_target,
            )
        fname_index = target_info.get("name_index")
        if not isinstance(fname_index, int):
            append_blocker(blockers, "target_fname_index_missing", target=expected_target)
        else:
            fname_indices[expected_target] = fname_index

    if tuple(snapshot_targets) != EXPECTED_TARGETS:
        append_blocker(
            blockers,
            "target_snapshot_order_mismatch",
            expected=list(EXPECTED_TARGETS),
            value=snapshot_targets,
        )
    if len(supported_shas) != 1:
        append_blocker(blockers, "supported_sha_unavailable", value=sorted(supported_shas))
    if set(fname_indices) != set(EXPECTED_TARGETS):
        append_blocker(
            blockers,
            "target_fname_indices_incomplete",
            missing=sorted(set(EXPECTED_TARGETS) - set(fname_indices)),
        )

    return {
        "supported_ark_binary_sha256": sorted(supported_shas),
        "target_fname_indices": fname_indices,
    }


def validate_fixture_boundary_report(report: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    boundary_reasons = [blocker.get("reason") for blocker in report.get("blockers", []) if isinstance(blocker, dict)]
    if not report.get("ready"):
        append_blocker(blockers, "fixture_boundary_failed", reasons=boundary_reasons)
    if any(reason in PUBLIC_CONTRACT_LEAK_REASONS for reason in boundary_reasons):
        append_blocker(blockers, "public_contract_leak", source_reasons=boundary_reasons)
    if report.get("target_set") != TARGET_SET:
        append_blocker(blockers, "target_set_mismatch", expected=TARGET_SET, value=report.get("target_set"))
    if report.get("fixture_only") is not True:
        append_blocker(blockers, "fixture_only_flag_missing", value=report.get("fixture_only"))

    summary = report.get("summary")
    if not isinstance(summary, dict):
        append_blocker(blockers, "fixture_summary_missing")
        return {}
    if summary.get("signature_count") != 2:
        append_blocker(blockers, "signature_count_mismatch", expected=2, value=summary.get("signature_count"))
    if summary.get("target_set_coverage_status") != "complete":
        append_blocker(
            blockers,
            "coverage_incomplete",
            expected="complete",
            value=summary.get("target_set_coverage_status"),
        )
    if summary.get("artifact_status") != "candidate_only":
        append_blocker(blockers, "artifact_status_mismatch", expected="candidate_only", value=summary.get("artifact_status"))
    if summary.get("promotion_ready") is not False:
        append_blocker(blockers, "fixture_promotion_ready_not_false", value=summary.get("promotion_ready"))
    if summary.get("copied_integer_fields") != list(EXPECTED_COPIED_INTEGER_FIELDS):
        append_blocker(
            blockers,
            "scalar_contract_mismatch",
            expected=list(EXPECTED_COPIED_INTEGER_FIELDS),
            value=summary.get("copied_integer_fields"),
        )
    if summary.get("redacted_struct_fields") != list(EXPECTED_REDACTED_STRUCT_FIELDS):
        append_blocker(
            blockers,
            "redaction_contract_mismatch",
            field="struct",
            expected=list(EXPECTED_REDACTED_STRUCT_FIELDS),
            value=summary.get("redacted_struct_fields"),
        )
    if summary.get("redacted_object_fields") != list(EXPECTED_REDACTED_OBJECT_FIELDS):
        append_blocker(
            blockers,
            "redaction_contract_mismatch",
            field="object_ref",
            expected=list(EXPECTED_REDACTED_OBJECT_FIELDS),
            value=summary.get("redacted_object_fields"),
        )
    for flag in FALSE_PUBLIC_RUNTIME_FLAGS:
        if report.get(flag) is not False:
            append_blocker(blockers, "public_or_runtime_flag_promoted", flag=flag, value=report.get(flag))
    return summary


def validate_decision_manifest(
    path: Path,
    blockers: list[dict[str, Any]],
    public_gameplay_events: Path = fixture_boundary.PUBLIC_GAMEPLAY_EVENTS_MANIFEST,
) -> dict[str, Any]:
    manifest = load_json(path)
    if manifest is None:
        append_blocker(blockers, "decision_manifest_unreadable", path=str(path))
        return {"path": str(path), "promotion_blockers": []}
    derived_signals = fixture_boundary.derive_inventory_copied_signals(public_gameplay_events, blockers)
    if manifest.get("schema") != DECISION_MANIFEST_SCHEMA:
        append_blocker(
            blockers,
            "decision_manifest_schema_mismatch",
            expected=DECISION_MANIFEST_SCHEMA,
            value=manifest.get("schema"),
        )
    if manifest.get("surface") != EXPECTED_DECISION_SURFACE:
        append_blocker(
            blockers,
            "decision_manifest_surface_mismatch",
            expected=EXPECTED_DECISION_SURFACE,
            value=manifest.get("surface"),
        )
    if manifest.get("status") != EXPECTED_DECISION_STATUS:
        append_blocker(
            blockers,
            "decision_manifest_status_mismatch",
            expected=EXPECTED_DECISION_STATUS,
            value=manifest.get("status"),
        )
    if manifest.get("decision") != "copied_signal_only":
        append_blocker(blockers, "decision_manifest_decision_mismatch", value=manifest.get("decision"))
    source_of_truth = manifest.get("source_of_truth")
    if not isinstance(source_of_truth, dict):
        append_blocker(blockers, "decision_manifest_source_of_truth_missing")
    elif source_of_truth.get("public_gameplay_events_manifest") != "docs/public_gameplay_events.json":
        append_blocker(
            blockers,
            "decision_manifest_source_of_truth_public_gameplay_events_mismatch",
            expected="docs/public_gameplay_events.json",
            value=source_of_truth.get("public_gameplay_events_manifest"),
        )

    public_contract = manifest.get("public_contract")
    if public_contract != EXPECTED_PUBLIC_CONTRACT:
        append_blocker(
            blockers,
            "decision_manifest_public_contract_mismatch",
            expected=EXPECTED_PUBLIC_CONTRACT,
            value=public_contract,
        )
    public_contract_scan = {}
    if isinstance(public_contract, dict):
        public_contract_scan = {
            "public_fields": public_contract.get("public_fields"),
            "required_flags": public_contract.get("required_flags"),
        }
    public_contract_text = json.dumps(public_contract_scan, sort_keys=True)
    leaked_public_tokens = [
        token for token in FORBIDDEN_DECISION_PUBLIC_CONTRACT_TOKENS if token in public_contract_text
    ]
    if leaked_public_tokens:
        append_blocker(
            blockers,
            "decision_manifest_public_contract_forbidden_terms",
            tokens=leaked_public_tokens,
        )

    allowed_signals = manifest.get("allowed_signals")
    if not isinstance(allowed_signals, list):
        append_blocker(blockers, "decision_manifest_allowed_signals_missing")
    elif allowed_signals != derived_signals:
        append_blocker(
            blockers,
            "decision_manifest_allowed_signals_mismatch",
            expected=derived_signals,
            value=allowed_signals,
        )

    blocked_contract = manifest.get("blocked_public_contract")
    if not isinstance(blocked_contract, dict):
        append_blocker(blockers, "decision_manifest_blocked_public_contract_missing")
        blocked_contract = {}
    for flag, expected in REQUIRED_BLOCKED_CONTRACT_FLAGS.items():
        if blocked_contract.get(flag) is not expected:
            append_blocker(
                blockers,
                "decision_manifest_blocked_contract_flag_mismatch",
                flag=flag,
                expected=expected,
                value=blocked_contract.get(flag),
            )
    forbidden_terms = blocked_contract.get("forbidden_terms")
    if not isinstance(forbidden_terms, list) or not all(isinstance(item, str) for item in forbidden_terms):
        append_blocker(blockers, "decision_manifest_blocked_contract_forbidden_terms_missing")
    else:
        missing_forbidden_terms = [term for term in REQUIRED_BLOCKED_CONTRACT_TERMS if term not in forbidden_terms]
        if missing_forbidden_terms:
            append_blocker(
                blockers,
                "decision_manifest_blocked_contract_forbidden_terms_incomplete",
                missing=missing_forbidden_terms,
            )
    mutation_surface = (
        blocked_contract.get("inventory_mutation_surface") if isinstance(blocked_contract, dict) else None
    )
    if not isinstance(mutation_surface, dict):
        append_blocker(blockers, "decision_manifest_mutation_surface_missing")
    else:
        if mutation_surface.get("id") != "obelisk.inventory_items_mutation.v1":
            append_blocker(
                blockers,
                "decision_manifest_mutation_surface_id_mismatch",
                value=mutation_surface.get("id"),
            )
        if mutation_surface.get("public_contract") != []:
            append_blocker(
                blockers,
                "decision_manifest_mutation_public_contract_present",
                value=mutation_surface.get("public_contract"),
            )

    promotion_blockers = manifest.get("next_promotion_blockers")
    if not isinstance(promotion_blockers, list):
        append_blocker(blockers, "decision_manifest_promotion_blockers_missing")
        return {"path": str(path), "promotion_blockers": []}

    blockers_by_id = {
        blocker.get("id"): blocker
        for blocker in promotion_blockers
        if isinstance(blocker, dict) and isinstance(blocker.get("id"), str)
    }
    expected_ids = tuple(REQUIRED_PROMOTION_BLOCKERS)
    actual_ids = tuple(blocker.get("id") for blocker in promotion_blockers if isinstance(blocker, dict))
    if actual_ids != expected_ids:
        append_blocker(
            blockers,
            "decision_manifest_promotion_blocker_order_mismatch",
            expected=list(expected_ids),
            value=list(actual_ids),
        )

    summary: list[dict[str, Any]] = []
    for blocker_id, required in REQUIRED_PROMOTION_BLOCKERS.items():
        entry = blockers_by_id.get(blocker_id)
        if not isinstance(entry, dict):
            append_blocker(blockers, "decision_manifest_promotion_blocker_missing", id=blocker_id)
            continue
        status = entry.get("status")
        if status != required["status"]:
            append_blocker(
                blockers,
                "decision_manifest_promotion_blocker_status_mismatch",
                id=blocker_id,
                expected=required["status"],
                value=status,
            )
        requires = entry.get("requires")
        must_not_unlock = entry.get("must_not_unlock")
        if not isinstance(requires, list) or not all(isinstance(item, str) for item in requires):
            append_blocker(blockers, "decision_manifest_promotion_blocker_requires_missing", id=blocker_id)
            requires = []
        if not isinstance(must_not_unlock, list) or not all(isinstance(item, str) for item in must_not_unlock):
            append_blocker(blockers, "decision_manifest_promotion_blocker_must_not_unlock_missing", id=blocker_id)
            must_not_unlock = []
        blocker_text = "\n".join([str(entry.get("current_state", "")), *requires, *must_not_unlock])
        missing_tokens = [token for token in required["required_tokens"] if token not in blocker_text]
        if missing_tokens:
            append_blocker(
                blockers,
                "decision_manifest_promotion_blocker_terms_incomplete",
                id=blocker_id,
                missing=missing_tokens,
            )
        summary.append(
            {
                "id": blocker_id,
                "status": status,
                "requires_count": len(requires),
                "must_not_unlock_count": len(must_not_unlock),
            }
        )

    return {"path": str(path), "promotion_blockers": summary}


def validate_gate_inputs(
    *,
    gate_enabled: bool,
    observer_profile: str,
    markers: list[str],
    ark_binary_sha256: str | None,
    fname_index: int | None,
    dispatch_budget: int | None,
    observation_budget: int | None,
    snapshot_identity: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    marker_set = set(markers)
    missing_markers = [marker for marker in REQUIRED_MARKERS if marker not in marker_set]
    supported_shas = snapshot_identity.get("supported_ark_binary_sha256", [])
    fname_indices_by_target = snapshot_identity.get("target_fname_indices", {})
    allowed_fname_indices = sorted(fname_indices_by_target.values()) if isinstance(fname_indices_by_target, dict) else []
    target_by_fname_index = (
        {str(value): target for target, value in sorted(fname_indices_by_target.items())}
        if isinstance(fname_indices_by_target, dict)
        else {}
    )
    selected_target = target_by_fname_index.get(str(fname_index)) if fname_index is not None else None

    if not gate_enabled:
        append_blocker(blockers, "disabled_gate")
    if observer_profile != REQUIRED_PROFILE:
        append_blocker(blockers, "invalid_profile", expected=REQUIRED_PROFILE, value=observer_profile)
    for marker in missing_markers:
        append_blocker(blockers, "missing_marker", marker=marker)
    if ark_binary_sha256 is None:
        append_blocker(blockers, "missing_supported_sha")
    elif ark_binary_sha256 not in supported_shas:
        append_blocker(blockers, "unsupported_sha", value=ark_binary_sha256, supported=supported_shas)
    if fname_index is None:
        append_blocker(blockers, "missing_fname_index")
    elif fname_index not in allowed_fname_indices:
        append_blocker(blockers, "non_target_fname", value=fname_index, allowed=allowed_fname_indices)
    if dispatch_budget is None:
        append_blocker(blockers, "missing_dispatch_budget")
    elif dispatch_budget != 0:
        append_blocker(blockers, "dispatch_budget_not_zero", expected=0, value=dispatch_budget)
    if observation_budget is None:
        append_blocker(blockers, "missing_observation_budget")
    elif observation_budget <= 0:
        append_blocker(blockers, "observation_budget_not_positive", minimum=1, value=observation_budget)
    elif observation_budget > MAX_OBSERVATION_BUDGET:
        append_blocker(
            blockers,
            "observation_budget_exceeds_maximum",
            maximum=MAX_OBSERVATION_BUDGET,
            value=observation_budget,
        )

    cheap_gate_passed = (
        gate_enabled
        and observer_profile == REQUIRED_PROFILE
        and not missing_markers
        and ark_binary_sha256 is not None
        and ark_binary_sha256 in supported_shas
        and fname_index is not None
        and fname_index in allowed_fname_indices
    )
    observation_budget_reservation_allowed = (
        cheap_gate_passed
        and observation_budget is not None
        and observation_budget > 0
        and observation_budget <= MAX_OBSERVATION_BUDGET
        and dispatch_budget == 0
        and not blockers
    )

    return {
        "gate_enabled": gate_enabled,
        "observer_profile": observer_profile,
        "required_markers": list(REQUIRED_MARKERS),
        "present_markers": sorted(marker_set),
        "missing_markers": missing_markers,
        "ark_binary_sha256": ark_binary_sha256,
        "supported_ark_binary_sha256": supported_shas,
        "fname_index": fname_index,
        "allowed_fname_indices": allowed_fname_indices,
        "target_by_fname_index": target_by_fname_index,
        "selected_target": selected_target,
        "dispatch_budget": dispatch_budget,
        "observation_budget": observation_budget,
        "cheap_gate_passed": cheap_gate_passed,
        "observation_budget_reservation_allowed": observation_budget_reservation_allowed,
        "runtime_param_read_before_cheap_gate_allowed": False,
        "dispatch_budget_reservation_allowed": False,
    }


def build_check(
    *,
    snapshot_root: Path = fixture_boundary.DEFAULT_SNAPSHOT_ROOT,
    public_sdk_surfaces: Path = fixture_boundary.PUBLIC_SDK_SURFACES_MANIFEST,
    decision_manifest: Path = DECISION_MANIFEST,
    public_gameplay_events: Path = fixture_boundary.PUBLIC_GAMEPLAY_EVENTS_MANIFEST,
    gate_enabled: bool = False,
    observer_profile: str = "stable",
    markers: list[str] | None = None,
    ark_binary_sha256: str | None = None,
    fname_index: int | None = None,
    dispatch_budget: int | None = None,
    observation_budget: int | None = None,
    fixture_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    snapshot_identity = read_supported_snapshot_identity(snapshot_root, blockers)
    if fixture_report is None:
        fixture_report = fixture_boundary.build_check(snapshot_root, public_sdk_surfaces, public_gameplay_events)
    fixture_summary = validate_fixture_boundary_report(fixture_report, blockers)
    decision_manifest_summary = validate_decision_manifest(decision_manifest, blockers, public_gameplay_events)
    gate = validate_gate_inputs(
        gate_enabled=gate_enabled,
        observer_profile=observer_profile,
        markers=markers or [],
        ark_binary_sha256=ark_binary_sha256,
        fname_index=fname_index,
        dispatch_budget=dispatch_budget,
        observation_budget=observation_budget,
        snapshot_identity=snapshot_identity,
        blockers=blockers,
    )
    ready = not blockers
    return {
        "schema": REPORT_SCHEMA,
        "status": "accepted_candidate_offline_gate" if ready else "blocked",
        "ready": ready,
        "candidate_only": True,
        "fixture_only": True,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "public_inventory_sdk_ready": False,
        "inventory_action_sdk_ready": False,
        "promotion_ready": False,
        "dispatch_ready": False,
        "target_set": TARGET_SET,
        "expected_targets": list(EXPECTED_TARGETS),
        "snapshot_root": str(snapshot_root),
        "gate": gate,
        "fixture_summary": fixture_summary,
        "decision_manifest": decision_manifest_summary,
        "public_contract_scan": fixture_report.get("public_contract_scan", {}),
        "blockers": blockers,
        "non_claims": [
            "offline preflight only; does not read runtime metadata, params, cores, or server files",
            "candidate redacted observer planning only; no runtime observer is implemented or approved",
            "no public Inventory SDK, Items SDK, mutation, lookup, ResourceHandle, return override, or public ABI",
            "AdditionalData remains a copied int32 candidate only with no stable semantic claim",
        ],
    }


def main() -> int:
    args = parse_args()
    report = build_check(
        snapshot_root=args.snapshot_root,
        public_sdk_surfaces=args.public_sdk_surfaces,
        public_gameplay_events=args.public_gameplay_events,
        decision_manifest=args.decision_manifest,
        gate_enabled=args.gate_enabled,
        observer_profile=args.observer_profile,
        markers=args.marker,
        ark_binary_sha256=args.ark_binary_sha256,
        fname_index=args.fname_index,
        dispatch_budget=args.dispatch_budget,
        observation_budget=args.observation_budget,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
