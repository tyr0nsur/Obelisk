#!/usr/bin/env python3
"""Validate candidate-only player identity principal/invalidation policy artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


SCHEMA = "obelisk.players-identity-principal-invalidation-policy.v1"
REPORT_SCHEMA = "obelisk.players-identity-principal-invalidation-policy-check.v1"

REQUIRED_PRINCIPAL_FIELD_NAMES = frozenset(
    ("principal", "generation", "state", "scope_flags", "privacy_class")
)
REQUIRED_INVALIDATION_CASES = frozenset(
    (
        "logout_or_disconnect",
        "reconnect_after_invalidation",
        "transfer_or_download_edge",
        "stale_controller_or_player_state",
        "duplicate_or_conflicting_identity",
        "server_restart",
        "plugin_reload",
        "malformed_or_unsupported_evidence",
    )
)
REQUIRED_NEGATIVE_RULES = frozenset(
    (
        "no_real_identity_public",
        "no_ue_pointer_or_handle_identity",
        "no_lookup_or_persistence_from_principal",
        "no_return_override_or_mutation_authority",
        "no_commands_or_permissions_claims",
        "fail_closed_on_invalid_or_stale",
    )
)
REQUIRED_TOP_LEVEL_KEYS = frozenset(
    (
        "schema",
        "artifact_status",
        "readiness_classification",
        "promotion_ready",
        "public_sdk_ready",
        "runtime_ready",
        "lifecycle_layout_source",
        "principal",
        "generation",
        "state",
        "scope_flags",
        "privacy_class",
        "invalidation_cases",
        "negative_consumer_rules",
        "rejected_public_identity_sources",
        "evidence_policy",
        "runtime_evidence",
        "promotion_gate",
        "safety_summary",
        "non_claims",
    )
)
REQUIRED_REJECTED_PUBLIC_IDENTITY_SOURCES = frozenset(
    (
        "SteamID",
        "EOSID",
        "UniqueNetId",
        "PlayerID",
        "PlayerDataID",
        "PlayerName",
        "IPAddress",
        "TribeID",
        "ResourceHandle",
        "GObjects",
        "FNames",
        "UObjectPointer",
    )
)
REQUIRED_NON_CLAIMS = frozenset(
    (
        "candidate-only principal invalidation policy",
        "does not expose real player identifiers, Steam/EOS, names, IPs, or tribe ids",
        "does not expose UE pointers, ResourceHandle, GObjects, FNames, lookup, mutation, or persistence",
        "does not expose return override, commands, permissions, moderation, or admin authority",
        "promote, public SDK readiness, and runtime readiness require separately approved runtime evidence",
    )
)
ALLOWED_LIFECYCLE_LAYOUT_SOURCE_KEYS = frozenset(
    (
        "status",
        "accepted_layout_only",
        "start_anchor",
        "end_anchor",
        "principal_invalidation_evidence",
        "source_binding",
    )
)
REQUIRED_EXCLUSIONS = frozenset(
    (
        "real_player_ids",
        "steam_ids",
        "eos_ids",
        "player_names",
        "ip_addresses",
        "tribe_ids",
        "ue_pointers",
        "ResourceHandle",
        "GObjects",
        "FNames",
        "lookup",
        "mutation",
        "return_override",
        "commands",
        "permissions",
        "persistence",
        "public_sdk",
        "runtime_readiness",
    )
)
REQUIRED_FORBIDDEN_CAPABILITY_CLAIMS = frozenset(
    (
        "lookup",
        "mutation",
        "return_override",
        "commands",
        "permissions",
    )
)

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

FORBIDDEN_PUBLIC_IDENTITY_RE = re.compile(
    r"\b("
    r"steam(?:id)?|"
    r"eos(?:id)?|"
    r"unique[_ -]?net[_ -]?id|"
    r"net[_ -]?id|"
    r"player[_ -]?(?:id|data[_ -]?id)|"
    r"account[_ -]?id|"
    r"player[_ -]?name|"
    r"character[_ -]?name|"
    r"display[_ -]?name|"
    r"ip(?:v4|v6)?(?:[_ -]?address)?|"
    r"tribe[_ -]?id|"
    r"resourcehandle|"
    r"gobjects?(?:[_ -]?index)?|"
    r"fnames?|"
    r"fname[_ -]?(?:index|id)?|"
    r"gobject[_ -]?(?:index|id)?|"
    r"uobject(?:[_ -]?pointer)?|"
    r"ue[_ -]?pointer|"
    r"raw[_ -]?pointer|"
    r"object[_ -]?address|"
    r"pointer[_ -]?identity"
    r")\b",
    re.IGNORECASE,
)
FORBIDDEN_CAPABILITY_CLAIM_RE = re.compile(
    r"\b("
    r"lookup|"
    r"mutation|"
    r"mutate|"
    r"return[_ -]?override|"
    r"override[_ -]?return|"
    r"commands?|"
    r"permissions?|"
    r"admin(?:istration)?|"
    r"moderation|"
    r"kick|"
    r"ban"
    r")\b",
    re.IGNORECASE,
)

NEGATIVE_CONTEXT_TOKENS = (
    "blocker",
    "deny",
    "excluded",
    "forbid",
    "forbidden",
    "forbids",
    "negative",
    "non_claim",
    "reject",
    "rejected",
    "safety",
)
PERMITTED_POSITIVE_TRAIL_TOKENS = (
    "invalidation_cases",
)


@dataclass
class Validation:
    blockers: list[dict[str, Any]]
    principal_fields: list[str]
    invalidation_cases: list[str]
    negative_rules: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Principal/invalidation candidate manifest to validate.")
    parser.add_argument("--json", action="store_true", help="Emit a JSON report.")
    parser.add_argument("--promote", action="store_true", help="Check promote readiness; candidate-only artifacts fail closed.")
    parser.add_argument(
        "--public-readiness",
        action="store_true",
        help="Check public SDK readiness; candidate-only artifacts fail closed.",
    )
    parser.add_argument(
        "--runtime-readiness",
        action="store_true",
        help="Check runtime readiness; candidate-only artifacts fail closed.",
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


def is_permitted_positive_context(trail: str) -> bool:
    lowered = trail.casefold()
    return any(token in lowered for token in PERMITTED_POSITIVE_TRAIL_TOKENS)


def find_forbidden_coordinate(value: Any, trail: str = "$") -> tuple[str, str] | None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if key in FORBIDDEN_COORDINATE_KEYS:
                return key, child_trail
            found = find_forbidden_coordinate(child, child_trail)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = find_forbidden_coordinate(child, f"{trail}[{index}]")
            if found is not None:
                return found
    return None


def find_forbidden_public_identity(value: Any, trail: str = "$") -> tuple[str, str] | None:
    if is_negative_context(trail):
        return None
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if key in FORBIDDEN_COORDINATE_KEYS:
                return key, child_trail
            if FORBIDDEN_PUBLIC_IDENTITY_RE.search(str(key)) and key not in {"privacy_class"}:
                return str(key), child_trail
            found = find_forbidden_public_identity(child, child_trail)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = find_forbidden_public_identity(child, f"{trail}[{index}]")
            if found is not None:
                return found
    elif isinstance(value, str) and FORBIDDEN_PUBLIC_IDENTITY_RE.search(value):
        return value, trail
    return None


def find_forbidden_positive_claim(value: Any, trail: str = "$") -> tuple[str, str] | None:
    if is_negative_context(trail) or is_permitted_positive_context(trail):
        return None
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if FORBIDDEN_CAPABILITY_CLAIM_RE.search(str(key)):
                return str(key), child_trail
            found = find_forbidden_positive_claim(child, child_trail)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = find_forbidden_positive_claim(child, f"{trail}[{index}]")
            if found is not None:
                return found
    elif isinstance(value, str) and FORBIDDEN_CAPABILITY_CLAIM_RE.search(value):
        return value, trail
    return None


def validate_principal(principal: Any, blockers: list[dict[str, Any]]) -> list[str]:
    if not isinstance(principal, dict):
        add(blockers, "principal_missing", "$.principal")
        return []
    if principal.get("kind") != "copied_opaque_principal":
        add(blockers, "principal_kind_not_copied_opaque", "$.principal.kind")
    if principal.get("copied") is not True:
        add(blockers, "principal_not_declared_copied", "$.principal.copied")
    if principal.get("ownership") != "obelisk_owned_copy":
        add(blockers, "principal_ownership_not_obelisk_copy", "$.principal.ownership")
    if principal.get("public_identity") not in {"opaque_principal", "opaque_principal_only"}:
        add(blockers, "principal_public_identity_not_opaque", "$.principal.public_identity")
    if principal.get("reversible") is not False:
        add(blockers, "principal_reversible_not_false", "$.principal.reversible")
    if principal.get("stable_across_processes") is not False:
        add(blockers, "principal_cross_process_overclaim", "$.principal.stable_across_processes")
    if principal.get("real_identity_source") is not None:
        add(blockers, "principal_real_identity_source_overclaim", "$.principal.real_identity_source")

    fields = principal.get("fields")
    if not isinstance(fields, list):
        add(blockers, "principal_fields_not_list", "$.principal.fields")
        return []
    field_names: list[str] = []
    for index, field in enumerate(fields):
        label = f"$.principal.fields[{index}]"
        if not isinstance(field, dict):
            add(blockers, "principal_field_invalid", label)
            continue
        name = field.get("name")
        if not isinstance(name, str) or not name:
            add(blockers, "principal_field_name_missing", f"{label}.name")
            continue
        field_names.append(name)
        if name not in REQUIRED_PRINCIPAL_FIELD_NAMES:
            add(blockers, "principal_field_unexpected", f"{label}.name", field=name)
        if field.get("copied") is not True:
            add(blockers, "principal_field_not_copied", f"{label}.copied", field=name)
        if field.get("source") != "obelisk_owned_copy":
            add(blockers, "principal_field_source_not_obelisk_copy", f"{label}.source", field=name)
        if field.get("consumer_visible") is not True:
            add(blockers, "principal_field_not_consumer_visible_candidate", f"{label}.consumer_visible", field=name)
        privacy_class = field.get("privacy_class")
        if not isinstance(privacy_class, str) or not privacy_class:
            add(blockers, "principal_field_privacy_class_missing", f"{label}.privacy_class", field=name)
        if name == "principal" and field.get("type") not in {"opaque_bytes", "uint128_opaque", "opaque_token"}:
            add(blockers, "principal_field_type_not_opaque", f"{label}.type", field=name)
        if name == "generation" and field.get("type") not in {"uint64", "uint32"}:
            add(blockers, "generation_field_type_invalid", f"{label}.type")
        if name == "state" and field.get("type") != "enum":
            add(blockers, "state_field_type_invalid", f"{label}.type")
        if name == "scope_flags" and field.get("type") not in {"uint64_flags", "uint32_flags"}:
            add(blockers, "scope_flags_field_type_invalid", f"{label}.type")
        if name == "privacy_class" and field.get("type") != "enum":
            add(blockers, "privacy_class_field_type_invalid", f"{label}.type")
    missing = REQUIRED_PRINCIPAL_FIELD_NAMES - set(field_names)
    if missing:
        add(blockers, "principal_fields_missing_required", "$.principal.fields", missing=sorted(missing))
    return sorted(field_names)


def validate_generation(generation: Any, blockers: list[dict[str, Any]]) -> None:
    if not isinstance(generation, dict):
        add(blockers, "generation_policy_missing", "$.generation")
        return
    if generation.get("field") != "generation":
        add(blockers, "generation_field_mismatch", "$.generation.field")
    if generation.get("zero_invalid") is not True:
        add(blockers, "generation_zero_invalid_missing", "$.generation.zero_invalid")
    increments = generation.get("increments_on")
    required = {
        "session_start",
        "logout_or_disconnect_invalidation",
        "reconnect_after_invalidation",
        "transfer_or_download_edge",
        "duplicate_or_conflicting_identity",
        "server_restart",
        "plugin_reload",
    }
    if not isinstance(increments, list) or not required.issubset(set(increments)):
        add(blockers, "generation_increments_missing_required_cases", "$.generation.increments_on")


def validate_state(state: Any, blockers: list[dict[str, Any]]) -> None:
    if not isinstance(state, dict):
        add(blockers, "state_policy_missing", "$.state")
        return
    if state.get("field") != "state":
        add(blockers, "state_field_mismatch", "$.state.field")
    allowed = state.get("allowed")
    if not isinstance(allowed, list) or not {"unknown", "active", "invalidated"}.issubset(set(allowed)):
        add(blockers, "state_allowed_values_missing_required", "$.state.allowed")
    fail_closed = state.get("fail_closed_states")
    if not isinstance(fail_closed, list) or not {"unknown", "invalidated"}.issubset(set(fail_closed)):
        add(blockers, "state_fail_closed_states_missing_required", "$.state.fail_closed_states")


def validate_scope_flags(scope_flags: Any, blockers: list[dict[str, Any]]) -> None:
    if not isinstance(scope_flags, dict):
        add(blockers, "scope_flags_policy_missing", "$.scope_flags")
        return
    if scope_flags.get("field") != "scope_flags":
        add(blockers, "scope_flags_field_mismatch", "$.scope_flags.field")
    required_allowed = {"process_local", "session_local", "not_cross_cluster"}
    allowed = scope_flags.get("allowed_flags")
    if not isinstance(allowed, list) or not required_allowed.issubset(set(allowed)):
        add(blockers, "scope_flags_allowed_missing_required", "$.scope_flags.allowed_flags")
    forbidden = scope_flags.get("forbidden_flags")
    required_forbidden = {"persistent", "cross_process", "cross_cluster"}
    if not isinstance(forbidden, list) or not required_forbidden.issubset(set(forbidden)):
        add(blockers, "scope_flags_forbidden_missing_required", "$.scope_flags.forbidden_flags")


def validate_privacy_class(privacy_class: Any, blockers: list[dict[str, Any]]) -> None:
    if not isinstance(privacy_class, dict):
        add(blockers, "privacy_class_policy_missing", "$.privacy_class")
        return
    if privacy_class.get("field") != "privacy_class":
        add(blockers, "privacy_class_field_mismatch", "$.privacy_class.field")
    allowed = privacy_class.get("allowed")
    if not isinstance(allowed, list) or "opaque_principal" not in set(allowed):
        add(blockers, "privacy_class_allowed_missing_opaque", "$.privacy_class.allowed")
    if privacy_class.get("public_value") != "opaque_principal":
        add(blockers, "privacy_class_public_value_not_opaque", "$.privacy_class.public_value")


def validate_invalidation_cases(cases: Any, blockers: list[dict[str, Any]]) -> list[str]:
    if not isinstance(cases, list):
        add(blockers, "invalidation_cases_not_list", "$.invalidation_cases")
        return []
    seen: list[str] = []
    for index, case in enumerate(cases):
        label = f"$.invalidation_cases[{index}]"
        if not isinstance(case, dict):
            add(blockers, "invalidation_case_invalid", label)
            continue
        name = case.get("case")
        if not isinstance(name, str) or not name:
            add(blockers, "invalidation_case_name_missing", f"{label}.case")
            continue
        seen.append(name)
        if name not in REQUIRED_INVALIDATION_CASES:
            add(blockers, "invalidation_case_unexpected", f"{label}.case", case=name)
        if case.get("fail_closed") is not True:
            add(blockers, "invalidation_case_not_fail_closed", f"{label}.fail_closed", case=name)
        if case.get("consumer_result") not in {"deny", "invalidate", "ignore_and_deny"}:
            add(blockers, "invalidation_case_consumer_result_not_denied", f"{label}.consumer_result", case=name)
        if not isinstance(case.get("generation_action"), str) or not case["generation_action"]:
            add(blockers, "invalidation_case_generation_action_missing", f"{label}.generation_action", case=name)
        if not isinstance(case.get("trigger"), str) or not case["trigger"]:
            add(blockers, "invalidation_case_trigger_missing", f"{label}.trigger", case=name)
    missing = REQUIRED_INVALIDATION_CASES - set(seen)
    if missing:
        add(blockers, "invalidation_cases_missing_required", "$.invalidation_cases", missing=sorted(missing))
    return sorted(seen)


def validate_negative_consumer_rules(rules: Any, blockers: list[dict[str, Any]]) -> list[str]:
    if not isinstance(rules, list):
        add(blockers, "negative_consumer_rules_not_list", "$.negative_consumer_rules")
        return []
    seen: list[str] = []
    forbidden_terms: set[str] = set()
    for index, rule in enumerate(rules):
        label = f"$.negative_consumer_rules[{index}]"
        if not isinstance(rule, dict):
            add(blockers, "negative_consumer_rule_invalid", label)
            continue
        name = rule.get("rule")
        if not isinstance(name, str) or not name:
            add(blockers, "negative_consumer_rule_name_missing", f"{label}.rule")
            continue
        seen.append(name)
        if name not in REQUIRED_NEGATIVE_RULES:
            add(blockers, "negative_consumer_rule_unexpected", f"{label}.rule", rule=name)
        if rule.get("fail_closed") is not True:
            add(blockers, "negative_consumer_rule_not_fail_closed", f"{label}.fail_closed", rule=name)
        forbids = rule.get("forbids")
        if not isinstance(forbids, list) or not all(isinstance(item, str) and item for item in forbids):
            add(blockers, "negative_consumer_rule_forbids_invalid", f"{label}.forbids", rule=name)
        else:
            forbidden_terms.update(forbids)
    missing = REQUIRED_NEGATIVE_RULES - set(seen)
    if missing:
        add(blockers, "negative_consumer_rules_missing_required", "$.negative_consumer_rules", missing=sorted(missing))
    missing_forbidden = REQUIRED_REJECTED_PUBLIC_IDENTITY_SOURCES - forbidden_terms
    if missing_forbidden:
        add(
            blockers,
            "negative_consumer_rules_missing_forbidden_identity_sources",
            "$.negative_consumer_rules",
            missing=sorted(missing_forbidden),
        )
    missing_capability_claims = REQUIRED_FORBIDDEN_CAPABILITY_CLAIMS - forbidden_terms
    if missing_capability_claims:
        add(
            blockers,
            "negative_consumer_rules_missing_forbidden_capability_claims",
            "$.negative_consumer_rules",
            missing=sorted(missing_capability_claims),
        )
    return sorted(seen)


def validate_evidence_policy(policy: Any, blockers: list[dict[str, Any]]) -> None:
    if not isinstance(policy, dict):
        add(blockers, "evidence_policy_missing", "$.evidence_policy")
        return
    if policy.get("accepted_evidence_class") != "candidate_policy_only":
        add(blockers, "evidence_policy_not_candidate_policy_only", "$.evidence_policy.accepted_evidence_class")
    if policy.get("malformed_evidence_result") != "deny":
        add(blockers, "evidence_policy_malformed_not_denied", "$.evidence_policy.malformed_evidence_result")
    if policy.get("unsupported_evidence_result") != "deny":
        add(blockers, "evidence_policy_unsupported_not_denied", "$.evidence_policy.unsupported_evidence_result")
    if policy.get("fail_closed") is not True:
        add(blockers, "evidence_policy_not_fail_closed", "$.evidence_policy.fail_closed")


def validate_runtime_evidence(evidence: Any, blockers: list[dict[str, Any]]) -> None:
    if not isinstance(evidence, dict):
        add(blockers, "runtime_evidence_missing", "$.runtime_evidence")
        return
    if evidence.get("approved") is not False:
        add(blockers, "runtime_evidence_approval_not_supported_by_candidate_checker", "$.runtime_evidence.approved")
    if evidence.get("status") not in {"missing", "not_approved", "candidate_only"}:
        add(blockers, "runtime_evidence_status_not_fail_closed", "$.runtime_evidence.status")
    required_for = evidence.get("required_for")
    expected = {"promote", "public_readiness", "runtime_readiness"}
    if not isinstance(required_for, list) or not expected.issubset(set(required_for)):
        add(blockers, "runtime_evidence_required_for_missing_readiness_modes", "$.runtime_evidence.required_for")


def validate_lifecycle_layout_source(source: Any, blockers: list[dict[str, Any]]) -> None:
    if not isinstance(source, dict):
        add(blockers, "lifecycle_layout_source_missing", "$.lifecycle_layout_source")
        return
    unexpected_keys = set(source) - ALLOWED_LIFECYCLE_LAYOUT_SOURCE_KEYS
    if unexpected_keys:
        add(
            blockers,
            "lifecycle_layout_source_fields_unexpected",
            "$.lifecycle_layout_source",
            unexpected=sorted(unexpected_keys),
        )
    if source.get("status") != "candidate_layout_consumable":
        add(blockers, "lifecycle_layout_source_status_not_candidate", "$.lifecycle_layout_source.status")
    if source.get("accepted_layout_only") is not True:
        add(blockers, "lifecycle_layout_source_not_layout_only", "$.lifecycle_layout_source.accepted_layout_only")
    if source.get("principal_invalidation_evidence") != "candidate_policy_only":
        add(
            blockers,
            "lifecycle_layout_source_principal_invalidation_overclaim",
            "$.lifecycle_layout_source.principal_invalidation_evidence",
        )


def validate_manifest(payload: dict[str, Any], *, check_mode: str) -> Validation:
    blockers: list[dict[str, Any]] = []
    if payload.get("schema") != SCHEMA:
        add(blockers, "schema_mismatch", "$.schema")
        return Validation(blockers, [], [], [])
    keys = set(payload)
    missing_keys = REQUIRED_TOP_LEVEL_KEYS - keys
    unexpected_keys = keys - REQUIRED_TOP_LEVEL_KEYS
    if missing_keys:
        add(blockers, "top_level_fields_missing_required", "$", missing=sorted(missing_keys))
    if unexpected_keys:
        add(blockers, "top_level_fields_unexpected", "$", unexpected=sorted(unexpected_keys))
    if payload.get("artifact_status") != "candidate_only":
        add(blockers, "status_not_candidate_only", "$.artifact_status")
    if payload.get("readiness_classification") != "planning_only":
        add(blockers, "readiness_classification_not_planning_only", "$.readiness_classification")
    for key in ("promotion_ready", "public_sdk_ready", "runtime_ready"):
        if payload.get(key) is not False:
            add(blockers, f"{key}_not_false", f"$.{key}")

    validate_lifecycle_layout_source(payload.get("lifecycle_layout_source"), blockers)
    principal_fields = validate_principal(payload.get("principal"), blockers)
    validate_generation(payload.get("generation"), blockers)
    validate_state(payload.get("state"), blockers)
    validate_scope_flags(payload.get("scope_flags"), blockers)
    validate_privacy_class(payload.get("privacy_class"), blockers)
    invalidation_cases = validate_invalidation_cases(payload.get("invalidation_cases"), blockers)
    negative_rules = validate_negative_consumer_rules(payload.get("negative_consumer_rules"), blockers)
    validate_evidence_policy(payload.get("evidence_policy"), blockers)
    validate_runtime_evidence(payload.get("runtime_evidence"), blockers)

    rejected = payload.get("rejected_public_identity_sources")
    if not isinstance(rejected, list) or not REQUIRED_REJECTED_PUBLIC_IDENTITY_SOURCES.issubset(set(rejected)):
        add(blockers, "rejected_public_identity_sources_missing_required", "$.rejected_public_identity_sources")

    promotion_gate = payload.get("promotion_gate")
    if not isinstance(promotion_gate, dict):
        add(blockers, "promotion_gate_missing", "$.promotion_gate")
    else:
        for key in ("ready", "promotion_ready", "public_sdk_ready", "runtime_ready"):
            if promotion_gate.get(key) is not False:
                add(blockers, f"promotion_gate_{key}_not_false", f"$.promotion_gate.{key}")
        blockers_value = promotion_gate.get("blockers")
        required_blockers = {"approved_runtime_evidence_missing", "principal_invalidation_semantics_unresolved"}
        if not isinstance(blockers_value, list) or not required_blockers.issubset(set(blockers_value)):
            add(blockers, "promotion_gate_missing_runtime_evidence_blocker", "$.promotion_gate.blockers")

    safety = payload.get("safety_summary")
    if not isinstance(safety, dict):
        add(blockers, "safety_summary_missing", "$.safety_summary")
    else:
        for key in ("promotion_ready", "public_sdk_ready", "runtime_ready"):
            if safety.get(key) is not False:
                add(blockers, f"safety_{key}_not_false", f"$.safety_summary.{key}")
        exclusions = safety.get("explicitly_excluded")
        if not isinstance(exclusions, list) or not REQUIRED_EXCLUSIONS.issubset(set(exclusions)):
            add(blockers, "safety_exclusions_missing_required", "$.safety_summary.explicitly_excluded")

    non_claims = payload.get("non_claims")
    if not isinstance(non_claims, list) or not REQUIRED_NON_CLAIMS.issubset(set(non_claims)):
        add(blockers, "non_claims_missing_required", "$.non_claims")

    coordinate = find_forbidden_coordinate(payload)
    if coordinate is not None:
        field, trail = coordinate
        add(blockers, "ue_coordinate_or_pointer_leakage", trail, field=field)
    forbidden = find_forbidden_public_identity(payload)
    if forbidden is not None:
        value, trail = forbidden
        add(blockers, "forbidden_public_identity_source", trail, value=value)
    claim = find_forbidden_positive_claim(payload)
    if claim is not None:
        value, trail = claim
        add(blockers, "forbidden_public_capability_claim", trail, value=value)

    if check_mode != "consume":
        add(
            blockers,
            f"{check_mode}_blocked_principal_invalidation_semantics_unresolved",
            "$.runtime_evidence",
        )
        add(
            blockers,
            f"{check_mode}_blocked_without_approved_runtime_evidence",
            "$.runtime_evidence",
        )
        add(
            blockers,
            "candidate_only_principal_invalidation_policy_not_readiness_evidence",
            "$",
        )

    return Validation(blockers, principal_fields, invalidation_cases, negative_rules)


def build_report(payload: dict[str, Any], validation: Validation, *, check_mode: str) -> dict[str, Any]:
    return {
        "schema": REPORT_SCHEMA,
        "input_schema": payload.get("schema"),
        "mode": check_mode,
        "ready": not validation.blockers,
        "candidate_only": payload.get("artifact_status") == "candidate_only",
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "principal_invalidation_ready": False,
        "remaining_blockers": ["principal_invalidation_semantics_unresolved"],
        "principal_fields": validation.principal_fields,
        "invalidation_cases": validation.invalidation_cases,
        "negative_consumer_rules": validation.negative_rules,
        "blockers": [blocker["reason"] for blocker in validation.blockers],
        "blocker_details": validation.blockers,
    }


def main() -> int:
    args = parse_args()
    check_mode = mode(args)
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
