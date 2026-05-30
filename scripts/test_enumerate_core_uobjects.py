#!/usr/bin/env python3
"""Offline tests for enumerate_core_uobjects.py."""

from __future__ import annotations

import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import enumerate_core_uobjects as enum
from test_scan_core_fname_tables import write_minimal_elf64_core


def build_core_fixture(path: Path) -> dict[str, int]:
    base = 0x10000000
    segment = bytearray(0x80000)
    addrs = {
        "base": base,
        "fname_root_slot": base + 0x100,
        "fname_table": base + 0x1000,
        "fname_chunk": base + 0x3000,
        "gobjects": base + 0x5000,
        "gobjects_chunks": base + 0x6000,
        "gobjects_chunk0": base + 0x7000,
        "package_class": base + 0x20000,
        "function_class": base + 0x20100,
        "package_object": base + 0x21000,
        "chat_function": base + 0x21100,
    }

    def put_ptr(address: int, value: int) -> None:
        struct.pack_into("<Q", segment, address - base, value)

    def put_i32(address: int, value: int) -> None:
        struct.pack_into("<i", segment, address - base, value)

    def put_u32(address: int, value: int) -> None:
        struct.pack_into("<I", segment, address - base, value)

    def put_entry(index: int, text: bytes) -> None:
        entry = base + 0x4000 + index * 0x80
        put_ptr(addrs["fname_chunk"] + index * 8, entry)
        put_u32(entry, index * 2)
        segment[entry - base + 0x10 : entry - base + 0x10 + len(text)] = text

    def put_uobject(address: int, flags: int, internal_index: int, class_address: int, name_index: int, outer: int) -> None:
        put_u32(address + enum.UOBJECT_FLAGS_OFFSET, flags)
        put_i32(address + enum.UOBJECT_INTERNAL_INDEX_OFFSET, internal_index)
        put_ptr(address + enum.UOBJECT_CLASS_OFFSET, class_address)
        put_i32(address + enum.UOBJECT_NAME_INDEX_OFFSET, name_index)
        put_i32(address + enum.UOBJECT_NAME_NUMBER_OFFSET, 0)
        put_ptr(address + enum.UOBJECT_OUTER_OFFSET, outer)

    def put_item(index: int, object_address: int, dword_0x8: int, dword_0xC: int) -> None:
        item = addrs["gobjects_chunk0"] + index * enum.FUOBJECT_ITEM_SIZE
        put_ptr(item, object_address)
        put_u32(item + 0x8, dword_0x8)
        put_i32(item + 0xC, dword_0xC)

    put_ptr(addrs["fname_root_slot"], addrs["fname_table"])
    put_ptr(addrs["fname_table"], addrs["fname_chunk"])
    put_u32(addrs["fname_table"] + 0x800, 16)
    put_u32(addrs["fname_table"] + 0x804, 1)
    put_entry(0, b"None\x00")
    put_entry(1, b"Package\x00")
    put_entry(2, b"Function\x00")
    put_entry(3, b"/Script/CoreUObject\x00")
    put_entry(4, b"ServerChat\x00")

    put_ptr(addrs["gobjects"] + enum.GOBJECTS_CHUNKS_OFFSET, addrs["gobjects_chunks"])
    put_i32(addrs["gobjects"] + enum.GOBJECTS_COUNT_OFFSET, 4)
    put_ptr(addrs["gobjects_chunks"], addrs["gobjects_chunk0"])

    put_uobject(addrs["package_class"], 1, 2, addrs["package_class"], 1, 0)
    put_uobject(addrs["function_class"], 1, 3, addrs["package_class"], 2, 0)
    put_uobject(addrs["package_object"], 1, 0, addrs["package_class"], 3, 0)
    put_uobject(addrs["chat_function"], 1, 1, addrs["function_class"], 4, addrs["package_object"])
    put_item(0, addrs["package_object"], 100, 200)
    put_item(1, addrs["chat_function"], 101, 201)

    write_minimal_elf64_core(path, base, bytes(segment))
    return addrs


class EnumerateCoreUObjectsTests(unittest.TestCase):
    def test_enumerates_uobjects_and_resolves_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            core = Path(temp_dir) / "core"
            addrs = build_core_fixture(core)

            memory = enum.CoreMemory(core)
            try:
                metadata, objects = enum.iter_uobjects(
                    memory,
                    gobjects=addrs["gobjects"],
                    fname_root_slot=addrs["fname_root_slot"],
                    max_objects=8,
                )
            finally:
                memory.close()

        self.assertEqual(metadata["object_count"], 4)
        self.assertEqual([item["name"] for item in objects], ["/Script/CoreUObject", "ServerChat"])
        self.assertEqual(objects[0]["class_name"], "Package")
        self.assertEqual(objects[1]["class_name"], "Function")
        self.assertTrue(objects[0]["internal_index_matches"])
        self.assertTrue(objects[1]["internal_index_matches"])
        self.assertEqual(objects[1]["item_dword_0x8"], 101)
        self.assertEqual(objects[1]["item_dword_0xC"], 201)
        self.assertEqual(objects[1]["outer"], hex(addrs["package_object"]))

    def test_filters_by_name_and_class(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            core = Path(temp_dir) / "core"
            addrs = build_core_fixture(core)

            memory = enum.CoreMemory(core)
            try:
                _metadata, objects = enum.iter_uobjects(
                    memory,
                    gobjects=addrs["gobjects"],
                    fname_root_slot=addrs["fname_root_slot"],
                    max_objects=8,
                    name_contains="chat",
                    class_contains="func",
                )
            finally:
                memory.close()

        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0]["name"], "ServerChat")
        self.assertEqual(objects[0]["class_name"], "Function")

    def test_can_skip_name_resolution_for_fast_flag_serial_scans(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            core = Path(temp_dir) / "core"
            addrs = build_core_fixture(core)

            memory = enum.CoreMemory(core)
            try:
                metadata, objects = enum.iter_uobjects(
                    memory,
                    gobjects=addrs["gobjects"],
                    fname_root_slot=addrs["fname_root_slot"],
                    max_objects=8,
                    resolve_names=False,
                )
            finally:
                memory.close()

        self.assertEqual(metadata["name_resolution"], "disabled")
        self.assertEqual([item["name"] for item in objects], [None, None])
        self.assertEqual([item["class_name"] for item in objects], [None, None])
        self.assertEqual([item["name_index"] for item in objects], [3, 4])
        self.assertEqual(objects[1]["item_dword_0x8"], 101)
        self.assertTrue(objects[1]["internal_index_matches"])

    def test_name_filters_require_name_resolution(self) -> None:
        for filter_kwargs in ({"name_contains": "chat"}, {"class_contains": "func"}):
            with self.subTest(filter_kwargs=filter_kwargs), tempfile.TemporaryDirectory() as temp_dir:
                core = Path(temp_dir) / "core"
                addrs = build_core_fixture(core)

                memory = enum.CoreMemory(core)
                try:
                    with self.assertRaisesRegex(ValueError, "filters require name resolution"):
                        enum.iter_uobjects(
                            memory,
                            gobjects=addrs["gobjects"],
                            fname_root_slot=addrs["fname_root_slot"],
                            max_objects=8,
                            resolve_names=False,
                            **filter_kwargs,
                        )
                finally:
                    memory.close()

    def test_cli_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            core = Path(temp_dir) / "core"
            addrs = build_core_fixture(core)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "enumerate_core_uobjects.py"),
                    "--core",
                    str(core),
                    "--gobjects",
                    hex(addrs["gobjects"]),
                    "--fname-root-slot",
                    hex(addrs["fname_root_slot"]),
                    "--max-objects",
                    "2",
                    "--json",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["metadata"]["object_count"], 4)
        self.assertEqual(len(payload["objects"]), 2)
        self.assertEqual(payload["objects"][1]["name"], "ServerChat")

    def test_cli_rejects_protected_core_and_symlink_before_open(self) -> None:
        for core_arg in (
            "/servidor/ark/obelisk/dumps/protected-core",
            None,
        ):
            with self.subTest(core_arg=core_arg), tempfile.TemporaryDirectory() as temp_dir:
                if core_arg is None:
                    link = Path(temp_dir) / "core-link"
                    link.symlink_to("/servidor/ark/obelisk/dumps/protected-core")
                    selected_core = str(link)
                else:
                    selected_core = core_arg
                result = subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPT_DIR / "enumerate_core_uobjects.py"),
                        "--core",
                        selected_core,
                        "--json",
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )

                self.assertEqual(result.returncode, 1)
                self.assertIn("--core must not read from protected server root", result.stderr)


if __name__ == "__main__":
    unittest.main()
