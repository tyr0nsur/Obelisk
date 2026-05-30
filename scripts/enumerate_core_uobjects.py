#!/usr/bin/env python3
"""Enumerate UE4 UObjects from an offline ELF core dump.

This tool is offline-only: it reads an existing core file and never attaches to a
running process. It currently targets the ARK research candidates observed by
Obelisk primary-core fixtures:

- direct GUObjectArray candidate: 0x595b7e0
- static FName root slot: 0x5956f30

For second-source artifacts, pass a FName root/table verified for that artifact instead of
reusing the primary-core slot by default.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from scan_core_fname_tables import CoreMemory, FNAME_CHUNK_SIZE  # noqa: E402
from snapshot_evidence_pack import reject_protected_input_path  # noqa: E402


DEFAULT_GOBJECTS = 0x595B7E0
DEFAULT_FNAME_ROOT_SLOT = 0x5956F30
DEFAULT_MAX_OBJECTS = 1024
GOBJECTS_CHUNKS_OFFSET = 0x10
GOBJECTS_COUNT_OFFSET = 0x24
GOBJECTS_CHUNK_SIZE = 0x10000
FUOBJECT_ITEM_SIZE = 0x10

UOBJECT_FLAGS_OFFSET = 0x8
UOBJECT_INTERNAL_INDEX_OFFSET = 0xC
UOBJECT_CLASS_OFFSET = 0x10
UOBJECT_NAME_INDEX_OFFSET = 0x18
UOBJECT_NAME_NUMBER_OFFSET = 0x1C
UOBJECT_OUTER_OFFSET = 0x20


@dataclass(frozen=True)
class FNameValue:
    index: int
    number: int
    text: str | None


def parse_int(value: str) -> int:
    return int(value, 0)


def read_i32(memory: CoreMemory, address: int) -> int | None:
    data = memory.read(address, 4)
    return None if data is None else struct.unpack("<i", data)[0]


def read_u32(memory: CoreMemory, address: int) -> int | None:
    data = memory.read(address, 4)
    return None if data is None else struct.unpack("<I", data)[0]


def resolve_fname(memory: CoreMemory, table: int | None, index: int | None, number: int | None = 0) -> FNameValue:
    if table is None or index is None or index < 0:
        return FNameValue(index=index if index is not None else -1, number=number or 0, text=None)

    chunk_index = index // FNAME_CHUNK_SIZE
    entry_index = index % FNAME_CHUNK_SIZE
    chunk = memory.read_ptr(table + chunk_index * 8)
    if not chunk:
        return FNameValue(index=index, number=number or 0, text=None)
    entry = memory.read_ptr(chunk + entry_index * 8)
    if not entry:
        return FNameValue(index=index, number=number or 0, text=None)

    header = read_u32(memory, entry)
    if header is not None and header != index * 2:
        return FNameValue(index=index, number=number or 0, text=None)
    text = memory.read_c_string(entry + 0x10, max_len=256)
    return FNameValue(index=index, number=number or 0, text=text)


def read_uobject(
    memory: CoreMemory,
    object_address: int,
    fname_table: int | None,
    *,
    resolve_names: bool = True,
) -> dict[str, object] | None:
    flags = read_u32(memory, object_address + UOBJECT_FLAGS_OFFSET)
    internal_index = read_i32(memory, object_address + UOBJECT_INTERNAL_INDEX_OFFSET)
    class_address = memory.read_ptr(object_address + UOBJECT_CLASS_OFFSET)
    name_index = read_i32(memory, object_address + UOBJECT_NAME_INDEX_OFFSET)
    name_number = read_i32(memory, object_address + UOBJECT_NAME_NUMBER_OFFSET)
    outer = memory.read_ptr(object_address + UOBJECT_OUTER_OFFSET)
    if flags is None or internal_index is None or class_address is None or name_index is None:
        return None

    name = resolve_fname(memory, fname_table, name_index, name_number) if resolve_names else None
    class_name: FNameValue | None = None
    if resolve_names and class_address:
        class_name_index = read_i32(memory, class_address + UOBJECT_NAME_INDEX_OFFSET)
        class_name_number = read_i32(memory, class_address + UOBJECT_NAME_NUMBER_OFFSET)
        class_name = resolve_fname(memory, fname_table, class_name_index, class_name_number)

    return {
        "address": f"0x{object_address:x}",
        "flags": flags,
        "internal_index": internal_index,
        "class": f"0x{class_address:x}" if class_address else None,
        "name_index": name.index if name else name_index,
        "name_number": name.number if name else name_number,
        "name": name.text if name else None,
        "outer": f"0x{outer:x}" if outer else None,
        "class_name": class_name.text if class_name else None,
    }


def iter_uobjects(
    memory: CoreMemory,
    gobjects: int,
    fname_root_slot: int,
    max_objects: int,
    name_contains: str | None = None,
    class_contains: str | None = None,
    resolve_names: bool = True,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    chunks = memory.read_ptr(gobjects + GOBJECTS_CHUNKS_OFFSET)
    object_count = read_i32(memory, gobjects + GOBJECTS_COUNT_OFFSET)
    fname_table = memory.read_ptr(fname_root_slot)

    metadata = {
        "gobjects": f"0x{gobjects:x}",
        "fname_root_slot": f"0x{fname_root_slot:x}",
        "fname_table": f"0x{fname_table:x}" if fname_table else None,
        "chunks": f"0x{chunks:x}" if chunks else None,
        "object_count": object_count,
        "max_objects": max_objects,
        "name_resolution": "enabled" if resolve_names else "disabled",
    }
    if not resolve_names and (name_contains or class_contains):
        raise ValueError("name/class filters require name resolution")
    if not chunks or object_count is None or object_count <= 0:
        return metadata, []

    limit = min(object_count, max_objects)
    results: list[dict[str, object]] = []
    name_filter = name_contains.lower() if name_contains else None
    class_filter = class_contains.lower() if class_contains else None

    for index in range(limit):
        chunk_index = index // GOBJECTS_CHUNK_SIZE
        index_in_chunk = index % GOBJECTS_CHUNK_SIZE
        chunk = memory.read_ptr(chunks + chunk_index * 8)
        if not chunk:
            continue

        item_address = chunk + index_in_chunk * FUOBJECT_ITEM_SIZE
        object_address = memory.read_ptr(item_address)
        if not object_address:
            continue

        item_qword_0x8 = memory.read_ptr(item_address + 0x8)
        item_dword_0x8 = read_u32(memory, item_address + 0x8)
        item_dword_0xC = read_i32(memory, item_address + 0xC)
        uobject = read_uobject(memory, object_address, fname_table, resolve_names=resolve_names)
        if uobject is None:
            continue

        object_name = str(uobject.get("name") or "")
        class_name = str(uobject.get("class_name") or "")
        if name_filter and name_filter not in object_name.lower():
            continue
        if class_filter and class_filter not in class_name.lower():
            continue

        uobject.update(
            {
                "index": index,
                "fuobject_item": f"0x{item_address:x}",
                "item_qword_0x8": f"0x{item_qword_0x8:x}" if item_qword_0x8 is not None else None,
                "item_dword_0x8": item_dword_0x8,
                "item_dword_0xC": item_dword_0xC,
                "internal_index_matches": uobject.get("internal_index") == index,
            }
        )
        results.append(uobject)

    return metadata, results


def format_text(metadata: dict[str, object], objects: Iterable[dict[str, object]]) -> str:
    lines = [
        "gobjects={gobjects} chunks={chunks} object_count={object_count} "
        "fname_table={fname_table} max_objects={max_objects}".format(**metadata)
    ]
    for item in objects:
        lines.append(
            "idx={index} object={address} class={class_name!r} name={name!r} "
            "internal_index={internal_index} match={internal_index_matches} "
            "outer={outer}".format(**item)
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline UObject enumeration from an ELF core dump.")
    parser.add_argument("--core", required=True, type=Path, help="Path to an existing ELF core dump.")
    parser.add_argument("--gobjects", type=parse_int, default=DEFAULT_GOBJECTS)
    parser.add_argument(
        "--fname-root-slot",
        type=parse_int,
        default=DEFAULT_FNAME_ROOT_SLOT,
        help="FName root slot for this artifact. Default is the primary-core fixture candidate; "
        "override for second-source artifacts.",
    )
    parser.add_argument("--max-objects", type=int, default=DEFAULT_MAX_OBJECTS)
    parser.add_argument("--name-contains")
    parser.add_argument("--class-contains")
    parser.add_argument(
        "--skip-name-resolution",
        action="store_true",
        help="Do not resolve FName text/class names; useful for fast flag/serial scans.",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_objects < 0:
        raise SystemExit("--max-objects must be non-negative")

    core_path = reject_protected_input_path(args.core, "--core")
    memory = CoreMemory(core_path)
    try:
        metadata, objects = iter_uobjects(
            memory,
            gobjects=args.gobjects,
            fname_root_slot=args.fname_root_slot,
            max_objects=args.max_objects,
            name_contains=args.name_contains,
            class_contains=args.class_contains,
            resolve_names=not args.skip_name_resolution,
        )
    finally:
        memory.close()

    if args.json:
        print(json.dumps({"core": str(core_path), "metadata": metadata, "objects": objects}, indent=2, sort_keys=True))
    else:
        print(format_text(metadata, objects))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
