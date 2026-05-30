#!/usr/bin/env python3
"""Executable contract for the plugin-local chat command parser scaffold."""

from __future__ import annotations

from dataclasses import fields
import unittest

from plugin_local_chat_command_parser_contract import (
    CHAT_MESSAGE_EVENT_ABI_VERSION,
    CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD,
    CHAT_MESSAGE_EVENT_MIN_STRUCT_SIZE,
    CHAT_SEND_MODE_MAX,
    ChatMessageEventFixture,
    ParsedChatCommand,
    parse_plugin_local_command,
)


class ChatCommandParserContractTests(unittest.TestCase):
    def make_event(
        self,
        message: str,
        *,
        abi_version: int = CHAT_MESSAGE_EVENT_ABI_VERSION,
        struct_size: int = CHAT_MESSAGE_EVENT_MIN_STRUCT_SIZE,
        send_mode: int = 0,
        flags: int = CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD,
    ) -> ChatMessageEventFixture:
        return ChatMessageEventFixture(
            abi_version=abi_version,
            struct_size=struct_size,
            send_mode=send_mode,
            flags=flags,
            sequence=17,
            message=message,
        )

    def test_parser_uses_copied_chat_message_text_only(self) -> None:
        parsed = parse_plugin_local_command(self.make_event(" !SetRate taming 2 "))

        self.assertEqual(parsed, ParsedChatCommand(name="setrate", argv=("taming", "2")))

    def test_non_commands_do_not_dispatch(self) -> None:
        for message in ("", "hello world", "!", "!   "):
            with self.subTest(message=message):
                self.assertIsNone(parse_plugin_local_command(self.make_event(message)))

    def test_shell_like_quoting_is_local_text_parsing(self) -> None:
        parsed = parse_plugin_local_command(self.make_event('!note "south base" enabled'))

        self.assertEqual(parsed, ParsedChatCommand(name="note", argv=("south base", "enabled")))

    def test_empty_prefix_is_rejected_before_parsing(self) -> None:
        with self.assertRaises(ValueError):
            parse_plugin_local_command(self.make_event("anything"), prefix="")

    def test_event_contract_rejects_non_copied_or_unknown_shapes(self) -> None:
        cases = (
            self.make_event("!ping", abi_version=0),
            self.make_event("!ping", struct_size=CHAT_MESSAGE_EVENT_MIN_STRUCT_SIZE - 1),
            self.make_event("!ping", flags=0),
            self.make_event("!ping", send_mode=CHAT_SEND_MODE_MAX + 1),
            self.make_event("!ping", send_mode=-1),
        )

        for event in cases:
            with self.subTest(event=event):
                self.assertIsNone(parse_plugin_local_command(event))

    def test_malformed_local_quoting_does_not_dispatch(self) -> None:
        self.assertIsNone(parse_plugin_local_command(self.make_event('!note "unterminated')))

    def test_event_fixture_matches_minimal_chat_message_event_surface(self) -> None:
        self.assertEqual(
            [field.name for field in fields(ChatMessageEventFixture)],
            [
                "abi_version",
                "struct_size",
                "send_mode",
                "flags",
                "sequence",
                "message",
            ],
        )

    def test_parser_result_carries_no_identity_permissions_or_authority(self) -> None:
        forbidden_result_terms = (
            "actor",
            "admin",
            "allow",
            "authorize",
            "identity",
            "permission",
            "player",
            "reply",
            "response",
            "return",
            "sender",
            "tribe",
            "override",
            "mutat",
        )

        result_fields = [field.name for field in fields(ParsedChatCommand)]
        self.assertEqual(result_fields, ["name", "argv"])
        for field_name in result_fields:
            lowered = field_name.lower()
            with self.subTest(field=field_name):
                for term in forbidden_result_terms:
                    self.assertNotIn(term, lowered)


if __name__ == "__main__":
    unittest.main()
