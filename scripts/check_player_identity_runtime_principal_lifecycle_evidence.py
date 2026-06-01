#!/usr/bin/env python3
"""Validate shape-only runtime principal lifecycle evidence fixtures.

This checker intentionally accepts only synthetic/redacted private fixtures. It is a
format guard for a future reviewed evidence manifest, not approval of runtime evidence.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


SCHEMA = "obelisk.players-identity-runtime-principal-lifecycle-evidence.v1"
REPORT_SCHEMA = "obelisk.players-identity-runtime-principal-lifecycle-evidence-check.v1"

REQUIRED_CASES = frozenset(
    (
        "session_start_anchor",
        "session_start_rejected_anchor",
        "session_end_anchor",
        "stale_after_logout",
        "malformed_or_unsupported_evidence",
    )
)
REQUIRED_CASE_SEQUENCE = (
    "session_start_anchor",
    "session_start_rejected_anchor",
    "session_end_anchor",
    "stale_after_logout",
    "malformed_or_unsupported_evidence",
)
REQUIRED_TARGETS = {
    "session_start_anchor": "ShooterGameMode.HandleNewPlayer",
    "session_start_rejected_anchor": "ShooterGameMode.HandleNewPlayer",
    "session_end_anchor": "ShooterGameMode.OnLogout",
    "stale_after_logout": "post_logout_consumer_check",
    "malformed_or_unsupported_evidence": "principal_consumer_boundary",
}
REQUIRED_COPIED_FIELDS = {
    "session_start_anchor": ("bIsFromLogin", "ReturnValue"),
    "session_start_rejected_anchor": ("bIsFromLogin", "ReturnValue"),
    "session_end_anchor": (),
    "stale_after_logout": ("generation_state",),
    "malformed_or_unsupported_evidence": (),
}
REQUIRED_COPIED_BOOL_FIELDS = {
    "session_start_anchor": ("bIsFromLogin", "ReturnValue"),
    "session_start_rejected_anchor": ("bIsFromLogin", "ReturnValue"),
    "session_end_anchor": (),
    "stale_after_logout": (),
    "malformed_or_unsupported_evidence": (),
}
REQUIRED_COPIED_BOOL_VALUES = {
    "session_start_anchor": ("1", "1"),
    "session_start_rejected_anchor": ("0", "1"),
    "session_end_anchor": (),
    "stale_after_logout": (),
    "malformed_or_unsupported_evidence": (),
}
REQUIRED_OBSERVATION_REDACTIONS = {
    "session_start_anchor": ("NewPlayer", "PlayerData", "PlayerCharacter"),
    "session_start_rejected_anchor": ("NewPlayer", "PlayerData", "PlayerCharacter"),
    "session_end_anchor": ("Exiting",),
    "stale_after_logout": (),
    "malformed_or_unsupported_evidence": (),
}
REQUIRED_POST_ORIGINAL = {
    "session_start_anchor": True,
    "session_start_rejected_anchor": True,
    "session_end_anchor": True,
    "stale_after_logout": False,
    "malformed_or_unsupported_evidence": False,
}
REQUIRED_ROLE = {
    "session_start_anchor": "session_start",
    "session_start_rejected_anchor": "session_start_rejected",
    "session_end_anchor": "session_end",
    "stale_after_logout": "none",
    "malformed_or_unsupported_evidence": "none",
}
REQUIRED_PRINCIPAL_ACTION = {
    "session_start_anchor": "candidate_created",
    "session_start_rejected_anchor": "none",
    "session_end_anchor": "candidate_invalidated",
    "stale_after_logout": "none",
    "malformed_or_unsupported_evidence": "none",
}
REQUIRED_REDACTED_FIELDS = frozenset(
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
        "raw_params",
    )
)
REQUIRED_NON_CLAIMS = frozenset(
    (
        "synthetic/redacted shape fixture only",
        "does not approve runtime evidence or server observations",
        "does not expose real player identifiers, names, IPs, tribe ids, UE pointers, FNames, GObjects, raw params, lookup, ResourceHandle, mutation, or return override",
        "does not promote public SDK, permissions, commands, moderation, or admin authority",
    )
)
REQUIRED_TOP_LEVEL_KEYS = frozenset(
    (
        "schema",
        "artifact_status",
        "readiness_classification",
        "synthetic_fixture",
        "private_manifest",
        "redacted",
        "promotion_ready",
        "public_sdk_ready",
        "runtime_ready",
        "approval",
        "observations",
        "privacy_boundary",
        "promotion_gate",
        "non_claims",
    )
)
FORBIDDEN_COORDINATE_KEYS = frozenset(
    (
        "address",
        "function_address",
        "gobject_index",
        "gobjects_index",
        "core_path",
        "dump_path",
        "live_log_path",
        "name_index",
        "fname_index",
        "object_address",
        "object_index",
        "raw_log_path",
        "raw_param_address",
        "raw_trace_path",
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
    r"player[_ -]?(?:id|data[_ -]?id|name)|"
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
    r"raw[_ -]?(?:logs?|traces?|payloads?|params?|pointer)|"
    r"live[_ -]?logs?|"
    r"dump[_ -]?path|"
    r"core[_ -]?path|"
    r"object[_ -]?address"
    r")\b",
    re.IGNORECASE,
)
NEGATIVE_CONTEXT_TOKENS = (
    "blocker",
    "deny",
    "excluded",
    "forbid",
    "forbidden",
    "non_claim",
    "privacy_boundary",
    "redacted",
    "reject",
    "rejected",
)


@dataclass
class Validation:
    blockers: list[dict[str, Any]]
    observed_cases: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, nargs="?", help="Synthetic/redacted runtime evidence shape manifest.")
    parser.add_argument("--json", action="store_true", help="Emit a JSON report.")
    parser.add_argument(
        "--emit-template",
        type=Path,
        help="Write the canonical synthetic/redacted shape fixture template and exit.",
    )
    parser.add_argument("--promote", action="store_true", help="Fail closed for promotion checks.")
    parser.add_argument("--public-readiness", action="store_true", help="Fail closed for public SDK readiness checks.")
    parser.add_argument("--runtime-readiness", action="store_true", help="Fail closed for runtime readiness checks.")
    return parser.parse_args()


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
    approval_gates = [
        "server access or player-facing evidence windows",
        "debug attachment, ptrace, gcore, or runtime scanners",
        "server starts, stops, restarts, or marker changes",
        "Discord/community/beta-test notices",
        "GitHub publication, tags, pushes, or release claims",
    ]
    observations = []
    for case in REQUIRED_CASE_SEQUENCE:
        observations.append(
            {
                "case": case,
                "target": REQUIRED_TARGETS[case],
                "synthetic": True,
                "redacted": True,
                "runtime_observed": False,
                "result": "shape_only",
                "consumer_result": "deny_or_invalidate_only",
                "copied_fields": list(REQUIRED_COPIED_FIELDS[case]),
                "copied_bool_fields": list(REQUIRED_COPIED_BOOL_FIELDS[case]),
                "copied_bool_values": list(REQUIRED_COPIED_BOOL_VALUES[case]),
                "redacted_count": len(REQUIRED_OBSERVATION_REDACTIONS[case]),
                "redacted_fields": list(REQUIRED_OBSERVATION_REDACTIONS[case]),
                "post_original": REQUIRED_POST_ORIGINAL[case],
                "role": REQUIRED_ROLE[case],
                "principal_action": REQUIRED_PRINCIPAL_ACTION[case],
                "delivery_claim": "none",
                "raw_payload_retained": False,
            }
        )
    return {
        "schema": SCHEMA,
        "artifact_status": "synthetic_redacted_fixture",
        "readiness_classification": "shape_only_private_fixture",
        "synthetic_fixture": True,
        "private_manifest": True,
        "redacted": True,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "approval": {
            "approved_runtime_evidence_present": False,
            "runtime_work_authorized_by_this_manifest": False,
            "server_operations_authorized_by_this_manifest": False,
            "publication_authorized_by_this_manifest": False,
            "separate_operator_approval_required_before": approval_gates,
        },
        "observations": observations,
        "privacy_boundary": {
            "copied_opaque_principal_only": True,
            "redacted_fields": sorted(REQUIRED_REDACTED_FIELDS),
            "lookup_allowed": False,
            "resource_handle_allowed": False,
            "mutation_allowed": False,
            "return_override_allowed": False,
        },
        "promotion_gate": {
            "ready": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "blockers": [
                "approved_runtime_evidence_missing",
                "synthetic_shape_fixture_not_runtime_evidence",
            ],
        },
        "non_claims": sorted(REQUIRED_NON_CLAIMS),
    }


def is_negative_context(trail: str) -> bool:
    lowered = trail.casefold()
    return any(token in lowered for token in NEGATIVE_CONTEXT_TOKENS)


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
            if FORBIDDEN_PUBLIC_IDENTITY_RE.search(str(key)):
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


def validate_approval(approval: Any, blockers: list[dict[str, Any]]) -> None:
    if not isinstance(approval, dict):
        add(blockers, "approval_missing", "$.approval")
        return
    for key in (
        "approved_runtime_evidence_present",
        "runtime_work_authorized_by_this_manifest",
        "server_operations_authorized_by_this_manifest",
        "publication_authorized_by_this_manifest",
    ):
        if approval.get(key) is not False:
            add(blockers, f"{key}_not_false", f"$.approval.{key}")
    required = {
        "server access or player-facing evidence windows",
        "debug attachment, ptrace, gcore, or runtime scanners",
        "server starts, stops, restarts, or marker changes",
        "Discord/community/beta-test notices",
        "GitHub publication, tags, pushes, or release claims",
    }
    separate = approval.get("separate_operator_approval_required_before")
    if not isinstance(separate, list) or not required.issubset(set(separate)):
        add(blockers, "approval_missing_required_separate_operator_gates", "$.approval.separate_operator_approval_required_before")


def validate_observations(observations: Any, blockers: list[dict[str, Any]]) -> list[str]:
    if not isinstance(observations, list):
        add(blockers, "observations_not_list", "$.observations")
        return []
    seen: list[str] = []
    for index, observation in enumerate(observations):
        label = f"$.observations[{index}]"
        if not isinstance(observation, dict):
            add(blockers, "observation_invalid", label)
            continue
        case = observation.get("case")
        if not isinstance(case, str) or not case:
            add(blockers, "observation_case_missing", f"{label}.case")
            continue
        seen.append(case)
        if case not in REQUIRED_CASES:
            add(blockers, "observation_case_unexpected", f"{label}.case", case=case)
        if observation.get("target") != REQUIRED_TARGETS.get(case):
            add(blockers, "observation_target_mismatch", f"{label}.target", case=case)
        if observation.get("synthetic") is not True:
            add(blockers, "observation_not_synthetic", f"{label}.synthetic", case=case)
        if observation.get("redacted") is not True:
            add(blockers, "observation_not_redacted", f"{label}.redacted", case=case)
        if observation.get("runtime_observed") is not False:
            add(blockers, "observation_runtime_observed_overclaim", f"{label}.runtime_observed", case=case)
        if observation.get("result") != "shape_only":
            add(blockers, "observation_result_not_shape_only", f"{label}.result", case=case)
        if observation.get("consumer_result") != "deny_or_invalidate_only":
            add(blockers, "observation_consumer_result_not_fail_closed", f"{label}.consumer_result", case=case)
        copied_fields = observation.get("copied_fields")
        if not isinstance(copied_fields, list):
            add(blockers, "observation_copied_fields_not_list", f"{label}.copied_fields", case=case)
        elif tuple(copied_fields) != REQUIRED_COPIED_FIELDS.get(case, ()):
            add(
                blockers,
                "observation_copied_fields_mismatch",
                f"{label}.copied_fields",
                case=case,
                expected=list(REQUIRED_COPIED_FIELDS.get(case, ())),
            )
        copied_bool_fields = observation.get("copied_bool_fields")
        if not isinstance(copied_bool_fields, list):
            add(blockers, "observation_copied_bool_fields_not_list", f"{label}.copied_bool_fields", case=case)
        elif tuple(copied_bool_fields) != REQUIRED_COPIED_BOOL_FIELDS.get(case, ()):
            add(
                blockers,
                "observation_copied_bool_fields_mismatch",
                f"{label}.copied_bool_fields",
                case=case,
                expected=list(REQUIRED_COPIED_BOOL_FIELDS.get(case, ())),
            )
        copied_bool_values = observation.get("copied_bool_values")
        if not isinstance(copied_bool_values, list):
            add(blockers, "observation_copied_bool_values_not_list", f"{label}.copied_bool_values", case=case)
        elif tuple(copied_bool_values) != REQUIRED_COPIED_BOOL_VALUES.get(case, ()):
            add(
                blockers,
                "observation_copied_bool_values_mismatch",
                f"{label}.copied_bool_values",
                case=case,
                expected=list(REQUIRED_COPIED_BOOL_VALUES.get(case, ())),
            )
        redacted_fields = observation.get("redacted_fields")
        expected_redacted_fields = REQUIRED_OBSERVATION_REDACTIONS.get(case, ())
        if not isinstance(redacted_fields, list):
            add(blockers, "observation_redacted_fields_not_list", f"{label}.redacted_fields", case=case)
        elif tuple(redacted_fields) != expected_redacted_fields:
            add(
                blockers,
                "observation_redacted_fields_mismatch",
                f"{label}.redacted_fields",
                case=case,
                expected=list(expected_redacted_fields),
            )
        if observation.get("redacted_count") != len(expected_redacted_fields):
            add(
                blockers,
                "observation_redacted_count_mismatch",
                f"{label}.redacted_count",
                case=case,
                expected=len(expected_redacted_fields),
            )
        if observation.get("post_original") is not REQUIRED_POST_ORIGINAL.get(case):
            add(
                blockers,
                "observation_post_original_mismatch",
                f"{label}.post_original",
                case=case,
                expected=REQUIRED_POST_ORIGINAL.get(case),
            )
        if observation.get("role") != REQUIRED_ROLE.get(case):
            add(
                blockers,
                "observation_role_mismatch",
                f"{label}.role",
                case=case,
                expected=REQUIRED_ROLE.get(case),
            )
        if observation.get("principal_action") != REQUIRED_PRINCIPAL_ACTION.get(case):
            add(
                blockers,
                "observation_principal_action_mismatch",
                f"{label}.principal_action",
                case=case,
                expected=REQUIRED_PRINCIPAL_ACTION.get(case),
            )
        if observation.get("delivery_claim") != "none":
            add(blockers, "observation_delivery_claim_not_none", f"{label}.delivery_claim", case=case)
        if observation.get("raw_payload_retained") is not False:
            add(blockers, "observation_raw_payload_retained", f"{label}.raw_payload_retained", case=case)
    missing = REQUIRED_CASES - set(seen)
    if missing:
        add(blockers, "observations_missing_required_cases", "$.observations", missing=sorted(missing))
    duplicates = sorted(case for case in set(seen) if seen.count(case) > 1)
    if duplicates:
        add(blockers, "observations_duplicate_cases", "$.observations", duplicates=duplicates)
    if tuple(seen) != REQUIRED_CASE_SEQUENCE:
        add(
            blockers,
            "observations_sequence_mismatch",
            "$.observations",
            expected=list(REQUIRED_CASE_SEQUENCE),
            observed=seen,
        )
    return sorted(seen)


def validate_privacy_boundary(boundary: Any, blockers: list[dict[str, Any]]) -> None:
    if not isinstance(boundary, dict):
        add(blockers, "privacy_boundary_missing", "$.privacy_boundary")
        return
    if boundary.get("copied_opaque_principal_only") is not True:
        add(blockers, "privacy_boundary_not_opaque_principal_only", "$.privacy_boundary.copied_opaque_principal_only")
    redacted = boundary.get("redacted_fields")
    if not isinstance(redacted, list) or not REQUIRED_REDACTED_FIELDS.issubset(set(redacted)):
        add(blockers, "privacy_boundary_missing_required_redactions", "$.privacy_boundary.redacted_fields")
    for key in ("lookup_allowed", "resource_handle_allowed", "mutation_allowed", "return_override_allowed"):
        if boundary.get(key) is not False:
            add(blockers, f"privacy_boundary_{key}_not_false", f"$.privacy_boundary.{key}")


def validate_promotion_gate(gate: Any, blockers: list[dict[str, Any]]) -> None:
    if not isinstance(gate, dict):
        add(blockers, "promotion_gate_missing", "$.promotion_gate")
        return
    for key in ("ready", "promotion_ready", "public_sdk_ready", "runtime_ready"):
        if gate.get(key) is not False:
            add(blockers, f"promotion_gate_{key}_not_false", f"$.promotion_gate.{key}")
    required = {"approved_runtime_evidence_missing", "synthetic_shape_fixture_not_runtime_evidence"}
    gate_blockers = gate.get("blockers")
    if not isinstance(gate_blockers, list) or not required.issubset(set(gate_blockers)):
        add(blockers, "promotion_gate_missing_required_blockers", "$.promotion_gate.blockers")


def validate_manifest(payload: dict[str, Any], *, check_mode: str) -> Validation:
    blockers: list[dict[str, Any]] = []
    if payload.get("schema") != SCHEMA:
        add(blockers, "schema_mismatch", "$.schema")
        return Validation(blockers, [])
    keys = set(payload)
    missing = REQUIRED_TOP_LEVEL_KEYS - keys
    unexpected = keys - REQUIRED_TOP_LEVEL_KEYS
    if missing:
        add(blockers, "top_level_fields_missing_required", "$", missing=sorted(missing))
    if unexpected:
        add(blockers, "top_level_fields_unexpected", "$", unexpected=sorted(unexpected))

    if payload.get("artifact_status") != "synthetic_redacted_fixture":
        add(blockers, "artifact_status_not_synthetic_redacted_fixture", "$.artifact_status")
    if payload.get("readiness_classification") != "shape_only_private_fixture":
        add(blockers, "readiness_classification_not_shape_only_private_fixture", "$.readiness_classification")
    for key in ("synthetic_fixture", "private_manifest", "redacted"):
        if payload.get(key) is not True:
            add(blockers, f"{key}_not_true", f"$.{key}")
    for key in ("promotion_ready", "public_sdk_ready", "runtime_ready"):
        if payload.get(key) is not False:
            add(blockers, f"{key}_not_false", f"$.{key}")

    validate_approval(payload.get("approval"), blockers)
    observed_cases = validate_observations(payload.get("observations"), blockers)
    validate_privacy_boundary(payload.get("privacy_boundary"), blockers)
    validate_promotion_gate(payload.get("promotion_gate"), blockers)

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

    if check_mode != "consume":
        add(blockers, f"{check_mode}_blocked_without_approved_runtime_evidence", "$.approval")
        add(blockers, "synthetic_shape_fixture_not_readiness_evidence", "$")

    return Validation(blockers, observed_cases)


def build_report(payload: dict[str, Any], validation: Validation, *, check_mode: str) -> dict[str, Any]:
    shape_accepted = not validation.blockers
    return {
        "schema": REPORT_SCHEMA,
        "input_schema": payload.get("schema"),
        "mode": check_mode,
        "ready": shape_accepted,
        "shape_accepted_by_this_checker": shape_accepted,
        "synthetic_redacted_fixture": payload.get("artifact_status") == "synthetic_redacted_fixture",
        "approved_runtime_evidence_present": False,
        "runtime_evidence_ready": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "remaining_blockers": ["approved_runtime_evidence_missing"],
        "observed_cases": validation.observed_cases,
        "blockers": [blocker["reason"] for blocker in validation.blockers],
        "blocker_details": validation.blockers,
        "non_claims": [
            "shape acceptance is a private synthetic fixture check only",
            "does not approve runtime evidence, authorize server work, promote public SDK, or publish claims",
        ],
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
