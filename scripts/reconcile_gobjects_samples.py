#!/usr/bin/env python3
"""Emit an offline GObjects/FUObjectItem reconciliation report for named indices."""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import enumerate_core_uobjects as uobjects  # noqa: E402
from snapshot_evidence_pack import (  # noqa: E402
    reject_protected_input_path,
    reject_protected_output_path,
    require_ignored_output_path,
)


REPORT_SCHEMA = "obelisk.gobjects-sample-reconciliation.v1"
STATUS_CANDIDATE_UOBJECT = "candidate-uobject"
STATUS_NOT_IN_GOBJECTS = "not-in-gobjects"
STATUS_NULL = "null"
STATIC_HANDLE_WINDOW = "0x1d56970..0x1d56eb0"


def parse_int(value: str) -> int:
    try:
        return int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer/address: {value}") from exc


def parse_sample_index(value: str) -> tuple[str, int]:
    if "=" in value:
        label, raw_index = value.split("=", 1)
        label = label.strip()
        if not label:
            raise argparse.ArgumentTypeError("sample label must not be empty")
        index = parse_int(raw_index)
    else:
        index = parse_int(value)
        label = f"index_{index}"
    if index < 0:
        raise argparse.ArgumentTypeError("--sample-index must be non-negative")
    return label, index


def hex_or_none(value: int | None) -> str | None:
    return None if value is None else f"0x{value:x}"


def read_i32(memory: uobjects.CoreMemory, address: int) -> int | None:
    data = memory.read(address, 4)
    return None if data is None else struct.unpack("<i", data)[0]


def read_u32(memory: uobjects.CoreMemory, address: int) -> int | None:
    data = memory.read(address, 4)
    return None if data is None else struct.unpack("<I", data)[0]


def read_u64(memory: uobjects.CoreMemory, address: int) -> int | None:
    data = memory.read(address, 8)
    return None if data is None else struct.unpack("<Q", data)[0]


def read_object_summary(memory: uobjects.CoreMemory, address: int | None, fname_table: int | None) -> dict[str, object] | None:
    if not address:
        return None
    raw = uobjects.read_uobject(memory, address, fname_table)
    if raw is None:
        return None

    outer_address = parse_hex_address(raw.get("outer"))
    outer_name = None
    outer_class_name = None
    if outer_address:
        outer = uobjects.read_uobject(memory, outer_address, fname_table)
        if outer:
            outer_name = outer.get("name")
            outer_class_name = outer.get("class_name")

    return {
        "address": raw["address"],
        "flags": raw["flags"],
        "internal_index": raw["internal_index"],
        "class": raw["class"],
        "class_name": raw["class_name"],
        "name_index": raw["name_index"],
        "name_number": raw["name_number"],
        "name": raw["name"],
        "outer": raw["outer"],
        "outer_name": outer_name,
        "outer_class_name": outer_class_name,
    }


def parse_hex_address(value: object) -> int | None:
    if not isinstance(value, str) or not value.startswith("0x"):
        return None
    return int(value, 16)


def read_item_object_at_index(
    memory: uobjects.CoreMemory,
    chunks: int | None,
    index: int | None,
) -> tuple[int | None, int | None]:
    if chunks is None or index is None or index < 0:
        return None, None
    chunk_index = index // uobjects.GOBJECTS_CHUNK_SIZE
    index_in_chunk = index % uobjects.GOBJECTS_CHUNK_SIZE
    chunk = memory.read_ptr(chunks + chunk_index * 8)
    if not chunk:
        return None, None
    item_address = chunk + index_in_chunk * uobjects.FUOBJECT_ITEM_SIZE
    return item_address, memory.read_ptr(item_address)


def membership_for_pointer(
    memory: uobjects.CoreMemory,
    chunks: int | None,
    pointer: int | None,
    summary: dict[str, object] | None,
) -> dict[str, object]:
    if not pointer:
        return {"status": STATUS_NULL, "index": None, "fuobject_item": None, "backref_object": None, "passes": True}
    if summary is None:
        return {
            "status": STATUS_NOT_IN_GOBJECTS,
            "index": None,
            "fuobject_item": None,
            "backref_object": None,
            "passes": False,
            "reason": "unreadable_uobject",
        }

    internal_index = summary.get("internal_index")
    index = internal_index if isinstance(internal_index, int) else None
    item_address, backref_object = read_item_object_at_index(memory, chunks, index)
    passes = backref_object == pointer
    return {
        "status": STATUS_CANDIDATE_UOBJECT if passes else STATUS_NOT_IN_GOBJECTS,
        "index": index,
        "fuobject_item": hex_or_none(item_address),
        "backref_object": hex_or_none(backref_object),
        "passes": passes,
    }


def static_handle_reconciliation(item_dword_0x8: int | None, item_dword_0xc: int | None) -> dict[str, object]:
    if item_dword_0x8 is None:
        compatibility = "missing_item_0x8"
    elif item_dword_0x8 == 0:
        compatibility = "compatible_with_lazy_or_absent_serial_publication"
    else:
        compatibility = "compatible_with_nonzero_item_0x8_serial_candidate"

    return {
        "window": STATIC_HANDLE_WINDOW,
        "item_serial_candidate_offset": "0x8",
        "item_unknown_dword_offset": "0xc",
        "item_serial_candidate_value": item_dword_0x8,
        "item_unknown_dword_value": item_dword_0xc,
        "compatibility": compatibility,
        "promotion_status": "internal-only-single-artifact",
    }


def sample_index(
    memory: uobjects.CoreMemory,
    *,
    label: str,
    index: int,
    chunks: int | None,
    object_count: int | None,
    fname_table: int | None,
) -> dict[str, object]:
    reject_reasons: list[str] = []
    in_bounds = True
    if object_count is None or object_count <= 0:
        reject_reasons.append("missing_or_invalid_gobjects_count")
        in_bounds = False
    elif index >= object_count:
        reject_reasons.append("sample_index_out_of_bounds")
        in_bounds = False

    item_address, object_address = read_item_object_at_index(memory, chunks, index) if in_bounds else (None, None)
    if in_bounds and item_address is None:
        reject_reasons.append("missing_gobjects_chunk")
    if in_bounds and not object_address:
        reject_reasons.append("missing_object_pointer")

    item_dword_0x8 = read_u32(memory, item_address + 0x8) if item_address is not None else None
    item_dword_0xc = read_u32(memory, item_address + 0xC) if item_address is not None else None
    item_qword_0x8 = read_u64(memory, item_address + 0x8) if item_address is not None else None

    target = read_object_summary(memory, object_address, fname_table)
    if object_address and target is None:
        reject_reasons.append("unreadable_uobject")

    class_address = parse_hex_address(target.get("class")) if target else None
    outer_address = parse_hex_address(target.get("outer")) if target else None
    class_summary = read_object_summary(memory, class_address, fname_table)
    outer_summary = read_object_summary(memory, outer_address, fname_table)

    target_membership = membership_for_pointer(memory, chunks, object_address, target)
    class_membership = membership_for_pointer(memory, chunks, class_address, class_summary)
    outer_membership = membership_for_pointer(memory, chunks, outer_address, outer_summary)
    membership_passes = (
        target_membership["passes"] is True
        and class_membership["passes"] is True
        and outer_membership["passes"] is True
    )
    if not membership_passes:
        reject_reasons.append("membership_check_failed")

    internal_index = target.get("internal_index") if target else None
    internal_index_matches = internal_index == index
    if not internal_index_matches:
        reject_reasons.append("internal_index_mismatch")

    return {
        "label": label,
        "index": index,
        "status": STATUS_CANDIDATE_UOBJECT if not reject_reasons else "rejected",
        "reject_reasons": reject_reasons,
        "fuobject_item": hex_or_none(item_address),
        "object": hex_or_none(object_address),
        "item_dword_0x8": item_dword_0x8,
        "item_dword_0xc": item_dword_0xc,
        "item_qword_0x8": hex_or_none(item_qword_0x8),
        "uobject": target,
        "class_uobject": class_summary,
        "outer_uobject": outer_summary,
        "object_name": target.get("name") if target else None,
        "class_name": target.get("class_name") if target else None,
        "outer_name": target.get("outer_name") if target else None,
        "membership": {
            "target": target_membership,
            "class": class_membership,
            "outer": outer_membership,
            "passes": membership_passes,
        },
        "uobject_internal_index": internal_index,
        "uobject_internal_index_matches": internal_index_matches,
        "static_handle_accessor_reconciliation": static_handle_reconciliation(item_dword_0x8, item_dword_0xc),
    }


def build_report(
    core: Path,
    *,
    gobjects: int,
    fname_root_slot: int,
    sample_indices: list[tuple[str, int]],
) -> dict[str, object]:
    memory = uobjects.CoreMemory(core)
    try:
        chunks = memory.read_ptr(gobjects + uobjects.GOBJECTS_CHUNKS_OFFSET)
        object_count = read_i32(memory, gobjects + uobjects.GOBJECTS_COUNT_OFFSET)
        fname_table = memory.read_ptr(fname_root_slot)
        samples = [
            sample_index(
                memory,
                label=label,
                index=index,
                chunks=chunks,
                object_count=object_count,
                fname_table=fname_table,
            )
            for label, index in sample_indices
        ]
    finally:
        memory.close()

    return {
        "schema": REPORT_SCHEMA,
        "status": "offline-reconciliation",
        "core": str(core),
        "inputs": {
            "gobjects_candidate": hex(gobjects),
            "fname_root_slot": hex(fname_root_slot),
            "sample_indices": [{"label": label, "index": index} for label, index in sample_indices],
        },
        "metadata": {
            "gobjects_chunks": hex_or_none(chunks),
            "gobjects_count": object_count,
            "fname_table": hex_or_none(fname_table),
            "static_handle_accessor_evidence": {
                "window": STATIC_HANDLE_WINDOW,
                "item_serial_candidate_offset": "0x8",
                "item_unknown_dword_offset": "0xc",
                "notes": [
                    "static accessor evidence compares handle serials against FUObjectItem+0x8",
                    "FUObjectItem+0xc remains unknown and must not be promoted as a serial field",
                ],
            },
        },
        "samples": samples,
        "summary": {
            "sample_count": len(samples),
            "accepted_count": sum(1 for sample in samples if sample.get("status") == STATUS_CANDIDATE_UOBJECT),
            "rejected_count": sum(1 for sample in samples if sample.get("status") != STATUS_CANDIDATE_UOBJECT),
            "membership_pass_count": sum(1 for sample in samples if sample.get("membership", {}).get("passes") is True),
            "item_dword_0x8_zero_count": sum(1 for sample in samples if sample.get("item_dword_0x8") == 0),
            "item_dword_0x8_nonzero_count": sum(
                1
                for sample in samples
                if isinstance(sample.get("item_dword_0x8"), int) and sample.get("item_dword_0x8") != 0
            ),
            "promotion_status": "internal-only-single-artifact",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", required=True, type=Path, help="Path to an existing offline ELF core dump.")
    parser.add_argument("--fname-root-slot", required=True, type=parse_int, help="Artifact-specific FName root slot.")
    parser.add_argument("--gobjects-candidate", required=True, type=parse_int, help="Direct GUObjectArray candidate.")
    parser.add_argument(
        "--sample-index",
        action="append",
        type=parse_sample_index,
        default=[],
        help="Named sample index as LABEL=INDEX, or INDEX. May be repeated.",
    )
    parser.add_argument("--output", type=Path, help="Optional JSON output path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.sample_index:
        raise SystemExit("at least one --sample-index is required")

    core = reject_protected_input_path(args.core, "--core")
    output = reject_protected_output_path(args.output, "--output") if args.output else None
    if output:
        require_ignored_output_path(output, "--output")
    report = build_report(
        core,
        gobjects=args.gobjects_candidate,
        fname_root_slot=args.fname_root_slot,
        sample_indices=list(args.sample_index),
    )
    text = json.dumps(report, indent=2, sort_keys=True)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
