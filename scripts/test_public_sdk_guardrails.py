#!/usr/bin/env python3
"""Guardrails that keep experimental gameplay modules out of the public SDK."""

from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class PublicSdkGuardrailTests(unittest.TestCase):
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

    def test_public_header_has_no_gameplay_module_api_until_promotion(self) -> None:
        header = (REPO_ROOT / "include/obelisk/ObeliskApi.h").read_text(encoding="utf-8")
        module_terms = [
            "Inventory",
            "Structure",
            "Buff",
            "Dino",
            "Tribe",
            "Mission",
            "Transfer",
            "Admin",
            "Player",
            "Item",
        ]
        forbidden = [
            f"OBELISK_API_CAPABILITY_{term.upper()}_EVENTS"
            for term in module_terms
        ] + [
            f"Obelisk{term}" for term in module_terms
        ] + [
            f"RegisterOn{term}" for term in module_terms
        ]

        offenders = [token for token in forbidden if token in header]
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
