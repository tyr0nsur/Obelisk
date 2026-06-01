#!/usr/bin/env python3
"""Validate candidate-only permissions/admin query fail-closed contracts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


SCHEMA = "obelisk.permissions-admin-query-failclosed-contract.v1"
REPORT_SCHEMA = "obelisk.permissions-admin-query-failclosed-contract-check.v1"

REQUIRED_QUERY_FIELDS = frozenset(
    (
        "plugin_owner_token",
        "principal_handle",
        "principal_generation",
        "principal_scope_flags",
        "action",
        "action_size",
        "resource_scope",
        "resource_scope_size",
        "request_flags",
    )
)
REQUIRED_QUERY_FIELD_SEQUENCE = (
    "plugin_owner_token",
    "principal_handle",
    "principal_generation",
    "principal_scope_flags",
    "action",
    "action_size",
    "resource_scope",
    "resource_scope_size",
    "request_flags",
)
REQUIRED_QUERY_FIELD_TYPES = {
    "plugin_owner_token": "uint64_owner_token",
    "principal_handle": "uint64_opaque",
    "principal_generation": "uint64",
    "principal_scope_flags": "uint64_flags",
    "action": "copied_bytes",
    "action_size": "size_t",
    "resource_scope": "copied_bytes",
    "resource_scope_size": "size_t",
    "request_flags": "uint64_flags",
}
REQUIRED_DECISIONS = frozenset(("deny", "allow", "unknown"))
REQUIRED_DECISION_SEQUENCE = ("deny", "allow", "unknown")
REQUIRED_PROVENANCE_FIELDS = frozenset(
    (
        "policy_source_id",
        "policy_source_generation",
        "authority_kind",
        "authority_generation",
        "policy_epoch",
    )
)
REQUIRED_RECOGNIZED_AUTHORITY_KINDS = frozenset(("operator-config", "runtime-local"))
REQUIRED_ALLOW_CAPABLE_AUTHORITY_KINDS = frozenset(("runtime-local",))
FORBIDDEN_ALLOW_CAPABLE_AUTHORITY_KINDS = frozenset(
    (
        "operator-config",
        "plugin-supplied-authority",
        "remote-service-authority",
        "cross-process-shared-authority",
    )
)
REQUIRED_FAIL_CLOSED_CASES = frozenset(
    (
        "stale_principal",
        "scope_mismatch",
        "missing_runtime_principal_identity",
        "command_text_principal_claim",
        "operator_config_principal_claim",
        "missing_action",
        "malformed_action_size",
        "missing_principal_generation",
        "principal_generation_mismatch",
        "missing_plugin_owner_token",
        "missing_capability",
        "rate_limit_exceeded",
        "unknown_authority",
        "missing_policy_source",
        "missing_policy_source_generation",
        "policy_source_generation_mismatch",
        "missing_policy_epoch",
        "missing_authority_generation",
        "authority_generation_mismatch",
        "plugin_supplied_provenance",
    )
)
REQUIRED_FAIL_CLOSED_CASE_SEQUENCE = (
    "stale_principal",
    "scope_mismatch",
    "missing_runtime_principal_identity",
    "command_text_principal_claim",
    "operator_config_principal_claim",
    "missing_action",
    "malformed_action_size",
    "missing_principal_generation",
    "principal_generation_mismatch",
    "missing_plugin_owner_token",
    "missing_capability",
    "rate_limit_exceeded",
    "unknown_authority",
    "missing_policy_source",
    "missing_policy_source_generation",
    "policy_source_generation_mismatch",
    "missing_policy_epoch",
    "missing_authority_generation",
    "authority_generation_mismatch",
    "plugin_supplied_provenance",
)
REQUIRED_EXCLUSIONS = frozenset(
    (
        "permission_groups",
        "admin_groups",
        "grants",
        "ban",
        "kick",
        "commands",
        "replies",
        "storage",
        "ue_pointers",
        "ResourceHandle",
        "lookup",
        "mutation",
        "return_override",
    )
)
REQUIRED_NON_CLAIMS = frozenset(
    (
        "candidate-only pre-ABI permissions/admin query contract",
        "does not add public headers, runtime wiring, public cache ABI, command responses, commands, replies, storage, groups, grants, ban/kick, mutation, lookup, ResourceHandle, UE pointers, or return override",
        "allow decisions require policy provenance and fail closed on missing or unknown authority",
        "command text and operator config cannot establish principal identity or permission claims before runtime principal observation",
        "promotion, public SDK readiness, and runtime readiness require a separate reviewed ABI and runtime gate",
    )
)
REQUIRED_PRINCIPAL_RUNTIME_IDENTITY_POLICY = {
    "config_enables_surface_only": True,
    "runtime_observation_establishes_identity": True,
    "runtime_principal_required_for_permission_authority": True,
    "command_text_principal_claim_allowed": False,
    "operator_config_principal_claim_allowed": False,
    "command_text_permission_claim_allowed": False,
    "operator_config_permission_claim_allowed": False,
}

FORBIDDEN_COORDINATE_KEYS = frozenset(
    (
        "address",
        "function_address",
        "gobject_index",
        "gobjects_index",
        "name_index",
        "fname_index",
        "object_address",
        "object_index",
        "raw_param_address",
        "ue_pointer",
        "uobject_address",
    )
)
NEGATIVE_CONTEXT_TOKENS = (
    "blocker",
    "deny",
    "exclude",
    "exclusion",
    "fail_closed",
    "forbid",
    "forbidden",
    "negative",
    "non_claim",
    "reject",
)
FORBIDDEN_SURFACE_RE = re.compile(
    r"\b("
    r"groups?|"
    r"permission[_ -]?groups?|"
    r"admin[_ -]?groups?|"
    r"grants?|grant[_ -]?(?:api|revoke)|"
    r"ban(?:[_ -]?player)?|"
    r"kick(?:[_ -]?player)?|"
    r"commands?|command[_ -]?router|"
    r"replies|reply(?:[_ -]?api)?|send[_ -]?chat|"
    r"storage|persistence|"
    r"ue[_ -]?pointers?|uobject|ufunction|raw[_ -]?params?|"
    r"resourcehandle|resource[_ -]?handle|"
    r"lookup|mutation|return[_ -]?override"
    r")\b",
    re.IGNORECASE,
)
READY_OVERCLAIM_KEYS = frozenset(
    (
        "promoted",
        "promote_ready",
        "promotion_ready",
        "public_sdk_ready",
        "runtime_ready",
    )
)
READY_OVERCLAIM_STRINGS = {
    "promoted": "promoted",
    "public sdk ready": "public_sdk_ready",
    "runtime ready": "runtime_ready",
    "promotion ready": "promotion_ready",
    "promote ready": "promote_ready",
}
OVERCLAIM_NEGATIVE_PREFIXES = (
    "$.negative_surface_exclusions",
    "$.non_claims",
    "$.promotion_gate.blockers",
)
FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_KEYS = frozenset(
    (
        "authority_claim_source",
        "identity_claim_source",
        "identity_source",
        "permission_claim_source",
        "permission_source",
        "principal_claim_source",
        "principal_source",
    )
)
FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_VALUES = frozenset(
    (
        "command text",
        "command-text",
        "command_text",
        "operator config",
        "operator-config",
        "operator_config",
    )
)


@dataclass
class Validation:
    blockers: list[dict[str, Any]]
    query_fields: list[str]
    decisions: list[str]
    provenance_fields: list[str]
    fail_closed_cases: list[str]
    recognized_authority_kinds: list[str]
    allow_capable_authority_kinds: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, nargs="?", help="Permissions/admin query candidate contract to validate.")
    parser.add_argument("--json", action="store_true", help="Emit a JSON report.")
    parser.add_argument(
        "--emit-template",
        type=Path,
        help="Write the canonical permissions/admin query fail-closed candidate template and exit.",
    )
    parser.add_argument("--promote", action="store_true", help="Check promote readiness; candidate-only contracts fail closed.")
    parser.add_argument(
        "--public-readiness",
        action="store_true",
        help="Check public SDK readiness; candidate-only contracts fail closed.",
    )
    parser.add_argument(
        "--runtime-readiness",
        action="store_true",
        help="Check runtime readiness; candidate-only contracts fail closed.",
    )
    return parser.parse_args()


def add(blockers: list[dict[str, Any]], reason: str, label: str, **extra: Any) -> None:
    blocker = {"reason": reason, "label": label}
    blocker.update(extra)
    blockers.append(blocker)


def load_json(path: Path) -> dict[str, Any]:
    reject_symlink_component(path, "manifest")
    path = reject_protected_input_path(path, "manifest")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{path}: top-level JSON must be an object")
    return payload


def build_template_manifest() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "artifact_status": "candidate_only",
        "readiness_classification": "planning_only",
        "pre_abi": True,
        "public_header_allowed": False,
        "public_cache_abi_allowed": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "runtime_promotion_allowed": False,
        "query_contract": {
            "kind": "query_only_fail_closed_permission_check",
            "mutation_allowed": False,
            "command_response_allowed": False,
            "public_cache_allowed": False,
            "fields": [
                {
                    "name": name,
                    "type": REQUIRED_QUERY_FIELD_TYPES[name],
                    "copied": True,
                    "source": "obelisk_owned_copy",
                    "consumer_visible": True,
                }
                for name in REQUIRED_QUERY_FIELD_SEQUENCE
            ],
        },
        "decision_contract": {
            "results": [
                {
                    "decision": decision,
                    "fail_closed": decision != "allow",
                    "requires_provenance": decision == "allow",
                }
                for decision in REQUIRED_DECISION_SEQUENCE
            ],
            "provenance_fields": sorted(REQUIRED_PROVENANCE_FIELDS),
            "allow_without_provenance_allowed": False,
            "unknown_authority_result": "unknown",
        },
        "authority_policy": {
            "recognized_authority_kinds": sorted(REQUIRED_RECOGNIZED_AUTHORITY_KINDS),
            "allow_capable_authority_kinds": sorted(REQUIRED_ALLOW_CAPABLE_AUTHORITY_KINDS),
            "allowed_authority_kinds": sorted(REQUIRED_RECOGNIZED_AUTHORITY_KINDS),
            "operator_config_allow_capable": False,
            "plugin_supplied_authority_allowed": False,
            "remote_authority_allowed": False,
            "cross_process_authority_allowed": False,
            "unknown_authority_fails_closed": True,
        },
        "principal_runtime_identity_policy": dict(REQUIRED_PRINCIPAL_RUNTIME_IDENTITY_POLICY),
        "fail_closed_cases": [
            {
                "case": case,
                "consumer_result": "deny",
                "fail_closed": True,
                "allow_allowed": False,
            }
            for case in REQUIRED_FAIL_CLOSED_CASE_SEQUENCE
        ],
        "negative_surface_exclusions": sorted(REQUIRED_EXCLUSIONS),
        "promotion_gate": {
            "ready": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "blockers": [
                "candidate_only_pre_abi_contract",
                "public_abi_review_missing",
                "runtime_evidence_missing",
            ],
        },
        "non_claims": sorted(REQUIRED_NON_CLAIMS),
    }


def mode(args: argparse.Namespace) -> str:
    requested = [
        name
        for name, enabled in (
            ("promote", args.promote),
            ("public_readiness", args.public_readiness),
            ("runtime_readiness", args.runtime_readiness),
        )
        if enabled
    ]
    if len(requested) > 1:
        raise SystemExit("--promote, --public-readiness, and --runtime-readiness are mutually exclusive")
    return requested[0] if requested else "consume"


def is_negative_context(trail: str) -> bool:
    lowered = trail.casefold()
    return any(token in lowered for token in NEGATIVE_CONTEXT_TOKENS)


def find_forbidden_coordinate(value: Any, trail: str = "$") -> tuple[str, str] | None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if key in FORBIDDEN_COORDINATE_KEYS:
                return str(key), child_trail
            found = find_forbidden_coordinate(child, child_trail)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = find_forbidden_coordinate(child, f"{trail}[{index}]")
            if found is not None:
                return found
    return None


def find_forbidden_surface(value: Any, trail: str = "$") -> tuple[str, str] | None:
    if is_negative_context(trail):
        return None
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if FORBIDDEN_SURFACE_RE.search(str(key)) and child is not False:
                return str(key), child_trail
            found = find_forbidden_surface(child, child_trail)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = find_forbidden_surface(child, f"{trail}[{index}]")
            if found is not None:
                return found
    elif isinstance(value, str) and FORBIDDEN_SURFACE_RE.search(value):
        return value, trail
    return None


def contains_forbidden_pre_runtime_claim_source(value: Any) -> bool:
    if isinstance(value, str):
        return value.casefold() in FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_VALUES
    if isinstance(value, list):
        return any(contains_forbidden_pre_runtime_claim_source(item) for item in value)
    if isinstance(value, dict):
        return any(contains_forbidden_pre_runtime_claim_source(item) for item in value.values())
    return False


def find_forbidden_pre_runtime_claim_source(value: Any, trail: str = "$") -> tuple[str, str] | None:
    if is_negative_context(trail):
        return None
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            normalized_key = str(key).casefold().replace("-", "_").replace(" ", "_")
            if normalized_key in FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_KEYS and contains_forbidden_pre_runtime_claim_source(child):
                return str(key), child_trail
            found = find_forbidden_pre_runtime_claim_source(child, child_trail)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = find_forbidden_pre_runtime_claim_source(child, f"{trail}[{index}]")
            if found is not None:
                return found
    return None


def collect_overclaim_fields(value: Any, trail: str = "$") -> list[dict[str, str]]:
    if any(trail.startswith(prefix) for prefix in OVERCLAIM_NEGATIVE_PREFIXES):
        return []
    found: list[dict[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if key in READY_OVERCLAIM_KEYS and child is True:
                found.append({"reason": f"{key}_overclaim", "label": child_trail})
            found.extend(collect_overclaim_fields(child, child_trail))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(collect_overclaim_fields(child, f"{trail}[{index}]"))
    elif isinstance(value, str):
        text = value.casefold()
        for needle, reason in READY_OVERCLAIM_STRINGS.items():
            if needle in text:
                found.append({"reason": f"{reason}_string_overclaim", "label": trail})
    return found


def validate_query_contract(contract: Any, blockers: list[dict[str, Any]]) -> list[str]:
    if not isinstance(contract, dict):
        add(blockers, "query_contract_missing", "$.query_contract")
        return []
    if contract.get("kind") != "query_only_fail_closed_permission_check":
        add(blockers, "query_contract_kind_not_query_only_fail_closed", "$.query_contract.kind")
    for key in ("mutation_allowed", "command_response_allowed", "public_cache_allowed"):
        if contract.get(key) is not False:
            add(blockers, f"query_contract_{key}_not_false", f"$.query_contract.{key}")

    fields = contract.get("fields")
    if not isinstance(fields, list):
        add(blockers, "query_fields_not_list", "$.query_contract.fields")
        return []

    names: list[str] = []
    for index, field in enumerate(fields):
        label = f"$.query_contract.fields[{index}]"
        if not isinstance(field, dict):
            add(blockers, "query_field_invalid", label)
            continue
        name = field.get("name")
        if not isinstance(name, str) or not name:
            add(blockers, "query_field_name_missing", f"{label}.name")
            continue
        names.append(name)
        if name not in REQUIRED_QUERY_FIELDS:
            add(blockers, "query_field_unexpected", f"{label}.name", field=name)
        expected_type = REQUIRED_QUERY_FIELD_TYPES.get(name)
        if expected_type is not None and field.get("type") != expected_type:
            add(
                blockers,
                "query_field_type_mismatch",
                f"{label}.type",
                field=name,
                expected=expected_type,
                value=field.get("type"),
            )
        if field.get("copied") is not True:
            add(blockers, "query_field_not_copied", f"{label}.copied", field=name)
        if field.get("source") != "obelisk_owned_copy":
            add(blockers, "query_field_source_not_obelisk_copy", f"{label}.source", field=name)
        if field.get("consumer_visible") is not True:
            add(blockers, "query_field_not_consumer_visible_candidate", f"{label}.consumer_visible", field=name)

    missing = REQUIRED_QUERY_FIELDS - set(names)
    if missing:
        add(blockers, "query_fields_missing_required", "$.query_contract.fields", missing=sorted(missing))
    return sorted(names)


def validate_decision_contract(contract: Any, blockers: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    if not isinstance(contract, dict):
        add(blockers, "decision_contract_missing", "$.decision_contract")
        return [], []
    if contract.get("allow_without_provenance_allowed") is not False:
        add(blockers, "allow_without_provenance_allowed_not_false", "$.decision_contract.allow_without_provenance_allowed")
    if contract.get("unknown_authority_result") not in {"deny", "unknown"}:
        add(blockers, "unknown_authority_result_not_fail_closed", "$.decision_contract.unknown_authority_result")

    result_names: list[str] = []
    results = contract.get("results")
    if not isinstance(results, list):
        add(blockers, "decision_results_not_list", "$.decision_contract.results")
    else:
        for index, result in enumerate(results):
            label = f"$.decision_contract.results[{index}]"
            if not isinstance(result, dict):
                add(blockers, "decision_result_invalid", label)
                continue
            name = result.get("decision")
            if not isinstance(name, str) or not name:
                add(blockers, "decision_result_name_missing", f"{label}.decision")
                continue
            result_names.append(name)
            if name not in REQUIRED_DECISIONS:
                add(blockers, "decision_result_unexpected", f"{label}.decision", decision=name)
            if name == "allow" and result.get("requires_provenance") is not True:
                add(blockers, "allow_decision_missing_provenance_requirement", f"{label}.requires_provenance")
            if name in {"deny", "unknown"} and result.get("fail_closed") is not True:
                add(blockers, "deny_unknown_decision_not_fail_closed", f"{label}.fail_closed", decision=name)
    missing_results = REQUIRED_DECISIONS - set(result_names)
    if missing_results:
        add(blockers, "decision_results_missing_required", "$.decision_contract.results", missing=sorted(missing_results))

    provenance = contract.get("provenance_fields")
    if not isinstance(provenance, list):
        add(blockers, "provenance_fields_not_list", "$.decision_contract.provenance_fields")
        provenance_names: list[str] = []
    else:
        provenance_names = [item for item in provenance if isinstance(item, str)]
        if len(provenance_names) != len(provenance):
            add(blockers, "provenance_field_invalid", "$.decision_contract.provenance_fields")
        unexpected = set(provenance_names) - REQUIRED_PROVENANCE_FIELDS
        if unexpected:
            add(
                blockers,
                "provenance_fields_unexpected",
                "$.decision_contract.provenance_fields",
                fields=sorted(unexpected),
            )
        missing = REQUIRED_PROVENANCE_FIELDS - set(provenance_names)
        if missing:
            add(
                blockers,
                "provenance_fields_missing_required",
                "$.decision_contract.provenance_fields",
                missing=sorted(missing),
            )

    return sorted(result_names), sorted(provenance_names)


def validate_authority_kind_list(
    value: Any,
    *,
    label: str,
    required: frozenset[str],
    blockers: list[dict[str, Any]],
    missing_reason: str,
    unexpected_reason: str,
) -> list[str]:
    if not isinstance(value, list):
        add(blockers, missing_reason, label)
        return []
    names = [item for item in value if isinstance(item, str)]
    if len(names) != len(value):
        add(blockers, "authority_kind_invalid", label)
    missing = required - set(names)
    if missing:
        add(blockers, missing_reason, label, missing=sorted(missing))
    unexpected = set(names) - required
    if unexpected:
        add(blockers, unexpected_reason, label, authority_kinds=sorted(unexpected))
    return sorted(names)


def validate_authority_policy(policy: Any, blockers: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    if not isinstance(policy, dict):
        add(blockers, "authority_policy_missing", "$.authority_policy")
        return [], []
    recognized = validate_authority_kind_list(
        policy.get("recognized_authority_kinds"),
        label="$.authority_policy.recognized_authority_kinds",
        required=REQUIRED_RECOGNIZED_AUTHORITY_KINDS,
        blockers=blockers,
        missing_reason="authority_recognized_kinds_missing_required",
        unexpected_reason="authority_recognized_kinds_unexpected",
    )
    allow_capable = validate_authority_kind_list(
        policy.get("allow_capable_authority_kinds"),
        label="$.authority_policy.allow_capable_authority_kinds",
        required=REQUIRED_ALLOW_CAPABLE_AUTHORITY_KINDS,
        blockers=blockers,
        missing_reason="authority_allow_capable_kinds_missing_required",
        unexpected_reason="authority_allow_capable_kinds_unexpected",
    )
    forbidden_allow_capable = set(allow_capable) & FORBIDDEN_ALLOW_CAPABLE_AUTHORITY_KINDS
    if forbidden_allow_capable:
        add(
            blockers,
            "authority_forbidden_allow_capable_kind",
            "$.authority_policy.allow_capable_authority_kinds",
            authority_kinds=sorted(forbidden_allow_capable),
        )

    legacy_allowed = policy.get("allowed_authority_kinds")
    if legacy_allowed is not None:
        legacy_names = [item for item in legacy_allowed if isinstance(item, str)] if isinstance(legacy_allowed, list) else []
        if not isinstance(legacy_allowed, list) or set(legacy_names) != REQUIRED_RECOGNIZED_AUTHORITY_KINDS:
            add(blockers, "authority_allowed_kinds_must_match_recognized_legacy_alias", "$.authority_policy.allowed_authority_kinds")
    for key in (
        "plugin_supplied_authority_allowed",
        "remote_authority_allowed",
        "cross_process_authority_allowed",
    ):
        if policy.get(key) is not False:
            add(blockers, f"authority_{key}_not_false", f"$.authority_policy.{key}")
    if policy.get("unknown_authority_fails_closed") is not True:
        add(blockers, "unknown_authority_not_fail_closed", "$.authority_policy.unknown_authority_fails_closed")
    if policy.get("operator_config_allow_capable") is not False:
        add(blockers, "operator_config_allow_capable_not_false", "$.authority_policy.operator_config_allow_capable")
    return recognized, allow_capable


def validate_principal_runtime_identity_policy(policy: Any, blockers: list[dict[str, Any]]) -> None:
    label = "$.principal_runtime_identity_policy"
    if not isinstance(policy, dict):
        add(blockers, "principal_runtime_identity_policy_missing", label)
        return
    for key, expected in REQUIRED_PRINCIPAL_RUNTIME_IDENTITY_POLICY.items():
        if policy.get(key) is not expected:
            add(
                blockers,
                f"principal_runtime_identity_policy_{key}_invalid",
                f"{label}.{key}",
                expected=expected,
                value=policy.get(key),
            )


def validate_fail_closed_cases(cases: Any, blockers: list[dict[str, Any]]) -> list[str]:
    if not isinstance(cases, list):
        add(blockers, "fail_closed_cases_not_list", "$.fail_closed_cases")
        return []
    names: list[str] = []
    for index, case in enumerate(cases):
        label = f"$.fail_closed_cases[{index}]"
        if not isinstance(case, dict):
            add(blockers, "fail_closed_case_invalid", label)
            continue
        name = case.get("case")
        if not isinstance(name, str) or not name:
            add(blockers, "fail_closed_case_name_missing", f"{label}.case")
            continue
        names.append(name)
        if name not in REQUIRED_FAIL_CLOSED_CASES:
            add(blockers, "fail_closed_case_unexpected", f"{label}.case", case=name)
        if case.get("fail_closed") is not True:
            add(blockers, "fail_closed_case_not_fail_closed", f"{label}.fail_closed", case=name)
        if case.get("allow_allowed") is not False:
            add(blockers, "fail_closed_case_allow_not_forbidden", f"{label}.allow_allowed", case=name)
        if case.get("consumer_result") not in {"deny", "unknown"}:
            add(blockers, "fail_closed_case_consumer_result_not_denied_or_unknown", f"{label}.consumer_result", case=name)
    missing = REQUIRED_FAIL_CLOSED_CASES - set(names)
    if missing:
        add(blockers, "fail_closed_cases_missing_required", "$.fail_closed_cases", missing=sorted(missing))
    return sorted(names)


def validate_negative_exclusions(exclusions: Any, blockers: list[dict[str, Any]]) -> None:
    if not isinstance(exclusions, list):
        add(blockers, "negative_surface_exclusions_not_list", "$.negative_surface_exclusions")
        return
    exclusion_set = {item for item in exclusions if isinstance(item, str)}
    if len(exclusion_set) != len(exclusions):
        add(blockers, "negative_surface_exclusion_invalid", "$.negative_surface_exclusions")
    missing = REQUIRED_EXCLUSIONS - exclusion_set
    if missing:
        add(blockers, "negative_surface_exclusions_missing_required", "$.negative_surface_exclusions", missing=sorted(missing))


def validate_promotion_gate(gate: Any, blockers: list[dict[str, Any]]) -> None:
    if not isinstance(gate, dict):
        add(blockers, "promotion_gate_missing", "$.promotion_gate")
        return
    for key in ("ready", "promotion_ready", "public_sdk_ready", "runtime_ready"):
        if gate.get(key) is not False:
            add(blockers, f"promotion_gate_{key}_not_false", f"$.promotion_gate.{key}")
    gate_blockers = gate.get("blockers")
    required = {"candidate_only_pre_abi_contract", "public_abi_review_missing", "runtime_evidence_missing"}
    if not isinstance(gate_blockers, list) or not required.issubset(set(gate_blockers)):
        add(blockers, "promotion_gate_missing_required_blockers", "$.promotion_gate.blockers")


def validate_manifest(payload: dict[str, Any], *, check_mode: str) -> Validation:
    blockers: list[dict[str, Any]] = []
    if payload.get("schema") != SCHEMA:
        add(blockers, "schema_mismatch", "$.schema")
        return Validation(blockers, [], [], [], [], [])
    if payload.get("artifact_status") != "candidate_only":
        add(blockers, "status_not_candidate_only", "$.artifact_status")
    if payload.get("readiness_classification") != "planning_only":
        add(blockers, "readiness_classification_not_planning_only", "$.readiness_classification")
    if payload.get("pre_abi") is not True:
        add(blockers, "pre_abi_not_true", "$.pre_abi")
    for key in (
        "public_header_allowed",
        "public_cache_abi_allowed",
        "promotion_ready",
        "public_sdk_ready",
        "runtime_ready",
        "runtime_promotion_allowed",
    ):
        if payload.get(key) is not False:
            add(blockers, f"{key}_not_false", f"$.{key}")

    query_fields = validate_query_contract(payload.get("query_contract"), blockers)
    decisions, provenance_fields = validate_decision_contract(payload.get("decision_contract"), blockers)
    recognized_authority_kinds, allow_capable_authority_kinds = validate_authority_policy(
        payload.get("authority_policy"), blockers
    )
    validate_principal_runtime_identity_policy(payload.get("principal_runtime_identity_policy"), blockers)
    fail_closed_cases = validate_fail_closed_cases(payload.get("fail_closed_cases"), blockers)
    validate_negative_exclusions(payload.get("negative_surface_exclusions"), blockers)
    validate_promotion_gate(payload.get("promotion_gate"), blockers)

    non_claims = payload.get("non_claims")
    if not isinstance(non_claims, list) or not REQUIRED_NON_CLAIMS.issubset(set(non_claims)):
        add(blockers, "non_claims_missing_required", "$.non_claims")

    coordinate = find_forbidden_coordinate(payload)
    if coordinate is not None:
        field, trail = coordinate
        add(blockers, "ue_coordinate_or_pointer_leakage", trail, field=field)

    forbidden = find_forbidden_surface(payload)
    if forbidden is not None:
        value, trail = forbidden
        add(blockers, "forbidden_surface_claim", trail, value=value)
    claim_source = find_forbidden_pre_runtime_claim_source(payload)
    if claim_source is not None:
        field, trail = claim_source
        add(blockers, "pre_runtime_principal_or_permission_claim_source", trail, field=field)
    for overclaim in collect_overclaim_fields(payload):
        add(blockers, overclaim["reason"], overclaim["label"])

    if check_mode != "consume":
        add(blockers, f"{check_mode}_blocked_for_candidate_only_pre_abi_contract", "$")
        add(blockers, "candidate_only_permissions_admin_query_contract_not_readiness_evidence", "$")

    return Validation(
        blockers,
        query_fields,
        decisions,
        provenance_fields,
        fail_closed_cases,
        recognized_authority_kinds,
        allow_capable_authority_kinds,
    )


def build_report(payload: dict[str, Any], validation: Validation, *, check_mode: str) -> dict[str, Any]:
    return {
        "schema": REPORT_SCHEMA,
        "input_schema": payload.get("schema"),
        "mode": check_mode,
        "ready": not validation.blockers,
        "candidate_only": payload.get("artifact_status") == "candidate_only",
        "pre_abi": payload.get("pre_abi") is True,
        "public_header_allowed": False,
        "public_cache_abi_allowed": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "query_fields": validation.query_fields,
        "decisions": validation.decisions,
        "provenance_fields": validation.provenance_fields,
        "fail_closed_cases": validation.fail_closed_cases,
        "recognized_authority_kinds": validation.recognized_authority_kinds,
        "allow_capable_authority_kinds": validation.allow_capable_authority_kinds,
        "blockers": [blocker["reason"] for blocker in validation.blockers],
        "blocker_details": validation.blockers,
    }


def main() -> int:
    args = parse_args()
    check_mode = mode(args)
    if args.emit_template is not None:
        payload = build_template_manifest()
        args.emit_template.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 0
    if args.manifest is None:
        raise SystemExit("manifest is required unless --emit-template is used")
    payload = load_json(args.manifest)
    validation = validate_manifest(payload, check_mode=check_mode)
    report = build_report(payload, validation, check_mode=check_mode)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif validation.blockers:
        for blocker in validation.blockers:
            print(f"{blocker['reason']}: {blocker['label']}", file=sys.stderr)
    return 0 if not validation.blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
