#!/usr/bin/env python3
"""Offline tests for inspect_core_ufunctions.py."""

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
import inspect_core_ufunctions as inspector
from test_scan_core_fname_tables import write_minimal_elf64_core


def build_core_fixture(path: Path) -> dict[str, int]:
    base = 0x10000000
    segment = bytearray(0x90000)
    addrs = {
        "base": base,
        "fname_root_slot": base + 0x100,
        "fname_table": base + 0x1000,
        "fname_chunk": base + 0x3000,
        "gobjects": base + 0x5000,
        "gobjects_chunks": base + 0x6000,
        "gobjects_chunk0": base + 0x7000,
        "class_class": base + 0x20000,
        "package_class": base + 0x20100,
        "function_class": base + 0x20200,
        "property_class": base + 0x20300,
        "package_object": base + 0x21000,
        "owner_class": base + 0x21100,
        "property_object": base + 0x21200,
        "chat_function": base + 0x21300,
        "chat_message_outer": base + 0x21400,
        "outer_matched_function": base + 0x21500,
        "readable_non_uobject": base + 0x80000,
    }

    def put_ptr(address: int, value: int) -> None:
        struct.pack_into("<Q", segment, address - base, value)

    def put_i32(address: int, value: int) -> None:
        struct.pack_into("<i", segment, address - base, value)

    def put_u16(address: int, value: int) -> None:
        struct.pack_into("<H", segment, address - base, value)

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

    def put_item(index: int, object_address: int, serial: int) -> None:
        item = addrs["gobjects_chunk0"] + index * enum.FUOBJECT_ITEM_SIZE
        put_ptr(item, object_address)
        put_u32(item + 0x8, 0)
        put_i32(item + 0xC, serial)

    put_ptr(addrs["fname_root_slot"], addrs["fname_table"])
    put_ptr(addrs["fname_table"], addrs["fname_chunk"])
    put_u32(addrs["fname_table"] + 0x800, 32)
    put_u32(addrs["fname_table"] + 0x804, 1)
    put_entry(0, b"None\x00")
    put_entry(1, b"Class\x00")
    put_entry(2, b"Package\x00")
    put_entry(3, b"Function\x00")
    put_entry(4, b"IntProperty\x00")
    put_entry(5, b"/Script/ShooterGame\x00")
    put_entry(6, b"ShooterGameMode\x00")
    put_entry(7, b"ChatMessage\x00")
    put_entry(8, b"ServerChat\x00")
    put_entry(9, b"AdminCommand\x00")

    put_ptr(addrs["gobjects"] + enum.GOBJECTS_CHUNKS_OFFSET, addrs["gobjects_chunks"])
    put_i32(addrs["gobjects"] + enum.GOBJECTS_COUNT_OFFSET, 10)
    put_ptr(addrs["gobjects_chunks"], addrs["gobjects_chunk0"])

    put_uobject(addrs["class_class"], 1, 0, addrs["class_class"], 1, 0)
    put_uobject(addrs["package_class"], 1, 1, addrs["class_class"], 2, 0)
    put_uobject(addrs["function_class"], 1, 2, addrs["class_class"], 3, 0)
    put_uobject(addrs["property_class"], 1, 3, addrs["class_class"], 4, 0)
    put_uobject(addrs["package_object"], 1, 4, addrs["package_class"], 5, 0)
    put_uobject(addrs["owner_class"], 1, 5, addrs["class_class"], 6, addrs["package_object"])
    put_uobject(addrs["property_object"], 1, 6, addrs["property_class"], 7, addrs["chat_function"])
    put_uobject(addrs["chat_function"], 1, 7, addrs["function_class"], 8, addrs["owner_class"])
    put_uobject(addrs["chat_message_outer"], 1, 8, addrs["class_class"], 7, addrs["package_object"])
    put_uobject(addrs["outer_matched_function"], 1, 9, addrs["function_class"], 9, addrs["chat_message_outer"])

    for index, key in enumerate(
        [
            "class_class",
            "package_class",
            "function_class",
            "property_class",
            "package_object",
            "owner_class",
            "property_object",
            "chat_function",
            "chat_message_outer",
            "outer_matched_function",
        ]
    ):
        put_item(index, addrs[key], 100 + index)

    put_ptr(addrs["chat_function"] + 0x38, addrs["property_object"])
    put_i32(addrs["chat_function"] + 0x40, 0x20)
    put_i32(addrs["chat_function"] + 0x44, 0x8)
    put_u32(addrs["chat_function"] + 0x90, 0x00204000)
    put_u16(addrs["chat_function"] + 0x94, 0xFFFF)
    put_u16(addrs["chat_function"] + 0x96, 1)
    put_u16(addrs["chat_function"] + 0x98, 0x18)
    put_u16(addrs["chat_function"] + 0x9A, 0xFFFF)
    put_u16(addrs["chat_function"] + 0x9C, 0)
    put_u16(addrs["chat_function"] + 0x9E, 0)
    put_ptr(addrs["chat_function"] + 0xB0, 0xDEADBEEF)
    put_i32(addrs["property_object"] + 0x30, 1)
    put_i32(addrs["property_object"] + 0x34, 0x10)
    put_ptr(addrs["property_object"] + 0x38, 0x280)
    put_i32(addrs["property_object"] + 0x4C, 0)
    put_u32(addrs["readable_non_uobject"], 0xABCD)

    write_minimal_elf64_core(path, base, bytes(segment))
    return addrs


class InspectCoreUFunctionsTests(unittest.TestCase):
    def test_inspects_index_and_resolves_candidate_uobject_pointers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            core = Path(temp_dir) / "core"
            addrs = build_core_fixture(core)
            memory = inspector.uobjects.CoreMemory(core)
            try:
                payload = inspector.inspect_core(
                    memory,
                    gobjects=addrs["gobjects"],
                    fname_root_slot=addrs["fname_root_slot"],
                    object_addresses=[],
                    indices=[7],
                    name_contains=[],
                    outer_contains=[],
                    window_size=0xC0,
                    max_object_scan=16,
                )
            finally:
                memory.close()

        target = payload["targets"][0]
        self.assertEqual(target["status"], "candidate")
        self.assertEqual(target["object"], hex(addrs["chat_function"]))
        self.assertEqual(target["object_summary"]["name"], "ServerChat")
        self.assertEqual(target["object_summary"]["class_name"], "Function")

        pointers = {item["offset"]: item for item in target["pointer_window"]}
        self.assertEqual(pointers["0x10"]["status"], "candidate-uobject")
        self.assertEqual(pointers["0x10"]["resolved_uobject"]["name"], "Function")
        self.assertEqual(pointers["0x20"]["resolved_uobject"]["name"], "ShooterGameMode")
        self.assertEqual(pointers["0x38"]["resolved_uobject"]["name"], "ChatMessage")
        self.assertEqual(pointers["0xb0"]["status"], "rejected")
        self.assertIn("pointer_target_not_in_core_segments", pointers["0xb0"]["reject_reasons"])

        fields = {item["label"]: item for item in target["candidate_fields"]}
        self.assertEqual(fields["ufunction.num_parms"]["value"], 1)
        self.assertEqual(fields["ufunction.num_parms"]["status"], "candidate")
        self.assertEqual(fields["ufunction.parms_size"]["value"], 0x18)
        self.assertEqual(fields["ufunction.function_flags"]["value_hex"], "0x204000")
        self.assertEqual(fields["ufunction.return_value_offset"]["value_hex"], "0xffff")
        self.assertEqual(target["property_chain"]["status"], "candidate")
        self.assertEqual(target["property_chain"]["observed_count"], 1)
        self.assertEqual(target["property_chain"]["properties"][0]["summary"]["name"], "ChatMessage")
        self.assertEqual(target["property_chain"]["properties"][0]["offset_internal"], 0)

    def test_rejects_non_function_target_without_promoting_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            core = Path(temp_dir) / "core"
            addrs = build_core_fixture(core)
            memory = inspector.uobjects.CoreMemory(core)
            try:
                payload = inspector.inspect_core(
                    memory,
                    gobjects=addrs["gobjects"],
                    fname_root_slot=addrs["fname_root_slot"],
                    object_addresses=[addrs["package_object"]],
                    indices=[],
                    name_contains=[],
                    outer_contains=[],
                    window_size=0x40,
                    max_object_scan=16,
                )
            finally:
                memory.close()

        target = payload["targets"][0]
        self.assertEqual(target["status"], "rejected")
        self.assertIn("class_name_not_function_or_struct", target["reject_reasons"])
        self.assertEqual(payload["interpretation"]["status"], "candidate-only")

    def test_cli_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            core = Path(temp_dir) / "core"
            addrs = build_core_fixture(core)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "inspect_core_ufunctions.py"),
                    "--core",
                    str(core),
                    "--gobjects",
                    hex(addrs["gobjects"]),
                    "--fname-root-slot",
                    hex(addrs["fname_root_slot"]),
                    "--index",
                    "7",
                    "--json",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["targets"][0]["object_summary"]["name"], "ServerChat")
        self.assertEqual(payload["targets"][0]["pointer_window"][2]["label"], "uobject.class")

    def test_cli_name_contains_finds_matching_function(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            core = Path(temp_dir) / "core"
            addrs = build_core_fixture(core)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "inspect_core_ufunctions.py"),
                    "--core",
                    str(core),
                    "--gobjects",
                    hex(addrs["gobjects"]),
                    "--fname-root-slot",
                    hex(addrs["fname_root_slot"]),
                    "--name-contains",
                    "Chat",
                    "--json",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        payload = json.loads(result.stdout)
        self.assertEqual([target["object_summary"]["name"] for target in payload["targets"]], ["ServerChat"])
        self.assertEqual(payload["targets"][0]["object_index"], 7)
        self.assertEqual(payload["targets"][0]["outer_summary"]["name"], "ShooterGameMode")

    def test_cli_outer_contains_finds_matching_function(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            core = Path(temp_dir) / "core"
            addrs = build_core_fixture(core)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "inspect_core_ufunctions.py"),
                    "--core",
                    str(core),
                    "--gobjects",
                    hex(addrs["gobjects"]),
                    "--fname-root-slot",
                    hex(addrs["fname_root_slot"]),
                    "--outer-contains",
                    "ChatMessage",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        self.assertIn("object_index=9 class='Function' name='AdminCommand'", result.stdout)
        self.assertIn("outer_index=8 outer_name='ChatMessage'", result.stdout)

    def test_cli_text_mentions_candidate_only_and_reject_reasons(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            core = Path(temp_dir) / "core"
            addrs = build_core_fixture(core)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "inspect_core_ufunctions.py"),
                    "--core",
                    str(core),
                    "--gobjects",
                    hex(addrs["gobjects"]),
                    "--fname-root-slot",
                    hex(addrs["fname_root_slot"]),
                    "--object",
                    hex(addrs["chat_function"]),
                    "--window-size",
                    "0xc0",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        self.assertIn("interpretation=candidate-only", result.stdout)
        self.assertIn("label=ufunction.trailing_pointer_candidate", result.stdout)
        self.assertIn("pointer_target_not_in_core_segments", result.stdout)
        self.assertIn("class='Function' name='ServerChat'", result.stdout)
        self.assertIn("resolved='IntProperty'/'ChatMessage'", result.stdout)
        self.assertIn("label=ufunction.function_flags", result.stdout)
        self.assertIn("property_chain", result.stdout)
        self.assertIn("prop depth=0", result.stdout)


if __name__ == "__main__":
    unittest.main()
