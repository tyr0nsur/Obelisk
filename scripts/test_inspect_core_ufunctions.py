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
        "byte_property_class": base + 0x20400,
        "object_property_class": base + 0x20500,
        "struct_property_class": base + 0x20600,
        "bool_property_class": base + 0x20700,
        "package_object": base + 0x21000,
        "owner_class": base + 0x21100,
        "property_object": base + 0x21200,
        "chat_function": base + 0x21300,
        "chat_message_outer": base + 0x21400,
        "outer_matched_function": base + 0x21500,
        "byte_property_object": base + 0x21600,
        "byte_function": base + 0x21700,
        "send_mode_enum": base + 0x21800,
        "send_mode_enum_names": base + 0x21900,
        "shooter_player_controller_class": base + 0x22000,
        "server_request_inventory_use_item": base + 0x22100,
        "inventory_comp_property": base + 0x22200,
        "item_id_property": base + 0x22300,
        "primal_item_class": base + 0x22400,
        "allow_remote_add_to_inventory": base + 0x22500,
        "inv_comp_property": base + 0x22600,
        "by_pc_property": base + 0x22700,
        "requested_by_player_property": base + 0x22800,
        "return_value_property": base + 0x22900,
        "can_use_function": base + 0x22A00,
        "ignore_cooldown_property": base + 0x22B00,
        "can_use_return_property": base + 0x22C00,
        "malformed_function": base + 0x22D00,
        "malformed_bool_property": base + 0x22E00,
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
        entry = base + 0x10000 + index * 0x80
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
    put_u32(addrs["fname_table"] + 0x800, 64)
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
    put_entry(10, b"ByteProperty\x00")
    put_entry(11, b"ServerSendChatMessage\x00")
    put_entry(12, b"SendMode\x00")
    put_entry(13, b"EChatSendMode::GlobalChat\x00")
    put_entry(14, b"EChatSendMode::GlobalTribeChat\x00")
    put_entry(15, b"EChatSendMode::LocalChat\x00")
    put_entry(16, b"EChatSendMode::AllianceChat\x00")
    put_entry(17, b"ObjectProperty\x00")
    put_entry(18, b"StructProperty\x00")
    put_entry(19, b"BoolProperty\x00")
    put_entry(20, b"ShooterPlayerController\x00")
    put_entry(21, b"ServerRequestInventoryUseItem\x00")
    put_entry(22, b"InventoryComp\x00")
    put_entry(23, b"ItemId\x00")
    put_entry(24, b"PrimalItem\x00")
    put_entry(25, b"AllowRemoteAddToInventory\x00")
    put_entry(26, b"invComp\x00")
    put_entry(27, b"ByPC\x00")
    put_entry(28, b"bRequestedByPlayer\x00")
    put_entry(29, b"ReturnValue\x00")
    put_entry(30, b"CanUse\x00")
    put_entry(31, b"bIgnoreCooldown\x00")
    put_entry(32, b"MalformedCanUse\x00")

    put_ptr(addrs["gobjects"] + enum.GOBJECTS_CHUNKS_OFFSET, addrs["gobjects_chunks"])
    put_i32(addrs["gobjects"] + enum.GOBJECTS_COUNT_OFFSET, 32)
    put_ptr(addrs["gobjects_chunks"], addrs["gobjects_chunk0"])

    put_uobject(addrs["class_class"], 1, 0, addrs["class_class"], 1, 0)
    put_uobject(addrs["package_class"], 1, 1, addrs["class_class"], 2, 0)
    put_uobject(addrs["function_class"], 1, 2, addrs["class_class"], 3, 0)
    put_uobject(addrs["property_class"], 1, 3, addrs["class_class"], 4, 0)
    put_uobject(addrs["byte_property_class"], 1, 10, addrs["class_class"], 10, 0)
    put_uobject(addrs["object_property_class"], 1, 13, addrs["class_class"], 17, 0)
    put_uobject(addrs["struct_property_class"], 1, 14, addrs["class_class"], 18, 0)
    put_uobject(addrs["bool_property_class"], 1, 15, addrs["class_class"], 19, 0)
    put_uobject(addrs["package_object"], 1, 4, addrs["package_class"], 5, 0)
    put_uobject(addrs["owner_class"], 1, 5, addrs["class_class"], 6, addrs["package_object"])
    put_uobject(addrs["property_object"], 1, 6, addrs["property_class"], 7, addrs["chat_function"])
    put_uobject(addrs["chat_function"], 1, 7, addrs["function_class"], 8, addrs["owner_class"])
    put_uobject(addrs["chat_message_outer"], 1, 8, addrs["class_class"], 7, addrs["package_object"])
    put_uobject(addrs["outer_matched_function"], 1, 9, addrs["function_class"], 9, addrs["chat_message_outer"])
    put_uobject(addrs["byte_property_object"], 1, 11, addrs["byte_property_class"], 12, addrs["byte_function"])
    put_uobject(addrs["byte_function"], 1, 12, addrs["function_class"], 11, addrs["owner_class"])
    put_uobject(
        addrs["shooter_player_controller_class"],
        1,
        16,
        addrs["class_class"],
        20,
        addrs["package_object"],
    )
    put_uobject(
        addrs["server_request_inventory_use_item"],
        1,
        17,
        addrs["function_class"],
        21,
        addrs["shooter_player_controller_class"],
    )
    put_uobject(
        addrs["inventory_comp_property"],
        1,
        18,
        addrs["object_property_class"],
        22,
        addrs["server_request_inventory_use_item"],
    )
    put_uobject(
        addrs["item_id_property"],
        1,
        19,
        addrs["struct_property_class"],
        23,
        addrs["server_request_inventory_use_item"],
    )
    put_uobject(addrs["primal_item_class"], 1, 20, addrs["class_class"], 24, addrs["package_object"])
    put_uobject(
        addrs["allow_remote_add_to_inventory"],
        1,
        21,
        addrs["function_class"],
        25,
        addrs["primal_item_class"],
    )
    put_uobject(
        addrs["inv_comp_property"],
        1,
        22,
        addrs["object_property_class"],
        26,
        addrs["allow_remote_add_to_inventory"],
    )
    put_uobject(
        addrs["by_pc_property"],
        1,
        23,
        addrs["object_property_class"],
        27,
        addrs["allow_remote_add_to_inventory"],
    )
    put_uobject(
        addrs["requested_by_player_property"],
        1,
        24,
        addrs["bool_property_class"],
        28,
        addrs["allow_remote_add_to_inventory"],
    )
    put_uobject(
        addrs["return_value_property"],
        1,
        25,
        addrs["bool_property_class"],
        29,
        addrs["allow_remote_add_to_inventory"],
    )
    put_uobject(addrs["can_use_function"], 1, 26, addrs["function_class"], 30, addrs["primal_item_class"])
    put_uobject(
        addrs["ignore_cooldown_property"],
        1,
        27,
        addrs["bool_property_class"],
        31,
        addrs["can_use_function"],
    )
    put_uobject(
        addrs["can_use_return_property"],
        1,
        28,
        addrs["bool_property_class"],
        29,
        addrs["can_use_function"],
    )
    put_uobject(addrs["malformed_function"], 1, 29, addrs["function_class"], 32, addrs["primal_item_class"])
    put_uobject(
        addrs["malformed_bool_property"],
        1,
        30,
        addrs["bool_property_class"],
        29,
        addrs["malformed_function"],
    )

    for index, key in [
        (0, "class_class"),
        (1, "package_class"),
        (2, "function_class"),
        (3, "property_class"),
        (4, "package_object"),
        (5, "owner_class"),
        (6, "property_object"),
        (7, "chat_function"),
        (8, "chat_message_outer"),
        (9, "outer_matched_function"),
        (10, "byte_property_class"),
        (11, "byte_property_object"),
        (12, "byte_function"),
        (13, "object_property_class"),
        (14, "struct_property_class"),
        (15, "bool_property_class"),
        (16, "shooter_player_controller_class"),
        (17, "server_request_inventory_use_item"),
        (18, "inventory_comp_property"),
        (19, "item_id_property"),
        (20, "primal_item_class"),
        (21, "allow_remote_add_to_inventory"),
        (22, "inv_comp_property"),
        (23, "by_pc_property"),
        (24, "requested_by_player_property"),
        (25, "return_value_property"),
        (26, "can_use_function"),
        (27, "ignore_cooldown_property"),
        (28, "can_use_return_property"),
        (29, "malformed_function"),
        (30, "malformed_bool_property"),
    ]:
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
    put_ptr(addrs["byte_function"] + 0x38, addrs["byte_property_object"])
    put_i32(addrs["byte_function"] + 0x40, 0x11)
    put_i32(addrs["byte_function"] + 0x44, 0x8)
    put_u32(addrs["byte_function"] + 0x90, 0x00204000)
    put_u16(addrs["byte_function"] + 0x94, 0xFFFF)
    put_u16(addrs["byte_function"] + 0x96, 1)
    put_u16(addrs["byte_function"] + 0x98, 0x11)
    put_u16(addrs["byte_function"] + 0x9A, 0xFFFF)
    put_i32(addrs["byte_property_object"] + 0x30, 1)
    put_i32(addrs["byte_property_object"] + 0x34, 1)
    put_ptr(addrs["byte_property_object"] + 0x38, 0x280)
    put_i32(addrs["byte_property_object"] + 0x4C, 0x10)
    put_ptr(addrs["byte_property_object"] + 0x70, addrs["send_mode_enum"])
    put_ptr(addrs["send_mode_enum"] + 0x40, addrs["send_mode_enum_names"])
    put_i32(addrs["send_mode_enum"] + 0x48, 4)
    for enum_value, name_index in enumerate(range(13, 17)):
        put_i32(addrs["send_mode_enum_names"] + enum_value * 8, name_index)
        put_i32(addrs["send_mode_enum_names"] + enum_value * 8 + 4, 0)
    put_u32(addrs["readable_non_uobject"], 0xABCD)

    def put_property_data(address: int, *, offset: int, element_size: int, next_field: int = 0) -> None:
        put_ptr(address + 0x28, next_field)
        put_i32(address + 0x30, 1)
        put_i32(address + 0x34, element_size)
        put_ptr(address + 0x38, 0x1040000280)
        put_i32(address + 0x4C, offset)

    def put_function_data(address: int, *, first_property: int, num_parms: int, parms_size: int) -> None:
        put_ptr(address + 0x38, first_property)
        put_i32(address + 0x40, parms_size)
        put_i32(address + 0x44, 0x8)
        put_u32(address + 0x90, 0x00204000)
        put_u16(address + 0x94, 0xFFFF)
        put_u16(address + 0x96, num_parms)
        put_u16(address + 0x98, parms_size)
        put_u16(address + 0x9A, 0xFFFF)

    put_function_data(
        addrs["server_request_inventory_use_item"],
        first_property=addrs["inventory_comp_property"],
        num_parms=2,
        parms_size=16,
    )
    put_property_data(
        addrs["inventory_comp_property"],
        offset=0,
        element_size=8,
        next_field=addrs["item_id_property"],
    )
    put_property_data(addrs["item_id_property"], offset=8, element_size=8)

    put_function_data(
        addrs["allow_remote_add_to_inventory"],
        first_property=addrs["inv_comp_property"],
        num_parms=4,
        parms_size=18,
    )
    put_property_data(addrs["inv_comp_property"], offset=0, element_size=8, next_field=addrs["by_pc_property"])
    put_property_data(
        addrs["by_pc_property"],
        offset=8,
        element_size=8,
        next_field=addrs["requested_by_player_property"],
    )
    put_property_data(
        addrs["requested_by_player_property"],
        offset=0x10,
        element_size=1,
        next_field=addrs["return_value_property"],
    )
    put_property_data(addrs["return_value_property"], offset=0x11, element_size=1)

    put_function_data(addrs["can_use_function"], first_property=addrs["ignore_cooldown_property"], num_parms=2, parms_size=2)
    put_property_data(
        addrs["ignore_cooldown_property"],
        offset=0,
        element_size=1,
        next_field=addrs["can_use_return_property"],
    )
    put_property_data(addrs["can_use_return_property"], offset=1, element_size=1)

    put_function_data(addrs["malformed_function"], first_property=addrs["malformed_bool_property"], num_parms=1, parms_size=1)
    put_property_data(addrs["malformed_bool_property"], offset=1, element_size=1)

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
        self.assertEqual(target["object_membership_status"], "candidate-uobject")
        self.assertEqual(target["object_gobjects_index"], 7)
        self.assertEqual(target["class_membership_status"], "candidate-uobject")
        self.assertEqual(target["class_index"], 2)
        self.assertEqual(target["outer_membership_status"], "candidate-uobject")
        self.assertEqual(target["outer_index"], 5)
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
        prop = target["property_chain"]["properties"][0]
        self.assertEqual(prop["summary"]["name"], "ChatMessage")
        self.assertEqual(prop["offset_internal"], 0)
        self.assertEqual(prop["membership_status"], "candidate-uobject")
        self.assertEqual(prop["gobjects_index"], 6)
        self.assertEqual(prop["class_membership_status"], "candidate-uobject")
        self.assertEqual(prop["class_gobjects_index"], 3)
        self.assertEqual(prop["outer_membership_status"], "candidate-uobject")
        self.assertEqual(prop["outer_gobjects_index"], 7)

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

    def test_byte_property_reports_enum_candidate(self) -> None:
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
                    indices=[12],
                    name_contains=[],
                    outer_contains=[],
                    window_size=0xC0,
                    max_object_scan=16,
                )
            finally:
                memory.close()

        prop = payload["targets"][0]["property_chain"]["properties"][0]
        self.assertEqual(prop["summary"]["class_name"], "ByteProperty")
        self.assertEqual(prop["summary"]["name"], "SendMode")
        self.assertEqual(prop["enum_candidate"]["status"], "candidate")
        self.assertEqual(
            [item["name"] for item in prop["enum_candidate"]["values"]],
            [
                "EChatSendMode::GlobalChat",
                "EChatSendMode::GlobalTribeChat",
                "EChatSendMode::LocalChat",
                "EChatSendMode::AllianceChat",
            ],
        )

    def test_non_chat_inventory_request_property_chain(self) -> None:
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
                    indices=[],
                    name_contains=["ServerRequestInventoryUseItem"],
                    outer_contains=["ShooterPlayerController"],
                    window_size=0xC0,
                    max_object_scan=32,
                )
            finally:
                memory.close()

        self.assertEqual(len(payload["targets"]), 1)
        target = payload["targets"][0]
        self.assertEqual(target["status"], "candidate")
        chain = target["property_chain"]
        self.assertEqual(chain["status"], "candidate")
        self.assertEqual(chain["observed_count"], 2)
        self.assertEqual(chain["expected_count"], 2)
        props = chain["properties"]
        self.assertEqual(
            [(prop["summary"]["name"], prop["summary"]["class_name"], prop["offset_internal"], prop["element_size"]) for prop in props],
            [
                ("InventoryComp", "ObjectProperty", 0, 8),
                ("ItemId", "StructProperty", 8, 8),
            ],
        )

    def test_primal_item_bool_return_property_chain(self) -> None:
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
                    indices=[],
                    name_contains=["AllowRemoteAddToInventory"],
                    outer_contains=["PrimalItem"],
                    window_size=0xC0,
                    max_object_scan=32,
                )
            finally:
                memory.close()

        self.assertEqual(len(payload["targets"]), 1)
        target = payload["targets"][0]
        chain = target["property_chain"]
        self.assertEqual(chain["status"], "candidate")
        self.assertEqual(chain["observed_count"], 4)
        props = chain["properties"]
        self.assertEqual(
            [(prop["summary"]["name"], prop["summary"]["class_name"], prop["offset_internal"], prop["element_size"]) for prop in props],
            [
                ("invComp", "ObjectProperty", 0, 8),
                ("ByPC", "ObjectProperty", 8, 8),
                ("bRequestedByPlayer", "BoolProperty", 0x10, 1),
                ("ReturnValue", "BoolProperty", 0x11, 1),
            ],
        )
        for prop in props:
            self.assertEqual(prop["membership_status"], "candidate-uobject")
            self.assertEqual(prop["class_membership_status"], "candidate-uobject")
            self.assertEqual(prop["outer_membership_status"], "candidate-uobject")

    def test_rejects_non_chat_property_exceeding_parms_size(self) -> None:
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
                    indices=[],
                    name_contains=["MalformedCanUse"],
                    outer_contains=["PrimalItem"],
                    window_size=0xC0,
                    max_object_scan=32,
                )
            finally:
                memory.close()

        target = payload["targets"][0]
        chain = target["property_chain"]
        self.assertEqual(chain["status"], "rejected")
        self.assertIn("property_0_rejected", chain["reject_reasons"])
        self.assertIn("property_exceeds_parms_size", chain["properties"][0]["reject_reasons"])

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
                    "ServerChat",
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
        self.assertIn("object_membership=candidate-uobject", result.stdout)
        self.assertIn("class_membership=candidate-uobject", result.stdout)
        self.assertIn("outer_membership=candidate-uobject", result.stdout)


if __name__ == "__main__":
    unittest.main()
