#!/usr/bin/env python3
"""Guardrails that keep experimental gameplay modules out of the public SDK."""

from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
UNPROMOTED_GAMEPLAY_SURFACES = (
    "Player",
    "Chat",
    "Tribe",
    "Inventory",
    "Item",
    "Dino",
    "Structure",
    "Mission",
    "Transfer",
    "Permission",
    "Timer",
    "Admin",
    "Command",
)


def unpromoted_gameplay_tokens() -> list[str]:
    tokens: list[str] = []
    for singular in UNPROMOTED_GAMEPLAY_SURFACES:
        plural = f"{singular}s"
        for term in (singular, plural):
            tokens.extend(
                [
                    f"OBELISK_API_CAPABILITY_{term.upper()}_EVENTS",
                    f"Obelisk{term}",
                    f"RegisterOn{term}",
                    f"Unregister{term}",
                    f"On{term}",
                ]
            )
    return tokens


class PublicSdkGuardrailTests(unittest.TestCase):
    def test_cpp_public_sdk_examples_catch_exceptions_at_entry_points(self) -> None:
        files = [
            REPO_ROOT / "README.md",
            REPO_ROOT / "tests/sdk_consumer/MinimalPlugin.cpp",
            REPO_ROOT / "tests/sdk_consumer/MinimalNoShutdownPlugin.cpp",
            REPO_ROOT / "tests/sdk_installed_consumer/consumer_plugin.cpp",
            REPO_ROOT / "tests/sdk_installed_consumer/no_shutdown_plugin.cpp",
        ]
        for path in files:
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                text = path.read_text(encoding="utf-8")
                self.assertIn("catch (...)", text)

    def test_handle_callback_guidance_requires_owner_token_capability(self) -> None:
        files = [
            REPO_ROOT / "README.md",
            REPO_ROOT / "docs/PLUGIN_ARCHITECTURE.md",
            REPO_ROOT / "docs/oBaseEvents.md",
            REPO_ROOT / "tests/sdk_consumer/MinimalPlugin.cpp",
            REPO_ROOT / "plugins/oBaseEvents/oBaseEvents.cpp",
        ]
        for path in files:
            text = path.read_text(encoding="utf-8")
            if "OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES" in text:
                self.assertIn(
                    "OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS",
                    text,
                    f"{path.relative_to(REPO_ROOT)} documents handle callbacks without owner-token capability",
                )

    def test_public_header_has_no_chat_api_until_promotion(self) -> None:
        header = (REPO_ROOT / "include/obelisk/ObeliskApi.h").read_text(encoding="utf-8")
        forbidden = [
            "OBELISK_API_CAPABILITY_CHAT_EVENTS",
            "ObeliskChatMessage",
            "ObeliskChatMessageSubscription",
            "ObeliskOnChatMessageCallback",
            "RegisterOnChatMessage",
            "OnChatMessage",
            "UnregisterChatMessage",
        ]

        offenders = [token for token in forbidden if token in header]
        self.assertEqual(offenders, [])

    def test_sdk_consumer_does_not_depend_on_experimental_chat(self) -> None:
        sdk_dir = REPO_ROOT / "tests/sdk_consumer"
        offenders: list[str] = []
        for path in sdk_dir.rglob("*"):
            if not path.is_file() or path.suffix not in {".cpp", ".h", ".hpp", ".txt"}:
                continue
            text = path.read_text(encoding="utf-8")
            for token in ("RegisterOnChatMessage", "ObeliskChatMessage", "OBELISK_API_CAPABILITY_CHAT_EVENTS"):
                if token in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")

        self.assertEqual(offenders, [])

    def test_public_examples_do_not_use_call_process_event_escape_hatch(self) -> None:
        scanned_roots = [
            REPO_ROOT / "plugins",
            REPO_ROOT / "tests" / "sdk_consumer",
        ]
        allowed_fixture_files = {
            REPO_ROOT / "tests" / "sdk_consumer" / "SdkConsumerFixture.cpp",
        }
        forbidden = (
            "OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT",
            ".CallProcessEvent",
            "->CallProcessEvent",
        )
        offenders: list[str] = []
        for root in scanned_roots:
            for path in root.rglob("*"):
                if path in allowed_fixture_files:
                    continue
                if not path.is_file() or path.suffix not in {".cpp", ".h", ".hpp", ".c"}:
                    continue
                text = path.read_text(encoding="utf-8")
                for token in forbidden:
                    if token in text:
                        offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")

        self.assertEqual(offenders, [])

    def test_unpromoted_gameplay_token_list_covers_documented_examples(self) -> None:
        tokens = set(unpromoted_gameplay_tokens())

        for token in (
            "ObeliskCommand",
            "RegisterOnTimer",
            "OBELISK_API_CAPABILITY_PERMISSION_EVENTS",
            "ObeliskPlayers",
            "UnregisterCommands",
        ):
            self.assertIn(token, tokens)

    def test_public_sdk_headers_have_no_gameplay_module_api_until_promotion(self) -> None:
        offenders: list[str] = []
        forbidden = unpromoted_gameplay_tokens()
        for path in (REPO_ROOT / "include" / "obelisk").rglob("*"):
            if not path.is_file() or path.suffix not in {".h", ".hpp"}:
                continue
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                if token in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")

        self.assertEqual(offenders, [])

    def test_chat_abi_preflight_documents_future_shapes(self) -> None:
        note = (REPO_ROOT / "docs/research/2026-05-27-chat-sdk-abi-preflight.md").read_text(
            encoding="utf-8"
        )

        for token in (
            "ObeliskStringView",
            "ObeliskChatMessage",
            "ObeliskChatMessageSubscription",
            "OBELISK_API_CAPABILITY_CHAT_EVENTS",
            "RegisterOnChatMessage",
            "Evidence-pack mode",
        ):
            self.assertIn(token, note)


if __name__ == "__main__":
    unittest.main()
