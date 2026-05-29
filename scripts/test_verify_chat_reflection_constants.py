#!/usr/bin/env python3
"""Offline tests for verify_chat_reflection_constants.py."""

from __future__ import annotations

import json
import hashlib
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import enumerate_core_uobjects as enum
import scan_core_fname_tables as scanner
import snapshot_evidence_pack
import verify_chat_reflection_constants as verifier


CHAT_REFLECTION_CPP = """
namespace Obelisk::UE::ChatReflection {
namespace {
constexpr int32_t kServerChatNameIndex = 9619;
constexpr int32_t kServerChatToNameIndex = 9620;
constexpr int32_t kServerChatToPlayerNameIndex = 9621;
constexpr int32_t kServerSendChatMessageNameIndex = 2697;
constexpr int32_t kClientChatMessageNameIndex = 1865;
constexpr int32_t kClientServerChatDirectMessageNameIndex = 1983;
constexpr int32_t kClientServerChatMessageNameIndex = 1984;
constexpr int32_t kSendServerChatMessageNameIndex = 9801;
constexpr int32_t kOnServerChatMessageDelegateNameIndex = 28549;
constexpr int32_t kShooterGameModeNameIndex = 9755;
constexpr int32_t kChatMessageNameIndex = 588;
constexpr int32_t kMessageTextNameIndex = 21409;
constexpr int32_t kMessageColorNameIndex = 21408;
constexpr int32_t kBIsBoldNameIndex = 21407;
constexpr int32_t kReceiverPlayerIDNameIndex = 28550;
constexpr int32_t kReceiverTeamIdNameIndex = 28551;
constexpr int32_t kSendModeNameIndex = 16753;
constexpr int32_t kSteamIDNameIndex = 20681;
constexpr int32_t kPlayerNameNameIndex = 16693;
constexpr int32_t kBytePropertyClassNameIndex = 1;
constexpr int32_t kBytePropertyClassObjectIndex = 533;
constexpr int32_t kBoolPropertyClassNameIndex = 3;
constexpr int32_t kIntPropertyClassNameIndex = 2;
constexpr int32_t kIntPropertyClassObjectIndex = 539;
constexpr int32_t kStructPropertyClassNameIndex = 10;
constexpr int32_t kStrPropertyClassNameIndex = 13;
constexpr int32_t kStrPropertyClassObjectIndex = 547;
constexpr size_t kFStringHeaderSize = 0x10;
constexpr size_t kBytePropertySize = 0x1;
constexpr size_t kBoolPropertySize = 0x1;
constexpr size_t kIntPropertySize = 0x4;
constexpr size_t kStructPropertySize = 0x10;
constexpr size_t kChatStructPropertySize = 0x90;
constexpr int32_t kAnyNameIndex = -1;
constexpr int32_t kAnyObjectIndex = -1;
constexpr int32_t kAnyOuterNameIndex = -1;
constexpr std::array<ChatFieldSpec, 1> kServerChatFields{{
    {ChatField::MessageText, kMessageTextNameIndex, 0x00, kFStringHeaderSize,
     kStrPropertyClassNameIndex, kStrPropertyClassObjectIndex},
}};
constexpr std::array<ChatFieldSpec, 2> kServerChatToFields{{
    {ChatField::SteamID, kSteamIDNameIndex, 0x00, kFStringHeaderSize,
     kStrPropertyClassNameIndex, kStrPropertyClassObjectIndex},
    {ChatField::MessageText, kMessageTextNameIndex, 0x10, kFStringHeaderSize,
     kStrPropertyClassNameIndex, kStrPropertyClassObjectIndex},
}};
constexpr std::array<ChatFieldSpec, 2> kServerChatToPlayerFields{{
    {ChatField::PlayerName, kPlayerNameNameIndex, 0x00, kFStringHeaderSize,
     kStrPropertyClassNameIndex, kStrPropertyClassObjectIndex},
    {ChatField::MessageText, kMessageTextNameIndex, 0x10, kFStringHeaderSize,
     kStrPropertyClassNameIndex, kStrPropertyClassObjectIndex},
}};
constexpr std::array<ChatFieldSpec, 2> kServerSendChatMessageFields{{
    {ChatField::ChatMessage, kChatMessageNameIndex, 0x00, kFStringHeaderSize,
     kStrPropertyClassNameIndex, kStrPropertyClassObjectIndex},
    {ChatField::SendMode, kSendModeNameIndex, 0x10, kBytePropertySize,
     kBytePropertyClassNameIndex, kBytePropertyClassObjectIndex},
}};
constexpr std::array<ChatFieldSpec, 1> kClientChatMessageFields{{
    {ChatField::Chat, kAnyNameIndex, 0x00, kChatStructPropertySize,
     kStructPropertyClassNameIndex, kAnyObjectIndex},
}};
constexpr std::array<ChatFieldSpec, 3> kClientServerChatMessageFields{{
    {ChatField::MessageText, kMessageTextNameIndex, 0x00, kFStringHeaderSize,
     kStrPropertyClassNameIndex, kStrPropertyClassObjectIndex},
    {ChatField::MessageColor, kAnyNameIndex, 0x10, kStructPropertySize,
     kStructPropertyClassNameIndex, kAnyObjectIndex},
    {ChatField::BIsBold, kAnyNameIndex, 0x20, kBoolPropertySize,
     kBoolPropertyClassNameIndex, kAnyObjectIndex},
}};
constexpr std::array<ChatFieldSpec, 5> kSendServerChatMessageFields{{
    {ChatField::MessageText, kMessageTextNameIndex, 0x00, kFStringHeaderSize,
     kStrPropertyClassNameIndex, kStrPropertyClassObjectIndex},
    {ChatField::MessageColor, kMessageColorNameIndex, 0x10, kStructPropertySize,
     kStructPropertyClassNameIndex, kAnyObjectIndex},
    {ChatField::BIsBold, kBIsBoldNameIndex, 0x20, kBoolPropertySize,
     kBoolPropertyClassNameIndex, kAnyObjectIndex},
    {ChatField::ReceiverTeamId, kReceiverTeamIdNameIndex, 0x24, kIntPropertySize,
     kIntPropertyClassNameIndex, kIntPropertyClassObjectIndex},
    {ChatField::ReceiverPlayerID, kReceiverPlayerIDNameIndex, 0x28, kIntPropertySize,
     kIntPropertyClassNameIndex, kIntPropertyClassObjectIndex},
}};
constexpr std::array<ChatFieldSpec, 3> kOnServerChatMessageDelegateFields{{
    {ChatField::MessageText, kMessageTextNameIndex, 0x00, kFStringHeaderSize,
     kStrPropertyClassNameIndex, kStrPropertyClassObjectIndex},
    {ChatField::ReceiverTeamId, kReceiverTeamIdNameIndex, 0x10, kIntPropertySize,
     kIntPropertyClassNameIndex, kIntPropertyClassObjectIndex},
    {ChatField::ReceiverPlayerID, kReceiverPlayerIDNameIndex, 0x14, kIntPropertySize,
     kIntPropertyClassNameIndex, kIntPropertyClassObjectIndex},
}};
constexpr ChatFunctionSpec kServerChatSpec{
    ChatFunction::ServerChat,
    kServerChatNameIndex,
    1,
    0x10,
    kServerChatFields.data(),
    kServerChatFields.size(),
    kAnyOuterNameIndex,
    false,
};
constexpr ChatFunctionSpec kServerChatToSpec{
    ChatFunction::ServerChatTo,
    kServerChatToNameIndex,
    2,
    0x20,
    kServerChatToFields.data(),
    kServerChatToFields.size(),
    kAnyOuterNameIndex,
    false,
};
constexpr ChatFunctionSpec kServerChatToPlayerSpec{
    ChatFunction::ServerChatToPlayer,
    kServerChatToPlayerNameIndex,
    2,
    0x20,
    kServerChatToPlayerFields.data(),
    kServerChatToPlayerFields.size(),
    kAnyOuterNameIndex,
    false,
};
constexpr ChatFunctionSpec kServerSendChatMessageSpec{
    ChatFunction::ServerSendChatMessage,
    kServerSendChatMessageNameIndex,
    2,
    0x11,
    kServerSendChatMessageFields.data(),
    kServerSendChatMessageFields.size(),
    kAnyOuterNameIndex,
    false,
};
constexpr ChatFunctionSpec kClientChatMessageSpec{
    ChatFunction::ClientChatMessage,
    kClientChatMessageNameIndex,
    1,
    0x90,
    kClientChatMessageFields.data(),
    kClientChatMessageFields.size(),
    kAnyOuterNameIndex,
    true,
};
constexpr ChatFunctionSpec kClientServerChatDirectMessageSpec{
    ChatFunction::ClientServerChatDirectMessage,
    kClientServerChatDirectMessageNameIndex,
    3,
    0x21,
    kClientServerChatMessageFields.data(),
    kClientServerChatMessageFields.size(),
    kAnyOuterNameIndex,
    true,
};
constexpr ChatFunctionSpec kClientServerChatMessageSpec{
    ChatFunction::ClientServerChatMessage,
    kClientServerChatMessageNameIndex,
    3,
    0x21,
    kClientServerChatMessageFields.data(),
    kClientServerChatMessageFields.size(),
    kAnyOuterNameIndex,
    true,
};
constexpr ChatFunctionSpec kSendServerChatMessageSpec{
    ChatFunction::SendServerChatMessage,
    kSendServerChatMessageNameIndex,
    5,
    0x2c,
    kSendServerChatMessageFields.data(),
    kSendServerChatMessageFields.size(),
    kShooterGameModeNameIndex,
    true,
};
constexpr ChatFunctionSpec kOnServerChatMessageDelegateSpec{
    ChatFunction::OnServerChatMessageDelegate,
    kOnServerChatMessageDelegateNameIndex,
    3,
    0x18,
    kOnServerChatMessageDelegateFields.data(),
    kOnServerChatMessageDelegateFields.size(),
    kShooterGameModeNameIndex,
    true,
};
}}}
"""


def write_chat_core_with_code_segment(path: Path, data_vaddr: int, data_segment: bytes, code_vaddr: int, code_segment: bytes) -> None:
    header_size = 64
    phoff = header_size
    phentsize = 56
    data_offset = 0x1000
    code_offset = data_offset + ((len(data_segment) + 0xFFF) & ~0xFFF)

    data = bytearray(code_offset + len(code_segment))
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
    struct.pack_into("<H", data, 0x38, 2)

    for slot, flags, offset, vaddr, segment in (
        (0, 6, data_offset, data_vaddr, data_segment),
        (1, 5, code_offset, code_vaddr, code_segment),
    ):
        struct.pack_into(
            "<IIQQQQQQ",
            data,
            phoff + slot * phentsize,
            scanner.PT_LOAD,
            flags,
            offset,
            vaddr,
            0,
            len(segment),
            len(segment),
            0x1000,
        )
        data[offset : offset + len(segment)] = segment

    path.write_bytes(data)


def build_chat_core_fixture(path: Path, *, mismatch_message_offset: bool = False) -> dict[str, int]:
    base = 0x10000000
    code_base = 0x154A000
    segment = bytearray(0x180000)
    addrs = {
        "base": base,
        "native_exec": 0x154A600,
        "fname_root_slot": base + 0x100,
        "fname_table": base + 0x1000,
        "fname_chunk0": base + 0x3000,
        "fname_chunk1": base + 0x80000,
        "gobjects": base + 0x5000,
        "gobjects_chunks": base + 0x6000,
        "gobjects_chunk0": base + 0x7000,
        "class_class": base + 0x20000,
        "function_class": base + 0x20100,
        "str_property_class": base + 0x20200,
        "byte_property_class": base + 0x20280,
        "bool_property_class": base + 0x202c0,
        "struct_property_class": base + 0x202e0,
        "int_property_class": base + 0x20320,
        "owner_class": base + 0x20300,
        "game_mode_owner_class": base + 0x20380,
        "server_chat": base + 0x30000,
        "server_chat_to": base + 0x30100,
        "server_chat_to_player": base + 0x30200,
        "server_send_chat_message": base + 0x30300,
        "client_chat_message": base + 0x30400,
        "client_server_chat_direct_message": base + 0x30500,
        "client_server_chat_message": base + 0x30600,
        "server_chat_message": base + 0x40000,
        "server_chat_to_steam": base + 0x40100,
        "server_chat_to_message": base + 0x40200,
        "server_chat_to_player_name": base + 0x40300,
        "server_chat_to_player_message": base + 0x40400,
        "server_send_chat_chat_message": base + 0x40500,
        "server_send_chat_send_mode": base + 0x40600,
        "client_chat_chat": base + 0x40700,
        "client_server_direct_message_text": base + 0x40800,
        "client_server_direct_message_color": base + 0x40900,
        "client_server_direct_b_is_bold": base + 0x40a00,
        "client_server_message_text": base + 0x40b00,
        "client_server_message_color": base + 0x40c00,
        "client_server_b_is_bold": base + 0x40d00,
        "send_server_chat_message": base + 0x30700,
        "on_server_chat_message_delegate": base + 0x30800,
        "send_server_message_text": base + 0x40e00,
        "send_server_message_color": base + 0x40f00,
        "send_server_b_is_bold": base + 0x41000,
        "send_server_receiver_team_id": base + 0x41100,
        "send_server_receiver_player_id": base + 0x41200,
        "delegate_message_text": base + 0x41300,
        "delegate_receiver_team_id": base + 0x41400,
        "delegate_receiver_player_id": base + 0x41500,
        "send_mode_enum": base + 0x41600,
        "send_mode_enum_names": base + 0x41700,
    }

    def put_ptr(address: int, value: int) -> None:
        struct.pack_into("<Q", segment, address - base, value)

    def put_i32(address: int, value: int) -> None:
        struct.pack_into("<i", segment, address - base, value)

    def put_u16(address: int, value: int) -> None:
        struct.pack_into("<H", segment, address - base, value)

    def put_u32(address: int, value: int) -> None:
        struct.pack_into("<I", segment, address - base, value)

    fname_entry_cursor = 0

    def put_entry(index: int, text: bytes) -> None:
        nonlocal fname_entry_cursor
        entry = base + 0x120000 + fname_entry_cursor * 0x80
        fname_entry_cursor += 1
        chunk_index = index // enum.FNAME_CHUNK_SIZE
        entry_index = index % enum.FNAME_CHUNK_SIZE
        put_ptr(addrs[f"fname_chunk{chunk_index}"] + entry_index * 8, entry)
        put_u32(entry, index * 2)
        segment[entry - base + 0x10 : entry - base + 0x10 + len(text)] = text

    def put_uobject(address: int, internal_index: int, class_address: int, name_index: int, outer: int = 0) -> None:
        put_u32(address + enum.UOBJECT_FLAGS_OFFSET, 1)
        put_i32(address + enum.UOBJECT_INTERNAL_INDEX_OFFSET, internal_index)
        put_ptr(address + enum.UOBJECT_CLASS_OFFSET, class_address)
        put_i32(address + enum.UOBJECT_NAME_INDEX_OFFSET, name_index)
        put_i32(address + enum.UOBJECT_NAME_NUMBER_OFFSET, 0)
        put_ptr(address + enum.UOBJECT_OUTER_OFFSET, outer)

    def put_item(index: int, object_address: int) -> None:
        item = addrs["gobjects_chunk0"] + index * enum.FUOBJECT_ITEM_SIZE
        put_ptr(item, object_address)
        put_u32(item + 0x8, 0)
        put_i32(item + 0xC, 1000 + index)

    def put_function(address: int, first_property: int, num_parms: int, parms_size: int, native_exec: int = 0) -> None:
        put_ptr(address + 0x38, first_property)
        put_i32(address + 0x40, parms_size)
        put_i32(address + 0x44, 8)
        put_u32(address + 0x90, 0x00204000)
        put_u16(address + 0x94, 0xFFFF)
        put_u16(address + 0x96, num_parms)
        put_u16(address + 0x98, parms_size)
        put_u16(address + 0x9A, 0xFFFF)
        if native_exec:
            put_ptr(address + 0xA8, native_exec)

    def put_property(address: int, next_field: int, offset: int, element_size: int = 0x10) -> None:
        put_ptr(address + 0x28, next_field)
        put_i32(address + 0x30, 1)
        put_i32(address + 0x34, element_size)
        put_ptr(address + 0x38, 0x280)
        put_i32(address + 0x4C, offset)

    put_ptr(addrs["fname_root_slot"], addrs["fname_table"])
    put_ptr(addrs["fname_table"], addrs["fname_chunk0"])
    put_ptr(addrs["fname_table"] + 8, addrs["fname_chunk1"])
    put_u32(addrs["fname_table"] + 0x800, 0x6000)
    put_u32(addrs["fname_table"] + 0x804, 2)
    for index, text in {
        1: b"ByteProperty\x00",
        2: b"IntProperty\x00",
        3: b"BoolProperty\x00",
        10: b"StructProperty\x00",
        13: b"StrProperty\x00",
        100: b"Function\x00",
        101: b"ShooterPlayerController\x00",
        588: b"ChatMessage\x00",
        1865: b"ClientChatMessage\x00",
        1983: b"ClientServerChatDirectMessage\x00",
        1984: b"ClientServerChatMessage\x00",
        2697: b"ServerSendChatMessage\x00",
        9801: b"SendServerChatMessage\x00",
        9619: b"ServerChat\x00",
        9620: b"ServerChatTo\x00",
        9621: b"ServerChatToPlayer\x00",
        9755: b"ShooterGameMode\x00",
        12000: b"Chat\x00",
        12001: b"MessageColor\x00",
        12002: b"bIsBold\x00",
        16753: b"SendMode\x00",
        16693: b"PlayerName\x00",
        20681: b"SteamID\x00",
        21407: b"bIsBold\x00",
        21408: b"MessageColor\x00",
        21409: b"MessageText\x00",
        28549: b"OnServerChatMessage__DelegateSignature\x00",
        28550: b"ReceiverPlayerID\x00",
        28551: b"ReceiverTeamId\x00",
        30000: b"EChatSendMode::GlobalChat\x00",
        30001: b"EChatSendMode::GlobalTribeChat\x00",
        30002: b"EChatSendMode::LocalChat\x00",
        30003: b"EChatSendMode::AllianceChat\x00",
        30004: b"EChatSendMode::MAX\x00",
        30005: b"EChatSendMode::EChatSendMode_MAX\x00",
    }.items():
        put_entry(index, text)

    put_ptr(addrs["gobjects"] + enum.GOBJECTS_CHUNKS_OFFSET, addrs["gobjects_chunks"])
    put_i32(addrs["gobjects"] + enum.GOBJECTS_COUNT_OFFSET, 28552)
    put_ptr(addrs["gobjects_chunks"], addrs["gobjects_chunk0"])

    put_uobject(addrs["class_class"], 0, addrs["class_class"], 2)
    put_uobject(addrs["function_class"], 100, addrs["class_class"], 100)
    put_uobject(addrs["owner_class"], 200, addrs["class_class"], 101)
    put_uobject(addrs["byte_property_class"], 533, addrs["class_class"], 1)
    put_uobject(addrs["bool_property_class"], 540, addrs["class_class"], 3)
    put_uobject(addrs["int_property_class"], 539, addrs["class_class"], 2)
    put_uobject(addrs["struct_property_class"], 541, addrs["class_class"], 10)
    put_uobject(addrs["str_property_class"], 547, addrs["class_class"], 13)
    put_uobject(addrs["game_mode_owner_class"], 411, addrs["class_class"], 9755)
    put_uobject(addrs["server_chat"], 25447, addrs["function_class"], 9619, addrs["owner_class"])
    put_uobject(addrs["server_chat_to"], 25449, addrs["function_class"], 9620, addrs["owner_class"])
    put_uobject(addrs["server_chat_to_player"], 25452, addrs["function_class"], 9621, addrs["owner_class"])
    put_uobject(addrs["server_send_chat_message"], 10443, addrs["function_class"], 2697, addrs["owner_class"])
    put_uobject(addrs["client_chat_message"], 9548, addrs["function_class"], 1865, addrs["owner_class"])
    put_uobject(
        addrs["client_server_chat_direct_message"],
        9768,
        addrs["function_class"],
        1983,
        addrs["owner_class"],
    )
    put_uobject(addrs["client_server_chat_message"], 9772, addrs["function_class"], 1984, addrs["owner_class"])
    put_uobject(
        addrs["send_server_chat_message"],
        26281,
        addrs["function_class"],
        9801,
        addrs["game_mode_owner_class"],
    )
    put_uobject(
        addrs["on_server_chat_message_delegate"],
        26240,
        addrs["function_class"],
        28549,
        addrs["game_mode_owner_class"],
    )
    put_uobject(addrs["server_chat_message"], 1000, addrs["str_property_class"], 21409, addrs["server_chat"])
    put_uobject(addrs["server_chat_to_steam"], 1001, addrs["str_property_class"], 20681, addrs["server_chat_to"])
    put_uobject(addrs["server_chat_to_message"], 1002, addrs["str_property_class"], 21409, addrs["server_chat_to"])
    put_uobject(addrs["server_chat_to_player_name"], 1003, addrs["str_property_class"], 16693, addrs["server_chat_to_player"])
    put_uobject(
        addrs["server_chat_to_player_message"],
        1004,
        addrs["str_property_class"],
        21409,
        addrs["server_chat_to_player"],
    )
    put_uobject(
        addrs["server_send_chat_chat_message"],
        1005,
        addrs["str_property_class"],
        588,
        addrs["server_send_chat_message"],
    )
    put_uobject(
        addrs["server_send_chat_send_mode"],
        1006,
        addrs["byte_property_class"],
        16753,
        addrs["server_send_chat_message"],
    )
    put_uobject(addrs["client_chat_chat"], 1007, addrs["struct_property_class"], 12000, addrs["client_chat_message"])
    put_uobject(
        addrs["client_server_direct_message_text"],
        1008,
        addrs["str_property_class"],
        21409,
        addrs["client_server_chat_direct_message"],
    )
    put_uobject(
        addrs["client_server_direct_message_color"],
        1009,
        addrs["struct_property_class"],
        12001,
        addrs["client_server_chat_direct_message"],
    )
    put_uobject(
        addrs["client_server_direct_b_is_bold"],
        1010,
        addrs["bool_property_class"],
        12002,
        addrs["client_server_chat_direct_message"],
    )
    put_uobject(
        addrs["client_server_message_text"],
        1011,
        addrs["str_property_class"],
        21409,
        addrs["client_server_chat_message"],
    )
    put_uobject(
        addrs["client_server_message_color"],
        1012,
        addrs["struct_property_class"],
        12001,
        addrs["client_server_chat_message"],
    )
    put_uobject(
        addrs["client_server_b_is_bold"],
        1013,
        addrs["bool_property_class"],
        12002,
        addrs["client_server_chat_message"],
    )
    put_uobject(addrs["send_server_message_text"], 1014, addrs["str_property_class"], 21409, addrs["send_server_chat_message"])
    put_uobject(
        addrs["send_server_message_color"],
        1015,
        addrs["struct_property_class"],
        21408,
        addrs["send_server_chat_message"],
    )
    put_uobject(addrs["send_server_b_is_bold"], 1016, addrs["bool_property_class"], 21407, addrs["send_server_chat_message"])
    put_uobject(
        addrs["send_server_receiver_team_id"],
        1017,
        addrs["int_property_class"],
        28551,
        addrs["send_server_chat_message"],
    )
    put_uobject(
        addrs["send_server_receiver_player_id"],
        1018,
        addrs["int_property_class"],
        28550,
        addrs["send_server_chat_message"],
    )
    put_uobject(
        addrs["delegate_message_text"],
        1019,
        addrs["str_property_class"],
        21409,
        addrs["on_server_chat_message_delegate"],
    )
    put_uobject(
        addrs["delegate_receiver_team_id"],
        1020,
        addrs["int_property_class"],
        28551,
        addrs["on_server_chat_message_delegate"],
    )
    put_uobject(
        addrs["delegate_receiver_player_id"],
        1021,
        addrs["int_property_class"],
        28550,
        addrs["on_server_chat_message_delegate"],
    )

    for index, key in [
        (0, "class_class"),
        (100, "function_class"),
        (200, "owner_class"),
        (411, "game_mode_owner_class"),
        (533, "byte_property_class"),
        (539, "int_property_class"),
        (540, "bool_property_class"),
        (541, "struct_property_class"),
        (547, "str_property_class"),
        (1000, "server_chat_message"),
        (1001, "server_chat_to_steam"),
        (1002, "server_chat_to_message"),
        (1003, "server_chat_to_player_name"),
        (1004, "server_chat_to_player_message"),
        (1005, "server_send_chat_chat_message"),
        (1006, "server_send_chat_send_mode"),
        (1007, "client_chat_chat"),
        (1008, "client_server_direct_message_text"),
        (1009, "client_server_direct_message_color"),
        (1010, "client_server_direct_b_is_bold"),
        (1011, "client_server_message_text"),
        (1012, "client_server_message_color"),
        (1013, "client_server_b_is_bold"),
        (1014, "send_server_message_text"),
        (1015, "send_server_message_color"),
        (1016, "send_server_b_is_bold"),
        (1017, "send_server_receiver_team_id"),
        (1018, "send_server_receiver_player_id"),
        (1019, "delegate_message_text"),
        (1020, "delegate_receiver_team_id"),
        (1021, "delegate_receiver_player_id"),
        (9548, "client_chat_message"),
        (9768, "client_server_chat_direct_message"),
        (9772, "client_server_chat_message"),
        (10443, "server_send_chat_message"),
        (26240, "on_server_chat_message_delegate"),
        (26281, "send_server_chat_message"),
        (25447, "server_chat"),
        (25449, "server_chat_to"),
        (25452, "server_chat_to_player"),
    ]:
        put_item(index, addrs[key])

    put_function(addrs["server_chat"], addrs["server_chat_message"], 1, 0x10)
    put_function(addrs["server_chat_to"], addrs["server_chat_to_steam"], 2, 0x20)
    put_function(addrs["server_chat_to_player"], addrs["server_chat_to_player_name"], 2, 0x20)
    put_function(addrs["server_send_chat_message"], addrs["server_send_chat_chat_message"], 2, 0x11, addrs["native_exec"])
    put_function(addrs["client_chat_message"], addrs["client_chat_chat"], 1, 0x90)
    put_function(addrs["client_server_chat_direct_message"], addrs["client_server_direct_message_text"], 3, 0x21)
    put_function(addrs["client_server_chat_message"], addrs["client_server_message_text"], 3, 0x21)
    put_function(addrs["send_server_chat_message"], addrs["send_server_message_text"], 5, 0x2C)
    put_function(addrs["on_server_chat_message_delegate"], addrs["delegate_message_text"], 3, 0x18)
    put_property(addrs["server_chat_message"], 0, 0)
    put_property(addrs["server_chat_to_steam"], addrs["server_chat_to_message"], 0)
    put_property(addrs["server_chat_to_message"], 0, 0x18 if mismatch_message_offset else 0x10)
    put_property(addrs["server_chat_to_player_name"], addrs["server_chat_to_player_message"], 0)
    put_property(addrs["server_chat_to_player_message"], 0, 0x10)
    put_property(addrs["server_send_chat_chat_message"], addrs["server_send_chat_send_mode"], 0)
    put_property(addrs["server_send_chat_send_mode"], 0, 0x10, 0x1)
    put_ptr(addrs["server_send_chat_send_mode"] + 0x70, addrs["send_mode_enum"])
    put_ptr(addrs["send_mode_enum"] + 0x40, addrs["send_mode_enum_names"])
    put_i32(addrs["send_mode_enum"] + 0x48, 6)
    for enum_value, name_index in enumerate(range(30000, 30006)):
        put_i32(addrs["send_mode_enum_names"] + enum_value * 8, name_index)
        put_i32(addrs["send_mode_enum_names"] + enum_value * 8 + 4, 0)
    put_property(addrs["client_chat_chat"], 0, 0, 0x90)
    put_property(addrs["client_server_direct_message_text"], addrs["client_server_direct_message_color"], 0)
    put_property(addrs["client_server_direct_message_color"], addrs["client_server_direct_b_is_bold"], 0x10)
    put_property(addrs["client_server_direct_b_is_bold"], 0, 0x20, 0x1)
    put_property(addrs["client_server_message_text"], addrs["client_server_message_color"], 0)
    put_property(addrs["client_server_message_color"], addrs["client_server_b_is_bold"], 0x10)
    put_property(addrs["client_server_b_is_bold"], 0, 0x20, 0x1)
    put_property(addrs["send_server_message_text"], addrs["send_server_message_color"], 0)
    put_property(addrs["send_server_message_color"], addrs["send_server_b_is_bold"], 0x10)
    put_property(addrs["send_server_b_is_bold"], addrs["send_server_receiver_team_id"], 0x20, 0x1)
    put_property(addrs["send_server_receiver_team_id"], addrs["send_server_receiver_player_id"], 0x24, 0x4)
    put_property(addrs["send_server_receiver_player_id"], 0, 0x28, 0x4)
    put_property(addrs["delegate_message_text"], addrs["delegate_receiver_team_id"], 0)
    put_property(addrs["delegate_receiver_team_id"], addrs["delegate_receiver_player_id"], 0x10, 0x4)
    put_property(addrs["delegate_receiver_player_id"], 0, 0x14, 0x4)

    write_chat_core_with_code_segment(path, base, bytes(segment), code_base, b"\x90" * 0x1000)
    return addrs


class VerifyChatReflectionConstantsTests(unittest.TestCase):
    def test_verifies_synthetic_core_against_chat_reflection_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            source = root / "ChatReflection.cpp"
            source.write_text(CHAT_REFLECTION_CPP, encoding="utf-8")
            addrs = build_chat_core_fixture(core)
            spec = verifier.parse_chat_reflection_source(source)
            memory = enum.CoreMemory(core)
            try:
                payload = verifier.verify_core(
                    memory,
                    chat_spec=spec,
                    gobjects=addrs["gobjects"],
                    fname_root_slot=addrs["fname_root_slot"],
                    max_object_scan=30000,
                    window_size=0xC0,
                    expected_server_send_chat_native=addrs["native_exec"],
                )
            finally:
                memory.close()

        self.assertEqual(payload["status"], "ok")
        self.assertEqual([item["function"] for item in payload["functions"]], list(verifier.DEFAULT_TARGETS))
        checks = {
            (function["function"], check["label"]): check
            for function in payload["functions"]
            for check in function["checks"]
        }
        self.assertEqual(checks[("ServerChat", "object membership")]["observed"], "candidate-uobject")
        self.assertEqual(checks[("ServerChat", "class membership")]["observed"], "candidate-uobject")
        self.assertEqual(checks[("ServerChat", "outer membership")]["observed"], "candidate-uobject")
        self.assertEqual(checks[("ServerChat", "MessageText[0] membership")]["observed"], "candidate-uobject")
        self.assertEqual(
            checks[("ServerChat", "MessageText[0] class membership")]["observed"],
            "candidate-uobject",
        )
        self.assertEqual(
            checks[("ServerChat", "MessageText[0] outer membership")]["observed"],
            "candidate-uobject",
        )
        self.assertEqual(checks[("ServerChat", "FName index")]["observed"], 9619)
        self.assertEqual(checks[("ServerChatTo", "MessageText[1] offset")]["observed"], 0x10)
        self.assertEqual(checks[("ServerChatToPlayer", "PlayerName[0] property class")]["observed"], "StrProperty")
        self.assertEqual(checks[("ServerSendChatMessage", "FName index")]["observed"], 2697)
        self.assertEqual(checks[("ServerSendChatMessage", "SendMode[1] property class")]["observed"], "ByteProperty")
        self.assertEqual(checks[("ServerSendChatMessage", "SendMode[1] element size")]["observed"], 1)
        self.assertEqual(checks[("ServerSendChatMessage", "native exec candidate")]["observed"], "0x154a600")
        self.assertTrue(checks[("ServerSendChatMessage", "native exec segment executable")]["observed"])
        self.assertEqual(
            checks[("ServerSendChatMessage", "SendMode enum values")]["observed"][:4],
            [
                "EChatSendMode::GlobalChat",
                "EChatSendMode::GlobalTribeChat",
                "EChatSendMode::LocalChat",
                "EChatSendMode::AllianceChat",
            ],
        )
        self.assertEqual(checks[("SendServerChatMessage", "FName index")]["observed"], 9801)
        self.assertEqual(checks[("SendServerChatMessage", "ReceiverTeamId[3] property class")]["observed"], "IntProperty")
        self.assertEqual(checks[("SendServerChatMessage", "ReceiverPlayerID[4] offset")]["observed"], 0x28)
        self.assertEqual(checks[("OnServerChatMessageDelegate", "FName index")]["observed"], 28549)
        self.assertEqual(checks[("OnServerChatMessageDelegate", "ReceiverTeamId[1] element size")]["observed"], 4)

    def test_reports_mismatch_for_property_offset_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            source = root / "ChatReflection.cpp"
            source.write_text(CHAT_REFLECTION_CPP, encoding="utf-8")
            addrs = build_chat_core_fixture(core, mismatch_message_offset=True)
            spec = verifier.parse_chat_reflection_source(source)
            memory = enum.CoreMemory(core)
            try:
                payload = verifier.verify_core(
                    memory,
                    chat_spec=spec,
                    gobjects=addrs["gobjects"],
                    fname_root_slot=addrs["fname_root_slot"],
                    max_object_scan=30000,
                    window_size=0xC0,
                    expected_server_send_chat_native=addrs["native_exec"],
                )
            finally:
                memory.close()

        self.assertEqual(payload["status"], "mismatch")
        mismatches = [
            check
            for function in payload["functions"]
            for check in function["checks"]
            if check["status"] == "mismatch"
        ]
        self.assertIn("MessageText[1] offset", {check["label"] for check in mismatches})

    def test_cli_json_exits_zero_for_matching_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            source = root / "ChatReflection.cpp"
            source.write_text(CHAT_REFLECTION_CPP, encoding="utf-8")
            addrs = build_chat_core_fixture(core)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "verify_chat_reflection_constants.py"),
                    "--core",
                    str(core),
                    "--chat-reflection-source",
                    str(source),
                    "--gobjects",
                    hex(addrs["gobjects"]),
                    "--fname-root-slot",
                    hex(addrs["fname_root_slot"]),
                    "--expected-server-send-chat-native",
                    hex(addrs["native_exec"]),
                    "--json",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["functions"][0]["function"], "ServerChat")

    def test_cli_rejects_protected_core_path_before_open(self) -> None:
        for core_path in (
            Path("/servidor/ark/obelisk/dumps/chat-core"),
            None,
        ):
            with self.subTest(core_path=core_path), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                candidate = core_path
                if candidate is None:
                    candidate = root / "core-link"
                    candidate.symlink_to("/servidor/ark/obelisk/dumps/chat-core")
                result = subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPT_DIR / "verify_chat_reflection_constants.py"),
                        "--core",
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--core must not read from protected server root /servidor/ark", result.stderr)

    def test_cli_rejects_protected_evidence_pack_path_before_manifest_read(self) -> None:
        for pack_path in (
            Path("/servidor/ark/obelisk/evidence/chat-pack"),
            None,
        ):
            with self.subTest(pack_path=pack_path), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                candidate = pack_path
                if candidate is None:
                    candidate = root / "pack-link"
                    candidate.symlink_to("/servidor/ark/obelisk/evidence/chat-pack")
                result = subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPT_DIR / "verify_chat_reflection_constants.py"),
                        "--evidence-pack",
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--evidence-pack must not read from protected server root /servidor/ark", result.stderr)

    def test_cli_json_accepts_evidence_pack_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"synthetic-binary")
            source = root / "ChatReflection.cpp"
            source.write_text(CHAT_REFLECTION_CPP, encoding="utf-8")
            addrs = build_chat_core_fixture(core)
            expected_core_sha = hashlib.sha256(core.read_bytes()).hexdigest()
            manifest = {
                "binary": {
                    "path": str(binary),
                    "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
                    "size_bytes": binary.stat().st_size,
                },
                "core": {
                    "path": str(core),
                    "sha256": expected_core_sha,
                    "size_bytes": core.stat().st_size,
                },
                "gobjects_candidates": [{"label": "gobjects", "address": hex(addrs["gobjects"])}],
                "fname_root_slots": [{"label": "fname", "address": hex(addrs["fname_root_slot"])}],
            }
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "verify_chat_reflection_constants.py"),
                    "--evidence-pack",
                    str(root),
                    "--chat-reflection-source",
                    str(source),
                    "--expected-server-send-chat-native",
                    hex(addrs["native_exec"]),
                    "--json",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["metadata"]["gobjects"], hex(addrs["gobjects"]))
        self.assertEqual(payload["metadata"]["fname_root_slot"], hex(addrs["fname_root_slot"]))
        self.assertEqual(payload["evidence_pack"]["manifest"], str(manifest_path))
        self.assertEqual(payload["evidence_pack"]["core_sha256"], expected_core_sha)

    def test_evidence_pack_rejects_protected_manifest_core_path_before_open(self) -> None:
        for protected_core in (
            Path("/servidor/ark/obelisk/dumps/chat-core"),
            None,
        ):
            with self.subTest(protected_core=protected_core), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                core = protected_core
                if core is None:
                    core = root / "core-link"
                    core.symlink_to("/servidor/ark/obelisk/dumps/chat-core")
                manifest = {
                    "core": {"path": str(core)},
                    "gobjects_candidates": [{"label": "gobjects", "address": "0x595b7e0"}],
                    "fname_root_slots": [{"label": "fname", "address": "0x5956f30"}],
                }
                manifest_path = root / "manifest.json"
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

                with self.assertRaisesRegex(SystemExit, "evidence pack core.path must not read"):
                    verifier.load_evidence_pack(manifest_path, verify_binary_sha=False)

    def test_evidence_pack_rejects_protected_manifest_binary_path_even_without_hashing(self) -> None:
        for protected_binary in (
            Path("/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer"),
            None,
        ):
            with self.subTest(protected_binary=protected_binary), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                core = root / "core"
                build_chat_core_fixture(core)
                binary = protected_binary
                if binary is None:
                    binary = root / "ShooterGameServer-link"
                    binary.symlink_to("/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer")
                manifest = {
                    "binary": {"path": str(binary)},
                    "core": {"path": str(core)},
                    "gobjects_candidates": [{"label": "gobjects", "address": "0x595b7e0"}],
                    "fname_root_slots": [{"label": "fname", "address": "0x5956f30"}],
                }
                manifest_path = root / "manifest.json"
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

                with self.assertRaisesRegex(SystemExit, "evidence pack binary.path must not read"):
                    verifier.load_evidence_pack(manifest_path, verify_binary_sha=False)

    def test_evidence_pack_allows_approved_offline_workspace_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            protected = root / "server-root"
            workspace = protected / "workspace-offline"
            workspace.mkdir(parents=True)
            core = workspace / "core"
            binary = workspace / "ShooterGameServer"
            build_chat_core_fixture(core)
            binary.write_bytes(b"synthetic-binary")
            expected_binary_sha = hashlib.sha256(binary.read_bytes()).hexdigest()
            manifest = {
                "binary": {
                    "path": str(binary),
                    "sha256": expected_binary_sha,
                },
                "core": {
                    "path": str(core),
                    "sha256": hashlib.sha256(core.read_bytes()).hexdigest(),
                },
                "gobjects_candidates": [{"label": "gobjects", "address": "0x595b7e0"}],
                "fname_root_slots": [{"label": "fname", "address": "0x5956f30"}],
            }
            manifest_path = workspace / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            with (
                mock.patch.object(snapshot_evidence_pack, "SERVER_ROOT", protected),
                mock.patch.object(snapshot_evidence_pack, "APPROVED_OFFLINE_WORKSPACE_ROOTS", (workspace,)),
            ):
                pack = verifier.load_evidence_pack(manifest_path)

        self.assertEqual(pack.core, core.resolve())
        self.assertEqual(pack.binary_sha256, expected_binary_sha)

    def test_evidence_pack_rejects_binary_sha_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"synthetic-binary")
            build_chat_core_fixture(core)
            manifest = {
                "binary": {"path": str(binary), "sha256": "0" * 64},
                "core": {"path": str(core)},
                "gobjects_candidates": [{"label": "gobjects", "address": "0x595b7e0"}],
                "fname_root_slots": [{"label": "fname", "address": "0x5956f30"}],
            }
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "binary sha256 mismatch"):
                verifier.load_evidence_pack(manifest_path)

    def test_evidence_pack_rejects_core_sha_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"synthetic-binary")
            build_chat_core_fixture(core)
            manifest = {
                "binary": {"path": str(binary), "sha256": hashlib.sha256(binary.read_bytes()).hexdigest()},
                "core": {"path": str(core), "sha256": "0" * 64},
                "gobjects_candidates": [{"label": "gobjects", "address": "0x595b7e0"}],
                "fname_root_slots": [{"label": "fname", "address": "0x5956f30"}],
            }
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "core sha256 mismatch"):
                verifier.load_evidence_pack(manifest_path)

    def test_evidence_pack_requires_gobjects_and_fname_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            build_chat_core_fixture(core)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps({"core": {"path": str(core)}, "fname_root_slots": []}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "gobjects_candidates"):
                verifier.load_evidence_pack(manifest_path, verify_binary_sha=False)

    def test_cli_rejects_evidence_pack_with_manual_gobjects_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"synthetic-binary")
            source = root / "ChatReflection.cpp"
            source.write_text(CHAT_REFLECTION_CPP, encoding="utf-8")
            addrs = build_chat_core_fixture(core)
            manifest = {
                "binary": {
                    "path": str(binary),
                    "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
                },
                "core": {"path": str(core)},
                "gobjects_candidates": [{"label": "gobjects", "address": hex(addrs["gobjects"])}],
                "fname_root_slots": [{"label": "fname", "address": hex(addrs["fname_root_slot"])}],
            }
            (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "verify_chat_reflection_constants.py"),
                    "--evidence-pack",
                    str(root),
                    "--chat-reflection-source",
                    str(source),
                    "--gobjects",
                    hex(addrs["gobjects"]),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("do not pass overrides", result.stderr)


if __name__ == "__main__":
    unittest.main()
