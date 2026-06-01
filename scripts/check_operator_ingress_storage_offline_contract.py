#!/usr/bin/env python3
"""Offline guardrail for obelisk.operator_ingress_storage.v1."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from collections.abc import Iterable
from typing import Any

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "docs" / "operator_ingress_storage_public_contract_decisions.json"
CONTRACT_ID = "obelisk.operator_ingress_storage.v1"
SCHEMA = "obelisk.operator-ingress-storage-offline-contract.v1"
FALSE_ONLY_TOP_LEVEL_KEYS = (
    "public_header_allowed",
    "public_sdk_ready",
    "public_abi_ready",
    "promotion_ready",
    "runtime_ready",
    "runtime_services",
)

REQUIRED_LANE_CHECKS = {
    "ingress": {
        "offline_only",
        "operator_owned_inputs",
        "no_runtime_entrypoint",
    },
    "storage_migration": {
        "schema_versioned",
        "dry_run_required",
        "rollback_note_required",
    },
    "queue_lifecycle": {
        "enqueue_dequeue_ack_nack_decisioned",
        "dead_letter_policy_decisioned",
        "retry_policy_decisioned",
    },
    "text_audit": {
        "text_payload_redaction_decisioned",
        "audit_record_retention_decisioned",
        "operator_visibility_boundary_decisioned",
    },
    "multi_instance_lifecycle": {
        "instance_scoped_state",
        "start_stop_restart_boundaries_decisioned",
        "cross_instance_isolation_decisioned",
    },
}

REQUIRED_LANE_FIELDS = {
    "ingress": {
        "candidate_ingress_transport",
        "trust_boundary",
        "authorization_source",
        "rate_limit",
        "backpressure_rule",
        "rejected_secret_classes",
        "fail_closed_mode",
    },
    "storage_migration": {
        "schema_version_field",
        "migration_order",
        "rollback_posture",
        "retention_policy",
        "corruption_handling",
        "per_instance_isolation",
    },
    "queue_lifecycle": {
        "enqueue_durability",
        "retry_policy",
        "poison_message_handling",
        "shutdown_drain",
        "plugin_unload_drain",
        "restart_recovery",
        "maximum_drain_deadline",
    },
    "text_audit": {
        "utf8_validation",
        "normalization_policy",
        "maximum_byte_length",
        "rejection_behavior",
        "log_audit_escaping",
        "stable_audit_event_names",
        "redacted_payload_rules",
    },
    "multi_instance_lifecycle": {
        "shared_root_locking",
        "duplicate_ingestion",
        "replay_protection",
        "crash_behavior",
        "init_failure_cleanup",
        "dlclose_safety",
        "owner_scoped_worker_callback_teardown",
    },
}

ALLOWED_REJECTION_CLASSIFICATION_FIELD = "rejected_secret_classes"
ALLOWED_NEGATIVE_FIELD_NAMES = frozenset(("no_runtime_entrypoint",))
CLAIM_KEY_EXEMPTIONS = frozenset(
    (
        "public_abi_ready",
        "runtime",
        "runtime_ready",
        "runtime_required",
        "runtime_services",
    )
)

PROHIBITED_CLAIM_RE = re.compile(
    r"secret[-_ ]?manager|secret(s)?|rcon|webhook|database|"
    r"(?<![A-Za-z0-9])db(?:[-_ ]?(?:service|storage|backend|migration|persistence|connector|adapter))?(?![A-Za-z0-9])|"
    r"(?<![A-Za-z0-9])storage[-_ ]?(?:service|api|runtime|implementation|backend|provider|connector|adapter)(?![A-Za-z0-9])|"
    r"(?<![A-Za-z0-9])cross[-_ ]?instance[-_ ]?(?:persistence|persistent[-_ ]?storage|"
    r"storage[-_ ]?(?:api|service|persistence)|state[-_ ]?persistence|db|database)(?![A-Za-z0-9])|"
    r"\bapi\b|"
    r"\bruntime(?:[-_ ]?(?:ready|readiness|services?|validated|validation|entrypoint|"
    r"code|hook|wiring|implementation))?\b|public[_ -]?(?:c[_ -]?)?abi|"
    r"v1(?:[_ -]?sdk)?[_ -]?completion(?:[_ -]?required)?",
    re.IGNORECASE,
)
REQUIRED_FIELDS_PATH_RE = re.compile(r"^\$\.lanes\[\d+\]\.required_fields\[\d+\]$")
REQUIRED_CHECKS_PATH_RE = re.compile(r"^\$\.lanes\[\d+\]\.required_checks\[\d+\]$")


def _walk_json(value: Any, path: str = "$") -> Iterable[tuple[str, Any]]:
    yield path, value
    if isinstance(value, dict):
        for key, item in value.items():
            child_path = f"{path}.{key}"
            yield from _walk_json(item, child_path)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk_json(item, f"{path}[{index}]")


def _walk_json_keys(value: Any, path: str = "$") -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, item in value.items():
            child_path = f"{path}.{key}"
            yield child_path, key
            yield from _walk_json_keys(item, child_path)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk_json_keys(item, f"{path}[{index}]")


def _is_allowed_rejection_classification_field(path: str, value: str) -> bool:
    return value == ALLOWED_REJECTION_CLASSIFICATION_FIELD and bool(
        REQUIRED_FIELDS_PATH_RE.match(path)
    )


def _is_allowed_negative_field_name(path: str, value: str) -> bool:
    return value in ALLOWED_NEGATIVE_FIELD_NAMES and bool(
        REQUIRED_CHECKS_PATH_RE.match(path)
    )


def load_contract(path: pathlib.Path) -> dict[str, Any]:
    reject_symlink_component(path, "--contract")
    resolved = reject_protected_input_path(path, "--contract")
    with resolved.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("contract root must be a JSON object")
    return value


def validate_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if contract.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
    if contract.get("contract_id") != CONTRACT_ID:
        errors.append(f"contract_id must be {CONTRACT_ID}")
    if contract.get("artifact_status") != "candidate_only":
        errors.append("artifact_status must be candidate_only")
    if contract.get("readiness_classification") != "planning_only":
        errors.append("readiness_classification must be planning_only")
    if contract.get("pre_abi") is not True:
        errors.append("pre_abi must remain true")

    for key in FALSE_ONLY_TOP_LEVEL_KEYS:
        if contract.get(key) is not False:
            errors.append(f"{key} must remain false")

    promotion = contract.get("promotion")
    if not isinstance(promotion, dict):
        errors.append("promotion must be an object")
    else:
        if promotion.get("public_sdk") is not False:
            errors.append("promotion.public_sdk must remain false")
        if promotion.get("runtime") is not False:
            errors.append("promotion.runtime must remain false")

    lanes = contract.get("lanes")
    if not isinstance(lanes, list):
        errors.append("lanes must be a list")
        lanes = []

    lane_by_id: dict[str, dict[str, Any]] = {}
    for index, lane in enumerate(lanes):
        if not isinstance(lane, dict):
            errors.append(f"lanes[{index}] must be an object")
            continue
        lane_id = lane.get("id")
        if not isinstance(lane_id, str):
            errors.append(f"lanes[{index}].id must be a string")
            continue
        if lane_id in lane_by_id:
            errors.append(f"duplicate lane id: {lane_id}")
        lane_by_id[lane_id] = lane

    expected_lanes = set(REQUIRED_LANE_CHECKS)
    actual_lanes = set(lane_by_id)
    for missing in sorted(expected_lanes - actual_lanes):
        errors.append(f"missing required lane: {missing}")
    for extra in sorted(actual_lanes - expected_lanes):
        errors.append(f"unexpected lane: {extra}")

    for lane_id, required_checks in REQUIRED_LANE_CHECKS.items():
        lane = lane_by_id.get(lane_id)
        if lane is None:
            continue
        if lane.get("mode") != "offline_contract_only":
            errors.append(f"{lane_id}.mode must be offline_contract_only")
        if lane.get("runtime_required") is not False:
            errors.append(f"{lane_id}.runtime_required must remain false")
        if lane.get("public_surface") is not False:
            errors.append(f"{lane_id}.public_surface must remain false")
        decision_required = lane.get("decision_required")
        if not isinstance(decision_required, str) or not decision_required.strip():
            errors.append(f"{lane_id}.decision_required must be a non-empty string")
        checks = lane.get("required_checks")
        if not isinstance(checks, list) or not all(isinstance(item, str) for item in checks):
            errors.append(f"{lane_id}.required_checks must be a list of strings")
        else:
            missing_checks = required_checks - set(checks)
            for missing in sorted(missing_checks):
                errors.append(f"{lane_id}.required_checks missing {missing}")
        required_fields = REQUIRED_LANE_FIELDS[lane_id]
        fields = lane.get("required_fields")
        if not isinstance(fields, list) or not all(isinstance(item, str) for item in fields):
            errors.append(f"{lane_id}.required_fields must be a list of strings")
            continue
        missing_fields = required_fields - set(fields)
        for missing in sorted(missing_fields):
            errors.append(f"{lane_id}.required_fields missing {missing}")

    for path, value in _walk_json(contract):
        if not isinstance(value, str):
            continue
        if value == ALLOWED_REJECTION_CLASSIFICATION_FIELD:
            if _is_allowed_rejection_classification_field(path, value):
                continue
            errors.append(
                f"{ALLOWED_REJECTION_CLASSIFICATION_FIELD} is only allowed as a "
                f"required rejection/classification field at {path}"
            )
            continue
        if _is_allowed_negative_field_name(path, value):
            continue
        match = PROHIBITED_CLAIM_RE.search(value)
        if match:
            errors.append(f"prohibited claim {match.group(0)!r} at {path}")

    for path, key in _walk_json_keys(contract):
        if key in CLAIM_KEY_EXEMPTIONS:
            continue
        if key == ALLOWED_REJECTION_CLASSIFICATION_FIELD:
            errors.append(
                f"{ALLOWED_REJECTION_CLASSIFICATION_FIELD} is only allowed as a "
                f"required rejection/classification field at {path}"
            )
            continue
        match = PROHIBITED_CLAIM_RE.search(key)
        if match:
            errors.append(f"prohibited claim {match.group(0)!r} at field {path}")

    return errors


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the offline operator ingress/storage v1 contract."
    )
    parser.add_argument(
        "--contract",
        type=pathlib.Path,
        default=DEFAULT_CONTRACT,
        help=f"contract JSON path (default: {DEFAULT_CONTRACT})",
    )
    parser.add_argument("--promote", action="store_true", help="always fails closed")
    parser.add_argument("--public-readiness", action="store_true", help="always fails closed")
    parser.add_argument("--runtime-readiness", action="store_true", help="always fails closed")
    parser.add_argument("--json", action="store_true", help="emit JSON result")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    errors: list[str] = []

    if args.promote:
        errors.append("--promote is fail-closed for this offline-only contract")
    if args.public_readiness:
        errors.append("--public-readiness is fail-closed for this offline-only contract")
    if args.runtime_readiness:
        errors.append("--runtime-readiness is fail-closed for this offline-only contract")

    try:
        contract = load_contract(args.contract)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"unable to load contract: {exc}")
    else:
        errors.extend(validate_contract(contract))

    ok = not errors
    if args.json:
        print(json.dumps({"ok": ok, "errors": errors}, indent=2, sort_keys=True))
    elif ok:
        print(f"{CONTRACT_ID}: offline contract valid")
    else:
        print(f"{CONTRACT_ID}: offline contract invalid", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
