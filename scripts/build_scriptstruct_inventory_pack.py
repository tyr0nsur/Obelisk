#!/usr/bin/env python3
"""Build a candidate-only offline ScriptStruct inventory pack from copied core evidence."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import inspect_core_ufunctions as inspector  # noqa: E402
import reflection_target_sets  # noqa: E402
import scan_core_fname_tables as fname_scanner  # noqa: E402
import summarize_core_ufunction_inventory as ufunction_inventory  # noqa: E402
from snapshot_evidence_pack import (  # noqa: E402
    SHA256_RE,
    evidence_pack_defaults,
    reject_protected_input_path,
    reject_protected_output_path,
    require_ignored_output_path,
    safe_component,
    sha256_file,
)


PACK_SCHEMA = "obelisk.scriptstruct-inventory-pack.v1"
INVENTORY_SCHEMA = "obelisk.scriptstruct-inventory.v1"
TARGET_SET_COVERAGE_SCHEMA = "obelisk.scriptstruct-inventory-target-set-coverage.v1"
SCRIPTSTRUCT_SNAPSHOT_SCHEMA = "obelisk.scriptstruct-chain.snapshot.v1"
DEFAULT_MAX_OBJECTS = ufunction_inventory.DEFAULT_MAX_OBJECTS
DEFAULT_MAX_GROUPS = 20
DEFAULT_WINDOW_SIZE = 0xC0
SCRIPTSTRUCT_TARGET_SETS = sorted(
    name
    for name in reflection_target_sets.TARGET_SETS
    if reflection_target_sets.schema_targets(name, SCRIPTSTRUCT_SNAPSHOT_SCHEMA)
)


def parse_index(value: str) -> tuple[str, int]:
    return fname_scanner.parse_index(value)


def parse_target(value: str) -> tuple[str, str]:
    outer, separator, name = value.rpartition(".")
    if not separator or not outer or not name:
        raise argparse.ArgumentTypeError("target must be Outer.Name")
    return outer, name


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a candidate-only offline ScriptStruct inventory pack.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--core", type=Path, help="Copied/offline ELF core path.")
    source.add_argument("--evidence-pack-manifest", type=Path, help="Validated core evidence-pack manifest.")
    parser.add_argument("--binary", type=Path, help="Copied/offline ShooterGameServer path for direct mode identity.")
    parser.add_argument("--ark-binary-sha256", help="Expected lowercase ShooterGameServer SHA256.")
    parser.add_argument("--gobjects", type=ufunction_inventory.parse_int)
    parser.add_argument("--fname-root-slot", type=ufunction_inventory.parse_int)
    parser.add_argument("--evidence-pack-fname-root-label")
    parser.add_argument("--evidence-pack-gobjects-label")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--artifact-kind", default="offline_core")
    parser.add_argument("--capture-id")
    parser.add_argument("--evidence-pack-id")
    parser.add_argument("--max-objects", type=int, default=DEFAULT_MAX_OBJECTS)
    parser.add_argument("--max-groups", type=int, default=DEFAULT_MAX_GROUPS)
    parser.add_argument("--outer-contains", action="append", default=[])
    parser.add_argument("--name-contains", action="append", default=[])
    parser.add_argument("--target", action="append", type=parse_target, default=[], metavar="OUTER.NAME")
    parser.add_argument("--include-structs", action="store_true")
    parser.add_argument(
        "--target-set",
        action="append",
        choices=SCRIPTSTRUCT_TARGET_SETS,
        default=[],
        help="Report coverage against a named ScriptStruct target set.",
    )
    parser.add_argument(
        "--fname-index",
        action="append",
        type=parse_index,
        default=[],
        metavar="LABEL=INDEX",
        help="FName index expected from the root slot. Defaults to known Obelisk clues.",
    )
    parser.add_argument(
        "--no-default-fname-indices",
        action="store_true",
        help="Do not use built-in FName root validation clues.",
    )
    parser.add_argument("--plan-regeneration", action="store_true", help="Include a dry-run snapshot regeneration plan.")
    parser.add_argument("--snapshot-manifest", type=Path, help="Candidate-only ScriptStruct snapshot manifest.")
    return parser.parse_args()


def validate_binary_sha(value: str, label: str) -> str:
    if SHA256_RE.fullmatch(value) is None:
        raise SystemExit(f"{label} must be a lowercase 64-character SHA256")
    return value


def resolve_binary_sha(args: argparse.Namespace) -> str:
    if args.binary:
        binary_path = reject_protected_input_path(args.binary, "--binary")
        observed = sha256_file(binary_path)
        if args.ark_binary_sha256 and observed != args.ark_binary_sha256:
            raise SystemExit("--ark-binary-sha256 does not match --binary contents")
        return observed
    if not args.ark_binary_sha256:
        raise SystemExit("direct --core mode requires --binary or --ark-binary-sha256")
    return validate_binary_sha(args.ark_binary_sha256, "--ark-binary-sha256")


def load_evidence_defaults(args: argparse.Namespace) -> tuple[Path, int, int, str, str, str, str, str]:
    if args.gobjects is not None or args.fname_root_slot is not None or args.binary is not None:
        raise SystemExit("--evidence-pack-manifest reads binary/core/gobjects/fname root from manifest; do not pass overrides")
    manifest = reject_protected_input_path(args.evidence_pack_manifest, "--evidence-pack-manifest")
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    binary = payload.get("binary")
    binary_sha = binary.get("sha256") if isinstance(binary, dict) else None
    if not isinstance(binary_sha, str):
        raise SystemExit(f"{manifest}: evidence pack manifest must include binary.sha256")
    binary_sha = validate_binary_sha(binary_sha, f"{manifest}: binary.sha256")
    if args.ark_binary_sha256 and args.ark_binary_sha256 != binary_sha:
        raise SystemExit(f"{manifest}: binary.sha256 conflicts with --ark-binary-sha256")
    defaults = evidence_pack_defaults(
        manifest,
        args.evidence_pack_fname_root_label,
        args.evidence_pack_gobjects_label,
        binary_sha,
        ufunction_inventory.parse_int,
    )
    return (
        defaults.core_path,
        defaults.gobjects,
        defaults.fname_root_slot,
        binary_sha,
        defaults.artifact_kind,
        defaults.capture_id,
        defaults.evidence_pack_id,
        defaults.artifact_sha256,
    )


def reject_artifact_symlink(path: Path) -> None:
    if path.is_symlink():
        raise SystemExit(f"refusing to overwrite symlinked pack artifact: {path}")


def write_json(path: Path, payload: dict[str, object]) -> None:
    reject_artifact_symlink(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def scriptstruct_targets(target_sets: list[str]) -> list[str]:
    targets = sorted(reflection_target_sets.expand_schema_target_sets(target_sets, SCRIPTSTRUCT_SNAPSHOT_SCHEMA))
    return targets


def target_key(row: dict[str, object]) -> str:
    outer = str(row.get("outer_name") or "")
    name = str(row.get("name") or "")
    return f"{outer}.{name}" if outer and name else ""


def hex_value(value: object) -> str | None:
    if isinstance(value, int):
        return f"0x{value:x}"
    if isinstance(value, str) and value.startswith("0x"):
        return value
    return None


def redact_property(prop: dict[str, object]) -> dict[str, object]:
    row: dict[str, object] = {
        "depth": prop.get("depth"),
        "name": prop.get("name"),
        "class_name": prop.get("class_name"),
        "offset_internal": prop.get("offset_internal"),
        "element_size": prop.get("element_size"),
        "array_dim": prop.get("array_dim"),
        "property_flags": hex_value(prop.get("property_flags")),
        "status": prop.get("status"),
        "reject_reasons": prop.get("reject_reasons", []),
        "membership": {
            "property": prop.get("membership_status"),
            "class": prop.get("class_membership_status"),
            "outer": prop.get("outer_membership_status"),
        },
    }
    for key in ("bool_field_size", "bool_byte_offset", "byte_mask", "field_mask", "native_bool"):
        if key in prop:
            row[key] = prop.get(key)
    semantics = prop.get("bool_property_semantics")
    if isinstance(semantics, dict):
        row["bool_property_semantics"] = {
            "status": semantics.get("status"),
            "reject_reasons": semantics.get("reject_reasons", []),
            "bool_field_size": semantics.get("bool_field_size"),
            "bool_byte_offset": semantics.get("bool_byte_offset"),
        }
    array_inner = prop.get("array_inner_candidate")
    if isinstance(array_inner, dict):
        inner = array_inner.get("inner_property")
        row["array_inner"] = {
            "status": array_inner.get("status"),
            "membership_status": array_inner.get("membership_status"),
            "source_property_class": inner.get("class_name") if isinstance(inner, dict) else None,
            "redaction": "array inner identity redacted",
        }
    struct_type = prop.get("struct_type_candidate")
    if isinstance(struct_type, dict):
        struct = struct_type.get("struct_type")
        row["struct_type"] = {
            "status": struct_type.get("status"),
            "membership_status": struct_type.get("membership_status"),
            "source_struct_name": struct.get("name") if isinstance(struct, dict) else None,
            "redaction": "struct type identity redacted",
        }
    return row


def row_from_snapshot_target(target: dict[str, object]) -> dict[str, object]:
    target_summary = target.get("target") if isinstance(target.get("target"), dict) else {}
    chain = target.get("property_chain") if isinstance(target.get("property_chain"), dict) else {}
    properties = [
        redact_property(prop)
        for prop in chain.get("properties", [])
        if isinstance(prop, dict)
    ]
    class_counts = Counter(str(prop.get("class_name") or "<unknown>") for prop in properties)
    row = {
        "name": target_summary.get("name"),
        "outer_name": target_summary.get("outer_name"),
        "class_name": target_summary.get("class_name"),
        "status": target.get("status"),
        "reject_reasons": target.get("reject_reasons", []),
        "membership": target.get("membership"),
        "properties_size": target.get("properties_size"),
        "min_alignment": target.get("min_alignment"),
        "property_chain_status": chain.get("status"),
        "property_chain_reject_reasons": chain.get("reject_reasons", []),
        "observed_property_count": chain.get("observed_count"),
        "property_class_counts": dict(sorted(class_counts.items())),
        "properties": properties,
    }
    row["target"] = target_key(row)
    return row


def inspect_exact_target(
    memory: inspector.uobjects.CoreMemory,
    *,
    gobjects: int,
    fname_root_slot: int,
    outer: str,
    name: str,
    max_objects: int,
) -> list[dict[str, object]]:
    payload = inspector.inspect_core(
        memory,
        gobjects=gobjects,
        fname_root_slot=fname_root_slot,
        object_addresses=[],
        indices=[],
        name_contains=[],
        outer_contains=[],
        name_exact=[name],
        outer_exact=[outer],
        window_size=DEFAULT_WINDOW_SIZE,
        max_object_scan=max_objects,
        inspection_mode="script-struct",
    )
    snapshot = inspector.build_fixture_snapshot(payload)
    return [
        row_from_snapshot_target(target)
        for target in snapshot.get("targets", [])
        if isinstance(target, dict)
    ]


def collect_scriptstruct_rows(
    memory: inspector.uobjects.CoreMemory,
    *,
    gobjects: int,
    fname_root_slot: int,
    targets: list[tuple[str, str]],
    target_sets: list[str],
    name_contains: list[str],
    outer_contains: list[str],
    max_objects: int,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    requested: list[tuple[str, str]] = list(targets)
    for target in scriptstruct_targets(target_sets):
        requested.append(parse_target(target))

    rows: list[dict[str, object]] = []
    if requested:
        for outer, name in requested:
            rows.extend(
                inspect_exact_target(
                    memory,
                    gobjects=gobjects,
                    fname_root_slot=fname_root_slot,
                    outer=outer,
                    name=name,
                    max_objects=max_objects,
                )
            )
        metadata = {"object_count": None, "max_object_scan": max_objects, "collection_mode": "exact_targets"}
    else:
        payload = inspector.inspect_core(
            memory,
            gobjects=gobjects,
            fname_root_slot=fname_root_slot,
            object_addresses=[],
            indices=[],
            name_contains=name_contains,
            outer_contains=outer_contains,
            name_exact=[],
            outer_exact=[],
            window_size=DEFAULT_WINDOW_SIZE,
            max_object_scan=max_objects,
            inspection_mode="script-struct",
        )
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        snapshot = inspector.build_fixture_snapshot(payload)
        rows = [
            row_from_snapshot_target(target)
            for target in snapshot.get("targets", [])
            if isinstance(target, dict)
        ]
    deduped: list[dict[str, object]] = []
    seen: set[str] = set()
    for row in rows:
        key = target_key(row)
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        deduped.append(row)
    return metadata, deduped


def summarize_rows(rows: list[dict[str, object]], *, max_groups: int) -> dict[str, object]:
    outer_counts = Counter(str(row.get("outer_name") or "<no outer>") for row in rows)
    class_counts: Counter[str] = Counter()
    for row in rows:
        class_counts.update({str(key): int(value) for key, value in row.get("property_class_counts", {}).items()})
    return {
        "scriptstruct_count": len(rows),
        "candidate_count": sum(1 for row in rows if row.get("status") == "candidate"),
        "rejected_count": sum(1 for row in rows if row.get("status") == "rejected"),
        "top_outers": [{"outer": key, "count": value} for key, value in outer_counts.most_common(max_groups)],
        "top_property_classes": [
            {"class_name": key, "count": value} for key, value in class_counts.most_common(max_groups)
        ],
    }


def target_set_coverage(rows: list[dict[str, object]], *, target_sets: list[str]) -> dict[str, object]:
    if not target_sets:
        return {}
    requested_targets = scriptstruct_targets(target_sets)
    by_key: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        key = target_key(row)
        if key in requested_targets:
            by_key.setdefault(key, []).append(row)
    matched = {key: {"count": len(value)} for key, value in sorted(by_key.items())}
    missing = [target for target in requested_targets if target not in matched]
    ambiguous = [
        {"target": key, "count": len(value)}
        for key, value in sorted(by_key.items())
        if len(value) > 1
    ]
    return {
        "schema": TARGET_SET_COVERAGE_SCHEMA,
        "target_sets": target_sets,
        "requested_targets": requested_targets,
        "requested_count": len(requested_targets),
        "matched_count": len(matched),
        "missing_count": len(missing),
        "missing_targets": missing,
        "ambiguous_count": len(ambiguous),
        "ambiguous_targets": ambiguous,
        "matched_targets": matched,
    }


def target_set_regeneration_plan(
    *,
    target_sets: list[str],
    snapshot_manifest: Path | None,
    core: Path,
    gobjects: int,
    fname_root_slot: int,
    evidence_pack_manifest: Path | None,
    evidence_pack_fname_root_label: str | None,
    evidence_pack_gobjects_label: str | None,
) -> dict[str, object]:
    commands: list[dict[str, object]] = []
    for target in scriptstruct_targets(target_sets):
        command = [
            sys.executable,
            "scripts/regenerate_scriptstruct_snapshots.py",
            "--core",
            str(core),
            "--target",
            target,
        ]
        if snapshot_manifest is not None:
            command.extend(["--manifest", str(snapshot_manifest)])
        if evidence_pack_manifest is not None:
            command.extend(["--evidence-pack-manifest", str(evidence_pack_manifest)])
            if evidence_pack_fname_root_label is not None:
                command.extend(["--evidence-pack-fname-root-label", evidence_pack_fname_root_label])
            if evidence_pack_gobjects_label is not None:
                command.extend(["--evidence-pack-gobjects-label", evidence_pack_gobjects_label])
        else:
            command.extend(["--gobjects", hex(gobjects), "--fname-root-slot", hex(fname_root_slot)])
        commands.append({"target": target, "argv": command})
    return {
        "schema": "obelisk.scriptstruct-target-set-regeneration-plan.v1",
        "target_sets": target_sets,
        "snapshot_manifest": str(snapshot_manifest) if snapshot_manifest else None,
        "core": str(core),
        "evidence_pack_manifest": str(evidence_pack_manifest) if evidence_pack_manifest else None,
        "evidence_pack_fname_root_label": evidence_pack_fname_root_label,
        "evidence_pack_gobjects_label": evidence_pack_gobjects_label,
        "gobjects": hex(gobjects),
        "fname_root_slot": hex(fname_root_slot),
        "requested_count": len(commands),
        "planned_command_count": len(commands),
        "regenerate_commands": commands,
        "promotion_status": "not_promoted_candidate_only",
    }


def main() -> int:
    args = parse_args()
    if args.max_objects < 0:
        raise SystemExit("--max-objects must be non-negative")
    if args.max_groups <= 0:
        raise SystemExit("--max-groups must be positive")
    if args.plan_regeneration and not args.target_set:
        raise SystemExit("--plan-regeneration requires at least one --target-set")

    output_dir = reject_protected_output_path(args.output_dir, "--output-dir")
    require_ignored_output_path(output_dir, "--output-dir")
    if output_dir.exists() and output_dir.is_symlink():
        raise SystemExit(f"--output-dir must not be a symlink: {output_dir}")
    if args.snapshot_manifest:
        reject_protected_input_path(args.snapshot_manifest, "--snapshot-manifest")

    if args.evidence_pack_manifest:
        (
            core,
            gobjects,
            fname_root_slot,
            binary_sha,
            artifact_kind,
            capture_id,
            evidence_pack_id,
            core_sha,
        ) = load_evidence_defaults(args)
        evidence_pack_manifest = reject_protected_input_path(args.evidence_pack_manifest, "--evidence-pack-manifest")
    else:
        if args.gobjects is None or args.fname_root_slot is None:
            raise SystemExit("direct --core mode requires explicit --gobjects and --fname-root-slot")
        core = reject_protected_input_path(args.core, "--core")
        gobjects = args.gobjects
        fname_root_slot = args.fname_root_slot
        binary_sha = resolve_binary_sha(args)
        artifact_kind = safe_component(args.artifact_kind, "artifact-kind")
        capture_id = safe_component(args.capture_id or core.stem, "capture-id")
        evidence_pack_id = safe_component(args.evidence_pack_id or "direct-core", "evidence-pack-id")
        core_sha = sha256_file(core)
        evidence_pack_manifest = None

    output_dir.mkdir(parents=True, exist_ok=True)

    indices = args.fname_index if (args.fname_index or args.no_default_fname_indices) else fname_scanner.DEFAULT_INDICES
    memory = fname_scanner.CoreMemory(core)
    try:
        root_validation = fname_scanner.validate_root_slot(memory, fname_root_slot, indices)
        root_readiness = fname_scanner.root_validation_readiness(root_validation, indices)
        metadata, rows = collect_scriptstruct_rows(
            memory,
            gobjects=gobjects,
            fname_root_slot=fname_root_slot,
            targets=args.target,
            target_sets=args.target_set,
            name_contains=args.name_contains,
            outer_contains=args.outer_contains,
            max_objects=args.max_objects,
        )
        fname_table = memory.read_ptr(fname_root_slot)
    finally:
        memory.close()

    coverage = target_set_coverage(rows, target_sets=args.target_set)
    inventory_payload: dict[str, object] = {
        "schema": INVENTORY_SCHEMA,
        "status": "offline-inventory",
        "source": "offline_core",
        "promotion_status": "not_promoted_candidate_only",
        "metadata": metadata,
        "filters": {
            "targets": [f"{outer}.{name}" for outer, name in args.target],
            "target_sets": args.target_set,
            "outer_contains": args.outer_contains,
            "name_contains": args.name_contains,
        },
        "summary": summarize_rows(rows, max_groups=args.max_groups),
        "target_set_coverage": coverage,
    }
    if args.plan_regeneration:
        inventory_payload["target_set_regeneration_plan"] = target_set_regeneration_plan(
            target_sets=args.target_set,
            snapshot_manifest=args.snapshot_manifest,
            core=core,
            gobjects=gobjects,
            fname_root_slot=fname_root_slot,
            evidence_pack_manifest=evidence_pack_manifest,
            evidence_pack_fname_root_label=args.evidence_pack_fname_root_label,
            evidence_pack_gobjects_label=args.evidence_pack_gobjects_label,
        )
    if args.include_structs:
        inventory_payload["scriptstructs"] = rows

    fname_payload = {
        "schema": fname_scanner.ROOT_VALIDATION_SCHEMA,
        "core": str(core),
        "requested_indices": [{"label": label, "index": index} for label, index in indices],
        "root_validation": root_validation,
        "manifest_readiness": root_readiness,
        "candidate_manifest": {
            "path": None,
            "schema": None,
            "evidence_status": None,
            "name_count": 0,
        },
    }
    summary = {
        "scriptstruct_count": inventory_payload["summary"]["scriptstruct_count"],
        "fname_root_ready": root_readiness["ready"],
        "target_requested_count": coverage.get("requested_count", 0) if coverage else 0,
        "target_matched_count": coverage.get("matched_count", 0) if coverage else 0,
        "target_missing_count": coverage.get("missing_count", 0) if coverage else 0,
        "target_ambiguous_count": coverage.get("ambiguous_count", 0) if coverage else 0,
    }
    blockers = list(root_readiness["blockers"]) if root_readiness["ready"] is not True else []
    if summary["target_ambiguous_count"]:
        blockers.append("ambiguous_target_matches")
    if summary["target_missing_count"]:
        blockers.append("missing_target_matches")
    manifest_payload: dict[str, object] = {
        "schema": PACK_SCHEMA,
        "source": "offline_core",
        "status": "candidate-only",
        "promotion_status": "not_promoted_candidate_only",
        "artifact_identity": {
            "artifact_kind": artifact_kind,
            "artifact_sha256": core_sha,
            "capture_id": capture_id,
            "evidence_pack_id": evidence_pack_id,
        },
        "binary": {"sha256": binary_sha},
        "core": {"path": str(core), "sha256": core_sha},
        "addresses": {
            "gobjects": f"0x{gobjects:x}",
            "fname_root_slot": f"0x{fname_root_slot:x}",
            "fname_table": f"0x{fname_table:x}" if fname_table else None,
        },
        "inputs": {
            "evidence_pack_manifest": str(evidence_pack_manifest) if evidence_pack_manifest else None,
            "target_sets": args.target_set,
            "targets": [f"{outer}.{name}" for outer, name in args.target],
            "max_objects": args.max_objects,
            "fname_indices": [{"label": label, "index": index} for label, index in indices],
        },
        "artifacts": {},
        "summary": summary,
        "blockers": blockers,
        "non_claims": [
            "Does not promote a public ScriptStruct SDK.",
            "Does not promote Inventory, Transfer, Items, or Resources SDK callbacks.",
            "Does not expose UObject pointers, raw UE params, FName/GObjects indices, object identity, lookup, or ResourceHandle.",
            "Does not decode transfer, item, inventory, player, actor, dino, tribe, or structure identity.",
            "Does not authorize mutation, return override, ProcessEvent blocking, or UE call replay.",
            "Does not claim portability across ARK binary hashes.",
        ],
    }

    inventory_artifact = output_dir / "scriptstruct-inventory.json"
    fname_artifact = output_dir / "fname-root-validation.json"
    write_json(inventory_artifact, inventory_payload)
    write_json(fname_artifact, fname_payload)
    manifest_payload["artifacts"] = {
        "scriptstruct_inventory": {
            "path": "scriptstruct-inventory.json",
            "sha256": sha256_file(inventory_artifact),
        },
        "fname_root_validation": {
            "path": "fname-root-validation.json",
            "sha256": sha256_file(fname_artifact),
        },
    }
    write_json(output_dir / "manifest.json", manifest_payload)
    print(json.dumps(manifest_payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
