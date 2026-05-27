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
import verify_chat_reflection_constants as verifier  # noqa: E402


DEFAULT_MAX_OBJECTS = 30000
MAX_SAMPLES_PER_GROUP = 8


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
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


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

    core = args.core
    gobjects = args.gobjects
    fname_root_slot = args.fname_root_slot
    evidence_pack_payload: dict[str, object] | None = None
    if args.evidence_pack:
        pack = verifier.load_evidence_pack(args.evidence_pack)
        core = pack.core
        gobjects = pack.gobjects
        fname_root_slot = pack.fname_root_slot
        evidence_pack_payload = {
            "manifest": str(pack.manifest_path),
            "binary_sha256": pack.binary_sha256,
            "core_sha256": pack.core_sha256,
        }

    memory = uobjects.CoreMemory(core)
    try:
        metadata, functions = collect_function_inventory(
            memory,
            gobjects=gobjects,
            fname_root_slot=fname_root_slot,
            max_objects=args.max_objects,
        )
    finally:
        memory.close()

    filters = {
        "outer_contains": args.outer_contains,
        "name_contains": args.name_contains,
        "family": args.family,
        "min_params": args.min_params,
        "max_params": args.max_params,
    }
    filtered_functions = filter_functions(functions, **filters)
    payload: dict[str, object] = {
        "status": "offline-inventory",
        "core": str(core),
        "metadata": metadata,
        "filters": filters,
        "unfiltered_function_count": len(functions),
        "summary": summarize_functions(filtered_functions, max_groups=args.max_groups),
    }
    if evidence_pack_payload:
        payload["evidence_pack"] = evidence_pack_payload
    if args.include_functions:
        payload["functions"] = filtered_functions
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(format_text(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
