#!/usr/bin/env python3
"""Scan copied cores for FUObjectItem serial and UObject flag evidence.

This tool is offline-only. It reads an existing ELF core through the same
GUObjectArray path used by the UObject inventory tools and emits a redacted
summary suitable for ResourceHandle research. It does not prove public handle
lifetime or object identity.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import enumerate_core_uobjects as uobjects  # noqa: E402
from snapshot_evidence_pack import reject_protected_input_path, reject_protected_output_path  # noqa: E402


REPORT_SCHEMA = "obelisk.resource-handle-serial-scan.v1"
DEFAULT_SAMPLE_LIMIT = 64
UOBJECT_VALIDITY_MASKS = (0x100, 0x4000)


def parse_int(value: str) -> int:
    try:
        return int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer/address: {value}") from exc


def _sample_object(obj: dict[str, Any]) -> dict[str, Any]:
    return {
        "index": obj.get("index"),
        "address": obj.get("address"),
        "class_name": obj.get("class_name"),
        "name": obj.get("name"),
        "flags": obj.get("flags"),
        "fuobject_item": obj.get("fuobject_item"),
        "item_dword_0x8": obj.get("item_dword_0x8"),
        "item_dword_0xC": obj.get("item_dword_0xC"),
        "internal_index_matches": obj.get("internal_index_matches"),
    }


def summarize_objects(
    objects: list[dict[str, Any]],
    *,
    sample_limit: int = DEFAULT_SAMPLE_LIMIT,
) -> dict[str, Any]:
    if sample_limit < 0:
        raise ValueError("sample_limit must be non-negative")

    totals = {
        "objects_read": len(objects),
        "serial_zero": 0,
        "serial_nonzero": 0,
        "serial_missing": 0,
        "flags_0x100": 0,
        "flags_0x4000": 0,
        "flags_any": 0,
        "internal_index_mismatch": 0,
    }
    nonzero_serial_samples: list[dict[str, Any]] = []
    flag_mask_samples: list[dict[str, Any]] = []
    serial_classes: dict[str, int] = {}

    for obj in objects:
        serial = obj.get("item_dword_0x8")
        flags = obj.get("flags") if isinstance(obj.get("flags"), int) else 0

        if serial is None:
            totals["serial_missing"] += 1
        elif serial == 0:
            totals["serial_zero"] += 1
        else:
            totals["serial_nonzero"] += 1
            class_name = str(obj.get("class_name") or "<unknown>")
            serial_classes[class_name] = serial_classes.get(class_name, 0) + 1
            if len(nonzero_serial_samples) < sample_limit:
                nonzero_serial_samples.append(_sample_object(obj))

        if flags & 0x100:
            totals["flags_0x100"] += 1
        if flags & 0x4000:
            totals["flags_0x4000"] += 1
        if flags & (0x100 | 0x4000):
            totals["flags_any"] += 1
            if len(flag_mask_samples) < sample_limit:
                flag_mask_samples.append(_sample_object(obj))

        if obj.get("internal_index_matches") is not True:
            totals["internal_index_mismatch"] += 1

    return {
        "totals": totals,
        "top_nonzero_serial_classes": sorted(
            serial_classes.items(),
            key=lambda item: (-item[1], item[0]),
        )[:30],
        "nonzero_serial_samples": nonzero_serial_samples,
        "flag_mask_samples": flag_mask_samples,
    }


def build_report(
    core: Path,
    *,
    gobjects: int,
    fname_root_slot: int,
    max_objects: int,
    label: str | None,
    core_sha256: str | None,
    sample_limit: int,
) -> dict[str, Any]:
    memory = uobjects.CoreMemory(core)
    try:
        metadata, objects = uobjects.iter_uobjects(
            memory,
            gobjects=gobjects,
            fname_root_slot=fname_root_slot,
            max_objects=max_objects,
        )
    finally:
        memory.close()

    summary = summarize_objects(objects, sample_limit=sample_limit)
    return {
        "schema": REPORT_SCHEMA,
        "source_label": label,
        "core_path": str(core),
        "core_sha256": core_sha256,
        "gobjects": f"0x{gobjects:x}",
        "fname_root_slot": f"0x{fname_root_slot:x}",
        "scan_limit": max_objects,
        "metadata": metadata,
        **summary,
        "interpretation": {
            "item_dword_0x8": (
                "nonzero samples support serial-backed FUObjectItem+0x8 for internal tooling"
                if summary["totals"]["serial_nonzero"] > 0
                else "no nonzero samples found in this scan window"
            ),
            "uobject_flags_masks": (
                "0x100/0x4000 samples found; semantics still require classification"
                if summary["totals"]["flags_any"] > 0
                else "no 0x100/0x4000 samples found in this scan window; lifetime flag semantics still unproven"
            ),
            "public_resource_handle_ready": False,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline FUObjectItem serial/UObject flag scan.")
    parser.add_argument("--core", required=True, type=Path)
    parser.add_argument("--gobjects", type=parse_int, default=uobjects.DEFAULT_GOBJECTS)
    parser.add_argument("--fname-root-slot", type=parse_int, default=uobjects.DEFAULT_FNAME_ROOT_SLOT)
    parser.add_argument("--max-objects", type=int, default=200000)
    parser.add_argument("--sample-limit", type=int, default=DEFAULT_SAMPLE_LIMIT)
    parser.add_argument("--label")
    parser.add_argument("--core-sha256")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_objects < 0:
        raise SystemExit("--max-objects must be non-negative")
    if args.sample_limit < 0:
        raise SystemExit("--sample-limit must be non-negative")

    core = reject_protected_input_path(args.core, "--core")
    output = reject_protected_output_path(args.output, "--output") if args.output else None
    report = build_report(
        core,
        gobjects=args.gobjects,
        fname_root_slot=args.fname_root_slot,
        max_objects=args.max_objects,
        label=args.label,
        core_sha256=args.core_sha256,
        sample_limit=args.sample_limit,
    )

    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload)
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
