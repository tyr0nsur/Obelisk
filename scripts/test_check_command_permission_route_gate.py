#!/usr/bin/env python3
"""Tests for check_command_permission_route_gate.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import importlib.util
from pathlib import Path
from types import SimpleNamespace


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_command_permission_route_gate.py"
QUERY_CONTRACT = REPO_ROOT / "docs" / "permissions_admin_query_failclosed_contract.json"
IDENTITY_DECISIONS = REPO_ROOT / "docs" / "player_identity_public_contract_decisions.json"

SPEC = importlib.util.spec_from_file_location("check_command_permission_route_gate", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
ROUTE_GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ROUTE_GATE)


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
        self.assertEqual(
            {
                "current_surface": "obelisk.player_identity.v1",
                "current_blocker": "approved_runtime_evidence_missing",
                "next_action": "produce_approved_runtime_principal_lifecycle_evidence",
                "next_after_runtime_evidence": "identity_public_contract_gate_missing",
                "permissions_admin_unlocked": False,
                "command_response_unlocked": False,
                "commands_replies_unlocked": False,
                "source_checker": "check_player_identity_first_evidence_readiness.py",
                "source_checker_exit_code": 1,
                "source_checker_schema": "obelisk.player-identity-first-evidence-readiness.v1",
                "source_checker_parse_error": None,
                "planning_only": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "public_abi_ready": False,
                "runtime_ready": False,
            },
            report["critical_path_phase"],
        )
        self.assertEqual(
            {
                "locked": True,
                "blocked_until": [
                    "approved_runtime_principal_lifecycle_evidence",
                    "reviewed_identity_public_contract",
                ],
                "non_claim": "route lock is an offline invariant; it does not promote identity, permissions, commands, runtime readiness, or v1 completion",
            },
            report["route_lock"],
        )
        check_names = {check["name"] for check in report["checks"]}
        self.assertIn("player_identity_public_contract_gap", check_names)
        self.assertIn("command_copied_response_intent_lifecycle_planning", check_names)
        self.assertEqual([], report["blockers"])
        for check in report["checks"]:
            self.assertTrue(check["valid"], check)
            self.assertEqual([], check["public_or_runtime_claims"], check)
            self.assertEqual(check["expected_schema"], check["report_schema"], check)

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

    def test_critical_path_phase_accepts_identity_runtime_and_contract_blockers(self) -> None:
        phase = {
            "current_surface": "obelisk.player_identity.v1",
            "current_blocker": "approved_runtime_evidence_missing",
            "source_checker_schema": "obelisk.player-identity-first-evidence-readiness.v1",
            "source_checker_parse_error": None,
            "permissions_admin_unlocked": False,
            "command_response_unlocked": False,
            "commands_replies_unlocked": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "public_abi_ready": False,
            "runtime_ready": False,
        }
        self.assertEqual([], ROUTE_GATE.validate_critical_path_phase(phase))

        phase["current_blocker"] = "identity_public_contract_gate_missing"
        self.assertEqual([], ROUTE_GATE.validate_critical_path_phase(phase))

        phase["current_blocker"] = "identity_public_contract_gate"
        self.assertEqual([], ROUTE_GATE.validate_critical_path_phase(phase))

    def test_critical_path_phase_rejects_unlocked_commands_or_unknown_blocker(self) -> None:
        phase = {
            "current_surface": "obelisk.player_identity.v1",
            "current_blocker": "unexpected",
            "source_checker_schema": "obelisk.player-identity-first-evidence-readiness.v1",
            "source_checker_parse_error": None,
            "permissions_admin_unlocked": False,
            "command_response_unlocked": False,
            "commands_replies_unlocked": True,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "public_abi_ready": False,
            "runtime_ready": False,
        }
        blockers = ROUTE_GATE.validate_critical_path_phase(phase)
        self.assertIn("critical_path_identity_gate_unexpected_blocker", blockers)
        self.assertIn("critical_path_commands_replies_unlocked_must_stay_false", blockers)

    def test_critical_path_phase_rejects_unparsable_or_schema_drifted_identity_readiness(self) -> None:
        phase = {
            "current_surface": "obelisk.player_identity.v1",
            "current_blocker": "approved_runtime_evidence_missing",
            "source_checker_schema": "wrong-schema",
            "source_checker_parse_error": "stdout_json_decode_error: broken",
            "permissions_admin_unlocked": False,
            "command_response_unlocked": False,
            "commands_replies_unlocked": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "public_abi_ready": False,
            "runtime_ready": False,
        }

        blockers = ROUTE_GATE.validate_critical_path_phase(phase)

        self.assertIn("critical_path_identity_readiness_schema_mismatch", blockers)
        self.assertIn("critical_path_identity_readiness_output_invalid", blockers)

    def test_route_check_rejects_schema_drift_even_when_otherwise_valid(self) -> None:
        original = ROUTE_GATE.run_check

        def fake_run_check(name: str, argv: list[str]) -> dict[str, object]:
            result = original(name, argv)
            if name == "permissions_query_failclosed":
                result["report_schema"] = "obelisk.permissions-admin-query-failclosed-contract-check.v999"
                result["valid"] = True
            return result

        args = SimpleNamespace(
            query_failclosed_artifact=ROUTE_GATE.DEFAULT_QUERY_CONTRACT,
            player_identity_decisions=ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_DECISIONS,
            public_sdk_surfaces=ROUTE_GATE.DEFAULT_PUBLIC_SDK_SURFACES,
            player_identity_private_candidate_contract=ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_PRIVATE_CANDIDATE,
            public_header=ROUTE_GATE.DEFAULT_PUBLIC_HEADER,
            command_response_root=None,
            command_response_readiness=None,
            json=True,
        )
        try:
            ROUTE_GATE.run_check = fake_run_check
            report = ROUTE_GATE.build_report(args)
        finally:
            ROUTE_GATE.run_check = original

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn(
            "permissions_query_failclosed: schema mismatch "
            "'obelisk.permissions-admin-query-failclosed-contract-check.v999' != "
            "'obelisk.permissions-admin-query-failclosed-contract-check.v1'",
            report["blockers"],
        )

    def test_route_check_rejects_public_command_reply_alias_claims(self) -> None:
        original = ROUTE_GATE.run_check

        def fake_run_check(name: str, argv: list[str]) -> dict[str, object]:
            result = original(name, argv)
            if name == "commands_replies_public_readiness":
                result["valid"] = False
                result["public_or_runtime_claims"] = [
                    "public_command_router_allowed",
                    "public_reply_or_send_chat_abi_allowed",
                ]
            return result

        args = SimpleNamespace(
            query_failclosed_artifact=ROUTE_GATE.DEFAULT_QUERY_CONTRACT,
            player_identity_decisions=ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_DECISIONS,
            public_sdk_surfaces=ROUTE_GATE.DEFAULT_PUBLIC_SDK_SURFACES,
            player_identity_private_candidate_contract=ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_PRIVATE_CANDIDATE,
            public_header=ROUTE_GATE.DEFAULT_PUBLIC_HEADER,
            command_response_root=None,
            command_response_readiness=None,
            json=True,
        )
        try:
            ROUTE_GATE.run_check = fake_run_check
            report = ROUTE_GATE.build_report(args)
        finally:
            ROUTE_GATE.run_check = original

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn(
            "commands_replies_public_readiness: unexpected public/runtime claim: "
            "public_command_router_allowed, public_reply_or_send_chat_abi_allowed",
            report["blockers"],
        )

    def test_run_check_recursively_rejects_subreport_public_alias_and_text_claims(self) -> None:
        original_run = ROUTE_GATE.subprocess.run

        def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
            report = {
                "schema": ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS["commands_replies_public_readiness"],
                "valid": True,
                "nested": {
                    "public_reply_abi_allowed": True,
                    "public_send_chat_abi_allowed": True,
                    "reply_send_chat_router_claims_allowed": True,
                    "public_abi_allowed": True,
                    "permissions_admin_ready": True,
                    "notes": [
                        "send-chat ABI is public and ready",
                        "command routing is public and ready",
                        "permissions/admin is public and ready",
                        "replies API is public and ready",
                    ],
                },
            }
            return subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=json.dumps(report),
                stderr="",
            )

        try:
            ROUTE_GATE.subprocess.run = fake_run
            result = ROUTE_GATE.run_check("commands_replies_public_readiness", ["unused.py", "--json"])
        finally:
            ROUTE_GATE.subprocess.run = original_run

        self.assertFalse(result["valid"])
        self.assertIn("nested.public_reply_abi_allowed", result["public_or_runtime_claims"])
        self.assertIn("nested.public_send_chat_abi_allowed", result["public_or_runtime_claims"])
        self.assertIn("nested.reply_send_chat_router_claims_allowed", result["public_or_runtime_claims"])
        self.assertIn("nested.public_abi_allowed", result["public_or_runtime_claims"])
        self.assertIn("nested.permissions_admin_ready", result["public_or_runtime_claims"])
        self.assertIn("nested.notes[0]:positive_text_claim", result["public_or_runtime_claims"])
        self.assertIn("nested.notes[1]:positive_text_claim", result["public_or_runtime_claims"])
        self.assertIn("nested.notes[2]:positive_text_claim", result["public_or_runtime_claims"])
        self.assertIn("nested.notes[3]:positive_text_claim", result["public_or_runtime_claims"])


if __name__ == "__main__":
    unittest.main()
