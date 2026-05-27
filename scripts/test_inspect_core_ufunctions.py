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
        "primal_dino_character_class": base + 0x22F00,
        "server_request_attack_function": base + 0x23000,
        "attack_index_property": base + 0x23100,
        "bp_notify_add_passenger_function": base + 0x23200,
        "passenger_char_property": base + 0x23300,
        "seat_index_property": base + 0x23400,
        "primal_structure_elevator_platform_class": base + 0x23500,
        "server_activate_function": base + 0x23600,
        "for_pc_property": base + 0x23700,
        "force_direction_property": base + 0x23800,
        "dir_property": base + 0x23900,
        "mission_type_class": base + 0x23A00,
        "add_player_to_mission_function": base + 0x23B00,
        "mission_player_character_property": base + 0x23C00,
        "mission_force_add_property": base + 0x23D00,
        "mission_return_value_property": base + 0x23E00,
        "bp_allow_player_leave_function": base + 0x23F00,
        "leave_player_character_property": base + 0x24000,
        "leave_return_value_property": base + 0x24100,
        "bp_on_player_added_function": base + 0x24200,
        "added_player_character_property": base + 0x24300,
        "added_player_controller_property": base + 0x24400,
        "deferred_mission_string_array_function": base + 0x24500,
        "mission_name_property": base + 0x24600,
        "mission_tags_property": base + 0x24700,
        "str_property_class": base + 0x24800,
        "array_property_class": base + 0x24900,
        "mission_tags_inner_property": base + 0x24980,
        "primal_structure_class": base + 0x24A00,
        "allow_structure_access_function": base + 0x24B00,
        "allow_structure_access_for_pc_property": base + 0x24C00,
        "allow_structure_access_return_property": base + 0x24D00,
        "is_allowed_to_demolish_function": base + 0x24E00,
        "demolish_for_pc_property": base + 0x24F00,
        "demolish_return_property": base + 0x25000,
        "set_variant_function": base + 0x25100,
        "variant_index_property": base + 0x25200,
        "force_set_property": base + 0x25300,
        "set_variant_return_property": base + 0x25400,
        "primal_structure_item_container_class": base + 0x25500,
        "verify_pin_code_function": base + 0x25600,
        "pin_code_property": base + 0x25700,
        "verify_pin_return_property": base + 0x25800,
        "primal_structure_seating_class": base + 0x25900,
        "can_seat_function": base + 0x25A00,
        "can_seat_for_pc_property": base + 0x25B00,
        "for_character_property": base + 0x25C00,
        "can_seat_force_property": base + 0x25D00,
        "can_seat_return_property": base + 0x25E00,
        "add_passenger_function": base + 0x25F00,
        "add_passenger_character_property": base + 0x26000,
        "passenger_seat_index_property": base + 0x26100,
        "force_passenger_property": base + 0x26200,
        "allow_flyers_water_property": base + 0x26300,
        "skip_line_trace_property": base + 0x26400,
        "add_passenger_return_property": base + 0x26500,
        "allow_carry_character_function": base + 0x26600,
        "can_carry_pawn_property": base + 0x26700,
        "allow_carry_return_property": base + 0x26800,
        "bp_allow_carry_character_function": base + 0x26900,
        "check_character_property": base + 0x26A00,
        "bp_allow_carry_return_property": base + 0x26B00,
        "set_character_status_tameable_function": base + 0x26C00,
        "set_tameable_property": base + 0x26D00,
        "create_inventory_property": base + 0x26E00,
        "inventory_for_waking_tame_property": base + 0x26F00,
        "server_request_dino_char_stats_function": base + 0x27000,
        "the_dino_char_property": base + 0x27100,
        "server_request_tribe_log_function": base + 0x27200,
        "script_struct_class": base + 0x27300,
        "tribute_dino_struct": base + 0x27400,
        "tribute_dino_class_name_property": base + 0x27500,
        "tribute_dino_id1_property": base + 0x27600,
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

    def add_uobject(
        key: str,
        *,
        object_index: int,
        class_key: str,
        name_index: int,
        outer_key: str | None,
    ) -> None:
        outer = addrs[outer_key] if outer_key else 0
        put_uobject(addrs[key], 1, object_index, addrs[class_key], name_index, outer)
        put_item(object_index, addrs[key], 100 + object_index)

    put_ptr(addrs["fname_root_slot"], addrs["fname_table"])
    put_ptr(addrs["fname_table"], addrs["fname_chunk"])
    put_u32(addrs["fname_table"] + 0x800, 128)
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
    put_entry(33, b"PrimalDinoCharacter\x00")
    put_entry(34, b"ServerRequestAttack\x00")
    put_entry(35, b"AttackIndex\x00")
    put_entry(36, b"BPNotifyAddPassenger\x00")
    put_entry(37, b"PassengerChar\x00")
    put_entry(38, b"SeatIndex\x00")
    put_entry(39, b"PrimalStructureElevatorPlatform\x00")
    put_entry(40, b"ServerActivate\x00")
    put_entry(41, b"ForPC\x00")
    put_entry(42, b"bForceDirection\x00")
    put_entry(43, b"Dir\x00")
    put_entry(44, b"MissionType\x00")
    put_entry(45, b"AddPlayerToMission\x00")
    put_entry(46, b"PlayerCharacter\x00")
    put_entry(47, b"bForceAdd\x00")
    put_entry(48, b"BPAllowPlayerToLeaveMission\x00")
    put_entry(49, b"BPOnPlayerAddedToMission\x00")
    put_entry(50, b"PlayerController\x00")
    put_entry(51, b"DeferredMissionStringArray\x00")
    put_entry(52, b"MissionName\x00")
    put_entry(53, b"MissionTags\x00")
    put_entry(54, b"StrProperty\x00")
    put_entry(55, b"ArrayProperty\x00")
    put_entry(56, b"PrimalStructure\x00")
    put_entry(57, b"AllowStructureAccess\x00")
    put_entry(58, b"IsAllowedToDemolish\x00")
    put_entry(59, b"SetVariant\x00")
    put_entry(60, b"VariantIndex\x00")
    put_entry(61, b"bForceSet\x00")
    put_entry(62, b"PrimalStructureItemContainer\x00")
    put_entry(63, b"VerifyPinCode\x00")
    put_entry(64, b"pinCode\x00")
    put_entry(65, b"PrimalStructureSeating\x00")
    put_entry(66, b"CanSeat\x00")
    put_entry(67, b"forCharacter\x00")
    put_entry(68, b"bForce\x00")
    put_entry(69, b"AddPassenger\x00")
    put_entry(70, b"ACharacter\x00")
    put_entry(71, b"PassengerSeatIndex\x00")
    put_entry(72, b"bForcePassenger\x00")
    put_entry(73, b"bAllowFlyersAndWaterDinos\x00")
    put_entry(74, b"bSkipLineTrace\x00")
    put_entry(75, b"AllowCarryCharacter\x00")
    put_entry(76, b"CanCarryPawn\x00")
    put_entry(77, b"BPAllowCarryCharacter\x00")
    put_entry(78, b"checkCharacter\x00")
    put_entry(79, b"SetCharacterStatusTameable\x00")
    put_entry(80, b"bSetTameable\x00")
    put_entry(81, b"bCreateInventory\x00")
    put_entry(82, b"bInventoryForWakingTame\x00")
    put_entry(83, b"ServerRequestDinoCharStats\x00")
    put_entry(84, b"theDinoChar\x00")
    put_entry(85, b"ServerRequestTribeLog\x00")
    put_entry(86, b"MissionTag\x00")
    put_entry(87, b"ScriptStruct\x00")
    put_entry(88, b"ARKTributeDino\x00")
    put_entry(89, b"DinoClassName\x00")
    put_entry(90, b"DinoID1\x00")

    put_ptr(addrs["gobjects"] + enum.GOBJECTS_CHUNKS_OFFSET, addrs["gobjects_chunks"])
    put_i32(addrs["gobjects"] + enum.GOBJECTS_COUNT_OFFSET, 104)
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
    add_uobject("primal_dino_character_class", object_index=31, class_key="class_class", name_index=33, outer_key="package_object")
    add_uobject(
        "server_request_attack_function",
        object_index=32,
        class_key="function_class",
        name_index=34,
        outer_key="primal_dino_character_class",
    )
    add_uobject(
        "attack_index_property",
        object_index=33,
        class_key="property_class",
        name_index=35,
        outer_key="server_request_attack_function",
    )
    add_uobject(
        "bp_notify_add_passenger_function",
        object_index=34,
        class_key="function_class",
        name_index=36,
        outer_key="primal_dino_character_class",
    )
    add_uobject(
        "passenger_char_property",
        object_index=35,
        class_key="object_property_class",
        name_index=37,
        outer_key="bp_notify_add_passenger_function",
    )
    add_uobject(
        "seat_index_property",
        object_index=36,
        class_key="property_class",
        name_index=38,
        outer_key="bp_notify_add_passenger_function",
    )
    add_uobject(
        "primal_structure_elevator_platform_class",
        object_index=37,
        class_key="class_class",
        name_index=39,
        outer_key="package_object",
    )
    add_uobject(
        "server_activate_function",
        object_index=38,
        class_key="function_class",
        name_index=40,
        outer_key="primal_structure_elevator_platform_class",
    )
    add_uobject(
        "for_pc_property",
        object_index=39,
        class_key="object_property_class",
        name_index=41,
        outer_key="server_activate_function",
    )
    add_uobject(
        "force_direction_property",
        object_index=40,
        class_key="bool_property_class",
        name_index=42,
        outer_key="server_activate_function",
    )
    add_uobject("dir_property", object_index=41, class_key="byte_property_class", name_index=43, outer_key="server_activate_function")
    add_uobject("str_property_class", object_index=42, class_key="class_class", name_index=54, outer_key=None)
    add_uobject("array_property_class", object_index=43, class_key="class_class", name_index=55, outer_key=None)
    add_uobject("mission_type_class", object_index=44, class_key="class_class", name_index=44, outer_key="package_object")
    add_uobject(
        "add_player_to_mission_function",
        object_index=45,
        class_key="function_class",
        name_index=45,
        outer_key="mission_type_class",
    )
    add_uobject(
        "mission_player_character_property",
        object_index=46,
        class_key="object_property_class",
        name_index=46,
        outer_key="add_player_to_mission_function",
    )
    add_uobject(
        "mission_force_add_property",
        object_index=47,
        class_key="bool_property_class",
        name_index=47,
        outer_key="add_player_to_mission_function",
    )
    add_uobject(
        "mission_return_value_property",
        object_index=48,
        class_key="bool_property_class",
        name_index=29,
        outer_key="add_player_to_mission_function",
    )
    add_uobject(
        "bp_allow_player_leave_function",
        object_index=49,
        class_key="function_class",
        name_index=48,
        outer_key="mission_type_class",
    )
    add_uobject(
        "leave_player_character_property",
        object_index=50,
        class_key="object_property_class",
        name_index=46,
        outer_key="bp_allow_player_leave_function",
    )
    add_uobject(
        "leave_return_value_property",
        object_index=51,
        class_key="bool_property_class",
        name_index=29,
        outer_key="bp_allow_player_leave_function",
    )
    add_uobject(
        "bp_on_player_added_function",
        object_index=52,
        class_key="function_class",
        name_index=49,
        outer_key="mission_type_class",
    )
    add_uobject(
        "added_player_character_property",
        object_index=53,
        class_key="object_property_class",
        name_index=46,
        outer_key="bp_on_player_added_function",
    )
    add_uobject(
        "added_player_controller_property",
        object_index=54,
        class_key="object_property_class",
        name_index=50,
        outer_key="bp_on_player_added_function",
    )
    add_uobject(
        "deferred_mission_string_array_function",
        object_index=55,
        class_key="function_class",
        name_index=51,
        outer_key="mission_type_class",
    )
    add_uobject(
        "mission_name_property",
        object_index=56,
        class_key="str_property_class",
        name_index=52,
        outer_key="deferred_mission_string_array_function",
    )
    add_uobject(
        "mission_tags_property",
        object_index=57,
        class_key="array_property_class",
        name_index=53,
        outer_key="deferred_mission_string_array_function",
    )
    add_uobject(
        "mission_tags_inner_property",
        object_index=99,
        class_key="str_property_class",
        name_index=86,
        outer_key="mission_tags_property",
    )
    add_uobject("primal_structure_class", object_index=58, class_key="class_class", name_index=56, outer_key="package_object")
    add_uobject(
        "allow_structure_access_function",
        object_index=59,
        class_key="function_class",
        name_index=57,
        outer_key="primal_structure_class",
    )
    add_uobject(
        "allow_structure_access_for_pc_property",
        object_index=60,
        class_key="object_property_class",
        name_index=41,
        outer_key="allow_structure_access_function",
    )
    add_uobject(
        "allow_structure_access_return_property",
        object_index=61,
        class_key="bool_property_class",
        name_index=29,
        outer_key="allow_structure_access_function",
    )
    add_uobject(
        "is_allowed_to_demolish_function",
        object_index=62,
        class_key="function_class",
        name_index=58,
        outer_key="primal_structure_class",
    )
    add_uobject(
        "demolish_for_pc_property",
        object_index=63,
        class_key="object_property_class",
        name_index=41,
        outer_key="is_allowed_to_demolish_function",
    )
    add_uobject(
        "demolish_return_property",
        object_index=64,
        class_key="bool_property_class",
        name_index=29,
        outer_key="is_allowed_to_demolish_function",
    )
    add_uobject(
        "set_variant_function",
        object_index=65,
        class_key="function_class",
        name_index=59,
        outer_key="primal_structure_class",
    )
    add_uobject(
        "variant_index_property",
        object_index=66,
        class_key="property_class",
        name_index=60,
        outer_key="set_variant_function",
    )
    add_uobject(
        "force_set_property",
        object_index=67,
        class_key="bool_property_class",
        name_index=61,
        outer_key="set_variant_function",
    )
    add_uobject(
        "set_variant_return_property",
        object_index=68,
        class_key="bool_property_class",
        name_index=29,
        outer_key="set_variant_function",
    )
    add_uobject(
        "primal_structure_item_container_class",
        object_index=69,
        class_key="class_class",
        name_index=62,
        outer_key="package_object",
    )
    add_uobject(
        "verify_pin_code_function",
        object_index=70,
        class_key="function_class",
        name_index=63,
        outer_key="primal_structure_item_container_class",
    )
    add_uobject(
        "pin_code_property",
        object_index=71,
        class_key="property_class",
        name_index=64,
        outer_key="verify_pin_code_function",
    )
    add_uobject(
        "verify_pin_return_property",
        object_index=72,
        class_key="bool_property_class",
        name_index=29,
        outer_key="verify_pin_code_function",
    )
    add_uobject(
        "primal_structure_seating_class",
        object_index=73,
        class_key="class_class",
        name_index=65,
        outer_key="package_object",
    )
    add_uobject(
        "can_seat_function",
        object_index=74,
        class_key="function_class",
        name_index=66,
        outer_key="primal_structure_seating_class",
    )
    add_uobject(
        "can_seat_for_pc_property",
        object_index=75,
        class_key="object_property_class",
        name_index=41,
        outer_key="can_seat_function",
    )
    add_uobject(
        "for_character_property",
        object_index=76,
        class_key="object_property_class",
        name_index=67,
        outer_key="can_seat_function",
    )
    add_uobject(
        "can_seat_force_property",
        object_index=77,
        class_key="bool_property_class",
        name_index=68,
        outer_key="can_seat_function",
    )
    add_uobject(
        "can_seat_return_property",
        object_index=78,
        class_key="bool_property_class",
        name_index=29,
        outer_key="can_seat_function",
    )
    add_uobject(
        "add_passenger_function",
        object_index=79,
        class_key="function_class",
        name_index=69,
        outer_key="primal_dino_character_class",
    )
    add_uobject(
        "add_passenger_character_property",
        object_index=80,
        class_key="object_property_class",
        name_index=70,
        outer_key="add_passenger_function",
    )
    add_uobject(
        "passenger_seat_index_property",
        object_index=81,
        class_key="property_class",
        name_index=71,
        outer_key="add_passenger_function",
    )
    add_uobject(
        "force_passenger_property",
        object_index=82,
        class_key="bool_property_class",
        name_index=72,
        outer_key="add_passenger_function",
    )
    add_uobject(
        "allow_flyers_water_property",
        object_index=83,
        class_key="bool_property_class",
        name_index=73,
        outer_key="add_passenger_function",
    )
    add_uobject(
        "skip_line_trace_property",
        object_index=84,
        class_key="bool_property_class",
        name_index=74,
        outer_key="add_passenger_function",
    )
    add_uobject(
        "add_passenger_return_property",
        object_index=85,
        class_key="bool_property_class",
        name_index=29,
        outer_key="add_passenger_function",
    )
    add_uobject(
        "allow_carry_character_function",
        object_index=86,
        class_key="function_class",
        name_index=75,
        outer_key="primal_dino_character_class",
    )
    add_uobject(
        "can_carry_pawn_property",
        object_index=87,
        class_key="object_property_class",
        name_index=76,
        outer_key="allow_carry_character_function",
    )
    add_uobject(
        "allow_carry_return_property",
        object_index=88,
        class_key="bool_property_class",
        name_index=29,
        outer_key="allow_carry_character_function",
    )
    add_uobject(
        "bp_allow_carry_character_function",
        object_index=89,
        class_key="function_class",
        name_index=77,
        outer_key="primal_dino_character_class",
    )
    add_uobject(
        "check_character_property",
        object_index=90,
        class_key="object_property_class",
        name_index=78,
        outer_key="bp_allow_carry_character_function",
    )
    add_uobject(
        "bp_allow_carry_return_property",
        object_index=91,
        class_key="bool_property_class",
        name_index=29,
        outer_key="bp_allow_carry_character_function",
    )
    add_uobject(
        "set_character_status_tameable_function",
        object_index=92,
        class_key="function_class",
        name_index=79,
        outer_key="primal_dino_character_class",
    )
    add_uobject(
        "set_tameable_property",
        object_index=93,
        class_key="bool_property_class",
        name_index=80,
        outer_key="set_character_status_tameable_function",
    )
    add_uobject(
        "create_inventory_property",
        object_index=94,
        class_key="bool_property_class",
        name_index=81,
        outer_key="set_character_status_tameable_function",
    )
    add_uobject(
        "inventory_for_waking_tame_property",
        object_index=95,
        class_key="bool_property_class",
        name_index=82,
        outer_key="set_character_status_tameable_function",
    )
    add_uobject(
        "server_request_dino_char_stats_function",
        object_index=96,
        class_key="function_class",
        name_index=83,
        outer_key="shooter_player_controller_class",
    )
    add_uobject(
        "the_dino_char_property",
        object_index=97,
        class_key="object_property_class",
        name_index=84,
        outer_key="server_request_dino_char_stats_function",
    )
    add_uobject(
        "server_request_tribe_log_function",
        object_index=98,
        class_key="function_class",
        name_index=85,
        outer_key="shooter_player_controller_class",
    )
    add_uobject("script_struct_class", object_index=100, class_key="class_class", name_index=87, outer_key=None)
    add_uobject(
        "tribute_dino_struct",
        object_index=101,
        class_key="script_struct_class",
        name_index=88,
        outer_key="package_object",
    )
    add_uobject(
        "tribute_dino_class_name_property",
        object_index=102,
        class_key="str_property_class",
        name_index=89,
        outer_key="tribute_dino_struct",
    )
    add_uobject(
        "tribute_dino_id1_property",
        object_index=103,
        class_key="property_class",
        name_index=90,
        outer_key="tribute_dino_struct",
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

    def add_function_chain(
        function_key: str,
        *,
        first_property_key: str,
        parms_size: int,
        properties: list[tuple[str, int, int]],
    ) -> None:
        put_function_data(
            addrs[function_key],
            first_property=addrs[first_property_key],
            num_parms=len(properties),
            parms_size=parms_size,
        )
        for index, (property_key, offset, element_size) in enumerate(properties):
            next_field = addrs[properties[index + 1][0]] if index + 1 < len(properties) else 0
            put_property_data(addrs[property_key], offset=offset, element_size=element_size, next_field=next_field)

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
    put_ptr(addrs["item_id_property"] + 0x70, addrs["chat_message_outer"])

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

    add_function_chain(
        "server_request_attack_function",
        first_property_key="attack_index_property",
        parms_size=4,
        properties=[("attack_index_property", 0, 4)],
    )
    add_function_chain(
        "bp_notify_add_passenger_function",
        first_property_key="passenger_char_property",
        parms_size=12,
        properties=[("passenger_char_property", 0, 8), ("seat_index_property", 8, 4)],
    )
    add_function_chain(
        "server_activate_function",
        first_property_key="for_pc_property",
        parms_size=10,
        properties=[
            ("for_pc_property", 0, 8),
            ("force_direction_property", 8, 1),
            ("dir_property", 9, 1),
        ],
    )
    add_function_chain(
        "add_player_to_mission_function",
        first_property_key="mission_player_character_property",
        parms_size=10,
        properties=[
            ("mission_player_character_property", 0, 8),
            ("mission_force_add_property", 8, 1),
            ("mission_return_value_property", 9, 1),
        ],
    )
    add_function_chain(
        "bp_allow_player_leave_function",
        first_property_key="leave_player_character_property",
        parms_size=9,
        properties=[("leave_player_character_property", 0, 8), ("leave_return_value_property", 8, 1)],
    )
    add_function_chain(
        "bp_on_player_added_function",
        first_property_key="added_player_character_property",
        parms_size=16,
        properties=[
            ("added_player_character_property", 0, 8),
            ("added_player_controller_property", 8, 8),
        ],
    )
    add_function_chain(
        "deferred_mission_string_array_function",
        first_property_key="mission_name_property",
        parms_size=16,
        properties=[("mission_name_property", 0, 16), ("mission_tags_property", 16, 16)],
    )
    put_ptr(addrs["mission_tags_property"] + 0x70, addrs["mission_tags_inner_property"])
    add_function_chain(
        "allow_structure_access_function",
        first_property_key="allow_structure_access_for_pc_property",
        parms_size=9,
        properties=[
            ("allow_structure_access_for_pc_property", 0, 8),
            ("allow_structure_access_return_property", 8, 1),
        ],
    )
    add_function_chain(
        "is_allowed_to_demolish_function",
        first_property_key="demolish_for_pc_property",
        parms_size=9,
        properties=[("demolish_for_pc_property", 0, 8), ("demolish_return_property", 8, 1)],
    )
    add_function_chain(
        "set_variant_function",
        first_property_key="variant_index_property",
        parms_size=6,
        properties=[
            ("variant_index_property", 0, 4),
            ("force_set_property", 4, 1),
            ("set_variant_return_property", 5, 1),
        ],
    )
    add_function_chain(
        "verify_pin_code_function",
        first_property_key="pin_code_property",
        parms_size=5,
        properties=[("pin_code_property", 0, 4), ("verify_pin_return_property", 4, 1)],
    )
    add_function_chain(
        "can_seat_function",
        first_property_key="can_seat_for_pc_property",
        parms_size=18,
        properties=[
            ("can_seat_for_pc_property", 0, 8),
            ("for_character_property", 8, 8),
            ("can_seat_force_property", 0x10, 1),
            ("can_seat_return_property", 0x11, 1),
        ],
    )
    add_function_chain(
        "add_passenger_function",
        first_property_key="add_passenger_character_property",
        parms_size=16,
        properties=[
            ("add_passenger_character_property", 0, 8),
            ("passenger_seat_index_property", 8, 4),
            ("force_passenger_property", 0xC, 1),
            ("allow_flyers_water_property", 0xD, 1),
            ("skip_line_trace_property", 0xE, 1),
            ("add_passenger_return_property", 0xF, 1),
        ],
    )
    add_function_chain(
        "allow_carry_character_function",
        first_property_key="can_carry_pawn_property",
        parms_size=9,
        properties=[("can_carry_pawn_property", 0, 8), ("allow_carry_return_property", 8, 1)],
    )
    add_function_chain(
        "bp_allow_carry_character_function",
        first_property_key="check_character_property",
        parms_size=9,
        properties=[("check_character_property", 0, 8), ("bp_allow_carry_return_property", 8, 1)],
    )
    add_function_chain(
        "set_character_status_tameable_function",
        first_property_key="set_tameable_property",
        parms_size=3,
        properties=[
            ("set_tameable_property", 0, 1),
            ("create_inventory_property", 1, 1),
            ("inventory_for_waking_tame_property", 2, 1),
        ],
    )
    add_function_chain(
        "server_request_dino_char_stats_function",
        first_property_key="the_dino_char_property",
        parms_size=8,
        properties=[("the_dino_char_property", 0, 8)],
    )
    put_function_data(addrs["server_request_tribe_log_function"], first_property=0, num_parms=0, parms_size=0)
    put_ptr(addrs["tribute_dino_struct"] + 0x38, addrs["tribute_dino_class_name_property"])
    put_i32(addrs["tribute_dino_struct"] + 0x40, 288)
    put_i32(addrs["tribute_dino_struct"] + 0x44, 0x8)
    put_property_data(
        addrs["tribute_dino_class_name_property"],
        offset=0,
        element_size=16,
        next_field=addrs["tribute_dino_id1_property"],
    )
    put_property_data(addrs["tribute_dino_id1_property"], offset=0x20, element_size=4)

    write_minimal_elf64_core(path, base, bytes(segment))
    return addrs


class InspectCoreUFunctionsTests(unittest.TestCase):
    def assert_property_sequence(self, chain: dict[str, object], expected: list[tuple[str, str, int, int]]) -> None:
        properties = chain["properties"]
        self.assertEqual(
            [
                (prop["summary"]["name"], prop["summary"]["class_name"], prop["offset_internal"], prop["element_size"])
                for prop in properties
            ],
            expected,
        )

    def inspect_single_by_name_outer(self, name: str, outer: str) -> dict[str, object]:
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
                    name_contains=[],
                    outer_contains=[],
                    name_exact=[name],
                    outer_exact=[outer],
                    window_size=0xC0,
                    max_object_scan=128,
                )
            finally:
                memory.close()

        self.assertEqual(len(payload["targets"]), 1)
        return payload["targets"][0]

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
        self.assertIn("class_name_not_function_or_script_struct", target["reject_reasons"])
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
        self.assert_property_sequence(
            chain,
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
        self.assert_property_sequence(
            chain,
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

    def test_primal_dino_server_request_attack_int_property_chain(self) -> None:
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
                    name_contains=["ServerRequestAttack"],
                    outer_contains=["PrimalDinoCharacter"],
                    window_size=0xC0,
                    max_object_scan=48,
                )
            finally:
                memory.close()

        chain = payload["targets"][0]["property_chain"]
        self.assertEqual(chain["status"], "candidate")
        self.assert_property_sequence(chain, [("AttackIndex", "IntProperty", 0, 4)])

    def test_primal_dino_notify_add_passenger_object_int_property_chain(self) -> None:
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
                    name_contains=["BPNotifyAddPassenger"],
                    outer_contains=["PrimalDinoCharacter"],
                    window_size=0xC0,
                    max_object_scan=48,
                )
            finally:
                memory.close()

        chain = payload["targets"][0]["property_chain"]
        self.assertEqual(chain["status"], "candidate")
        self.assert_property_sequence(
            chain,
            [
                ("PassengerChar", "ObjectProperty", 0, 8),
                ("SeatIndex", "IntProperty", 8, 4),
            ],
        )

    def test_primal_dino_add_passenger_policy_property_chain(self) -> None:
        target = self.inspect_single_by_name_outer("AddPassenger", "PrimalDinoCharacter")
        chain = target["property_chain"]

        self.assertEqual(chain["status"], "candidate")
        self.assert_property_sequence(
            chain,
            [
                ("ACharacter", "ObjectProperty", 0, 8),
                ("PassengerSeatIndex", "IntProperty", 8, 4),
                ("bForcePassenger", "BoolProperty", 0xC, 1),
                ("bAllowFlyersAndWaterDinos", "BoolProperty", 0xD, 1),
                ("bSkipLineTrace", "BoolProperty", 0xE, 1),
                ("ReturnValue", "BoolProperty", 0xF, 1),
            ],
        )

    def test_primal_dino_allow_carry_property_chain(self) -> None:
        target = self.inspect_single_by_name_outer("AllowCarryCharacter", "PrimalDinoCharacter")
        chain = target["property_chain"]

        self.assertEqual(chain["status"], "candidate")
        self.assert_property_sequence(
            chain,
            [
                ("CanCarryPawn", "ObjectProperty", 0, 8),
                ("ReturnValue", "BoolProperty", 8, 1),
            ],
        )

    def test_primal_dino_bp_allow_carry_property_chain(self) -> None:
        target = self.inspect_single_by_name_outer("BPAllowCarryCharacter", "PrimalDinoCharacter")
        chain = target["property_chain"]

        self.assertEqual(chain["status"], "candidate")
        self.assert_property_sequence(
            chain,
            [
                ("checkCharacter", "ObjectProperty", 0, 8),
                ("ReturnValue", "BoolProperty", 8, 1),
            ],
        )

    def test_primal_dino_set_tameable_bool_property_chain(self) -> None:
        target = self.inspect_single_by_name_outer("SetCharacterStatusTameable", "PrimalDinoCharacter")
        chain = target["property_chain"]

        self.assertEqual(chain["status"], "candidate")
        self.assert_property_sequence(
            chain,
            [
                ("bSetTameable", "BoolProperty", 0, 1),
                ("bCreateInventory", "BoolProperty", 1, 1),
                ("bInventoryForWakingTame", "BoolProperty", 2, 1),
            ],
        )

    def test_player_controller_request_dino_stats_property_chain(self) -> None:
        target = self.inspect_single_by_name_outer("ServerRequestDinoCharStats", "ShooterPlayerController")
        chain = target["property_chain"]

        self.assertEqual(chain["status"], "candidate")
        self.assert_property_sequence(chain, [("theDinoChar", "ObjectProperty", 0, 8)])

    def test_player_controller_tribe_log_zero_param_chain(self) -> None:
        target = self.inspect_single_by_name_outer("ServerRequestTribeLog", "ShooterPlayerController")
        chain = target["property_chain"]

        self.assertEqual(target["num_parms"], 0)
        self.assertEqual(target["parms_size"], 0)
        self.assertEqual(chain["status"], "candidate")
        self.assertEqual(chain["expected_count"], 0)
        self.assertEqual(chain["observed_count"], 0)
        self.assertEqual(chain["properties"], [])

    def test_primal_structure_elevator_server_activate_byte_property_chain(self) -> None:
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
                    name_contains=["ServerActivate"],
                    outer_contains=["PrimalStructureElevatorPlatform"],
                    window_size=0xC0,
                    max_object_scan=48,
                )
            finally:
                memory.close()

        chain = payload["targets"][0]["property_chain"]
        self.assertEqual(chain["status"], "candidate")
        self.assert_property_sequence(
            chain,
            [
                ("ForPC", "ObjectProperty", 0, 8),
                ("bForceDirection", "BoolProperty", 8, 1),
                ("Dir", "ByteProperty", 9, 1),
            ],
        )

    def test_primal_structure_access_bool_return_property_chain(self) -> None:
        target = self.inspect_single_by_name_outer("AllowStructureAccess", "PrimalStructure")
        chain = target["property_chain"]

        self.assertEqual(chain["status"], "candidate")
        self.assert_property_sequence(
            chain,
            [
                ("ForPC", "ObjectProperty", 0, 8),
                ("ReturnValue", "BoolProperty", 8, 1),
            ],
        )

    def test_primal_structure_demolish_bool_return_property_chain(self) -> None:
        target = self.inspect_single_by_name_outer("IsAllowedToDemolish", "PrimalStructure")
        chain = target["property_chain"]

        self.assertEqual(chain["status"], "candidate")
        self.assert_property_sequence(
            chain,
            [
                ("ForPC", "ObjectProperty", 0, 8),
                ("ReturnValue", "BoolProperty", 8, 1),
            ],
        )

    def test_primal_structure_variant_int_bool_return_property_chain(self) -> None:
        target = self.inspect_single_by_name_outer("SetVariant", "PrimalStructure")
        chain = target["property_chain"]

        self.assertEqual(chain["status"], "candidate")
        self.assert_property_sequence(
            chain,
            [
                ("VariantIndex", "IntProperty", 0, 4),
                ("bForceSet", "BoolProperty", 4, 1),
                ("ReturnValue", "BoolProperty", 5, 1),
            ],
        )

    def test_primal_structure_item_container_pin_code_property_chain(self) -> None:
        target = self.inspect_single_by_name_outer("VerifyPinCode", "PrimalStructureItemContainer")
        chain = target["property_chain"]

        self.assertEqual(chain["status"], "candidate")
        self.assert_property_sequence(
            chain,
            [
                ("pinCode", "IntProperty", 0, 4),
                ("ReturnValue", "BoolProperty", 4, 1),
            ],
        )

    def test_primal_structure_seating_can_seat_property_chain(self) -> None:
        target = self.inspect_single_by_name_outer("CanSeat", "PrimalStructureSeating")
        chain = target["property_chain"]

        self.assertEqual(chain["status"], "candidate")
        self.assert_property_sequence(
            chain,
            [
                ("ForPC", "ObjectProperty", 0, 8),
                ("forCharacter", "ObjectProperty", 8, 8),
                ("bForce", "BoolProperty", 0x10, 1),
                ("ReturnValue", "BoolProperty", 0x11, 1),
            ],
        )

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

    def test_mission_add_player_to_mission_property_chain(self) -> None:
        target = self.inspect_single_by_name_outer("AddPlayerToMission", "MissionType")
        chain = target["property_chain"]

        self.assertEqual(chain["status"], "candidate")
        self.assert_property_sequence(
            chain,
            [
                ("PlayerCharacter", "ObjectProperty", 0, 8),
                ("bForceAdd", "BoolProperty", 8, 1),
                ("ReturnValue", "BoolProperty", 9, 1),
            ],
        )

    def test_mission_allow_player_to_leave_property_chain(self) -> None:
        target = self.inspect_single_by_name_outer("BPAllowPlayerToLeaveMission", "MissionType")
        chain = target["property_chain"]

        self.assertEqual(chain["status"], "candidate")
        self.assert_property_sequence(
            chain,
            [
                ("PlayerCharacter", "ObjectProperty", 0, 8),
                ("ReturnValue", "BoolProperty", 8, 1),
            ],
        )

    def test_mission_player_added_object_pair_property_chain(self) -> None:
        target = self.inspect_single_by_name_outer("BPOnPlayerAddedToMission", "MissionType")
        chain = target["property_chain"]

        self.assertEqual(chain["status"], "candidate")
        self.assert_property_sequence(
            chain,
            [
                ("PlayerCharacter", "ObjectProperty", 0, 8),
                ("PlayerController", "ObjectProperty", 8, 8),
            ],
        )

    def test_rejects_deferred_mission_string_array_chain(self) -> None:
        target = self.inspect_single_by_name_outer("DeferredMissionStringArray", "MissionType")
        chain = target["property_chain"]

        self.assertEqual(chain["status"], "rejected")
        self.assertIn("property_1_rejected", chain["reject_reasons"])
        self.assert_property_sequence(
            chain,
            [
                ("MissionName", "StrProperty", 0, 16),
                ("MissionTags", "ArrayProperty", 16, 16),
            ],
        )
        self.assertIn("property_exceeds_parms_size", chain["properties"][1]["reject_reasons"])

    def test_array_property_reports_inner_candidate(self) -> None:
        target = self.inspect_single_by_name_outer("DeferredMissionStringArray", "MissionType")
        array_prop = target["property_chain"]["properties"][1]

        self.assertEqual(array_prop["summary"]["class_name"], "ArrayProperty")
        inner = array_prop["array_inner_candidate"]
        self.assertEqual(inner["status"], "candidate")
        self.assertEqual(inner["membership_status"], "candidate-uobject")
        self.assertEqual(inner["reject_reasons"], [])
        self.assertEqual(
            inner["inner_property"],
            {"name": "MissionTag", "name_index": 86, "class_name": "StrProperty"},
        )

    def test_fixture_snapshot_preserves_array_inner_candidate(self) -> None:
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
                    name_contains=["DeferredMissionStringArray"],
                    outer_contains=["MissionType"],
                    window_size=0xC0,
                    max_object_scan=128,
                )
            finally:
                memory.close()

        snapshot = inspector.build_fixture_snapshot(payload)
        array_prop = snapshot["targets"][0]["property_chain"]["properties"][1]
        self.assertEqual(
            array_prop["array_inner_candidate"],
            {
                "status": "candidate",
                "reject_reasons": [],
                "membership_status": "candidate-uobject",
                "inner_property": {"name": "MissionTag", "name_index": 86, "class_name": "StrProperty"},
            },
        )
        serialized = json.dumps(snapshot, sort_keys=True)
        self.assertNotIn(hex(addrs["mission_tags_inner_property"]), serialized)
        self.assertNotIn(str(core), serialized)

    def test_struct_property_reports_type_candidate(self) -> None:
        target = self.inspect_single_by_name_outer("ServerRequestInventoryUseItem", "ShooterPlayerController")
        struct_prop = target["property_chain"]["properties"][1]

        self.assertEqual(struct_prop["summary"]["class_name"], "StructProperty")
        struct_type = struct_prop["struct_type_candidate"]
        self.assertEqual(struct_type["status"], "candidate")
        self.assertEqual(struct_type["membership_status"], "candidate-uobject")
        self.assertEqual(struct_type["reject_reasons"], [])
        self.assertEqual(
            struct_type["struct_type"],
            {"name": "ChatMessage", "name_index": 7, "class_name": "Class"},
        )

    def test_fixture_snapshot_preserves_struct_type_candidate(self) -> None:
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
                    max_object_scan=128,
                )
            finally:
                memory.close()

        snapshot = inspector.build_fixture_snapshot(payload)
        struct_prop = snapshot["targets"][0]["property_chain"]["properties"][1]
        self.assertEqual(
            struct_prop["struct_type_candidate"],
            {
                "status": "candidate",
                "reject_reasons": [],
                "membership_status": "candidate-uobject",
                "struct_type": {"name": "ChatMessage", "name_index": 7, "class_name": "Class"},
            },
        )
        serialized = json.dumps(snapshot, sort_keys=True)
        self.assertNotIn(hex(addrs["chat_message_outer"]), serialized)
        self.assertNotIn(str(core), serialized)

    def test_script_struct_target_uses_ustruct_properties_size(self) -> None:
        target = self.inspect_single_by_name_outer("ARKTributeDino", "/Script/ShooterGame")
        chain = target["property_chain"]

        self.assertEqual(target["object_summary"]["class_name"], "ScriptStruct")
        self.assertEqual(target["inspection_mode"], "script_struct")
        self.assertIsNone(target["num_parms"])
        self.assertEqual(target["parms_size"], 288)
        self.assertEqual(chain["status"], "candidate")
        self.assertIsNone(chain["expected_count"])
        self.assertEqual(chain["parms_size"], 288)
        self.assert_property_sequence(
            chain,
            [
                ("DinoClassName", "StrProperty", 0, 16),
                ("DinoID1", "IntProperty", 0x20, 4),
            ],
        )

    def test_script_struct_snapshot_uses_separate_schema(self) -> None:
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
                    name_contains=[],
                    outer_contains=[],
                    name_exact=["ARKTributeDino"],
                    outer_exact=["/Script/ShooterGame"],
                    window_size=0xC0,
                    max_object_scan=128,
                )
            finally:
                memory.close()

        snapshot = inspector.build_fixture_snapshot(payload)
        self.assertEqual(snapshot["schema"], "obelisk.scriptstruct-chain.snapshot.v1")
        target = snapshot["targets"][0]
        self.assertEqual(target["inspection_mode"], "script_struct")
        self.assertEqual(target["target"]["class_name"], "ScriptStruct")
        self.assertEqual(target["properties_size"], 288)
        self.assertNotIn("num_parms", target)
        self.assertNotIn("function_flags", target)
        self.assertEqual(target["property_chain"]["expected_count"], None)
        self.assertEqual(target["property_chain"]["properties_size"], 288)
        serialized = json.dumps(snapshot, sort_keys=True)
        self.assertNotIn(hex(addrs["tribute_dino_struct"]), serialized)
        self.assertNotIn(str(core), serialized)

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

    def test_fixture_snapshot_omits_addresses_and_keeps_property_shape(self) -> None:
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
                    name_contains=["ServerActivate"],
                    outer_contains=["PrimalStructureElevatorPlatform"],
                    window_size=0xC0,
                    max_object_scan=64,
                )
            finally:
                memory.close()

        evidence = {
            "ark_binary_sha256": "fixture-sha",
            "obelisk_commit": "fixture-commit",
            "source": "synthetic_core",
            "status": "candidate-only",
            "generated_by": "unit-test",
        }
        snapshot = inspector.build_fixture_snapshot(payload, evidence=evidence)
        self.assertEqual(snapshot["schema"], "obelisk.ufunction-chain.snapshot.v1")
        self.assertEqual(snapshot["evidence"], evidence)
        target = snapshot["targets"][0]
        self.assertEqual(target["target"]["name"], "ServerActivate")
        self.assertEqual(target["target"]["outer_name"], "PrimalStructureElevatorPlatform")
        self.assertEqual(
            target["membership"],
            {"target": "candidate-uobject", "class": "candidate-uobject", "outer": "candidate-uobject"},
        )
        self.assertEqual(target["function_flags"], "0x204000")
        self.assertEqual(target["return_value_offset"], "0xffff")
        self.assertEqual(
            [
                (prop["depth"], prop["name"], prop["class_name"], prop["offset_internal"], prop["element_size"])
                for prop in target["property_chain"]["properties"]
            ],
            [
                (0, "ForPC", "ObjectProperty", 0, 8),
                (1, "bForceDirection", "BoolProperty", 8, 1),
                (2, "Dir", "ByteProperty", 9, 1),
            ],
        )
        serialized = json.dumps(snapshot, sort_keys=True)
        self.assertNotIn(hex(addrs["server_activate_function"]), serialized)
        self.assertNotIn(str(core), serialized)
        self.assertNotIn("pointer_window", serialized)

    def test_fixture_snapshot_preserves_rejected_chain_reasons(self) -> None:
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
                    name_contains=["DeferredMissionStringArray"],
                    outer_contains=["MissionType"],
                    window_size=0xC0,
                    max_object_scan=64,
                )
            finally:
                memory.close()

        target = inspector.build_fixture_snapshot(payload)["targets"][0]
        chain = target["property_chain"]
        self.assertEqual(chain["status"], "rejected")
        self.assertIn("property_1_rejected", chain["reject_reasons"])
        self.assertIn("property_exceeds_parms_size", chain["properties"][1]["reject_reasons"])
        serialized = json.dumps(target, sort_keys=True)
        self.assertNotIn(hex(addrs["deferred_mission_string_array_function"]), serialized)

    def test_cli_snapshot_json_output_omits_core_path(self) -> None:
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
                    "BPAllowPlayerToLeaveMission",
                    "--outer-contains",
                    "MissionType",
                    "--snapshot-json",
                    "--evidence-ark-sha256",
                    "fixture-sha",
                    "--evidence-obelisk-commit",
                    "fixture-commit",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["evidence"]["ark_binary_sha256"], "fixture-sha")
        self.assertEqual(payload["evidence"]["obelisk_commit"], "fixture-commit")
        self.assertEqual(payload["evidence"]["source"], "offline_core")
        self.assertEqual(payload["evidence"]["status"], "candidate-only")
        self.assertEqual(payload["targets"][0]["target"]["name"], "BPAllowPlayerToLeaveMission")
        self.assertNotIn(str(core), result.stdout)
        self.assertNotIn(hex(addrs["bp_allow_player_leave_function"]), result.stdout)
        self.assertNotIn(hex(addrs["leave_player_character_property"]), result.stdout)
        self.assertNotIn(hex(addrs["gobjects"]), result.stdout)
        self.assertNotIn(hex(addrs["fname_table"]), result.stdout)

    def test_cli_script_struct_mode_emits_script_struct_snapshot(self) -> None:
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
                    "--inspection-mode",
                    "script-struct",
                    "--name-exact",
                    "ARKTributeDino",
                    "--snapshot-json",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema"], "obelisk.scriptstruct-chain.snapshot.v1")
        self.assertEqual(payload["targets"][0]["inspection_mode"], "script_struct")

    def test_cli_script_struct_mode_rejects_function_target(self) -> None:
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
                    "--inspection-mode",
                    "script-struct",
                    "--name-exact",
                    "ServerChat",
                    "--json",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["targets"][0]["status"], "rejected")
        self.assertIn("class_name_not_script_struct", payload["targets"][0]["reject_reasons"])

    def test_cli_snapshot_json_rejects_mixed_inspection_modes(self) -> None:
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
                    "--name-exact",
                    "ServerChat",
                    "--name-exact",
                    "ARKTributeDino",
                    "--snapshot-json",
                ],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("single inspection_mode", result.stderr)

    def test_cli_rejects_full_and_snapshot_json_together(self) -> None:
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
                    "--snapshot-json",
                ],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("choose only one", result.stderr)

    def test_cli_rejects_evidence_metadata_without_snapshot_json(self) -> None:
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
                    "--evidence-ark-sha256",
                    "fixture-sha",
                ],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("evidence metadata flags require --snapshot-json", result.stderr)

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

    def test_cli_exact_filters_find_single_matching_function(self) -> None:
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
                    "--name-exact",
                    "AllowStructureAccess",
                    "--outer-exact",
                    "PrimalStructure",
                    "--json",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(len(payload["targets"]), 1)
        self.assertEqual(payload["targets"][0]["object_summary"]["name"], "AllowStructureAccess")
        self.assertEqual(payload["targets"][0]["outer_summary"]["name"], "PrimalStructure")

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
