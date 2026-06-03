#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "scripts" / "check_player_services_economy_mobility_public_contract.py"
CONTRACT_PATH = ROOT / "docs" / "player_services_economy_mobility_public_contract_decisions.json"

SPEC = importlib.util.spec_from_file_location("player_services_contract_checker", CHECKER_PATH)
assert SPEC is not None
checker = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(checker)


class PlayerServicesEconomyMobilityPublicContractTests(unittest.TestCase):
    def load_valid_contract(self) -> dict:
        return checker.load_contract(CONTRACT_PATH)

    def run_checker(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CHECKER_PATH), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_default_contract_passes(self) -> None:
        result = self.run_checker()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("candidate-only contract valid", result.stdout)

    def test_fail_closed_readiness_flags(self) -> None:
        for flag in ("--promote", "--public-readiness", "--runtime-readiness"):
            with self.subTest(flag=flag):
                result = self.run_checker(flag)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("fail-closed", result.stderr)

    def test_public_and_runtime_gates_must_remain_false(self) -> None:
        contract = self.load_valid_contract()
        contract["status"] = "ready"
        contract["public_header_allowed"] = True
        contract["public_contract_allowed"] = True
        contract["public_sdk_ready"] = True
        contract["public_abi_ready"] = True
        contract["promotion_ready"] = True
        contract["runtime_ready"] = True
        contract["runtime_services"] = True
        contract["promotion"]["public_sdk"] = True
        contract["promotion"]["runtime"] = True

        errors = checker.validate_contract(contract)

        self.assertIn("status must remain offline_internal_contract", errors)
        self.assertIn("public_header_allowed must remain false", errors)
        self.assertIn("public_contract_allowed must remain false", errors)
        self.assertIn("public_sdk_ready must remain false", errors)
        self.assertIn("public_abi_ready must remain false", errors)
        self.assertIn("promotion_ready must remain false", errors)
        self.assertIn("runtime_ready must remain false", errors)
        self.assertIn("runtime_services must remain false", errors)
        self.assertIn("promotion.public_sdk must remain false", errors)
        self.assertIn("promotion.runtime must remain false", errors)

    def test_required_dependencies_controls_and_audit_units_are_enforced(self) -> None:
        contract = self.load_valid_contract()
        contract["dependencies"] = [
            dependency
            for dependency in contract["dependencies"]
            if dependency["id"] != "obelisk.permissions_admin.v1"
        ]
        contract["required_control_gates"] = [
            control for control in contract["required_control_gates"] if control["id"] != "rollback"
        ]
        contract["audit_units"] = [
            unit for unit in contract["audit_units"] if unit["id"] != "timed_notices"
        ]
        contract["audit_units"][0]["blocked_until_controls"].remove("abuse")
        contract["audit_units"][1]["blocked_until_controls"].append("player_location_ready")
        contract["audit_units"][0]["forbidden_public_contract"].remove("shop API")
        contract["audit_units"][2]["forbidden_public_contract"].remove("area membership API")

        errors = checker.validate_contract(contract)

        self.assertIn("missing required dependency: obelisk.permissions_admin.v1", errors)
        self.assertIn("missing required control gate: rollback", errors)
        self.assertIn("missing required audit unit: timed_notices", errors)
        self.assertIn("economy.blocked_until_controls missing abuse", errors)
        self.assertIn("mobility.blocked_until_controls unexpected player_location_ready", errors)
        self.assertIn("economy.forbidden_public_contract missing shop API", errors)
        self.assertIn("areas.forbidden_public_contract missing area membership API", errors)

    def test_command_response_dependency_is_required_for_player_facing_notices(self) -> None:
        contract = self.load_valid_contract()
        contract["dependencies"] = [
            dependency
            for dependency in contract["dependencies"]
            if dependency["id"] != "obelisk.command_chat_response_path.v1"
        ]
        contract["required_control_gates"] = [
            control
            for control in contract["required_control_gates"]
            if control["id"] != "command_chat_response_path"
        ]
        contract["audit_units"][-1]["blocked_until_controls"].remove("command_chat_response_path")

        errors = checker.validate_contract(contract)

        self.assertIn("missing required dependency: obelisk.command_chat_response_path.v1", errors)
        self.assertIn("missing required control gate: command_chat_response_path", errors)
        self.assertIn("timed_notices.blocked_until_controls missing command_chat_response_path", errors)

    def test_dependencies_and_controls_must_remain_unresolved(self) -> None:
        contract = self.load_valid_contract()
        contract["dependencies"][0]["status"] = "promoted"
        contract["required_control_gates"][0]["status"] = "ready"
        contract["required_control_gates"][1]["must_exist_before_promotion"] = False

        errors = checker.validate_contract(contract)

        self.assertIn("obelisk.player_identity.v1.status must remain unresolved", errors)
        self.assertIn("identity.status must remain unresolved", errors)
        self.assertIn("permissions_admin.must_exist_before_promotion must be true", errors)

    def test_rejects_public_surface_overclaims_outside_negative_context(self) -> None:
        contract = self.load_valid_contract()
        contract["notes"] = ["teleport public API is available"]
        contract["audit_units"][0]["forbidden_public_contract"].append("balance API")

        errors = checker.validate_contract(contract)

        self.assertTrue(
            any("public surface overclaim 'teleport'" in error for error in errors),
            errors,
        )
        self.assertFalse(
            any("public surface overclaim 'balance'" in error for error in errors),
            errors,
        )

    def test_required_non_claims_preserve_non_promotional_boundary(self) -> None:
        contract = self.load_valid_contract()
        contract["non_claims"] = [
            item
            for item in contract["non_claims"]
            if not item.startswith("identity, permissions/admin, command/chat response path")
        ]

        errors = checker.validate_contract(contract)

        self.assertTrue(
            any(
                error.startswith(
                    "non_claims missing identity, permissions/admin, command/chat response path"
                )
                for error in errors
            ),
            errors,
        )

    def test_non_claims_reject_affirmative_availability_wording(self) -> None:
        contract = self.load_valid_contract()
        contract["non_claims"].append("umbrella planning lane available")

        errors = checker.validate_contract(contract)

        self.assertIn("non_claims[4] must use explicit non-claim or blocking wording", errors)
        self.assertIn("non_claims[4] contains affirmative availability term 'available'", errors)

    def test_json_output_reports_errors(self) -> None:
        contract = self.load_valid_contract()
        contract["runtime_services"] = True
        with tempfile.TemporaryDirectory() as tempdir:
            path = pathlib.Path(tempdir) / "contract.json"
            path.write_text(json.dumps(contract), encoding="utf-8")
            result = self.run_checker("--contract", str(path), "--json")

        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertIn("runtime_services must remain false", payload["errors"])


if __name__ == "__main__":
    unittest.main()
