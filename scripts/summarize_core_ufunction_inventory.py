#!/usr/bin/env python3
"""Summarize UFunction inventory from an offline core dump.

The script is passive: it reads an existing core/evidence pack, enumerates objects whose
class resolves to Function, and produces coarse grouping data for roadmap planning. It
does not attach to a process, scan live memory, or promote any function as SDK-ready.
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import enumerate_core_uobjects as uobjects  # noqa: E402
import reflection_target_sets  # noqa: E402
import verify_chat_reflection_constants as verifier  # noqa: E402
from snapshot_evidence_pack import reject_protected_input_path  # noqa: E402


DEFAULT_MAX_OBJECTS = 30000
MAX_SAMPLES_PER_GROUP = 8
DEFAULT_SNAPSHOT_MANIFEST = Path("tests/fixtures/ufunction_snapshots/manifest.json")
REGENERATOR_SCRIPT = "scripts/regenerate_ufunction_snapshots.py"
UFUNCTION_TARGET_SETS = sorted(
    name
    for name in reflection_target_sets.TARGET_SETS
    if reflection_target_sets.schema_targets(name, "obelisk.ufunction-chain.snapshot.v1")
)


def parse_int(value: str) -> int:
    return int(value, 0)


def read_u16(memory: uobjects.CoreMemory, address: int) -> int | None:
    data = memory.read(address, 2)
    return None if data is None else struct.unpack("<H", data)[0]


def read_u32(memory: uobjects.CoreMemory, address: int) -> int | None:
    data = memory.read(address, 4)
    return None if data is None else struct.unpack("<I", data)[0]


def hex_or_none(value: int | None) -> str | None:
    return None if value is None else f"0x{value:x}"


def parse_address(value: object) -> int | None:
    if not isinstance(value, str) or not value.startswith("0x"):
        return None
    return int(value, 16)


def function_family(name: str) -> str:
    if not name:
        return "<unnamed>"
    match = re.match(r"^(Server|Client|Receive|BP|Blueprint|K2|Multicast|On|Set|Get|Add|Remove|Can|Is|Has)", name)
    if match:
        return match.group(1)
    camel = re.match(r"^([A-Z][a-z0-9]+)", name)
    if camel:
        return camel.group(1)
    return name.split("_", 1)[0]


def add_sample(group: dict[str, object], item: dict[str, object]) -> None:
    samples = group.setdefault("samples", [])
    if isinstance(samples, list) and len(samples) < MAX_SAMPLES_PER_GROUP:
        samples.append(item)


def summarize_functions(functions: list[dict[str, object]], *, max_groups: int) -> dict[str, object]:
    outer_counts = Counter(str(item.get("outer_name") or "<no outer>") for item in functions)
    family_counts = Counter(str(item.get("family") or "<unknown>") for item in functions)
    class_counts = Counter(str(item.get("outer_class_name") or "<unknown>") for item in functions)

    outer_groups: dict[str, dict[str, object]] = {}
    for item in functions:
        outer_name = str(item.get("outer_name") or "<no outer>")
        group = outer_groups.setdefault(
            outer_name,
            {
                "outer": outer_name,
                "outer_class_name": item.get("outer_class_name"),
                "count": 0,
                "families": {},
                "samples": [],
            },
        )
        group["count"] = int(group["count"]) + 1
        families = group["families"]
        if isinstance(families, dict):
            family = str(item.get("family") or "<unknown>")
            families[family] = int(families.get(family, 0)) + 1
        add_sample(group, item)

    top_outer_groups = sorted(
        outer_groups.values(),
        key=lambda group: (-int(group["count"]), str(group["outer"])),
    )[:max_groups]

    return {
        "function_count": len(functions),
        "top_outers": [{"outer": key, "count": value} for key, value in outer_counts.most_common(max_groups)],
        "top_families": [{"family": key, "count": value} for key, value in family_counts.most_common(max_groups)],
        "top_outer_classes": [
            {"outer_class_name": key, "count": value} for key, value in class_counts.most_common(max_groups)
        ],
        "outer_groups": top_outer_groups,
    }


def function_key(item: dict[str, object]) -> str:
    outer = str(item.get("outer_name") or "")
    name = str(item.get("name") or "")
    return f"{outer}.{name}" if outer and name else ""


def load_snapshot_manifest(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "obelisk.ufunction-snapshot-manifest.v1":
        raise SystemExit(f"{path}: unsupported UFunction snapshot manifest schema")
    if payload.get("source") != "offline_core":
        raise SystemExit(f"{path}: source must be offline_core")
    if payload.get("status") != "candidate-only":
        raise SystemExit(f"{path}: status must be candidate-only")
    entries = payload.get("targets")
    if not isinstance(entries, list):
        raise SystemExit(f"{path}: manifest targets must be a list")
    return payload


def snapshot_manifest_targets(manifest: dict[str, object]) -> dict[str, dict[str, object]]:
    targets: dict[str, dict[str, object]] = {}
    entries = manifest.get("targets")
    if not isinstance(entries, list):
        raise SystemExit("snapshot manifest targets must be a list")
    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            raise SystemExit("snapshot manifest targets must be objects")
        outer = raw_entry.get("outer")
        name = raw_entry.get("name")
        if not isinstance(outer, str) or not isinstance(name, str) or not outer or not name:
            raise SystemExit("snapshot manifest target missing outer/name")
        key = f"{outer}.{name}"
        if key in targets:
            raise SystemExit(f"duplicate snapshot manifest target: {key}")
        targets[key] = raw_entry
    return targets


def suggested_manifest_entry(target: str) -> dict[str, object]:
    outer, _, name = target.partition(".")
    return {
        "module": "sdk_candidates",
        "outer": outer,
        "name": name,
        "file": f"{target}.snapshot.json",
    }


def target_set_regeneration_plan(
    functions: list[dict[str, object]],
    *,
    target_sets: list[str],
    snapshot_manifest: dict[str, object],
    snapshot_manifest_path: Path,
    core: Path,
    gobjects: int,
    fname_root_slot: int,
    evidence_pack_manifest: Path | None = None,
) -> dict[str, object]:
    requested_targets = sorted(
        reflection_target_sets.expand_schema_target_sets(target_sets, "obelisk.ufunction-chain.snapshot.v1")
    )
    manifest_targets = snapshot_manifest_targets(snapshot_manifest)
    inventory_by_key: dict[str, list[dict[str, object]]] = {}
    for item in functions:
        key = function_key(item)
        if key in requested_targets:
            inventory_by_key.setdefault(key, []).append(item)

    targets: list[dict[str, object]] = []
    blocked: list[dict[str, object]] = []
    commands: list[dict[str, object]] = []
    recommendations: list[dict[str, object]] = []

    for target in requested_targets:
        inventory_matches = inventory_by_key.get(target, [])
        manifest_entry = manifest_targets.get(target)
        if not inventory_matches:
            inventory_status = "missing"
        elif len(inventory_matches) == 1:
            inventory_status = "present"
        else:
            inventory_status = "ambiguous"
        manifest_status = "present" if manifest_entry else "missing"

        record: dict[str, object] = {
            "target": target,
            "inventory_status": inventory_status,
            "inventory_match_count": len(inventory_matches),
            "manifest_status": manifest_status,
            "status": "planned",
        }
        if inventory_status == "ambiguous":
            record["status"] = "blocked"
            record["blocker"] = "ambiguous_inventory_target"
            blocked.append({"target": target, "reason": "ambiguous_inventory_target"})
        elif inventory_status == "missing":
            record["status"] = "blocked"
            record["blocker"] = "missing_inventory_target"
            blocked.append({"target": target, "reason": "missing_inventory_target"})
        elif manifest_entry is None:
            record["status"] = "needs_manifest_entry_review"
            recommendation = suggested_manifest_entry(target)
            record["candidate_manifest_entry"] = recommendation
            recommendations.append({"target": target, "entry": recommendation})
        else:
            command = [
                sys.executable,
                REGENERATOR_SCRIPT,
                "--core",
                str(core),
                "--manifest",
                str(snapshot_manifest_path),
                "--target",
                target,
            ]
            if evidence_pack_manifest is not None:
                command.extend(["--evidence-pack-manifest", str(evidence_pack_manifest)])
            else:
                command.extend(["--gobjects", hex(gobjects), "--fname-root-slot", hex(fname_root_slot)])
            record["regenerate_command"] = command
            commands.append({"target": target, "argv": command})
        targets.append(record)

    return {
        "schema": "obelisk.ufunction-target-set-regeneration-plan.v1",
        "target_sets": target_sets,
        "snapshot_manifest": str(snapshot_manifest_path),
        "core": str(core),
        "evidence_pack_manifest": str(evidence_pack_manifest) if evidence_pack_manifest else None,
        "gobjects": hex(gobjects),
        "fname_root_slot": hex(fname_root_slot),
        "requested_count": len(requested_targets),
        "planned_command_count": len(commands),
        "recommendation_count": len(recommendations),
        "blocked_count": len(blocked),
        "targets": targets,
        "regenerate_commands": commands,
        "candidate_manifest_recommendations": recommendations,
        "blockers": blocked,
        "promotion_status": "not_promoted_candidate_only",
    }


def target_set_coverage(
    functions: list[dict[str, object]],
    *,
    target_sets: list[str],
    max_samples: int = MAX_SAMPLES_PER_GROUP,
) -> dict[str, object]:
    if not target_sets:
        return {}

    requested_targets = sorted(
        reflection_target_sets.expand_schema_target_sets(target_sets, "obelisk.ufunction-chain.snapshot.v1")
    )
    requested = set(requested_targets)
    by_key: dict[str, list[dict[str, object]]] = {}
    unassigned_samples: list[dict[str, object]] = []
    unassigned_count = 0

    for item in functions:
        key = function_key(item)
        if key in requested:
            by_key.setdefault(key, []).append(item)
        else:
            unassigned_count += 1
            if len(unassigned_samples) < max_samples:
                unassigned_samples.append(item)

    matched = {
        key: {
            "count": len(items),
            "samples": items[:max_samples],
        }
        for key, items in sorted(by_key.items())
    }
    missing = [target for target in requested_targets if target not in matched]
    ambiguous = [
        {
            "target": key,
            "count": len(items),
            "samples": items[:max_samples],
        }
        for key, items in sorted(by_key.items())
        if len(items) > 1
    ]

    return {
        "schema": "obelisk.ufunction-inventory-target-set-coverage.v1",
        "target_sets": target_sets,
        "requested_targets": requested_targets,
        "requested_count": len(requested_targets),
        "matched_count": len(matched),
        "missing_count": len(missing),
        "missing_targets": missing,
        "ambiguous_count": len(ambiguous),
        "ambiguous_targets": ambiguous,
        "matched_targets": matched,
        "unassigned_function_count": unassigned_count,
        "unassigned_samples": unassigned_samples,
    }


def contains_filter(value: object, needle: str | None) -> bool:
    if not needle:
        return True
    return needle.lower() in str(value or "").lower()


def filter_functions(
    functions: list[dict[str, object]],
    *,
    outer_contains: str | None = None,
    name_contains: str | None = None,
    family: str | None = None,
    min_params: int | None = None,
    max_params: int | None = None,
) -> list[dict[str, object]]:
    filtered: list[dict[str, object]] = []
    for item in functions:
        if not contains_filter(item.get("outer_name"), outer_contains):
            continue
        if not contains_filter(item.get("name"), name_contains):
            continue
        if family and str(item.get("family") or "").lower() != family.lower():
            continue
        num_parms = item.get("num_parms")
        if not isinstance(num_parms, int):
            if min_params is not None or max_params is not None:
                continue
        else:
            if min_params is not None and num_parms < min_params:
                continue
            if max_params is not None and num_parms > max_params:
                continue
        filtered.append(item)
    return filtered


def collect_function_inventory(
    memory: uobjects.CoreMemory,
    *,
    gobjects: int,
    fname_root_slot: int,
    max_objects: int,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    metadata, objects = uobjects.iter_uobjects(
        memory,
        gobjects=gobjects,
        fname_root_slot=fname_root_slot,
        max_objects=max_objects,
        class_contains="Function",
    )
    fname_table = memory.read_ptr(fname_root_slot)
    functions: list[dict[str, object]] = []
    for item in objects:
        address = parse_address(item.get("address"))
        outer_address = parse_address(item.get("outer"))
        outer_summary = uobjects.read_uobject(memory, outer_address, fname_table) if outer_address else None
        name = str(item.get("name") or "")
        function_flags = read_u32(memory, address + 0x90) if address is not None else None
        num_parms = read_u16(memory, address + 0x96) if address is not None else None
        parms_size = read_u16(memory, address + 0x98) if address is not None else None
        functions.append(
            {
                "index": item.get("index"),
                "object": item.get("address"),
                "name": name,
                "family": function_family(name),
                "name_index": item.get("name_index"),
                "outer": item.get("outer"),
                "outer_name": outer_summary.get("name") if outer_summary else None,
                "outer_class_name": outer_summary.get("class_name") if outer_summary else None,
                "function_flags": hex_or_none(function_flags),
                "num_parms": num_parms,
                "parms_size": parms_size,
                "internal_index_matches": item.get("internal_index_matches"),
            }
        )
    return metadata, functions


def redact_function_inventory(functions: list[dict[str, object]]) -> list[dict[str, object]]:
    redacted: list[dict[str, object]] = []
    for item in functions:
        redacted.append(
            {
                "name": item.get("name"),
                "family": item.get("family"),
                "outer_name": item.get("outer_name"),
                "outer_class_name": item.get("outer_class_name"),
                "function_flags": item.get("function_flags"),
                "num_parms": item.get("num_parms"),
                "parms_size": item.get("parms_size"),
            }
        )
    return redacted


def build_ufunction_inventory_payload(
    memory: uobjects.CoreMemory,
    *,
    core: Path,
    gobjects: int,
    fname_root_slot: int,
    max_objects: int,
    max_groups: int,
    filters: dict[str, object],
    target_sets: list[str],
    include_functions: bool = False,
    redact_pointers: bool = False,
    snapshot_manifest: dict[str, object] | None = None,
    snapshot_manifest_path: Path | None = None,
    plan_regeneration: bool = False,
    evidence_pack_manifest: Path | None = None,
    evidence_pack_payload: dict[str, object] | None = None,
) -> dict[str, object]:
    metadata, functions = collect_function_inventory(
        memory,
        gobjects=gobjects,
        fname_root_slot=fname_root_slot,
        max_objects=max_objects,
    )
    inventory_functions = redact_function_inventory(functions) if redact_pointers else functions
    filtered_functions = filter_functions(inventory_functions, **filters)
    payload: dict[str, object] = {
        "status": "offline-inventory",
        "core": str(core),
        "metadata": metadata,
        "filters": filters,
        "unfiltered_function_count": len(functions),
        "summary": summarize_functions(filtered_functions, max_groups=max_groups),
    }
    coverage = target_set_coverage(inventory_functions, target_sets=target_sets)
    if coverage:
        payload["target_set_coverage"] = coverage
    if plan_regeneration:
        if snapshot_manifest is None or snapshot_manifest_path is None:
            raise SystemExit("--plan-regeneration requires a snapshot manifest")
        payload["target_set_regeneration_plan"] = target_set_regeneration_plan(
            inventory_functions,
            target_sets=target_sets,
            snapshot_manifest=snapshot_manifest,
            snapshot_manifest_path=snapshot_manifest_path,
            core=core,
            gobjects=gobjects,
            fname_root_slot=fname_root_slot,
            evidence_pack_manifest=evidence_pack_manifest,
        )
    if evidence_pack_payload:
        payload["evidence_pack"] = evidence_pack_payload
    if include_functions:
        payload["functions"] = filtered_functions
    return payload


def format_text(payload: dict[str, object]) -> str:
    summary = payload["summary"]
    lines = [
        "status={status} function_count={count} core={core}".format(
            status=payload["status"],
            count=summary["function_count"],
            core=payload["core"],
        )
    ]
    lines.append("top_families=" + ", ".join(f"{item['family']}:{item['count']}" for item in summary["top_families"]))
    lines.append("top_outers=" + ", ".join(f"{item['outer']}:{item['count']}" for item in summary["top_outers"]))
    for group in summary["outer_groups"]:
        lines.append(
            "outer={outer!r} class={outer_class_name!r} count={count} families={families}".format(**group)
        )
        for sample in group["samples"]:
            lines.append(
                "  idx={index} name={name!r} family={family} parms={num_parms} size={parms_size} flags={function_flags}".format(
                    **sample
                )
            )
    coverage = payload.get("target_set_coverage")
    if isinstance(coverage, dict):
        lines.append(
            "target_sets={target_sets} requested={requested_count} matched={matched_count} "
            "missing={missing_count} unassigned={unassigned_function_count}".format(**coverage)
        )
        for target in coverage.get("missing_targets", []):
            lines.append(f"  missing={target}")
    plan = payload.get("target_set_regeneration_plan")
    if isinstance(plan, dict):
        lines.append(
            "regeneration_plan requested={requested_count} commands={planned_command_count} "
            "recommendations={recommendation_count} blocked={blocked_count}".format(**plan)
        )
        for target in plan.get("targets", []):
            if isinstance(target, dict):
                lines.append(
                    "  target={target} inventory={inventory_status} manifest={manifest_status} "
                    "status={status}".format(**target)
                )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize offline UFunction inventory from a core dump.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--core", type=Path)
    source.add_argument("--evidence-pack", type=Path)
    parser.add_argument("--gobjects", type=parse_int, default=uobjects.DEFAULT_GOBJECTS)
    parser.add_argument("--fname-root-slot", type=parse_int, default=uobjects.DEFAULT_FNAME_ROOT_SLOT)
    parser.add_argument("--max-objects", type=int, default=DEFAULT_MAX_OBJECTS)
    parser.add_argument("--max-groups", type=int, default=20)
    parser.add_argument("--outer-contains", help="Limit inventory to functions whose outer name contains this text.")
    parser.add_argument("--name-contains", help="Limit inventory to function names containing this text.")
    parser.add_argument("--family", help="Limit inventory to one derived function family, e.g. Server or Client.")
    parser.add_argument("--min-params", type=int, help="Limit inventory to functions with at least this many params.")
    parser.add_argument("--max-params", type=int, help="Limit inventory to functions with at most this many params.")
    parser.add_argument(
        "--include-functions",
        action="store_true",
        help="Include the filtered function rows in JSON output for focused offline review.",
    )
    parser.add_argument(
        "--target-set",
        action="append",
        choices=UFUNCTION_TARGET_SETS,
        default=[],
        help="Report coverage against a named UFunction target set.",
    )
    parser.add_argument(
        "--plan-regeneration",
        action="store_true",
        help="Emit a dry-run target-set regeneration plan. Requires --target-set.",
    )
    parser.add_argument(
        "--snapshot-manifest",
        type=Path,
        default=DEFAULT_SNAPSHOT_MANIFEST,
        help="Candidate-only UFunction snapshot manifest used by --plan-regeneration.",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def reject_evidence_pack_manifest_paths(path: Path) -> None:
    reject_protected_input_path(path, "--evidence-pack")
    manifest_path = path / "manifest.json" if path.is_dir() else path
    reject_protected_input_path(manifest_path, "--evidence-pack")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{manifest_path}: evidence pack manifest must be a JSON object")
    core = payload.get("core")
    if isinstance(core, dict) and isinstance(core.get("path"), str):
        reject_protected_input_path(Path(str(core["path"])), f"{manifest_path}: evidence pack core.path")
    binary = payload.get("binary")
    if isinstance(binary, dict) and isinstance(binary.get("path"), str):
        reject_protected_input_path(Path(str(binary["path"])), f"{manifest_path}: evidence pack binary.path")


def main() -> int:
    args = parse_args()
    if args.max_objects < 0:
        raise SystemExit("--max-objects must be non-negative")
    if args.max_groups <= 0:
        raise SystemExit("--max-groups must be positive")
    if args.min_params is not None and args.min_params < 0:
        raise SystemExit("--min-params must be non-negative")
    if args.max_params is not None and args.max_params < 0:
        raise SystemExit("--max-params must be non-negative")
    if args.min_params is not None and args.max_params is not None and args.min_params > args.max_params:
        raise SystemExit("--min-params must be less than or equal to --max-params")
    if args.plan_regeneration and not args.target_set:
        raise SystemExit("--plan-regeneration requires at least one --target-set")
    if args.core is not None:
        reject_protected_input_path(args.core, "--core")
    if args.evidence_pack is not None:
        reject_evidence_pack_manifest_paths(args.evidence_pack)
    if args.plan_regeneration:
        reject_protected_input_path(args.snapshot_manifest, "--snapshot-manifest")

    core = args.core
    gobjects = args.gobjects
    fname_root_slot = args.fname_root_slot
    evidence_pack_payload: dict[str, object] | None = None
    evidence_pack_manifest_path: Path | None = None
    if args.evidence_pack:
        pack = verifier.load_evidence_pack(args.evidence_pack)
        core = pack.core
        gobjects = pack.gobjects
        fname_root_slot = pack.fname_root_slot
        evidence_pack_manifest_path = pack.manifest_path
        evidence_pack_payload = {
            "manifest": str(pack.manifest_path),
            "binary_sha256": pack.binary_sha256,
            "core_sha256": pack.core_sha256,
        }

    memory = uobjects.CoreMemory(core)
    try:
        filters = {
            "outer_contains": args.outer_contains,
            "name_contains": args.name_contains,
            "family": args.family,
            "min_params": args.min_params,
            "max_params": args.max_params,
        }
        snapshot_manifest = load_snapshot_manifest(args.snapshot_manifest) if args.plan_regeneration else None
        payload = build_ufunction_inventory_payload(
            memory,
            core=core,
            gobjects=gobjects,
            fname_root_slot=fname_root_slot,
            max_objects=args.max_objects,
            max_groups=args.max_groups,
            filters=filters,
            target_sets=args.target_set,
            include_functions=args.include_functions,
            snapshot_manifest=snapshot_manifest,
            snapshot_manifest_path=args.snapshot_manifest if args.plan_regeneration else None,
            plan_regeneration=args.plan_regeneration,
            evidence_pack_manifest=evidence_pack_manifest_path,
            evidence_pack_payload=evidence_pack_payload,
        )
    finally:
        memory.close()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(format_text(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
