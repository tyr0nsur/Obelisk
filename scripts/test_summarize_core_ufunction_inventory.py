#!/usr/bin/env python3
"""Offline tests for summarize_core_ufunction_inventory.py."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import summarize_core_ufunction_inventory as inventory


class UFunctionInventorySummaryTests(unittest.TestCase):
    def test_function_family_uses_common_unreal_prefixes(self) -> None:
        self.assertEqual(inventory.function_family("ServerSendChatMessage"), "Server")
        self.assertEqual(inventory.function_family("ClientRestart"), "Client")
        self.assertEqual(inventory.function_family("BPOverrideAllowStructureAccess"), "BP")
        self.assertEqual(inventory.function_family("K2_GetActorLocation"), "K2")
        self.assertEqual(inventory.function_family("Destroy"), "Destroy")

    def test_summarize_functions_groups_by_outer_and_family(self) -> None:
        payload = inventory.summarize_functions(
            [
                {
                    "name": "ServerDoThing",
                    "family": "Server",
                    "outer_name": "ShooterPlayerController",
                    "outer_class_name": "Class",
                    "index": 1,
                },
                {
                    "name": "ClientDoThing",
                    "family": "Client",
                    "outer_name": "ShooterPlayerController",
                    "outer_class_name": "Class",
                    "index": 2,
                },
                {
                    "name": "BPGetValue",
                    "family": "BP",
                    "outer_name": "PrimalItem",
                    "outer_class_name": "Class",
                    "index": 3,
                },
            ],
            max_groups=10,
        )

        self.assertEqual(payload["function_count"], 3)
        self.assertEqual(payload["top_outers"][0], {"outer": "ShooterPlayerController", "count": 2})
        self.assertIn({"family": "Server", "count": 1}, payload["top_families"])
        groups = {group["outer"]: group for group in payload["outer_groups"]}
        self.assertEqual(groups["ShooterPlayerController"]["families"], {"Server": 1, "Client": 1})
        self.assertEqual(len(groups["ShooterPlayerController"]["samples"]), 2)

    def test_filter_functions_combines_focus_filters(self) -> None:
        functions = [
            {
                "name": "ServerDoThing",
                "family": "Server",
                "outer_name": "ShooterPlayerController",
                "num_parms": 2,
            },
            {
                "name": "ClientDoThing",
                "family": "Client",
                "outer_name": "ShooterPlayerController",
                "num_parms": 1,
            },
            {
                "name": "ServerDoDinoThing",
                "family": "Server",
                "outer_name": "PrimalDinoCharacter",
                "num_parms": 3,
            },
        ]

        filtered = inventory.filter_functions(
            functions,
            outer_contains="player",
            name_contains="do",
            family="server",
            min_params=2,
            max_params=2,
        )

        self.assertEqual([item["name"] for item in filtered], ["ServerDoThing"])

    def test_filter_functions_rejects_unknown_param_count_when_param_filter_is_set(self) -> None:
        functions = [{"name": "ServerMaybe", "family": "Server", "outer_name": "Controller", "num_parms": None}]

        self.assertEqual(inventory.filter_functions(functions, min_params=1), [])


if __name__ == "__main__":
    unittest.main()
