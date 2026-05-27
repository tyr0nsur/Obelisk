#!/usr/bin/env python3
"""Scan an ELF core file for legacy UE4 FName table shaped candidates.

This is offline-only tooling. It reads an existing core dump and does not attach to a
running process. The scanner starts from known FName strings such as "None", finds
entry-pointer and chunk-pointer chains, then validates requested FName indices.
"""

from __future__ import annotations

import argparse
import json
import mmap
import struct
from dataclasses import dataclass
from pathlib import Path


PT_LOAD = 1
FNAME_CHUNK_SIZE = 0x4000
DEFAULT_INDICES = [
    ("None", 0),
    ("ClientMessage", 4884),
    ("ServerChat", 9619),
]


@dataclass(frozen=True)
class LoadSegment:
    offset: int
    vaddr: int
    filesz: int
    memsz: int
    flags: int

    @property
    def end_offset(self) -> int:
        return self.offset + self.filesz

    @property
    def end_vaddr(self) -> int:
        return self.vaddr + self.filesz

    def contains_vaddr(self, address: int, size: int = 1) -> bool:
        return self.vaddr <= address and address + size <= self.end_vaddr

    def vaddr_to_offset(self, address: int) -> int:
        return self.offset + (address - self.vaddr)

    def offset_to_vaddr(self, offset: int) -> int:
        return self.vaddr + (offset - self.offset)


class CoreMemory:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.handle = path.open("rb")
        self.mmap = mmap.mmap(self.handle.fileno(), 0, access=mmap.ACCESS_READ)
        self.segments = parse_elf64_load_segments(self.mmap)

    def close(self) -> None:
        self.mmap.close()
        self.handle.close()

    def segment_for_vaddr(self, address: int, size: int = 1) -> LoadSegment | None:
        for segment in self.segments:
            if segment.contains_vaddr(address, size):
                return segment
        return None

    def read(self, address: int, size: int) -> bytes | None:
        segment = self.segment_for_vaddr(address, size)
        if segment is None:
            return None
        offset = segment.vaddr_to_offset(address)
        return self.mmap[offset : offset + size]

    def read_u32(self, address: int) -> int | None:
        data = self.read(address, 4)
        return None if data is None else struct.unpack("<I", data)[0]

    def read_ptr(self, address: int) -> int | None:
        data = self.read(address, 8)
        return None if data is None else struct.unpack("<Q", data)[0]

    def read_c_string(self, address: int, max_len: int = 128) -> str | None:
        data = self.read(address, max_len)
        if data is None:
            return None
        end = data.find(b"\x00")
        if end < 0:
            return None
        raw = data[:end]
        if not raw:
            return ""
        try:
            return raw.decode("ascii")
        except UnicodeDecodeError:
            return None

    def iter_find(self, needle: bytes, limit: int) -> list[int]:
        hits: list[int] = []
        for segment in self.segments:
            start = segment.offset
            end = segment.end_offset
            cursor = start
            while len(hits) < limit:
                found = self.mmap.find(needle, cursor, end)
                if found < 0:
                    break
                hits.append(segment.offset_to_vaddr(found))
                cursor = found + 1
            if len(hits) >= limit:
                break
        return hits


def parse_elf64_load_segments(data: mmap.mmap) -> list[LoadSegment]:
    if data[:4] != b"\x7fELF":
        raise ValueError("not an ELF file")
    if data[4] != 2 or data[5] != 1:
        raise ValueError("only little-endian ELF64 core files are supported")

    e_phoff = struct.unpack_from("<Q", data, 0x20)[0]
    e_phentsize = struct.unpack_from("<H", data, 0x36)[0]
    e_phnum = struct.unpack_from("<H", data, 0x38)[0]

    segments: list[LoadSegment] = []
    for index in range(e_phnum):
        offset = e_phoff + index * e_phentsize
        p_type, p_flags, p_offset, p_vaddr, _p_paddr, p_filesz, p_memsz, _p_align = struct.unpack_from(
            "<IIQQQQQQ", data, offset
        )
        if p_type != PT_LOAD or p_filesz == 0:
            continue
        segments.append(
            LoadSegment(
                offset=p_offset,
                vaddr=p_vaddr,
                filesz=p_filesz,
                memsz=p_memsz,
                flags=p_flags,
            )
        )
    return segments


def parse_index(value: str) -> tuple[str, int]:
    if "=" in value:
        label, raw_index = value.split("=", 1)
        label = label.strip()
        if not label:
            raise argparse.ArgumentTypeError("index label must not be empty")
        return label, int(raw_index, 0)
    index = int(value, 0)
    return f"fname_{index}", index


def plausible_count(value: int | None, low: int, high: int) -> bool:
    return value is not None and low <= value <= high


def validate_index(memory: CoreMemory, table: int, label: str, index: int) -> dict[str, object]:
    chunk_index = index // FNAME_CHUNK_SIZE
    entry_index = index % FNAME_CHUNK_SIZE
    chunk = memory.read_ptr(table + chunk_index * 8)
    entry = memory.read_ptr(chunk + entry_index * 8) if chunk else None
    header = memory.read_u32(entry) if entry else None
    name = memory.read_c_string(entry + 0x10) if entry else None
    expected_header = index * 2
    return {
        "label": label,
        "index": index,
        "chunk": f"0x{chunk:x}" if chunk else None,
        "entry": f"0x{entry:x}" if entry else None,
        "header": f"0x{header:x}" if header is not None else None,
        "expected_header": f"0x{expected_header:x}",
        "header_index_ok": header == expected_header,
        "name_matches_label": name == label,
        "name": name,
    }


def scan_fname_tables(
    memory: CoreMemory,
    indices: list[tuple[str, int]],
    max_none_hits: int,
    max_pointer_hits: int,
) -> list[dict[str, object]]:
    table_candidates: dict[int, dict[str, object]] = {}
    none_hits = memory.iter_find(b"None\x00", max_none_hits)
    for none_string in none_hits:
        entry0 = none_string - 0x10
        entry0_data = memory.read(entry0, 0x18)
        if entry0_data is None:
            continue

        entry0_ptr = struct.pack("<Q", entry0)
        chunk_hits = memory.iter_find(entry0_ptr, max_pointer_hits)
        for chunk0 in chunk_hits:
            chunk0_ptr = struct.pack("<Q", chunk0)
            table_hits = memory.iter_find(chunk0_ptr, max_pointer_hits)
            for table in table_hits:
                num_elements = memory.read_u32(table + 0x800)
                num_chunks = memory.read_u32(table + 0x804)
                if not plausible_count(num_elements, 1, 10_000_000):
                    continue
                if not plausible_count(num_chunks, 1, 4096):
                    continue

                resolved = [validate_index(memory, table, label, index) for label, index in indices]
                header_ok = sum(1 for item in resolved if item["header_index_ok"])
                name_matches = sum(1 for item in resolved if item["name_matches_label"])
                has_none_clue = any(label == "None" and index == 0 for label, index in indices)
                none_ok = any(
                    item["label"] == "None"
                    and item["index"] == 0
                    and item["header_index_ok"]
                    and item["name"] == "None"
                    for item in resolved
                )
                if header_ok == 0:
                    continue
                if has_none_clue and not none_ok:
                    continue

                table_candidates.setdefault(
                    table,
                    {
                        "table": f"0x{table:x}",
                        "chunk0": f"0x{chunk0:x}",
                        "entry0": f"0x{entry0:x}",
                        "none_string": f"0x{none_string:x}",
                        "num_elements": num_elements,
                        "num_chunks": num_chunks,
                        "header_index_ok": header_ok,
                        "name_matches": name_matches,
                        "resolved_indices": resolved,
                    },
                )

    return sorted(
        table_candidates.values(),
        key=lambda item: (
            -int(item["header_index_ok"]),
            -int(item["name_matches"]),
            -int(item["num_elements"]),
            item["table"],
        ),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Offline scan of an ELF core file for legacy UE4 FName table candidates."
    )
    parser.add_argument("--core", required=True, type=Path, help="Path to an existing ELF core dump.")
    parser.add_argument(
        "--index",
        action="append",
        type=parse_index,
        default=[],
        metavar="LABEL=INDEX",
        help="FName index to resolve for each candidate. Defaults to known Obelisk clues.",
    )
    parser.add_argument("--max-none-hits", type=int, default=256)
    parser.add_argument("--max-pointer-hits", type=int, default=2048)
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    indices = args.index or DEFAULT_INDICES
    memory = CoreMemory(args.core)
    try:
        candidates = scan_fname_tables(
            memory,
            indices=indices,
            max_none_hits=args.max_none_hits,
            max_pointer_hits=args.max_pointer_hits,
        )
    finally:
        memory.close()

    if args.json:
        print(json.dumps({"core": str(args.core), "candidates": candidates}, indent=2, sort_keys=True))
    else:
        if not candidates:
            print("No FName table candidates found.")
        for candidate in candidates:
            print(
                "table={table} chunk0={chunk0} entry0={entry0} "
                "num_elements={num_elements} num_chunks={num_chunks} "
                "header_index_ok={header_index_ok} name_matches={name_matches}".format(**candidate)
            )
            for resolved in candidate["resolved_indices"]:
                print(
                    "  idx={index} label={label} entry={entry} header={header} "
                    "header_ok={header_index_ok} name_match={name_matches_label} "
                    "name={name!r}".format(**resolved)
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
