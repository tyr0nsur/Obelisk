#!/usr/bin/env python3
"""Test-only scaffold for plugin-local chat command parsing.

This models only the copied fields already exposed by ObeliskChatMessageEvent.
It is not a runtime helper, public SDK surface, authorization layer, response
path, gameplay mutator, or return-override mechanism.
"""

from __future__ import annotations

from dataclasses import dataclass
import string


CHAT_MESSAGE_EVENT_ABI_VERSION = 1
CHAT_MESSAGE_EVENT_MIN_STRUCT_SIZE = 48
CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD = 1
CHAT_SEND_MODE_MAX = 3
MAX_LOCAL_COMMAND_BYTES = 1024
MAX_LOCAL_COMMAND_NAME_BYTES = 32
SAFE_COMMAND_CHARS = set(string.ascii_letters + string.digits + "_-")


@dataclass(frozen=True)
class ChatMessageEventFixture:
    abi_version: int
    struct_size: int
    send_mode: int
    flags: int
    sequence: int
    message: str


@dataclass(frozen=True)
class ParsedChatCommand:
    name: str


def is_safe_command_name(value: str) -> bool:
    encoded = value.encode("utf-8")
    if not encoded or len(encoded) > MAX_LOCAL_COMMAND_NAME_BYTES:
        return False
    return all(ch in SAFE_COMMAND_CHARS for ch in value)


def is_safe_prefix(value: str) -> bool:
    encoded = value.encode("utf-8")
    if not encoded or len(encoded) > 8:
        return False
    return all(not chr(byte).isspace() and byte >= 0x20 and byte != 0x7f for byte in encoded)


def is_ascii_space(ch: str) -> bool:
    return ch in " \t\n\r\f\v"


def parse_plugin_local_command(
    event: ChatMessageEventFixture,
    *,
    prefix: str = "!",
) -> ParsedChatCommand | None:
    """Parse copied chat text for plugin-local tests.

    Routing, authorization, responses, gameplay mutation, and return overrides
    belong outside this helper.
    """
    if not is_safe_prefix(prefix):
        raise ValueError("prefix must be non-empty, <=8 bytes, and contain no whitespace or control characters")
    if event.abi_version != CHAT_MESSAGE_EVENT_ABI_VERSION:
        return None
    if event.struct_size < CHAT_MESSAGE_EVENT_MIN_STRUCT_SIZE:
        return None
    if not (event.flags & CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD):
        return None
    if event.send_mode < 0 or event.send_mode > CHAT_SEND_MODE_MAX:
        return None
    if len(event.message.encode("utf-8")) > MAX_LOCAL_COMMAND_BYTES:
        return None

    text = event.message
    if not text.startswith(prefix):
        return None

    cursor = len(prefix)
    while cursor < len(text) and is_ascii_space(text[cursor]):
        cursor += 1
    command_start = cursor
    while cursor < len(text) and not is_ascii_space(text[cursor]):
        cursor += 1
    command = text[command_start:cursor]
    if not is_safe_command_name(command):
        return None
    return ParsedChatCommand(name=command)
