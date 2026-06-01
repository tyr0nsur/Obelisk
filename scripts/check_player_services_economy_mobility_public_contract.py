#!/usr/bin/env python3
"""Offline guardrail for obelisk.player_services_economy_mobility.v1."""

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
DEFAULT_CONTRACT = ROOT / "docs" / "player_services_economy_mobility_public_contract_decisions.json"
CONTRACT_ID = "obelisk.player_services_economy_mobility.v1"
SCHEMA = "obelisk.player-services-economy-mobility-public-contract-decisions.v1"

FALSE_ONLY_TOP_LEVEL_KEYS = (
    "public_header_allowed",
    "public_contract_allowed",
    "public_sdk_ready",
    "public_abi_ready",
    "promotion_ready",
    "runtime_ready",
    "runtime_services",
)
REQUIRED_DEPENDENCIES = {
    "obelisk.player_identity.v1": "identity",
    "obelisk.permissions_admin.v1": "permissions_admin",
    "obelisk.operator_ingress_storage.v1": "storage_persistence",
}
REQUIRED_CONTROL_GATES = {
    "identity",
    "permissions_admin",
    "storage_persistence",
    "audit",
    "rollback",
    "abuse",
}
REQUIRED_AUDIT_UNITS = {
    "economy": {
        "economy API",
        "shop API",
        "rewards API",
        "kits API",
        "stats API",
    },
    "mobility": {
        "homes API",
        "teleport API",
        "spawn API",
    },
    "areas": {
        "safe-zone API",
        "area policy API",
    },
    "timed_notices": {
        "broadcast API",
        "timed notice service",
        "scheduled notices API",
    },
}
ALLOWED_BLOCKED_TERMS_PATH_MARKERS = (
    ".forbidden_public_contract",
    ".non_claims",
)
ALLOWED_PUBLIC_TERM_PATH_RE = re.compile(
    r"^\$(?:"
    r"\.schema|"
    r"\.contract_id|"
    r"\.required_control_gates\[\d+\]\.decision_required|"
    r"\.audit_units\[\d+\]\.(?:id|label|forbidden_public_contract\[\d+\])|"
    r"\.non_claims\[\d+\]"
    r")$"
)
NEGATIVE_CONTEXT_TERMS = re.compile(
    r"\b(?:before|block(?:ed|s|er)?|does not add|forbidden|must be|no|not|without|until|requires?)\b",
    re.IGNORECASE,
)
PROMOTION_OVERCLAIM_RE = re.compile(
    r"\b(?:promoted|promotion[-_ ]?ready|public[-_ ]?(?:sdk|abi|contract)[-_ ]?ready|"
    r"runtime[-_ ]?(?:ready|services?|wiring)|public[-_ ]?headers?|public[-_ ]?abi)\b",
    re.IGNORECASE,
)
PUBLIC_SURFACE_CLAIM_RE = re.compile(
    r"\b(?:economy|shop|rewards?|kits?|stats?|balance|currency|homes?|teleport|spawn|"
    r"safe[-_ ]?zones?|area[-_ ]?policy|broadcast|timed[-_ ]?notice|scheduled[-_ ]?notice|"
    r"send[-_ ]?chat|mutation|lookup|resourcehandle|resource[-_ ]?handle|ue[-_ ]?pointers?|"
    r"raw[-_ ]?params?|return[-_ ]?override)\b",
    re.IGNORECASE,
)


def _walk_json(value: Any, path: str = "$") -> Iterable[tuple[str, Any]]:
    yield path, value
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _walk_json(item, f"{path}.{key}")
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


def _allowed_blocked_term_path(path: str) -> bool:
    return bool(ALLOWED_PUBLIC_TERM_PATH_RE.match(path)) or any(
        marker in path for marker in ALLOWED_BLOCKED_TERMS_PATH_MARKERS
    )


def _negative_context(value: str) -> bool:
    return bool(NEGATIVE_CONTEXT_TERMS.search(value))


def load_contract(path: pathlib.Path) -> dict[str, Any]:
    reject_symlink_component(path, "--contract")
    resolved = reject_protected_input_path(path, "--contract")
    with resolved.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("contract root must be a JSON object")
    return value


def _validate_dependencies(contract: dict[str, Any], errors: list[str]) -> None:
    dependencies = contract.get("dependencies")
    if not isinstance(dependencies, list):
        errors.append("dependencies must be a list")
        return

    by_id: dict[str, dict[str, Any]] = {}
    for index, dependency in enumerate(dependencies):
        if not isinstance(dependency, dict):
            errors.append(f"dependencies[{index}] must be an object")
            continue
        dependency_id = dependency.get("id")
        if not isinstance(dependency_id, str):
            errors.append(f"dependencies[{index}].id must be a string")
            continue
        if dependency_id in by_id:
            errors.append(f"duplicate dependency id: {dependency_id}")
        by_id[dependency_id] = dependency

    for dependency_id, kind in REQUIRED_DEPENDENCIES.items():
        dependency = by_id.get(dependency_id)
        if dependency is None:
            errors.append(f"missing required dependency: {dependency_id}")
            continue
        if dependency.get("kind") != kind:
            errors.append(f"{dependency_id}.kind must be {kind}")
        if dependency.get("required_before_public_surface") is not True:
            errors.append(f"{dependency_id}.required_before_public_surface must be true")
        if dependency.get("status") != "unresolved":
            errors.append(f"{dependency_id}.status must remain unresolved")

    for dependency_id in sorted(set(by_id) - set(REQUIRED_DEPENDENCIES)):
        errors.append(f"unexpected dependency: {dependency_id}")


def _validate_control_gates(contract: dict[str, Any], errors: list[str]) -> None:
    controls = contract.get("required_control_gates")
    if not isinstance(controls, list):
        errors.append("required_control_gates must be a list")
        return

    by_id: dict[str, dict[str, Any]] = {}
    for index, control in enumerate(controls):
        if not isinstance(control, dict):
            errors.append(f"required_control_gates[{index}] must be an object")
            continue
        control_id = control.get("id")
        if not isinstance(control_id, str):
            errors.append(f"required_control_gates[{index}].id must be a string")
            continue
        if control_id in by_id:
            errors.append(f"duplicate control gate id: {control_id}")
        by_id[control_id] = control

    for control_id in sorted(REQUIRED_CONTROL_GATES):
        control = by_id.get(control_id)
        if control is None:
            errors.append(f"missing required control gate: {control_id}")
            continue
        if control.get("status") != "unresolved":
            errors.append(f"{control_id}.status must remain unresolved")
        if control.get("must_exist_before_promotion") is not True:
            errors.append(f"{control_id}.must_exist_before_promotion must be true")
        decision_required = control.get("decision_required")
        if not isinstance(decision_required, str) or not decision_required.strip():
            errors.append(f"{control_id}.decision_required must be a non-empty string")

    for control_id in sorted(set(by_id) - REQUIRED_CONTROL_GATES):
        errors.append(f"unexpected control gate: {control_id}")


def _validate_audit_units(contract: dict[str, Any], errors: list[str]) -> None:
    audit_units = contract.get("audit_units")
    if not isinstance(audit_units, list):
        errors.append("audit_units must be a list")
        return

    by_id: dict[str, dict[str, Any]] = {}
    for index, unit in enumerate(audit_units):
        if not isinstance(unit, dict):
            errors.append(f"audit_units[{index}] must be an object")
            continue
        unit_id = unit.get("id")
        if not isinstance(unit_id, str):
            errors.append(f"audit_units[{index}].id must be a string")
            continue
        if unit_id in by_id:
            errors.append(f"duplicate audit unit id: {unit_id}")
        by_id[unit_id] = unit

    for unit_id, forbidden_terms in REQUIRED_AUDIT_UNITS.items():
        unit = by_id.get(unit_id)
        if unit is None:
            errors.append(f"missing required audit unit: {unit_id}")
            continue
        if unit.get("mode") != "offline_contract_only":
            errors.append(f"{unit_id}.mode must be offline_contract_only")
        if unit.get("runtime_required") is not False:
            errors.append(f"{unit_id}.runtime_required must remain false")
        if unit.get("public_surface") is not False:
            errors.append(f"{unit_id}.public_surface must remain false")
        blocked_until = unit.get("blocked_until_controls")
        if not isinstance(blocked_until, list) or not all(isinstance(item, str) for item in blocked_until):
            errors.append(f"{unit_id}.blocked_until_controls must be a list of strings")
        else:
            missing_controls = REQUIRED_CONTROL_GATES - set(blocked_until)
            for missing in sorted(missing_controls):
                errors.append(f"{unit_id}.blocked_until_controls missing {missing}")
        forbidden_public_contract = unit.get("forbidden_public_contract")
        if (
            not isinstance(forbidden_public_contract, list)
            or not all(isinstance(item, str) for item in forbidden_public_contract)
        ):
            errors.append(f"{unit_id}.forbidden_public_contract must be a list of strings")
            continue
        for missing in sorted(forbidden_terms - set(forbidden_public_contract)):
            errors.append(f"{unit_id}.forbidden_public_contract missing {missing}")

    for unit_id in sorted(set(by_id) - set(REQUIRED_AUDIT_UNITS)):
        errors.append(f"unexpected audit unit: {unit_id}")


def _validate_no_overclaims(contract: dict[str, Any], errors: list[str]) -> None:
    for path, key in _walk_json_keys(contract):
        match = PROMOTION_OVERCLAIM_RE.search(key)
        if match and key not in FALSE_ONLY_TOP_LEVEL_KEYS:
            errors.append(f"promotion overclaim field {match.group(0)!r} at {path}")

    for path, value in _walk_json(contract):
        if not isinstance(value, str):
            continue

        promotion_match = PROMOTION_OVERCLAIM_RE.search(value)
        if promotion_match and not _negative_context(value):
            errors.append(f"promotion overclaim {promotion_match.group(0)!r} at {path}")

        public_match = PUBLIC_SURFACE_CLAIM_RE.search(value)
        if public_match and not (_allowed_blocked_term_path(path) or _negative_context(value)):
            errors.append(f"public surface overclaim {public_match.group(0)!r} at {path}")


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

    _validate_dependencies(contract, errors)
    _validate_control_gates(contract, errors)
    _validate_audit_units(contract, errors)
    _validate_no_overclaims(contract, errors)

    return errors


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the offline player services/economy/mobility public contract guardrail."
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
        errors.append("--promote is fail-closed for this candidate-only contract")
    if args.public_readiness:
        errors.append("--public-readiness is fail-closed for this candidate-only contract")
    if args.runtime_readiness:
        errors.append("--runtime-readiness is fail-closed for this candidate-only contract")

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
        print(f"{CONTRACT_ID}: candidate-only contract valid")
    else:
        print(f"{CONTRACT_ID}: candidate-only contract invalid", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
