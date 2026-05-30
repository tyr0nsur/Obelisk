#!/usr/bin/env python3
"""Test-only scaffold for plugin-local chat command parsing.

This models only the copied fields already exposed by ObeliskChatMessageEvent.
It is not a runtime helper, public SDK surface, authorization layer, response
path, gameplay mutator, or return-override mechanism.
"""

from __future__ import annotations

from dataclasses import dataclass
import shlex


CHAT_MESSAGE_EVENT_ABI_VERSION = 1
CHAT_MESSAGE_EVENT_MIN_STRUCT_SIZE = 48
CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD = 1
CHAT_SEND_MODE_MAX = 3


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
    argv: tuple[str, ...]


def parse_plugin_local_command(
    event: ChatMessageEventFixture,
    *,
    prefix: str = "!",
) -> ParsedChatCommand | None:
    """Parse copied chat text for plugin-local tests.

    Routing, authorization, responses, gameplay mutation, and return overrides
    belong outside this helper.
    """
    if not prefix:
        raise ValueError("prefix must not be empty")
    if event.abi_version != CHAT_MESSAGE_EVENT_ABI_VERSION:
        return None
    if event.struct_size < CHAT_MESSAGE_EVENT_MIN_STRUCT_SIZE:
        return None
    if not (event.flags & CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD):
        return None
    if event.send_mode < 0 or event.send_mode > CHAT_SEND_MODE_MAX:
        return None

    text = event.message.strip()
    if not text.startswith(prefix):
        return None

    body = text[len(prefix):].strip()
    if not body:
        return None

    try:
        tokens = shlex.split(body)
    except ValueError:
        return None
    if not tokens:
        return None

    return ParsedChatCommand(name=tokens[0].lower(), argv=tuple(tokens[1:]))
