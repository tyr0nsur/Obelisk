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
CHECKER_PATH = ROOT / "scripts" / "check_operator_ingress_storage_offline_contract.py"
CONTRACT_PATH = ROOT / "docs" / "operator_ingress_storage_public_contract_decisions.json"

SPEC = importlib.util.spec_from_file_location("offline_contract_checker", CHECKER_PATH)
assert SPEC is not None
checker = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(checker)


class OperatorIngressStorageOfflineContractTests(unittest.TestCase):
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
        self.assertIn("offline contract valid", result.stdout)

    def test_fail_closed_readiness_flags(self) -> None:
        for flag in ("--promote", "--public-readiness", "--runtime-readiness"):
            with self.subTest(flag=flag):
                result = self.run_checker(flag)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("fail-closed", result.stderr)

    def test_public_and_runtime_gates_must_remain_false(self) -> None:
        contract = self.load_valid_contract()
        contract["public_header_allowed"] = True
        contract["public_sdk_ready"] = True
        contract["public_abi_ready"] = True
        contract["promotion_ready"] = True
        contract["runtime_ready"] = True
        contract["runtime_services"] = True
        contract["promotion"]["public_sdk"] = True
        contract["promotion"]["runtime"] = True

        errors = checker.validate_contract(contract)

        self.assertIn("public_header_allowed must remain false", errors)
        self.assertIn("public_sdk_ready must remain false", errors)
        self.assertIn("public_abi_ready must remain false", errors)
        self.assertIn("promotion_ready must remain false", errors)
        self.assertIn("runtime_ready must remain false", errors)
        self.assertIn("runtime_services must remain false", errors)
        self.assertIn("promotion.public_sdk must remain false", errors)
        self.assertIn("promotion.runtime must remain false", errors)

    def test_required_lanes_and_lane_checks_are_enforced(self) -> None:
        contract = self.load_valid_contract()
        contract["lanes"] = [
            lane for lane in contract["lanes"] if lane["id"] != "queue_lifecycle"
        ]
        contract["lanes"].append(
            {
                "id": "unexpected_lane",
                "mode": "offline_contract_only",
                "runtime_required": False,
                "public_surface": False,
                "required_checks": [],
            }
        )
        contract["lanes"][0]["required_checks"].remove("offline_only")
        contract["lanes"][0]["required_fields"].remove("candidate_ingress_transport")
        contract["lanes"][1]["decision_required"] = ""

        errors = checker.validate_contract(contract)

        self.assertIn("missing required lane: queue_lifecycle", errors)
        self.assertIn("unexpected lane: unexpected_lane", errors)
        self.assertIn("ingress.required_checks missing offline_only", errors)
        self.assertIn(
            "ingress.required_fields missing candidate_ingress_transport",
            errors,
        )
        self.assertIn(
            "storage_migration.decision_required must be a non-empty string",
            errors,
        )

    def test_rejected_secret_classes_allowed_only_as_required_field(self) -> None:
        contract = self.load_valid_contract()
        self.assertIn("rejected_secret_classes", contract["lanes"][0]["required_fields"])
        self.assertEqual(checker.validate_contract(contract), [])

        contract = self.load_valid_contract()
        contract["lanes"][0]["label"] = "rejected_secret_classes"
        errors = checker.validate_contract(contract)

        self.assertTrue(
            any(
                "only allowed as a required rejection/classification field" in error
                for error in errors
            ),
            errors,
        )

        contract = self.load_valid_contract()
        contract["lanes"][0]["rejected_secret_classes"] = []
        errors = checker.validate_contract(contract)

        self.assertTrue(
            any(
                "only allowed as a required rejection/classification field" in error
                for error in errors
            ),
            errors,
        )

    def test_rejects_prohibited_claims(self) -> None:
        prohibited_values = [
            "secret",
            "RCON",
            "webhook",
            "db",
            "database",
            "secret-manager",
            "API",
            "runtime ready",
            "public ABI",
            "v1 completion",
            "v1_completion_required",
        ]
        for value in prohibited_values:
            with self.subTest(value=value):
                contract = self.load_valid_contract()
                contract["lanes"][0]["label"] = value
                errors = checker.validate_contract(contract)
                self.assertTrue(
                    any("prohibited claim" in error for error in errors),
                    errors,
                )

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
