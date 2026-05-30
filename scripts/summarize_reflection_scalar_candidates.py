#!/usr/bin/env python3
"""Summarize copied-scalar candidates from sanitized reflection snapshots."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import protected_paths
from reflection_target_sets import TARGET_SETS


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT_ROOT = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"
SUPPORTED_SCHEMA = "obelisk.ufunction-chain.snapshot.v1"
PROTECTED_SERVER_ROOT = Path("/servidor/ark")
APPROVED_OFFLINE_WORKSPACE_ROOTS = (Path("/servidor/ark/workspace-offline"),)
COPIED_BOOL_CLASS = "BoolProperty"
COPIED_INT32_CLASS = "IntProperty"
REDACTED_CLASSES = {
    "ArrayProperty",
    "ClassProperty",
    "ObjectProperty",
    "StrProperty",
    "StructProperty",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Classify sanitized UFunction snapshot fields as copied scalar candidates "
            "or redacted fields without reading cores or touching servers."
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
        required=True,
        choices=sorted(TARGET_SETS),
        help="Named UFunction target set to summarize. Repeatable.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser.parse_args()


def load_manifest(snapshot_root: Path) -> dict[str, Any]:
    reject_protected_input_path("snapshot root", snapshot_root)
    manifest_path = snapshot_root / "manifest.json"
    reject_protected_input_path("snapshot manifest", manifest_path)
    if not manifest_path.is_file():
        raise SystemExit(f"missing snapshot manifest: {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def is_under_path(path: Path, root: Path) -> bool:
    return protected_paths.is_under_path(path, root)


def is_approved_offline_workspace_path(path: Path) -> bool:
    return protected_paths.is_approved_offline_workspace_path(
        path,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )


def reject_protected_input_path(label: str, path: Path) -> None:
    protected_paths.reject_protected_input_path(
        path,
        label,
        protected_root=PROTECTED_SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
        message=f"{label} must not read from protected live-server path: {path}",
    )


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


def expand_ufunction_targets(target_sets: list[str]) -> list[str]:
    targets: list[str] = []
    seen: set[str] = set()
    for target_set in target_sets:
        for entry in TARGET_SETS[target_set]:
            schema, _, target = entry.partition(":")
            if schema != SUPPORTED_SCHEMA:
                continue
            if target not in seen:
                targets.append(target)
                seen.add(target)
    if not targets:
        raise SystemExit("target sets did not include UFunction snapshots")
    return targets


def require_single_target(payload: dict[str, Any], path: Path) -> dict[str, Any]:
    if payload.get("schema") != SUPPORTED_SCHEMA:
        raise SystemExit(f"unsupported snapshot schema in {path}: {payload.get('schema')!r}")
    targets = payload.get("targets")
    if not isinstance(targets, list) or len(targets) != 1 or not isinstance(targets[0], dict):
        raise SystemExit(f"snapshot must contain exactly one target: {path}")
    return targets[0]


def classify_property(prop: dict[str, Any]) -> dict[str, Any]:
    name = prop.get("name")
    class_name = prop.get("class_name")
    offset = prop.get("offset_internal")
    element_size = prop.get("element_size")
    array_dim = prop.get("array_dim")
    status = prop.get("status")

    if not isinstance(name, str) or not isinstance(class_name, str):
        raise SystemExit(f"invalid property identity: {prop!r}")

    field = {
        "name": name,
        "class_name": class_name,
        "offset": offset,
        "size": element_size,
        "array_dim": array_dim,
        "status": status,
    }

    if (
        class_name == COPIED_BOOL_CLASS
        and status == "candidate"
        and element_size == 1
        and array_dim == 1
    ):
        field["classification"] = "copied_bool"
        field["reason"] = "candidate BoolProperty with one byte element and array_dim=1"
    elif (
        class_name == COPIED_INT32_CLASS
        and status == "candidate"
        and element_size == 4
        and array_dim == 1
    ):
        field["classification"] = "copied_int32"
        field["reason"] = "candidate IntProperty with four byte element and array_dim=1"
    elif class_name in REDACTED_CLASSES:
        field["classification"] = "redacted"
        field["reason"] = f"{class_name} is not copied into internal scalar payloads"
    else:
        field["classification"] = "blocked"
        field["reason"] = f"unsupported or non-candidate property class: {class_name}"
    return field


def summarize_target(path: Path) -> dict[str, Any]:
    reject_protected_input_path("snapshot", path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    target_payload = require_single_target(payload, path)
    target_identity = target_payload.get("target")
    property_chain = target_payload.get("property_chain")
    if not isinstance(target_identity, dict) or not isinstance(property_chain, dict):
        raise SystemExit(f"snapshot missing target identity or property chain: {path}")
    properties = property_chain.get("properties")
    if not isinstance(properties, list):
        raise SystemExit(f"snapshot property_chain.properties must be a list: {path}")

    fields = [classify_property(prop) for prop in properties if isinstance(prop, dict)]
    return {
        "target": f"{target_identity.get('outer_name')}.{target_identity.get('name')}",
        "outer_name": target_identity.get("outer_name"),
        "name": target_identity.get("name"),
        "function_flags": target_payload.get("function_flags"),
        "num_parms": target_payload.get("num_parms"),
        "parms_size": target_payload.get("parms_size"),
        "return_value_offset": target_payload.get("return_value_offset"),
        "copied_fields": [
            field
            for field in fields
            if field["classification"] in {"copied_bool", "copied_int32"}
        ],
        "redacted_fields": [field for field in fields if field["classification"] == "redacted"],
        "blocked_fields": [field for field in fields if field["classification"] == "blocked"],
    }


def build_report(snapshot_root: Path, target_sets: list[str]) -> dict[str, Any]:
    manifest = load_manifest(snapshot_root)
    indexed = manifest_index(manifest, snapshot_root)
    targets = expand_ufunction_targets(target_sets)

    summaries = []
    missing = []
    for target in targets:
        path = indexed.get(target)
        if path is None or not path.is_file():
            missing.append(target)
            continue
        summaries.append(summarize_target(path))

    return {
        "schema": "obelisk.reflection-scalar-candidate-summary.v1",
        "snapshot_root": str(snapshot_root),
        "target_sets": target_sets,
        "target_count": len(targets),
        "summarized_count": len(summaries),
        "missing_targets": missing,
        "targets": summaries,
        "non_claims": [
            "candidate-only snapshot summary",
            "does not promote public SDK callbacks",
            "does not expose UE pointers, identity, arrays, raw params, mutation, or return overrides",
        ],
    }


def print_text(report: dict[str, Any]) -> None:
    for target in report["targets"]:
        print(
            "{target} flags={function_flags} parms={num_parms} size={parms_size} ret={return_value_offset}".format(
                **target
            )
        )
        for field in target["copied_fields"]:
            print("  {classification} {name} offset={offset} size={size}".format(**field))
        for field in target["redacted_fields"]:
            print("  redacted {name} class={class_name} reason={reason}".format(**field))
        for field in target["blocked_fields"]:
            print("  blocked {name} class={class_name} reason={reason}".format(**field))
    if report["missing_targets"]:
        print("missing targets:")
        for target in report["missing_targets"]:
            print(f"  {target}")


def main() -> int:
    args = parse_args()
    report = build_report(args.snapshot_root, args.target_set)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_text(report)
    return 1 if report["missing_targets"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
