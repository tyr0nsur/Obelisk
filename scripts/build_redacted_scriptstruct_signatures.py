#!/usr/bin/env python3
"""Build candidate-only redacted ScriptStruct signatures from sanitized snapshots."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT_ROOT = REPO_ROOT / "tests" / "fixtures" / "scriptstruct_snapshots"
SUPPORTED_SNAPSHOT_SCHEMA = "obelisk.scriptstruct-chain.snapshot.v1"
OUTPUT_SCHEMA = "obelisk.redacted-scriptstruct-signatures.v1"
TARGET_SET_COVERAGE_SCHEMA = "obelisk.redacted-scriptstruct-target-set-coverage.v1"
PROTECTED_SERVER_ROOT = Path("/servidor/ark")
APPROVED_OFFLINE_WORKSPACE_ROOTS = (Path("/servidor/ark/workspace-offline"),)
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

BOOL_MASK_KEYS = (
    "byte_mask",
    "field_mask",
    "bool_byte_mask",
    "bool_field_mask",
    "bitmask",
    "mask",
)

SENSITIVE_SCALAR_NAME_FRAGMENTS = (
    "id",
    "password",
    "pin",
    "steam",
    "token",
    "unique",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert sanitized ScriptStruct snapshots into redacted, candidate-only "
            "signature reports without reading cores or touching servers."
        )
    )
    parser.add_argument(
        "--snapshot-root",
        type=Path,
        default=DEFAULT_SNAPSHOT_ROOT,
        help="ScriptStruct snapshot root containing manifest.json and snapshot files.",
    )
    parser.add_argument(
        "--target-set",
        action="append",
        default=[],
        help="Named ScriptStruct target set from reflection_target_sets.py. Repeatable.",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        action="append",
        default=[],
        help="Sanitized ScriptStruct snapshot JSON to include directly. Repeatable.",
    )
    parser.add_argument(
        "--source-target-set",
        action="append",
        default=[],
        help=(
            "Named ScriptStruct target set covered by direct --snapshot inputs. Repeatable. "
            "The emitted signatures must exactly match the declared target set union."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
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


def expand_scriptstruct_target_sets(target_sets: list[str]) -> dict[str, list[str]]:
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
            raise SystemExit(f"target set did not include ScriptStruct snapshots: {target_set}")
        expanded[target_set] = targets
    return expanded


def expand_scriptstruct_targets(target_sets: list[str]) -> list[str]:
    targets: list[str] = []
    seen: set[str] = set()
    for entries in expand_scriptstruct_target_sets(target_sets).values():
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
    low = parse_int_value(prop.get("property_flags_low"))
    high = parse_int_value(prop.get("property_flags_high"))
    if low is None and high is None:
        return None
    return ((high or 0) << 32) | (low or 0)


def bool_masks(prop: dict[str, Any]) -> dict[str, Any]:
    masks: dict[str, Any] = {}
    for key in BOOL_MASK_KEYS:
        value = parse_int_value(prop.get(key))
        if value is not None and 0 < value <= 0xFF:
            masks[key] = f"0x{value:02x}" if value < 0x10 else f"0x{value:x}"
    return masks


def is_sensitive_scalar_name(name: str) -> bool:
    lowered = name.lower()
    return any(fragment in lowered for fragment in SENSITIVE_SCALAR_NAME_FRAGMENTS)


def append_membership_blocker(blockers: list[str], prop: dict[str, Any], key: str) -> None:
    if prop.get(key) != CANDIDATE_UOBJECT_STATUS:
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
    blockers: list[str] = ["scriptstruct_payload_not_runtime_observed"]
    if property_flags(prop) is None:
        blockers.append("property_flags_missing")
    append_membership_blocker(blockers, prop, "membership_status")
    append_membership_blocker(blockers, prop, "class_membership_status")
    append_membership_blocker(blockers, prop, "outer_membership_status")
    append_nested_membership_blockers(blockers, prop, "array_inner_candidate")
    append_nested_membership_blockers(blockers, prop, "struct_type_candidate")
    if prop.get("class_name") == "BoolProperty" and not bool_masks(prop) and prop.get("native_bool") is not True:
        blockers.append("bool_semantics_missing_mask_or_native_bool_marker")
    return sorted(set(blockers))


def redacted_type(prop: dict[str, Any]) -> tuple[str, str]:
    class_name = prop.get("class_name")
    name = prop.get("name")
    if not isinstance(class_name, str) or not class_name:
        return "blocked_unknown", "missing property class"
    if not isinstance(name, str) or not name:
        return "blocked_unknown", "missing property name"
    if class_name in SCALAR_TYPE_BY_CLASS and is_sensitive_scalar_name(name):
        return "redacted_sensitive_scalar", "identity-like scalar redacted by name"
    if class_name in SCALAR_TYPE_BY_CLASS:
        if class_name in {"ByteProperty", "EnumProperty"}:
            return SCALAR_TYPE_BY_CLASS[class_name], "enum identity redacted"
        return SCALAR_TYPE_BY_CLASS[class_name], "copied scalar candidate"
    if class_name in REDACTED_TYPE_BY_CLASS:
        return REDACTED_TYPE_BY_CLASS[class_name], f"{class_name} identity/payload redacted"
    return "blocked_unknown", f"unsupported property class: {class_name}"


def classify_property(prop: dict[str, Any]) -> dict[str, Any]:
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
        "type": type_name,
        "source_property_class": class_name,
        "offset": prop.get("offset_internal"),
        "element_size": prop.get("element_size"),
        "array_dim": prop.get("array_dim"),
        "status": prop.get("status"),
        "redaction": reason,
    }
    if flags is not None:
        field["property_flags"] = f"0x{flags:x}"
    if class_name == "BoolProperty":
        masks = bool_masks(prop)
        if masks:
            field["bool_masks"] = masks

    nested = prop.get("array_inner_candidate")
    if isinstance(nested, dict):
        inner = nested.get("inner_property")
        if isinstance(inner, dict):
            field["array_inner"] = {
                "source_property_class": inner.get("class_name"),
                "redaction": "array inner identity redacted",
            }

    nested = prop.get("struct_type_candidate")
    if isinstance(nested, dict):
        struct_type = nested.get("struct_type")
        if isinstance(struct_type, dict):
            field["struct_type"] = {
                "source_property_class": struct_type.get("class_name"),
                "redaction": "struct type identity redacted",
            }

    blockers = promotion_blockers_for_property(prop)
    if blockers:
        field["promotion_blockers"] = blockers
    return field


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

    fields = [classify_property(prop) for prop in properties if isinstance(prop, dict)]
    signature: dict[str, Any] = {
        "target": target_name(target_identity),
        "outer_name": target_identity.get("outer_name"),
        "name": target_identity.get("name"),
        "properties_size": target_payload.get("properties_size"),
        "min_alignment": target_payload.get("min_alignment"),
        "property_count": len(fields),
        "property_chain_status": property_chain.get("status"),
        "fields": fields,
        "promotion_blockers": sorted(
            {
                "scriptstruct_layout_candidate_only",
                "no_runtime_payload_ownership_policy",
                "no_public_scriptstruct_sdk",
            }
        ),
    }
    if source_snapshot:
        signature.update(source_snapshot)
    return signature


def load_snapshot_signatures(path: Path, source_snapshot: dict[str, str] | None = None) -> list[dict[str, Any]]:
    payload = load_json_file("snapshot", path)
    return [build_target_signature(target, path, source_snapshot) for target in require_snapshot_payload(payload, path)]


def summarize_safety(signatures: list[dict[str, Any]]) -> dict[str, Any]:
    scalar_counts: dict[str, int] = {}
    redacted_counts: dict[str, int] = {}
    blocker_counts: dict[str, int] = {}
    scalar_total = 0
    redacted_total = 0
    field_total = 0

    for signature in signatures:
        for blocker in signature.get("promotion_blockers", []):
            blocker_counts[blocker] = blocker_counts.get(blocker, 0) + 1
        fields = signature.get("fields", [])
        if not isinstance(fields, list):
            continue
        for field in fields:
            if not isinstance(field, dict):
                continue
            field_total += 1
            field_type = field.get("type")
            if not isinstance(field_type, str):
                continue
            if field_type.startswith("redacted_"):
                redacted_total += 1
                redacted_counts[field_type.removeprefix("redacted_")] = (
                    redacted_counts.get(field_type.removeprefix("redacted_"), 0) + 1
                )
            elif field_type != "blocked_unknown":
                scalar_total += 1
                scalar_counts[field_type] = scalar_counts.get(field_type, 0) + 1
            for blocker in field.get("promotion_blockers", []):
                blocker_counts[blocker] = blocker_counts.get(blocker, 0) + 1

    return {
        "artifact_status": "candidate_only",
        "promotion_ready": False,
        "intended_use": "offline_review_only",
        "field_count_total": field_total,
        "copied_scalar_count_total": scalar_total,
        "copied_scalar_by_kind": dict(sorted(scalar_counts.items())),
        "redacted_count_total": redacted_total,
        "redacted_by_reason": dict(sorted(redacted_counts.items())),
        "promotion_blocker_count_total": sum(blocker_counts.values()),
        "promotion_blockers_by_reason": dict(sorted(blocker_counts.items())),
        "not_promoted_surfaces": [
            "public_scriptstruct_sdk",
            "transfer_payload_decoding",
            "resource_handle",
            "object_identity",
            "mutation",
            "return_override",
            "raw_ue_params",
        ],
    }


def target_set_coverage(
    target_sets: list[str],
    expected_targets: list[str],
    observed_targets: list[str],
    source: str,
) -> dict[str, Any]:
    missing = [target for target in expected_targets if target not in observed_targets]
    unexpected = [target for target in observed_targets if target not in expected_targets]
    return {
        "schema": TARGET_SET_COVERAGE_SCHEMA,
        "status": "complete" if not missing and not unexpected else "incomplete",
        "complete": not missing and not unexpected,
        "source": source,
        "declared_target_sets": target_sets,
        "expected_targets": expected_targets,
        "observed_targets": observed_targets,
        "missing_targets": missing,
        "unexpected_targets": unexpected,
    }


def redacted_source_snapshots(paths: list[Path]) -> list[dict[str, str]]:
    snapshots = []
    for index, path in enumerate(paths, start=1):
        snapshots.append({"id": f"snapshot-{index:04d}", "sha256": file_sha256(path)})
    return snapshots


def build_report(
    *,
    snapshot_root: Path | None = None,
    target_sets: list[str] | None = None,
    snapshots: list[Path] | None = None,
    source_target_sets: list[str] | None = None,
) -> dict[str, Any]:
    snapshot_root = snapshot_root or DEFAULT_SNAPSHOT_ROOT
    target_sets = target_sets or []
    snapshots = snapshots or []
    source_target_sets = source_target_sets or []
    signatures: list[dict[str, Any]] = []
    missing_targets: list[str] = []
    coverage: dict[str, Any] | None = None
    source_paths: list[Path] = []

    if target_sets:
        manifest = load_manifest(snapshot_root)
        indexed = manifest_index(manifest, snapshot_root)
        expected_targets = expand_scriptstruct_targets(target_sets)
        for target in expected_targets:
            path = indexed.get(target)
            if path is None or not path.is_file():
                missing_targets.append(target)
                continue
            source_paths.append(path)
            signatures.extend(load_snapshot_signatures(path))
        observed_targets = [signature["target"] for signature in signatures]
        coverage = target_set_coverage(target_sets, expected_targets, observed_targets, "manifest")

    if snapshots:
        direct_source = redacted_source_snapshots(snapshots)
        before = len(signatures)
        for path, source in zip(snapshots, direct_source, strict=True):
            source_paths.append(path)
            signatures.extend(load_snapshot_signatures(path, {"source_snapshot": source["id"], "source_snapshot_sha256": source["sha256"]}))
        if source_target_sets:
            expected_targets = expand_scriptstruct_targets(source_target_sets)
            observed_targets = [signature["target"] for signature in signatures[before:]]
            coverage = target_set_coverage(source_target_sets, expected_targets, observed_targets, "direct")
            if not coverage["complete"]:
                missing_targets.extend(coverage["missing_targets"])

    if not target_sets and not snapshots:
        raise SystemExit("provide --target-set or --snapshot")

    report = {
        "schema": OUTPUT_SCHEMA,
        "snapshot_root": "redacted",
        "target_sets": target_sets,
        "source_target_sets": source_target_sets,
        "snapshot_count": len(source_paths),
        "signature_count": len(signatures),
        "missing_targets": sorted(set(missing_targets)),
        "generated_from": {
            "snapshot_schema": SUPPORTED_SNAPSHOT_SCHEMA,
            "input_snapshots": redacted_source_snapshots(source_paths),
        },
        "safety_summary": summarize_safety(signatures),
        "signatures": signatures,
        "non_claims": [
            "candidate-only ScriptStruct layout summary",
            "does not promote public ScriptStruct or Transfer SDK callbacks",
            "does not decode transfer payloads or expose UE pointers, identity, raw params, mutation, or return overrides",
        ],
    }
    if coverage is not None:
        report["target_set_coverage"] = coverage
    return report


def print_text(report: dict[str, Any]) -> None:
    for signature in report["signatures"]:
        print(
            "{target} properties={property_count} size={properties_size} alignment={min_alignment}".format(
                **signature
            )
        )
        for field in signature["fields"]:
            print(
                "  {type} {name} class={source_property_class} offset={offset} size={element_size} array_dim={array_dim}".format(
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
        snapshots=args.snapshot,
        source_target_sets=args.source_target_set,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_text(report)
    return 1 if report["missing_targets"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
