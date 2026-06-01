#!/usr/bin/env python3
"""Tests for check_command_permission_route_gate.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_command_permission_route_gate.py"
QUERY_CONTRACT = REPO_ROOT / "docs" / "permissions_admin_query_failclosed_contract.json"
IDENTITY_DECISIONS = REPO_ROOT / "docs" / "player_identity_public_contract_decisions.json"


class CommandPermissionRouteGateTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def test_accepts_current_route_as_planning_only(self) -> None:
        result = self.run_checker("--json")
        report = json.loads(result.stdout)

        self.assertTrue(report["valid"])
        self.assertTrue(report["accepted_for_planning"])
        self.assertTrue(report["planning_only"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertEqual(
            [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
                "obelisk.commands_replies.v1",
            ],
            report["dependency_chain"],
        )
        self.assertEqual(8, len(report["checks"]))
        check_names = {check["name"] for check in report["checks"]}
        self.assertIn("player_identity_public_contract_gap", check_names)
        self.assertIn("command_copied_response_intent_lifecycle_planning", check_names)
        self.assertEqual([], report["blockers"])
        for check in report["checks"]:
            self.assertTrue(check["valid"], check)
            self.assertEqual([], check["public_or_runtime_claims"], check)

    def test_rejects_broken_query_contract_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            query_contract = Path(tmp) / "permissions_admin_query_failclosed_contract.json"
            payload = json.loads(QUERY_CONTRACT.read_text(encoding="utf-8"))
            payload["schema"] = "wrong-schema"
            query_contract.write_text(json.dumps(payload), encoding="utf-8")

            result = self.run_checker(
                "--query-failclosed-artifact",
                str(query_contract),
                "--json",
                check=False,
            )
            report = json.loads(result.stdout)

            self.assertNotEqual(0, result.returncode)
            self.assertFalse(report["valid"])
            self.assertFalse(report["accepted_for_planning"])
            self.assertTrue(any("permissions_query_failclosed" in blocker for blocker in report["blockers"]))

    def test_rejects_identity_public_contract_gap_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            decisions = Path(tmp) / "player_identity_public_contract_decisions.json"
            payload = json.loads(IDENTITY_DECISIONS.read_text(encoding="utf-8"))
            payload["public_header_allowed"] = True
            decisions.write_text(json.dumps(payload), encoding="utf-8")

            result = self.run_checker(
                "--player-identity-decisions",
                str(decisions),
                "--json",
                check=False,
            )
            report = json.loads(result.stdout)

            self.assertNotEqual(0, result.returncode)
            self.assertFalse(report["valid"])
            self.assertFalse(report["accepted_for_planning"])
            self.assertTrue(
                any("player_identity_public_contract_gap" in blocker for blocker in report["blockers"])
            )


if __name__ == "__main__":
    unittest.main()
