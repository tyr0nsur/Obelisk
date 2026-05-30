#!/usr/bin/env python3
"""Build candidate-only redacted UFunction signatures from sanitized snapshots.

The output is intentionally not a public SDK contract. It preserves enough metadata for
offline reversing triage while redacting UE object/class/struct/enum identity and raw
parameter ownership details.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT_ROOT = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"
SUPPORTED_SNAPSHOT_SCHEMA = "obelisk.ufunction-chain.snapshot.v1"
OUTPUT_SCHEMA = "obelisk.redacted-ufunction-signatures.v1"
TARGET_SET_COVERAGE_SCHEMA = "obelisk.redacted-ufunction-target-set-coverage.v1"
PROTECTED_SERVER_ROOT = Path("/servidor/ark")
APPROVED_OFFLINE_WORKSPACE_ROOTS = (Path("/servidor/ark/workspace-offline"),)

CPF_CONST_PARM = 0x2
CPF_PARM = 0x80
CPF_OUT_PARM = 0x100
CPF_ZERO_CONSTRUCTOR = 0x200
CPF_RETURN_PARM = 0x400
CPF_REFERENCE_PARM = 0x08000000
KNOWN_PROPERTY_FLAG_BITS = (
    CPF_CONST_PARM
    | CPF_PARM
    | CPF_OUT_PARM
    | CPF_ZERO_CONSTRUCTOR
    | CPF_RETURN_PARM
    | CPF_REFERENCE_PARM
)
CANDIDATE_UOBJECT_STATUS = "candidate-uobject"

SCALAR_TYPE_BY_CLASS = {
    "BoolProperty": "bool",
    "ByteProperty": "byte_or_enum",
    "DoubleProperty": "double",
    "EnumProperty": "enum",
    "FloatProperty": "float",
    "Int16Property": "int16",
    "Int64Property": "int64",
    "Int8Property": "int8",
    "IntProperty": "int32",
    "NameProperty": "fname",
    "UInt16Property": "uint16",
    "UInt32Property": "uint32",
    "UInt64Property": "uint64",
}

REDACTED_TYPE_BY_CLASS = {
    "ArrayProperty": "redacted_array",
    "ClassProperty": "redacted_class_ref",
    "DelegateProperty": "redacted_delegate",
    "InterfaceProperty": "redacted_interface_ref",
    "LazyObjectProperty": "redacted_uobject_ref",
    "MapProperty": "redacted_map",
    "MulticastDelegateProperty": "redacted_delegate",
    "ObjectProperty": "redacted_uobject_ref",
    "SetProperty": "redacted_set",
    "SoftClassProperty": "redacted_class_ref",
    "SoftObjectProperty": "redacted_uobject_ref",
    "StrProperty": "redacted_text",
    "StructProperty": "redacted_struct",
    "TextProperty": "redacted_text",
    "WeakObjectProperty": "redacted_uobject_ref",
}

IDENTITY_KEYS_TO_REDACT = {
    "class",
    "class_name",
    "enum",
    "enum_name",
    "inner",
    "inner_class",
    "inner_class_name",
    "object_class",
    "object_class_name",
    "property_class",
    "property_class_name",
    "struct",
    "struct_name",
}

BOOL_MASK_KEYS = (
    "byte_mask",
    "field_mask",
    "bool_byte_mask",
    "bool_field_mask",
    "bitmask",
    "mask",
)

SENSITIVE_SCALAR_NAMES = {
    "adminpassword",
    "allianceid",
    "enemytribeid",
    "eosid",
    "groupid",
    "grouprank",
    "invitecode",
    "invitetribeid",
    "lockcode",
    "newrank",
    "oldrank",
    "ownerplayerid",
    "ownertribeid",
    "passcode",
    "password",
    "platformid",
    "playerid",
    "pincode",
    "pin_code",
    "rankgroupid",
    "rankid",
    "requesterplayerid",
    "secret",
    "steamid",
    "targetingteam",
    "targetplayerid",
    "teamid",
    "token",
    "tribegrouppermission",
    "tribeid",
    "uniqueid",
    "uniquenetid",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert sanitized UFunction snapshots into redacted, candidate-only "
            "signature reports without reading cores or touching servers."
        )
    )
    parser.add_argument(
        "--snapshot-root",
        type=Path,
        default=DEFAULT_SNAPSHOT_ROOT,
        help="Snapshot root containing manifest.json and snapshot files.",
    )
    parser.add_argument(
        "--target-set",
        action="append",
        default=[],
        help="Named UFunction target set from reflection_target_sets.py. Repeatable.",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        action="append",
        default=[],
        help="Sanitized snapshot JSON to include directly. Repeatable.",
    )
    parser.add_argument(
        "--source-target-set",
        action="append",
        default=[],
        help=(
            "Named target set covered by direct --snapshot inputs. Repeatable. "
            "The emitted signatures must exactly match the declared target set union."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON. Text output is the default.",
    )
    return parser.parse_args()


def is_under_path(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def is_approved_offline_workspace_path(path: Path) -> bool:
    resolved = path.resolve()
    return any(is_under_path(resolved, root.resolve()) for root in APPROVED_OFFLINE_WORKSPACE_ROOTS)


def reject_protected_input_path(label: str, path: Path) -> None:
    expanded = path.expanduser()
    direct = expanded.absolute()
    resolved = expanded.resolve()
    direct_protected = PROTECTED_SERVER_ROOT.absolute()
    protected = PROTECTED_SERVER_ROOT.resolve()
    if is_under_path(direct, direct_protected) and not is_approved_offline_workspace_path(expanded):
        raise SystemExit(f"{label} must not read from protected live-server path: {path}")
    if is_under_path(resolved, protected) and not is_approved_offline_workspace_path(resolved):
        raise SystemExit(f"{label} must not read from protected live-server path: {path}")


def load_json_file(label: str, path: Path) -> dict[str, Any]:
    reject_protected_input_path(label, path)
    if not path.is_file():
        raise SystemExit(f"missing {label}: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{label} must contain a JSON object: {path}")
    return payload


def file_sha256(path: Path) -> str:
    reject_protected_input_path("hash input", path)
    if not path.is_file():
        raise SystemExit(f"missing hash input: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(snapshot_root: Path) -> dict[str, Any]:
    reject_protected_input_path("snapshot root", snapshot_root)
    return load_json_file("snapshot manifest", snapshot_root / "manifest.json")


def manifest_index(manifest: dict[str, Any], snapshot_root: Path) -> dict[str, Path]:
    sha_prefix = manifest.get("sha_prefix")
    if not isinstance(sha_prefix, str) or not sha_prefix:
        raise SystemExit("snapshot manifest missing sha_prefix")

    entries = manifest.get("targets")
    if not isinstance(entries, list):
        raise SystemExit("snapshot manifest targets must be a list")

    indexed: dict[str, Path] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise SystemExit("snapshot manifest target entry must be an object")
        outer = entry.get("outer")
        name = entry.get("name")
        module = entry.get("module")
        file_name = entry.get("file")
        if not all(isinstance(value, str) and value for value in (outer, name, module, file_name)):
            raise SystemExit(f"invalid snapshot manifest entry: {entry!r}")

        target = f"{outer}.{name}"
        path = snapshot_root / sha_prefix / module / file_name
        reject_protected_input_path("snapshot", path)
        if target in indexed:
            raise SystemExit(f"duplicate snapshot manifest target: {target}")
        indexed[target] = path
    return indexed


def expand_ufunction_target_sets(target_sets: list[str]) -> dict[str, list[str]]:
    from reflection_target_sets import TARGET_SETS

    expanded: dict[str, list[str]] = {}
    for target_set in target_sets:
        if target_set in expanded:
            raise SystemExit(f"duplicate target set: {target_set}")
        entries = TARGET_SETS.get(target_set)
        if entries is None:
            raise SystemExit(f"unknown target set: {target_set}")
        targets: list[str] = []
        seen: set[str] = set()
        for entry in entries:
            schema, _, target = entry.partition(":")
            if schema != SUPPORTED_SNAPSHOT_SCHEMA:
                continue
            if target not in seen:
                targets.append(target)
                seen.add(target)
        if not targets:
            raise SystemExit(f"target set did not include UFunction snapshots: {target_set}")
        expanded[target_set] = targets
    return expanded


def expand_ufunction_targets(target_sets: list[str]) -> list[str]:
    targets: list[str] = []
    seen: set[str] = set()
    for entries in expand_ufunction_target_sets(target_sets).values():
        for target in entries:
            if target not in seen:
                targets.append(target)
                seen.add(target)
    return targets


def parse_int_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 0)
        except ValueError:
            return None
    return None


def property_flags(prop: dict[str, Any]) -> int | None:
    direct = parse_int_value(prop.get("property_flags"))
    if direct is not None:
        return direct
    direct = parse_int_value(prop.get("property_flags_hex"))
    if direct is not None:
        return direct
    low = parse_int_value(prop.get("property_flags_low"))
    high = parse_int_value(prop.get("property_flags_high"))
    if low is None and high is None:
        return None
    return ((high or 0) << 32) | (low or 0)


def has_flag(flags: int | None, flag: int) -> bool:
    return flags is not None and bool(flags & flag)


def classify_direction(prop: dict[str, Any], return_value_offset: Any) -> str:
    flags = property_flags(prop)
    offset = parse_int_value(prop.get("offset_internal"))
    return_offset = parse_int_value(return_value_offset)
    is_return = has_flag(flags, CPF_RETURN_PARM) or prop.get("name") == "ReturnValue"
    if not is_return and return_offset is not None and offset == return_offset:
        is_return = True
    if is_return:
        return "return"
    if has_flag(flags, CPF_OUT_PARM):
        return "out"
    if has_flag(flags, CPF_PARM):
        return "in"
    return "candidate_member_or_local"


def flag_labels(flags: int | None) -> list[str]:
    if flags is None:
        return ["flags_missing"]
    labels: list[str] = []
    if flags & CPF_CONST_PARM:
        labels.append("ConstParm")
    if flags & CPF_PARM:
        labels.append("Parm")
    if flags & CPF_OUT_PARM:
        labels.append("OutParm")
    if flags & CPF_ZERO_CONSTRUCTOR:
        labels.append("ZeroConstructor")
    if flags & CPF_RETURN_PARM:
        labels.append("ReturnParm")
    if flags & CPF_REFERENCE_PARM:
        labels.append("ReferenceParm")
    return labels


def append_membership_blocker(blockers: list[str], prop: dict[str, Any], key: str) -> None:
    status = prop.get(key)
    if status != CANDIDATE_UOBJECT_STATUS:
        blockers.append(f"{key}_not_candidate_uobject")


def append_nested_membership_blockers(blockers: list[str], prop: dict[str, Any], key: str) -> None:
    nested = prop.get(key)
    if nested is None:
        return
    if not isinstance(nested, dict):
        blockers.append(f"{key}_not_object")
        return
    if nested.get("membership_status") != CANDIDATE_UOBJECT_STATUS:
        blockers.append(f"{key}_membership_not_candidate_uobject")


def promotion_blockers_for_property(prop: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    flags = property_flags(prop)
    if flags is None:
        blockers.append("property_flags_missing")
    else:
        unknown = flags & ~KNOWN_PROPERTY_FLAG_BITS
        if unknown:
            blockers.append("property_flags_unknown_bits")

    append_membership_blocker(blockers, prop, "membership_status")
    append_membership_blocker(blockers, prop, "class_membership_status")
    append_membership_blocker(blockers, prop, "outer_membership_status")
    append_nested_membership_blockers(blockers, prop, "array_inner_candidate")
    append_nested_membership_blockers(blockers, prop, "struct_type_candidate")

    if prop.get("class_name") == "BoolProperty" and not bool_masks(prop) and prop.get("native_bool") is not True:
        blockers.append("bool_semantics_missing_mask_or_native_bool_marker")

    return sorted(set(blockers))


def is_valid_zero_param_signature(target_payload: dict[str, Any], property_count: int) -> bool:
    if property_count != 0:
        return False
    num_parms = parse_int_value(target_payload.get("num_parms"))
    parms_size = parse_int_value(target_payload.get("parms_size"))
    return_value_offset = parse_int_value(target_payload.get("return_value_offset"))
    property_chain = target_payload.get("property_chain")
    expected_count = None
    observed_count = None
    if isinstance(property_chain, dict):
        expected_count = parse_int_value(property_chain.get("expected_count"))
        observed_count = parse_int_value(property_chain.get("observed_count"))
    return (
        num_parms == 0
        and parms_size == 0
        and expected_count == 0
        and observed_count == 0
        and return_value_offset in (0xFFFF, -1)
    )


def promotion_blockers_for_signature(target_payload: dict[str, Any], property_count: int) -> list[str]:
    blockers = ["function_flags_not_bound_to_exact_target_gate"]
    if parse_int_value(target_payload.get("function_flags")) is None:
        blockers.append("function_flags_missing_or_unparseable")
    property_chain = target_payload.get("property_chain")
    expected_count = None
    observed_count = None
    if isinstance(property_chain, dict):
        expected_count = parse_int_value(property_chain.get("expected_count"))
        observed_count = parse_int_value(property_chain.get("observed_count"))

    if expected_count is None:
        blockers.append("property_chain_expected_count_missing")
    if observed_count is None:
        blockers.append("property_chain_observed_count_missing")
    if expected_count is not None and observed_count is not None and expected_count != observed_count:
        blockers.append("property_chain_count_mismatch")
    if observed_count is not None and observed_count != property_count:
        blockers.append("property_chain_observed_count_not_property_count")

    if property_count == 0 and not is_valid_zero_param_signature(target_payload, property_count):
        blockers.append("zero_param_shape_not_proven")
    return sorted(set(blockers))


def redacted_type(prop: dict[str, Any]) -> tuple[str, str]:
    class_name = prop.get("class_name")
    name = prop.get("name")
    if not isinstance(class_name, str) or not class_name:
        return "blocked_unknown", "missing property class"
    if isinstance(name, str) and name.lower() in SENSITIVE_SCALAR_NAMES:
        return "redacted_sensitive_scalar", "credential-like scalar redacted by name"
    if class_name in SCALAR_TYPE_BY_CLASS:
        if class_name in {"ByteProperty", "EnumProperty"}:
            return SCALAR_TYPE_BY_CLASS[class_name], "enum identity redacted"
        return SCALAR_TYPE_BY_CLASS[class_name], "copied scalar candidate"
    if class_name in REDACTED_TYPE_BY_CLASS:
        return REDACTED_TYPE_BY_CLASS[class_name], f"{class_name} identity/payload redacted"
    return "blocked_unknown", f"unsupported property class: {class_name}"


def bool_masks(prop: dict[str, Any]) -> dict[str, Any]:
    masks: dict[str, Any] = {}
    for key in BOOL_MASK_KEYS:
        value = parse_int_value(prop.get(key))
        if value is not None and 0 < value <= 0xFF:
            masks[key] = f"0x{value:02x}" if value < 0x10 else f"0x{value:x}"
    return masks


def redaction_notes(prop: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    for key in sorted(IDENTITY_KEYS_TO_REDACT):
        if key in prop and prop.get(key) not in (None, "", [], {}):
            notes.append(f"{key}_redacted")
    return notes


def classify_property(prop: dict[str, Any], return_value_offset: Any) -> dict[str, Any]:
    name = prop.get("name")
    class_name = prop.get("class_name")
    if not isinstance(name, str) or not name:
        raise SystemExit(f"invalid property name: {prop!r}")
    if not isinstance(class_name, str) or not class_name:
        raise SystemExit(f"invalid property class for {name}: {prop!r}")

    flags = property_flags(prop)
    type_name, reason = redacted_type(prop)
    field: dict[str, Any] = {
        "name": name,
        "direction": classify_direction(prop, return_value_offset),
        "type": type_name,
        "source_property_class": class_name,
        "offset": prop.get("offset_internal"),
        "element_size": prop.get("element_size"),
        "array_dim": prop.get("array_dim"),
        "status": prop.get("status"),
        "property_flag_labels": flag_labels(flags),
        "redaction": reason,
    }
    if flags is not None:
        field["property_flags"] = f"0x{flags:x}"
    if class_name == "BoolProperty":
        masks = bool_masks(prop)
        if masks:
            field["bool_masks"] = masks
    blockers = promotion_blockers_for_property(prop)
    if blockers:
        field["promotion_blockers"] = blockers
    notes = redaction_notes(prop)
    if notes:
        field["redacted_identity_fields"] = notes
    return field


def blocked_property(prop: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "name": prop.get("name"),
        "source_property_class": prop.get("class_name"),
        "status": prop.get("status"),
        "reason": reason,
    }


def target_name(target_identity: dict[str, Any]) -> str:
    outer = target_identity.get("outer_name")
    name = target_identity.get("name")
    if not isinstance(outer, str) or not outer or not isinstance(name, str) or not name:
        raise SystemExit(f"invalid target identity: {target_identity!r}")
    return f"{outer}.{name}"


def require_snapshot_payload(payload: dict[str, Any], path: Path) -> list[dict[str, Any]]:
    if payload.get("schema") != SUPPORTED_SNAPSHOT_SCHEMA:
        raise SystemExit(f"unsupported snapshot schema in {path}: {payload.get('schema')!r}")
    targets = payload.get("targets")
    if not isinstance(targets, list) or not targets:
        raise SystemExit(f"snapshot must contain at least one target: {path}")
    if not all(isinstance(target, dict) for target in targets):
        raise SystemExit(f"snapshot targets must be objects: {path}")
    return targets


def build_target_signature(
    target_payload: dict[str, Any],
    path: Path,
    source_snapshot: dict[str, str] | None = None,
) -> dict[str, Any]:
    target_identity = target_payload.get("target")
    property_chain = target_payload.get("property_chain")
    if not isinstance(target_identity, dict) or not isinstance(property_chain, dict):
        raise SystemExit(f"snapshot missing target identity or property chain: {path}")
    properties = property_chain.get("properties")
    if not isinstance(properties, list):
        raise SystemExit(f"snapshot property_chain.properties must be a list: {path}")

    return_value_offset = target_payload.get("return_value_offset")
    params: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for prop in properties:
        if not isinstance(prop, dict):
            blocked.append({"name": None, "source_property_class": None, "status": None, "reason": "property entry is not an object"})
            continue
        if prop.get("status") != "candidate":
            blocked.append(blocked_property(prop, "property status is not candidate"))
            continue
        field = classify_property(prop, return_value_offset)
        if field["type"] == "blocked_unknown":
            blocked.append(blocked_property(prop, field["redaction"]))
            continue
        params.append(field)

    identity = target_name(target_identity)
    signature = {
        "target": identity,
        "outer_name": target_identity.get("outer_name"),
        "name": target_identity.get("name"),
        "function_flags": target_payload.get("function_flags"),
        "num_parms": target_payload.get("num_parms"),
        "parms_size": target_payload.get("parms_size"),
        "return_value_offset": return_value_offset,
        "signature_status": "candidate-only",
        "promotion_blockers": promotion_blockers_for_signature(target_payload, len(properties)),
        "params": params,
        "blocked_properties": blocked,
    }
    if source_snapshot is not None:
        signature["source_snapshot"] = source_snapshot["id"]
        signature["source_snapshot_sha256"] = source_snapshot["sha256"]
    return signature


def build_from_snapshot(path: Path, source_snapshot: dict[str, str]) -> list[dict[str, Any]]:
    payload = load_json_file("snapshot", path)
    return [
        build_target_signature(target, path, source_snapshot)
        for target in require_snapshot_payload(payload, path)
    ]


def scalar_summary_kind(type_name: str) -> str | None:
    if type_name == "bool":
        return "bool"
    if type_name in {"byte_or_enum", "enum"}:
        return "byte_or_enum_like"
    if type_name == "fname":
        return "name_like"
    if type_name in {"float", "double"}:
        return "float"
    if type_name in {"int8", "int16", "int32", "int64", "uint16", "uint32", "uint64"}:
        return "integer"
    return None


def redacted_summary_reason(type_name: str) -> str | None:
    if type_name == "redacted_sensitive_scalar":
        return "sensitive_scalar"
    if type_name in {"redacted_uobject_ref", "redacted_interface_ref"}:
        return "object_ref"
    if type_name == "redacted_class_ref":
        return "class_ref"
    if type_name in {"redacted_array", "redacted_map", "redacted_set"}:
        return "container"
    if type_name == "redacted_struct":
        return "struct"
    if type_name == "redacted_delegate":
        return "delegate"
    if type_name == "redacted_text":
        return "text"
    return None


def increment(counter: dict[str, int], key: str) -> None:
    counter[key] = counter.get(key, 0) + 1


def safety_summary(signatures: list[dict[str, Any]], *, snapshot_count: int, target_sets: list[str], missing_targets: list[str]) -> dict[str, Any]:
    copied_scalar_by_kind: dict[str, int] = {}
    redacted_by_reason: dict[str, int] = {}
    blocked_by_reason: dict[str, int] = {}
    promotion_blockers_by_reason: dict[str, int] = {}
    direction_counts: dict[str, int] = {}
    param_count = 0
    copied_scalar_count = 0
    redacted_count = 0
    blocked_count = 0
    promotion_blocker_count = 0
    bool_masked_field_count = 0
    zero_param_signature_count = 0

    for signature in signatures:
        if not signature["params"] and not signature["blocked_properties"]:
            zero_param_signature_count += 1
        for blocker in signature.get("promotion_blockers", []):
            if isinstance(blocker, str):
                promotion_blocker_count += 1
                increment(promotion_blockers_by_reason, blocker)
        for param in signature["params"]:
            param_count += 1
            direction = param.get("direction")
            if isinstance(direction, str):
                increment(direction_counts, direction)
            type_name = param.get("type")
            if not isinstance(type_name, str):
                continue
            scalar_kind = scalar_summary_kind(type_name)
            if scalar_kind is not None:
                copied_scalar_count += 1
                increment(copied_scalar_by_kind, scalar_kind)
            redacted_reason = redacted_summary_reason(type_name)
            if redacted_reason is not None:
                redacted_count += 1
                increment(redacted_by_reason, redacted_reason)
            if "bool_masks" in param:
                bool_masked_field_count += 1
            for blocker in param.get("promotion_blockers", []):
                if isinstance(blocker, str):
                    promotion_blocker_count += 1
                    increment(promotion_blockers_by_reason, blocker)
        for blocked in signature["blocked_properties"]:
            blocked_count += 1
            reason = blocked.get("reason")
            increment(blocked_by_reason, reason if isinstance(reason, str) else "unknown")

    return {
        "artifact_status": "candidate_only",
        "promotion_ready": False,
        "intended_use": "offline_review_only",
        "evidence_scope": "redacted_ufunction_signature_metadata",
        "signature_count": len(signatures),
        "zero_param_signature_count": zero_param_signature_count,
        "snapshot_count": snapshot_count,
        "target_set_count": len(target_sets),
        "missing_target_count": len(missing_targets),
        "param_count_total": param_count,
        "copied_scalar_count_total": copied_scalar_count,
        "copied_scalar_by_kind": dict(sorted(copied_scalar_by_kind.items())),
        "redacted_count_total": redacted_count,
        "redacted_by_reason": dict(sorted(redacted_by_reason.items())),
        "blocked_count_total": blocked_count,
        "blocked_by_reason": dict(sorted(blocked_by_reason.items())),
        "promotion_blocker_count_total": promotion_blocker_count,
        "promotion_blockers_by_reason": dict(sorted(promotion_blockers_by_reason.items())),
        "direction_counts": dict(sorted(direction_counts.items())),
        "bool_masked_field_count": bool_masked_field_count,
        "unknown_or_blocked_present": blocked_count > 0,
        "direction_model": "return_out_in_order; ReferenceParm_label_only",
        "redaction_policy": "object_class_identity_sensitive_scalars_and_container_payloads_redacted",
        "not_promoted_surfaces": [
            "public_sdk",
            "object_identity",
            "class_identity",
            "lookup",
            "mutation",
            "return_override",
            "resource_handle",
            "cross_binary_portability",
        ],
    }


def snapshot_paths_from_target_sets(snapshot_root: Path, target_sets: list[str]) -> tuple[list[Path], list[str]]:
    if not target_sets:
        return [], []
    manifest = load_manifest(snapshot_root)
    indexed = manifest_index(manifest, snapshot_root)
    paths: list[Path] = []
    missing: list[str] = []
    for target in expand_ufunction_targets(target_sets):
        path = indexed.get(target)
        if path is None or not path.is_file():
            missing.append(target)
            continue
        paths.append(path)
    return paths, missing


def unique_ordered(values: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            ordered.append(value)
            seen.add(value)
    return ordered


def target_set_coverage(
    *,
    manifest_target_sets: list[str],
    source_target_sets: list[str],
    emitted_targets: list[str],
) -> dict[str, Any]:
    if set(manifest_target_sets).intersection(source_target_sets):
        overlap = sorted(set(manifest_target_sets).intersection(source_target_sets))
        raise SystemExit(f"target set declared for both manifest and direct snapshots: {', '.join(overlap)}")

    declared: list[tuple[str, str]] = [
        *[(target_set, "manifest") for target_set in manifest_target_sets],
        *[(target_set, "snapshot") for target_set in source_target_sets],
    ]
    expanded = expand_ufunction_target_sets([target_set for target_set, _ in declared]) if declared else {}
    emitted_set = set(emitted_targets)
    expected_targets = unique_ordered(
        [
            target
            for target_set, _ in declared
            for target in expanded[target_set]
        ]
    )
    expected_set = set(expected_targets)
    missing_targets = [target for target in expected_targets if target not in emitted_set]
    unexpected_targets = [target for target in emitted_targets if target not in expected_set] if declared else []
    entries: list[dict[str, Any]] = []

    for target_set, source in declared:
        targets = expanded[target_set]
        covered = [target for target in targets if target in emitted_set]
        missing = [target for target in targets if target not in emitted_set]
        entries.append(
            {
                "name": target_set,
                "source": source,
                "expected_targets": targets,
                "covered_targets": covered,
                "missing_targets": missing,
                "complete": not missing,
            }
        )

    if declared and (missing_targets or unexpected_targets):
        detail = []
        if missing_targets:
            detail.append("missing=" + ",".join(missing_targets))
        if unexpected_targets:
            detail.append("unexpected=" + ",".join(unexpected_targets))
        raise SystemExit("target-set coverage mismatch: " + " ".join(detail))

    return {
        "schema": TARGET_SET_COVERAGE_SCHEMA,
        "status": "complete" if declared else "not_declared",
        "complete": not missing_targets and not unexpected_targets,
        "declared_target_sets": entries,
        "expected_targets": expected_targets,
        "emitted_targets": emitted_targets,
        "missing_targets": missing_targets,
        "unexpected_targets": unexpected_targets,
    }


def build_report(
    *,
    snapshot_root: Path = DEFAULT_SNAPSHOT_ROOT,
    target_sets: list[str] | None = None,
    source_target_sets: list[str] | None = None,
    snapshots: list[Path] | None = None,
) -> dict[str, Any]:
    target_sets = target_sets or []
    source_target_sets = source_target_sets or []
    snapshots = snapshots or []
    if source_target_sets and not snapshots:
        raise SystemExit("--source-target-set requires at least one --snapshot")
    manifest_paths, missing_targets = snapshot_paths_from_target_sets(snapshot_root, target_sets)
    if missing_targets:
        raise SystemExit("target-set manifest missing targets: " + ",".join(missing_targets))
    all_paths = [*manifest_paths, *snapshots]
    if not all_paths:
        raise SystemExit("provide at least one --target-set or --snapshot")

    signatures: list[dict[str, Any]] = []
    seen_targets: set[str] = set()
    input_snapshots = [
        {"id": f"snapshot-{index:04d}", "sha256": file_sha256(path)}
        for index, path in enumerate(all_paths, start=1)
    ]
    for path, source_snapshot in zip(all_paths, input_snapshots, strict=True):
        for signature in build_from_snapshot(path, source_snapshot):
            target = signature["target"]
            if target in seen_targets:
                raise SystemExit(f"duplicate target in signature inputs: {target}")
            signatures.append(signature)
            seen_targets.add(target)
    emitted_targets = [signature["target"] for signature in signatures]
    coverage = target_set_coverage(
        manifest_target_sets=target_sets,
        source_target_sets=source_target_sets,
        emitted_targets=emitted_targets,
    )
    all_target_sets = [*target_sets, *source_target_sets]

    return {
        "schema": OUTPUT_SCHEMA,
        "generated_from": {
            "snapshot_schema": SUPPORTED_SNAPSHOT_SCHEMA,
            "input_snapshots": input_snapshots,
        },
        "snapshot_root": "redacted",
        "target_sets": target_sets,
        "source_target_sets": source_target_sets,
        "target_set_coverage": coverage,
        "snapshot_count": len(all_paths),
        "signature_count": len(signatures),
        "missing_targets": missing_targets,
        "safety_summary": safety_summary(
            signatures,
            snapshot_count=len(all_paths),
            target_sets=all_target_sets,
            missing_targets=missing_targets,
        ),
        "signatures": signatures,
        "non_claims": [
            "candidate-only redacted UFunction signature report",
            "does not promote public SDK callbacks or public metadata helpers",
            "does not expose UE pointers, object identity, class identity, raw params, mutation, or return overrides",
        ],
    }


def print_text(report: dict[str, Any]) -> None:
    for signature in report["signatures"]:
        print(
            "{target} flags={function_flags} parms={num_parms} size={parms_size} ret={return_value_offset}".format(
                **signature
            )
        )
        for param in signature["params"]:
            flags = ",".join(param["property_flag_labels"])
            print(
                "  {direction} {name}: {type} offset={offset} size={element_size} array_dim={array_dim} flags={flags}".format(
                    flags=flags,
                    **param,
                )
            )
        for field in signature["blocked_properties"]:
            print(
                "  blocked {name} class={source_property_class} status={status} reason={reason}".format(
                    **field
                )
            )
    if report["missing_targets"]:
        print("missing targets:")
        for target in report["missing_targets"]:
            print(f"  {target}")


def main() -> int:
    args = parse_args()
    report = build_report(
        snapshot_root=args.snapshot_root,
        target_sets=args.target_set,
        source_target_sets=args.source_target_set,
        snapshots=args.snapshot,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_text(report)
    return 1 if report["missing_targets"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
