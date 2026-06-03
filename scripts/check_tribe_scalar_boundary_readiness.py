#!/usr/bin/env python3
"""Read-only readiness check for the internal Tribe scalar-boundary lane."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_SNAPSHOT_ROOT = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"
REPORT_SCHEMA = "obelisk.tribe-scalar-boundary-readiness-check.v1"
SNAPSHOT_SCHEMA = "obelisk.ufunction-chain.snapshot.v1"
TARGET_SET = "tribe-compact-intake"
OPTIONAL_CONTROL_TARGET = "ShooterPlayerController.ServerRequestTribeLog"
REQUIRED_TARGETS = {
    "ShooterPlayerController.AllowTribeGroupPermission",
    "ShooterPlayerController.IsInTribe",
}
REDACTION_TARGETS = {
    "ShooterPlayerController.ClientReceiveMyTribeOnlineList",
    "ShooterPlayerController.ClientReceiveActiveMissionTags",
}
CONSIDERED_TARGETS = REQUIRED_TARGETS | REDACTION_TARGETS | {OPTIONAL_CONTROL_TARGET}
EXPECTED_ACCEPTED_FIELDS = {
    "ShooterPlayerController.AllowTribeGroupPermission.TribeGroupPermission": {
        "class_name": "ByteProperty",
        "direction": "in",
        "element_size": 1,
        "offset_internal": 0,
        "type": "byte_enum",
    },
    "ShooterPlayerController.AllowTribeGroupPermission.ReturnValue": {
        "class_name": "BoolProperty",
        "direction": "return",
        "element_size": 1,
        "offset_internal": 16,
        "type": "bool",
    },
    "ShooterPlayerController.IsInTribe.ReturnValue": {
        "class_name": "BoolProperty",
        "direction": "return",
        "element_size": 1,
        "offset_internal": 0,
        "type": "bool",
    },
}
EXPECTED_REDACTED_FIELDS = {
    "ShooterPlayerController.AllowTribeGroupPermission.OnObject": "object_ref_onobject",
    "ShooterPlayerController.ClientReceiveMyTribeOnlineList.OnlinePlayerIDs": "online_list_array_identity",
    "ShooterPlayerController.ClientReceiveActiveMissionTags.MissionTags": "array_name_payload",
}
EXPECTED_REQUIRED_REDACTIONS = {
    "ShooterPlayerController.AllowTribeGroupPermission.OnObject",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
IDENTITY_FIELD_RE = re.compile(
    r"(?:player|steam|eos|unique[_-]?net|tribe[_-]?id|tribeid|onlineplayerids|"
    r"owner|team|rank|group|identity|principal|account|session|profile)",
    re.IGNORECASE,
)
STRING_OR_LOG_FIELD_RE = re.compile(r"(?:log|message|motd|notice|text|string|payload)", re.IGNORECASE)
FORBIDDEN_READY_KEYS = {
    "abi_ready",
    "identity_ready",
    "lookup_ready",
    "mutation_ready",
    "promotion_ready",
    "public_abi_ready",
    "public_api_ready",
    "public_sdk_ready",
    "public_surface",
    "resource_handle_ready",
    "return_override_ready",
    "runtime_ready",
    "sdk_ready",
    "tribe_sdk_ready",
    "v1_complete",
    "v1_completion_ready",
    "v1_ready",
}
FORBIDDEN_CLAIM_KEY_RE = re.compile(
    r"(?:resource[_-]?handle|return[_-]?override|public[_-]?(?:sdk|api|abi|surface)|"
    r"runtime[_-]?(?:ready|hook|observer|wiring)|v1[_-]?(?:ready|complete|completion)|"
    r"lookup[_-]?ready|mutation[_-]?ready|identity[_-]?ready)",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Tribe scalar-boundary candidate readiness from sanitized snapshots only."
    )
    parser.add_argument(
        "--snapshot-root",
        type=Path,
        default=DEFAULT_SNAPSHOT_ROOT,
        help="Root containing sanitized UFunction snapshot fixtures.",
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


def target_key(snapshot_target: dict[str, Any]) -> str | None:
    target = snapshot_target.get("target")
    if not isinstance(target, dict):
        return None
    outer_name = target.get("outer_name")
    name = target.get("name")
    if not isinstance(outer_name, str) or not isinstance(name, str):
        return None
    return f"{outer_name}.{name}"


def property_key(target: str, prop: dict[str, Any]) -> str | None:
    name = prop.get("name")
    if not isinstance(name, str) or not name:
        return None
    return f"{target}.{name}"


def parse_hex_or_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None
    try:
        return int(value, 0)
    except ValueError:
        return None


def bool_mask_is_one(value: Any) -> bool:
    parsed = parse_hex_or_int(value)
    return parsed == 1


def read_json_file(path: Path, blockers: list[dict[str, Any]]) -> dict[str, Any] | None:
    try:
        content = path.read_bytes()
        payload = json.loads(content.decode("utf-8"))
    except OSError as exc:
        append_blocker(blockers, "snapshot_unreadable", path=str(path), detail=str(exc))
        return None
    except json.JSONDecodeError as exc:
        append_blocker(blockers, "snapshot_malformed", path=str(path), detail=str(exc))
        return None
    if not isinstance(payload, dict):
        append_blocker(blockers, "snapshot_not_object", path=str(path))
        return None
    payload["_source_path"] = str(path)
    payload["_source_sha256"] = hashlib.sha256(content).hexdigest()
    return payload


def first_target(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any] | None:
    targets = payload.get("targets")
    if not isinstance(targets, list) or len(targets) != 1 or not isinstance(targets[0], dict):
        append_blocker(blockers, "snapshot_target_count_mismatch", path=payload.get("_source_path"))
        return None
    return targets[0]


def load_snapshots(snapshot_root: Path, blockers: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    snapshots: dict[str, dict[str, Any]] = {}
    if not snapshot_root.exists():
        append_blocker(blockers, "snapshot_root_missing", path=str(snapshot_root))
        return snapshots
    for path in sorted(snapshot_root.rglob("*.snapshot.json")):
        payload = read_json_file(path, blockers)
        if payload is None:
            continue
        target_payload = first_target(payload, blockers)
        if target_payload is None:
            continue
        key = target_key(target_payload)
        if key not in CONSIDERED_TARGETS:
            continue
        if key in snapshots:
            append_blocker(
                blockers,
                "duplicate_target_snapshot",
                target=key,
                first=snapshots[key].get("_source_path"),
                duplicate=str(path),
            )
            continue
        snapshots[key] = payload
    return snapshots


def properties_for(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    target_payload = first_target(payload, blockers)
    if target_payload is None:
        return []
    chain = target_payload.get("property_chain")
    if not isinstance(chain, dict):
        append_blocker(blockers, "property_chain_missing", target=target_key(target_payload))
        return []
    properties = chain.get("properties")
    if not isinstance(properties, list) or not all(isinstance(item, dict) for item in properties):
        append_blocker(blockers, "property_chain_properties_malformed", target=target_key(target_payload))
        return []
    return properties


def validate_snapshot_common(key: str, payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if payload.get("schema") != SNAPSHOT_SCHEMA:
        append_blocker(blockers, "snapshot_schema_mismatch", target=key, value=payload.get("schema"))
    source_sha = payload.get("_source_sha256")
    if not isinstance(source_sha, str) or SHA256_RE.fullmatch(source_sha) is None:
        append_blocker(blockers, "snapshot_sha256_malformed", target=key, value=source_sha)

    evidence = payload.get("evidence")
    if not isinstance(evidence, dict) or evidence.get("status") != "candidate-only":
        append_blocker(blockers, "snapshot_evidence_status_mismatch", target=key)
    interpretation = payload.get("interpretation")
    if not isinstance(interpretation, dict) or interpretation.get("status") != "candidate-only":
        append_blocker(blockers, "snapshot_interpretation_status_mismatch", target=key)

    target_payload = first_target(payload, blockers)
    if target_payload is None:
        return
    if target_payload.get("status") != "candidate":
        append_blocker(blockers, "target_status_mismatch", target=key, value=target_payload.get("status"))
    membership = target_payload.get("membership")
    if not isinstance(membership, dict):
        append_blocker(blockers, "target_membership_missing", target=key)
    else:
        for field in ("class", "outer", "target"):
            if membership.get(field) != "candidate-uobject":
                append_blocker(
                    blockers,
                    "target_membership_mismatch",
                    target=key,
                    field=field,
                    value=membership.get(field),
                )
    chain = target_payload.get("property_chain")
    if not isinstance(chain, dict):
        append_blocker(blockers, "property_chain_missing", target=key)
        return
    properties = chain.get("properties")
    if not isinstance(properties, list):
        append_blocker(blockers, "property_chain_properties_malformed", target=key)
        return
    expected_count = chain.get("expected_count")
    observed_count = chain.get("observed_count")
    if expected_count != len(properties) or observed_count != len(properties):
        append_blocker(
            blockers,
            "property_chain_count_mismatch",
            target=key,
            expected_count=expected_count,
            observed_count=observed_count,
            property_count=len(properties),
        )
    if target_payload.get("num_parms") != len(properties):
        append_blocker(
            blockers,
            "num_parms_mismatch",
            target=key,
            num_parms=target_payload.get("num_parms"),
            property_count=len(properties),
        )


def validate_property_candidate(target: str, field: str, prop: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if prop.get("status") != "candidate":
        append_blocker(blockers, "property_status_mismatch", field=field, value=prop.get("status"))
    for key in ("membership_status", "class_membership_status", "outer_membership_status"):
        if prop.get(key) != "candidate-uobject":
            append_blocker(blockers, "property_membership_mismatch", target=target, field=field, member=key)
    if prop.get("array_dim") != 1:
        append_blocker(blockers, "property_array_dim_mismatch", field=field, value=prop.get("array_dim"))


def validate_bool_field(field: str, prop: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    expected = {
        "bool_byte_offset": 0,
        "bool_field_size": 1,
        "element_size": 1,
        "field_mask": "0xff",
        "native_bool": False,
    }
    for key, expected_value in expected.items():
        if prop.get(key) != expected_value:
            append_blocker(
                blockers,
                "bool_scalar_metadata_mismatch",
                field=field,
                metadata_key=key,
                expected=expected_value,
                value=prop.get(key),
            )
    if not bool_mask_is_one(prop.get("byte_mask")):
        append_blocker(blockers, "bool_scalar_metadata_mismatch", field=field, metadata_key="byte_mask", value=prop.get("byte_mask"))
    semantics = prop.get("bool_property_semantics")
    if not isinstance(semantics, dict) or semantics.get("status") != "candidate":
        append_blocker(blockers, "bool_semantics_missing_or_not_candidate", field=field)


def validate_byte_enum_field(field: str, prop: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    enum_candidate = prop.get("enum_candidate")
    if not isinstance(enum_candidate, dict) or enum_candidate.get("status") != "candidate":
        append_blocker(blockers, "byte_enum_candidate_missing", field=field)
        return
    values = enum_candidate.get("values")
    if not isinstance(values, list) or not values or not all(isinstance(value, str) for value in values):
        append_blocker(blockers, "byte_enum_values_missing", field=field)


def validate_accepted_field(target: str, field: str, prop: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    spec = EXPECTED_ACCEPTED_FIELDS[field]
    validate_property_candidate(target, field, prop, blockers)
    for key in ("class_name", "element_size", "offset_internal"):
        if prop.get(key) != spec[key]:
            append_blocker(
                blockers,
                "accepted_scalar_shape_mismatch",
                field=field,
                metadata_key=key,
                expected=spec[key],
                value=prop.get(key),
            )
    if spec["type"] == "bool":
        validate_bool_field(field, prop, blockers)
    elif spec["type"] == "byte_enum":
        validate_byte_enum_field(field, prop, blockers)
    return {
        "accepted_field": field,
        "direction": spec["direction"],
        "type": spec["type"],
        "property_class": prop.get("class_name"),
        "offset_internal": prop.get("offset_internal"),
        "element_size": prop.get("element_size"),
        "source_snapshot": target,
    }


def redact_field(target: str, field: str, prop: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    validate_property_candidate(target, field, prop, blockers)
    class_name = prop.get("class_name")
    reason = EXPECTED_REDACTED_FIELDS.get(field)
    if field == "ShooterPlayerController.AllowTribeGroupPermission.OnObject" and class_name != "ObjectProperty":
        append_blocker(blockers, "onobject_redaction_shape_mismatch", field=field, property_class=class_name)
    if field == "ShooterPlayerController.ClientReceiveMyTribeOnlineList.OnlinePlayerIDs" and class_name != "ArrayProperty":
        append_blocker(blockers, "online_list_array_shape_mismatch", field=field, property_class=class_name)
    if field == "ShooterPlayerController.ClientReceiveActiveMissionTags.MissionTags" and class_name != "ArrayProperty":
        append_blocker(blockers, "mission_tags_array_shape_mismatch", field=field, property_class=class_name)
    if class_name in {"StrProperty", "TextProperty"} or STRING_OR_LOG_FIELD_RE.search(field):
        append_blocker(blockers, "string_or_log_payload_present", field=field, property_class=class_name)
    if IDENTITY_FIELD_RE.search(field):
        reason = reason or "identity_field_redacted"
    return {
        "redacted_field": field,
        "reason": reason or "not_in_scalar_allowlist",
        "property_class": class_name,
        "source_snapshot": target,
    }


def validate_control(snapshot: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    target_payload = first_target(snapshot, blockers)
    if target_payload is None:
        return {"target": OPTIONAL_CONTROL_TARGET, "present": True, "ready": False}
    chain = target_payload.get("property_chain") if isinstance(target_payload.get("property_chain"), dict) else {}
    properties = chain.get("properties") if isinstance(chain, dict) else None
    zero_param = (
        target_payload.get("num_parms") == 0
        and target_payload.get("parms_size") == 0
        and target_payload.get("return_value_offset") == "0xffff"
        and isinstance(properties, list)
        and len(properties) == 0
    )
    if not zero_param:
        append_blocker(
            blockers,
            "server_request_tribe_log_not_zero_param",
            num_parms=target_payload.get("num_parms"),
            parms_size=target_payload.get("parms_size"),
            return_value_offset=target_payload.get("return_value_offset"),
        )
    return {
        "target": OPTIONAL_CONTROL_TARGET,
        "present": True,
        "ready": zero_param,
        "zero_param": zero_param,
    }


def reject_forbidden_claims(value: Any, blockers: list[dict[str, Any]], path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.startswith("_"):
                continue
            key_lower = key.lower()
            if key_lower in FORBIDDEN_READY_KEYS and child is not False and child is not None:
                append_blocker(blockers, "forbidden_readiness_claim", path=f"{path}.{key}", value=child)
            elif FORBIDDEN_CLAIM_KEY_RE.search(key) and child is True:
                append_blocker(blockers, "forbidden_positive_claim_key", path=f"{path}.{key}", value=child)
            reject_forbidden_claims(child, blockers, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            reject_forbidden_claims(child, blockers, f"{path}[{index}]")


def validate_snapshots(snapshots: dict[str, dict[str, Any]], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    for key, payload in snapshots.items():
        validate_snapshot_common(key, payload, blockers)
        reject_forbidden_claims(payload, blockers, path=f"$.snapshots.{key}")

    missing_required = sorted(REQUIRED_TARGETS - set(snapshots))
    if missing_required:
        append_blocker(blockers, "required_target_snapshot_missing", missing=missing_required)

    accepted: list[dict[str, Any]] = []
    redacted: list[dict[str, Any]] = []
    observed_redacted_fields: set[str] = set()
    observed_accepted_fields: set[str] = set()

    for target in sorted(REQUIRED_TARGETS | REDACTION_TARGETS):
        payload = snapshots.get(target)
        if payload is None:
            continue
        for prop in properties_for(payload, blockers):
            field = property_key(target, prop)
            if field is None:
                append_blocker(blockers, "property_name_missing", target=target)
                continue
            if field in EXPECTED_ACCEPTED_FIELDS:
                accepted.append(validate_accepted_field(target, field, prop, blockers))
                observed_accepted_fields.add(field)
                continue
            if field in EXPECTED_REDACTED_FIELDS or target in REDACTION_TARGETS:
                redacted.append(redact_field(target, field, prop, blockers))
                observed_redacted_fields.add(field)
                continue
            if IDENTITY_FIELD_RE.search(field):
                append_blocker(blockers, "forbidden_identity_field_in_required_target", field=field)
            if prop.get("class_name") in {"ObjectProperty", "ArrayProperty", "StrProperty", "TextProperty"}:
                append_blocker(
                    blockers,
                    "unexpected_redaction_candidate_in_required_target",
                    field=field,
                    property_class=prop.get("class_name"),
                )
            else:
                append_blocker(
                    blockers,
                    "unexpected_required_target_scalar",
                    field=field,
                    property_class=prop.get("class_name"),
                )

    missing_accepted = sorted(set(EXPECTED_ACCEPTED_FIELDS) - observed_accepted_fields)
    if missing_accepted:
        append_blocker(blockers, "accepted_scalar_field_missing", missing=missing_accepted)
    missing_redacted = sorted(EXPECTED_REQUIRED_REDACTIONS - observed_redacted_fields)
    if missing_redacted:
        append_blocker(blockers, "required_redacted_field_missing", missing=missing_redacted)

    control = {"target": OPTIONAL_CONTROL_TARGET, "present": False, "ready": None, "zero_param": None}
    if OPTIONAL_CONTROL_TARGET in snapshots:
        control = validate_control(snapshots[OPTIONAL_CONTROL_TARGET], blockers)
        for prop in properties_for(snapshots[OPTIONAL_CONTROL_TARGET], blockers):
            field = property_key(OPTIONAL_CONTROL_TARGET, prop) or OPTIONAL_CONTROL_TARGET
            redacted.append(redact_field(OPTIONAL_CONTROL_TARGET, field, prop, blockers))

    return {
        "accepted_scalar_fields": sorted(entry["accepted_field"] for entry in accepted),
        "accepted_scalars": sorted(accepted, key=lambda entry: entry["accepted_field"]),
        "redacted_fields": sorted(entry["redacted_field"] for entry in redacted),
        "redactions": sorted(redacted, key=lambda entry: entry["redacted_field"]),
        "optional_controls": [control],
        "required_targets": sorted(REQUIRED_TARGETS),
        "redaction_targets_present": sorted(set(snapshots) & REDACTION_TARGETS),
        "target_set": TARGET_SET,
    }


def build_report(snapshot_root: Path = DEFAULT_SNAPSHOT_ROOT) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    safe_snapshot_root = safe_path(snapshot_root, "--snapshot-root", blockers)
    snapshots = load_snapshots(safe_snapshot_root, blockers) if safe_snapshot_root is not None else {}
    summary = validate_snapshots(snapshots, blockers)
    ready = not blockers
    return {
        "schema": REPORT_SCHEMA,
        "status": "candidate_ready" if ready else "blocked",
        "ready": ready,
        "accepted_for_internal_planning": ready,
        "offline_only": True,
        "fixture_only": True,
        "not_artifact_gate": True,
        "target_set": TARGET_SET,
        "snapshot_root": str(snapshot_root),
        "checked_targets": sorted(snapshots),
        "summary": summary,
        "tribe_scalar_boundary_ready": ready,
        "scalar_boundary_ready": ready,
        "server_request_tribe_log_control_ready": summary["optional_controls"][0]["ready"],
        "public_sdk_ready": False,
        "public_tribe_sdk_ready": False,
        "public_abi_ready": False,
        "runtime_ready": False,
        "runtime_observer_approved": False,
        "identity_ready": False,
        "lookup_ready": False,
        "mutation_ready": False,
        "return_override_ready": False,
        "resource_handle_ready": False,
        "v1_completion_ready": False,
        "promotion_ready": False,
        "blockers": blockers,
        "non_claims": [
            "candidate readiness is internal planning evidence only",
            "no public Tribe SDK, public C ABI, public runtime API, or v1 completion",
            "no runtime hook wiring, observer window, dispatcher wiring, or server validation",
            "no tribe/player identity, online-list payload exposure, lookup, ownership, or ResourceHandle",
            "no strings, tribe log payloads, MOTD, notices, raw params, UE pointers, or object references exposed",
            "no mutation, return override, authority policy enforcement, or UE function call",
        ],
    }


def main() -> int:
    args = parse_args()
    report = build_report(args.snapshot_root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
