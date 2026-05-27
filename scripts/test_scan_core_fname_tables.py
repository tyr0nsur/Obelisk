#!/usr/bin/env python3
"""Offline tests for scan_core_fname_tables.py."""

from __future__ import annotations

import struct
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import scan_core_fname_tables as scanner


def write_minimal_elf64_core(path: Path, segment_vaddr: int, segment: bytes) -> None:
    header_size = 64
    phoff = header_size
    phentsize = 56
    segment_offset = 0x1000

    data = bytearray(segment_offset + len(segment))
    data[0:4] = b"\x7fELF"
    data[4] = 2
    data[5] = 1
    data[6] = 1
    struct.pack_into("<H", data, 0x10, 4)
    struct.pack_into("<H", data, 0x12, 0x3E)
    struct.pack_into("<I", data, 0x14, 1)
    struct.pack_into("<Q", data, 0x20, phoff)
    struct.pack_into("<H", data, 0x34, header_size)
    struct.pack_into("<H", data, 0x36, phentsize)
    struct.pack_into("<H", data, 0x38, 1)

    struct.pack_into(
        "<IIQQQQQQ",
        data,
        phoff,
        scanner.PT_LOAD,
        6,
        segment_offset,
        segment_vaddr,
        0,
        len(segment),
        len(segment),
        0x1000,
    )
    data[segment_offset : segment_offset + len(segment)] = segment
    path.write_bytes(data)


class ScanCoreFNameTablesTests(unittest.TestCase):
    def test_scans_legacy_fname_table_shape(self) -> None:
        segment_vaddr = 0x10000000
        table = segment_vaddr + 0x1000
        chunk0 = segment_vaddr + 0x3000
        entry0 = segment_vaddr + 0x5000
        client_entry = segment_vaddr + 0x5100
        server_entry = segment_vaddr + 0x5200
        segment = bytearray(0x20000)

        def put_ptr(address: int, value: int) -> None:
            struct.pack_into("<Q", segment, address - segment_vaddr, value)

        def put_u32(address: int, value: int) -> None:
            struct.pack_into("<I", segment, address - segment_vaddr, value)

        def put_entry(address: int, index: int, name: bytes) -> None:
            put_u32(address, index * 2)
            segment[address - segment_vaddr + 0x10 : address - segment_vaddr + 0x10 + len(name)] = name

        put_ptr(table, chunk0)
        put_u32(table + 0x800, 10000)
        put_u32(table + 0x804, 1)
        put_ptr(chunk0, entry0)
        put_ptr(chunk0 + 4884 * 8, client_entry)
        put_ptr(chunk0 + 9619 * 8, server_entry)
        put_entry(entry0, 0, b"None\x00")
        put_entry(client_entry, 4884, b"ClientMessage\x00")
        put_entry(server_entry, 9619, b"ServerChat\x00")

        with tempfile.TemporaryDirectory() as temp_dir:
            core = Path(temp_dir) / "core"
            write_minimal_elf64_core(core, segment_vaddr, bytes(segment))

            memory = scanner.CoreMemory(core)
            try:
                candidates = scanner.scan_fname_tables(
                    memory,
                    indices=scanner.DEFAULT_INDICES,
                    max_none_hits=16,
                    max_pointer_hits=16,
                )
            finally:
                memory.close()

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["table"], hex(table))
        self.assertEqual(candidates[0]["chunk0"], hex(chunk0))
        self.assertEqual(candidates[0]["header_index_ok"], 3)
        names = {item["label"]: item["name"] for item in candidates[0]["resolved_indices"]}
        self.assertEqual(names["None"], "None")
        self.assertEqual(names["ClientMessage"], "ClientMessage")
        self.assertEqual(names["ServerChat"], "ServerChat")


if __name__ == "__main__":
    unittest.main()
