#!/usr/bin/env python3
"""Offline UProperty redaction and planning-metadata coverage checker.

This checker consumes sanitized reflection JSON only. It does not read cores, decode
payloads, look up UE objects, mutate state, or publish an ABI contract.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import protected_paths


REPO_ROOT = Path(__file__).resolve().parents[1]
UFUNCTION_SCHEMA = "obelisk.ufunction-chain.snapshot.v1"
SCRIPTSTRUCT_SCHEMA = "obelisk.scriptstruct-chain.snapshot.v1"
REPORT_SCHEMA = "obelisk.reflection-property-redaction-coverage-check.v1"
PROTECTED_SERVER_ROOT = Path("/servidor/ark")
APPROVED_OFFLINE_WORKSPACE_ROOTS = (Path("/servidor/ark/workspace-offline"),)

DEFAULT_REQUIRED_COVERAGE = (
    "ArrayProperty",
    "ArrayProperty.Inner",
    "BoolProperty",
    "ByteProperty",
    "ClassProperty",
    "IntProperty",
    "ObjectProperty",
    "StrProperty",
    "StructProperty",
    "UInt64Property",
)

SCALAR_METADATA_CLASSES = {
    "BoolProperty": "bool_metadata",
    "ByteProperty": "byte_or_enum_metadata",
    "IntProperty": "int32_metadata",
    "UInt64Property": "uint64_metadata",
}

REDACTED_CLASSES = {
    "ArrayProperty": "container_redacted",
    "ClassProperty": "class_ref_redacted",
    "ObjectProperty": "uobject_ref_redacted",
    "StrProperty": "fstring_redacted",
    "StructProperty": "struct_redacted",
}

IDENTITY_KEYS = (
    "class_name_index",
    "class_object_index",
    "enum",
    "enum_name",
    "inner_class_name",
    "name_index",
    "object_index",
    "outer_name_index",
    "outer_object_index",
    "property_class_name",
    "struct",
    "struct_name",
    "value",
)

SENSITIVE_SCALAR_NAMES = {
    "eosid",
    "ownerplayerid",
    "ownertribeid",
    "password",
    "playerdataid",
    "playerid",
    "playersteamid",
    "pincode",
    "platformid",
    "steamid",
    "targetingteam",
    "tribeid",
}

NON_CLAIMS = (
    "planning-only metadata coverage",
    "does not decode UE parameter payloads or FString contents",
    "does not expose object identity, lookup, ResourceHandle, raw params, or UE pointers",
    "does not authorize mutation, return override, runtime observation, public callbacks, or public ABI",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate offline reflection property coverage, redaction policy, and UFunction ParmsSize bounds."
    )
    parser.add_argument(
        "--artifact",
        action="append",
        type=Path,
        default=[],
        help="Sanitized reflection snapshot JSON to check. Repeatable.",
    )
    parser.add_argument(
        "--snapshot-root",
        type=Path,
        help="Root to scan recursively for *.snapshot.json artifacts.",
    )
    parser.add_argument(
        "--require-class",
        action="append",
        default=[],
        help="Require a property coverage key such as BoolProperty or ArrayProperty.Inner. Repeatable.",
    )
    parser.add_argument(
        "--require-default-coverage",
        action="store_true",
        help="Require the default generic UProperty class coverage set.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON. The default text form is concise.")
    return parser.parse_args()


def reject_protected_input_path(label: str, path: Path) -> None:
    protected_paths.reject_protected_input_path(
        path,
        label,
        protected_root=PROTECTED_SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
        message=f"{label} must not read from protected live-server path: {path}",
    )


def parse_int(value: Any) -> int | None:
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


def is_sensitive_scalar_name(name: str) -> bool:
    normalized = "".join(ch for ch in name.lower() if ch.isalnum())
    return normalized in SENSITIVE_SCALAR_NAMES


def identity_redaction_notes(prop: dict[str, Any]) -> list[str]:
    return [
        f"{key}_redacted"
        for key in IDENTITY_KEYS
        if prop.get(key) not in (None, "", [], {})
    ]


def classify_policy(prop: dict[str, Any]) -> tuple[str, str]:
    class_name = prop.get("class_name")
    name = prop.get("name")
    if not isinstance(class_name, str) or not class_name:
        return "blocked_unknown", "missing property class"
    if isinstance(name, str) and class_name in SCALAR_METADATA_CLASSES and is_sensitive_scalar_name(name):
        return "redacted_sensitive_scalar", "identity-like scalar redacted by name"
    if class_name in SCALAR_METADATA_CLASSES:
        if class_name == "ByteProperty":
            return SCALAR_METADATA_CLASSES[class_name], "byte value metadata only; enum identity redacted"
        return SCALAR_METADATA_CLASSES[class_name], "planning scalar metadata only"
    if class_name in REDACTED_CLASSES:
        return REDACTED_CLASSES[class_name], f"{class_name} identity/payload redacted"
    return "blocked_unknown", f"unsupported property class: {class_name}"


def target_label(target: dict[str, Any]) -> str:
    identity = target.get("target")
    if not isinstance(identity, dict):
        return "<unknown-target>"
    outer = identity.get("outer_name")
    name = identity.get("name")
    if isinstance(outer, str) and isinstance(name, str):
        return f"{outer}.{name}"
    return "<unknown-target>"


def bound_for_target(schema: str, target: dict[str, Any]) -> tuple[str, int | None]:
    if schema == UFUNCTION_SCHEMA:
        return "ParmsSize", parse_int(target.get("parms_size"))
    if schema == SCRIPTSTRUCT_SCHEMA:
        return "PropertiesSize", parse_int(target.get("properties_size"))
    return "unknown", None


def check_bounds(
    *,
    field: dict[str, Any],
    target: str,
    prop: dict[str, Any],
    bound_name: str,
    bound: int | None,
    blockers: list[dict[str, Any]],
) -> None:
    offset = parse_int(prop.get("offset_internal"))
    element_size = parse_int(prop.get("element_size"))
    array_dim = parse_int(prop.get("array_dim"))
    field["offset"] = offset
    field["element_size"] = element_size
    field["array_dim"] = array_dim
    if offset is None or element_size is None or array_dim is None or array_dim < 1:
        blockers.append(
            {
                "reason": "property_bounds_metadata_missing",
                "target": target,
                "property": field["name"],
                "class": field["class"],
            }
        )
        return
    end = offset + (element_size * array_dim)
    field["end_offset"] = end
    if bound is not None:
        field["bound"] = bound
        field["bound_name"] = bound_name
        if offset < 0 or element_size < 0 or end > bound:
            blockers.append(
                {
                    "reason": "property_exceeds_target_bounds",
                    "target": target,
                    "property": field["name"],
                    "class": field["class"],
                    "offset": offset,
                    "element_size": element_size,
                    "array_dim": array_dim,
                    "end_offset": end,
                    "bound_name": bound_name,
                    "bound": bound,
                }
            )
    elif bound_name == "ParmsSize":
        blockers.append(
            {
                "reason": "ufunction_parms_size_missing",
                "target": target,
                "property": field["name"],
                "class": field["class"],
            }
        )


def classify_property(
    *,
    schema: str,
    artifact_id: str,
    target: str,
    bound_name: str,
    bound: int | None,
    prop: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    name = prop.get("name")
    class_name = prop.get("class_name")
    if not isinstance(name, str) or not name:
        name = "<unnamed>"
    if not isinstance(class_name, str) or not class_name:
        class_name = "<unknown-class>"

    policy, policy_reason = classify_policy(prop)
    field = {
        "artifact": artifact_id,
        "target": target,
        "name": name,
        "class": class_name,
        "coverage_key": class_name,
        "status": prop.get("status"),
        "policy": policy,
        "policy_reason": policy_reason,
        "identity_redaction": identity_redaction_notes(prop),
        "payload_decode_claim": False,
        "planning_only": True,
    }
    if class_name == "StrProperty":
        field["fstring_policy"] = "redacted"
    if class_name == "ByteProperty":
        field["enum_metadata_policy"] = "metadata_only_identity_redacted"
    check_bounds(
        field=field,
        target=target,
        prop=prop,
        bound_name=bound_name,
        bound=bound,
        blockers=blockers,
    )

    fields = [field]
    if class_name == "ArrayProperty":
        nested = prop.get("array_inner_candidate")
        inner = nested.get("inner_property") if isinstance(nested, dict) else None
        if isinstance(inner, dict):
            inner_class = inner.get("class_name")
            fields.append(
                {
                    "artifact": artifact_id,
                    "target": target,
                    "name": f"{name}.Inner",
                    "class": inner_class if isinstance(inner_class, str) else "<unknown-class>",
                    "coverage_key": "ArrayProperty.Inner",
                    "status": inner.get("status", prop.get("status")),
                    "policy": "array_inner_metadata_redacted",
                    "policy_reason": "ArrayProperty inner identity is metadata-only and redacted",
                    "identity_redaction": identity_redaction_notes(inner),
                    "payload_decode_claim": False,
                    "planning_only": True,
                }
            )
        else:
            blockers.append(
                {
                    "reason": "array_inner_metadata_missing",
                    "target": target,
                    "property": name,
                    "class": class_name,
                }
            )
    return fields


def iter_targets(payload: dict[str, Any], path: Path) -> tuple[str, list[dict[str, Any]]]:
    schema = payload.get("schema")
    if schema not in {UFUNCTION_SCHEMA, SCRIPTSTRUCT_SCHEMA}:
        raise SystemExit(f"unsupported reflection artifact schema in {path}: {schema!r}")
    targets = payload.get("targets")
    if not isinstance(targets, list):
        raise SystemExit(f"reflection artifact targets must be a list: {path}")
    return schema, [target for target in targets if isinstance(target, dict)]


def collect_artifact_paths(args: argparse.Namespace) -> list[Path]:
    paths: list[Path] = []
    for path in args.artifact:
        reject_protected_input_path("artifact", path)
        paths.append(path)
    if args.snapshot_root is not None:
        reject_protected_input_path("snapshot root", args.snapshot_root)
        if not args.snapshot_root.is_dir():
            raise SystemExit(f"snapshot root is not a directory: {args.snapshot_root}")
        for path in sorted(args.snapshot_root.rglob("*.snapshot.json")):
            reject_protected_input_path("snapshot", path)
            paths.append(path)
    if not paths:
        raise SystemExit("provide --artifact or --snapshot-root")
    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved not in seen:
            deduped.append(path)
            seen.add(resolved)
    return deduped


def build_report(paths: list[Path], required_classes: list[str]) -> dict[str, Any]:
    fields: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    artifact_summaries: list[dict[str, Any]] = []

    for index, path in enumerate(paths, start=1):
        reject_protected_input_path("artifact", path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise SystemExit(f"reflection artifact must be a JSON object: {path}")
        artifact_id = f"artifact-{index:04d}"
        schema, targets = iter_targets(payload, path)
        artifact_summaries.append({"id": artifact_id, "schema": schema, "path": "redacted"})
        for target_payload in targets:
            label = target_label(target_payload)
            bound_name, bound = bound_for_target(schema, target_payload)
            chain = target_payload.get("property_chain")
            properties = chain.get("properties") if isinstance(chain, dict) else None
            if not isinstance(properties, list):
                blockers.append(
                    {
                        "reason": "property_chain_missing",
                        "artifact": artifact_id,
                        "target": label,
                    }
                )
                continue
            for prop in properties:
                if isinstance(prop, dict):
                    fields.extend(
                        classify_property(
                            schema=schema,
                            artifact_id=artifact_id,
                            target=label,
                            bound_name=bound_name,
                            bound=bound,
                            prop=prop,
                            blockers=blockers,
                        )
                    )

    coverage_counts = Counter(field["coverage_key"] for field in fields)
    policy_counts = Counter(field["policy"] for field in fields)
    missing = [class_name for class_name in required_classes if coverage_counts.get(class_name, 0) == 0]
    for class_name in missing:
        blockers.append({"reason": "required_property_class_missing", "class": class_name})

    return {
        "schema": REPORT_SCHEMA,
        "artifact_count": len(artifact_summaries),
        "artifacts": artifact_summaries,
        "required_coverage": required_classes,
        "coverage": dict(sorted(coverage_counts.items())),
        "policy_counts": dict(sorted(policy_counts.items())),
        "field_count": len(fields),
        "fields": fields,
        "blockers": blockers,
        "ok": not blockers,
        "non_claims": list(NON_CLAIMS),
    }


def print_text(report: dict[str, Any]) -> None:
    status = "ok" if report["ok"] else "blocked"
    print(f"{status}: artifacts={report['artifact_count']} fields={report['field_count']}")
    print("coverage:")
    for class_name, count in report["coverage"].items():
        print(f"  {class_name}: {count}")
    if report["blockers"]:
        print("blockers:")
        for blocker in report["blockers"]:
            print(f"  {blocker['reason']}: {json.dumps(blocker, sort_keys=True)}")


def main() -> int:
    args = parse_args()
    paths = collect_artifact_paths(args)
    required = list(args.require_class)
    if args.require_default_coverage:
        required.extend(class_name for class_name in DEFAULT_REQUIRED_COVERAGE if class_name not in required)
    report = build_report(paths, required)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_text(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
