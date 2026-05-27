#!/usr/bin/env python3
"""Offline tests for verify_chat_reflection_constants.py."""

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
import verify_chat_reflection_constants as verifier
from test_scan_core_fname_tables import write_minimal_elf64_core


CHAT_REFLECTION_CPP = """
namespace Obelisk::UE::ChatReflection {
namespace {
constexpr int32_t kServerChatNameIndex = 9619;
constexpr int32_t kServerChatToNameIndex = 9620;
constexpr int32_t kServerChatToPlayerNameIndex = 9621;
constexpr int32_t kMessageTextNameIndex = 21409;
constexpr int32_t kSteamIDNameIndex = 20681;
constexpr int32_t kPlayerNameNameIndex = 16693;
constexpr int32_t kStrPropertyClassNameIndex = 13;
constexpr int32_t kStrPropertyClassObjectIndex = 547;
constexpr size_t kFStringHeaderSize = 0x10;
constexpr std::array<ChatFieldSpec, 1> kServerChatFields{{
    {ChatField::MessageText, kMessageTextNameIndex, 0x00, kFStringHeaderSize},
}};
constexpr std::array<ChatFieldSpec, 2> kServerChatToFields{{
    {ChatField::SteamID, kSteamIDNameIndex, 0x00, kFStringHeaderSize},
    {ChatField::MessageText, kMessageTextNameIndex, 0x10, kFStringHeaderSize},
}};
constexpr std::array<ChatFieldSpec, 2> kServerChatToPlayerFields{{
    {ChatField::PlayerName, kPlayerNameNameIndex, 0x00, kFStringHeaderSize},
    {ChatField::MessageText, kMessageTextNameIndex, 0x10, kFStringHeaderSize},
}};
constexpr ChatFunctionSpec kServerChatSpec{
    ChatFunction::ServerChat,
    kServerChatNameIndex,
    1,
    0x10,
    kServerChatFields.data(),
    kServerChatFields.size(),
};
constexpr ChatFunctionSpec kServerChatToSpec{
    ChatFunction::ServerChatTo,
    kServerChatToNameIndex,
    2,
    0x20,
    kServerChatToFields.data(),
    kServerChatToFields.size(),
};
constexpr ChatFunctionSpec kServerChatToPlayerSpec{
    ChatFunction::ServerChatToPlayer,
    kServerChatToPlayerNameIndex,
    2,
    0x20,
    kServerChatToPlayerFields.data(),
    kServerChatToPlayerFields.size(),
};
}}}
"""


def build_chat_core_fixture(path: Path, *, mismatch_message_offset: bool = False) -> dict[str, int]:
    base = 0x10000000
    segment = bytearray(0x180000)
    addrs = {
        "base": base,
        "fname_root_slot": base + 0x100,
        "fname_table": base + 0x1000,
        "fname_chunk": base + 0x3000,
        "gobjects": base + 0x5000,
        "gobjects_chunks": base + 0x6000,
        "gobjects_chunk0": base + 0x7000,
        "class_class": base + 0x20000,
        "function_class": base + 0x20100,
        "str_property_class": base + 0x20200,
        "owner_class": base + 0x20300,
        "server_chat": base + 0x30000,
        "server_chat_to": base + 0x30100,
        "server_chat_to_player": base + 0x30200,
        "server_chat_message": base + 0x40000,
        "server_chat_to_steam": base + 0x40100,
        "server_chat_to_message": base + 0x40200,
        "server_chat_to_player_name": base + 0x40300,
        "server_chat_to_player_message": base + 0x40400,
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
        entry = base + 0x80000 + index * 0x20
        put_ptr(addrs["fname_chunk"] + index * 8, entry)
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

    def put_function(address: int, first_property: int, num_parms: int, parms_size: int) -> None:
        put_ptr(address + 0x38, first_property)
        put_i32(address + 0x40, parms_size)
        put_i32(address + 0x44, 8)
        put_u32(address + 0x90, 0x00204000)
        put_u16(address + 0x94, 0xFFFF)
        put_u16(address + 0x96, num_parms)
        put_u16(address + 0x98, parms_size)
        put_u16(address + 0x9A, 0xFFFF)

    def put_property(address: int, next_field: int, offset: int) -> None:
        put_ptr(address + 0x28, next_field)
        put_i32(address + 0x30, 1)
        put_i32(address + 0x34, 0x10)
        put_ptr(address + 0x38, 0x280)
        put_i32(address + 0x4C, offset)

    put_ptr(addrs["fname_root_slot"], addrs["fname_table"])
    put_ptr(addrs["fname_table"], addrs["fname_chunk"])
    put_u32(addrs["fname_table"] + 0x800, 0x6000)
    put_u32(addrs["fname_table"] + 0x804, 1)
    for index, text in {
        1: b"Class\x00",
        13: b"StrProperty\x00",
        100: b"Function\x00",
        101: b"ShooterPlayerController\x00",
        9619: b"ServerChat\x00",
        9620: b"ServerChatTo\x00",
        9621: b"ServerChatToPlayer\x00",
        16693: b"PlayerName\x00",
        20681: b"SteamID\x00",
        21409: b"MessageText\x00",
    }.items():
        put_entry(index, text)

    put_ptr(addrs["gobjects"] + enum.GOBJECTS_CHUNKS_OFFSET, addrs["gobjects_chunks"])
    put_i32(addrs["gobjects"] + enum.GOBJECTS_COUNT_OFFSET, 25453)
    put_ptr(addrs["gobjects_chunks"], addrs["gobjects_chunk0"])

    put_uobject(addrs["class_class"], 0, addrs["class_class"], 1)
    put_uobject(addrs["function_class"], 100, addrs["class_class"], 100)
    put_uobject(addrs["owner_class"], 200, addrs["class_class"], 101)
    put_uobject(addrs["str_property_class"], 547, addrs["class_class"], 13)
    put_uobject(addrs["server_chat"], 25447, addrs["function_class"], 9619, addrs["owner_class"])
    put_uobject(addrs["server_chat_to"], 25449, addrs["function_class"], 9620, addrs["owner_class"])
    put_uobject(addrs["server_chat_to_player"], 25452, addrs["function_class"], 9621, addrs["owner_class"])
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

    for index, key in [
        (0, "class_class"),
        (100, "function_class"),
        (200, "owner_class"),
        (547, "str_property_class"),
        (1000, "server_chat_message"),
        (1001, "server_chat_to_steam"),
        (1002, "server_chat_to_message"),
        (1003, "server_chat_to_player_name"),
        (1004, "server_chat_to_player_message"),
        (25447, "server_chat"),
        (25449, "server_chat_to"),
        (25452, "server_chat_to_player"),
    ]:
        put_item(index, addrs[key])

    put_function(addrs["server_chat"], addrs["server_chat_message"], 1, 0x10)
    put_function(addrs["server_chat_to"], addrs["server_chat_to_steam"], 2, 0x20)
    put_function(addrs["server_chat_to_player"], addrs["server_chat_to_player_name"], 2, 0x20)
    put_property(addrs["server_chat_message"], 0, 0)
    put_property(addrs["server_chat_to_steam"], addrs["server_chat_to_message"], 0)
    put_property(addrs["server_chat_to_message"], 0, 0x18 if mismatch_message_offset else 0x10)
    put_property(addrs["server_chat_to_player_name"], addrs["server_chat_to_player_message"], 0)
    put_property(addrs["server_chat_to_player_message"], 0, 0x10)

    write_minimal_elf64_core(path, base, bytes(segment))
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
        self.assertEqual(checks[("ServerChat", "FName index")]["observed"], 9619)
        self.assertEqual(checks[("ServerChatTo", "MessageText[1] offset")]["observed"], 0x10)
        self.assertEqual(checks[("ServerChatToPlayer", "PlayerName[0] property class")]["observed"], "StrProperty")

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
                    "--json",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["functions"][0]["function"], "ServerChat")


if __name__ == "__main__":
    unittest.main()
