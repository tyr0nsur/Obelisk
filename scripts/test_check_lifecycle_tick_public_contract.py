#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "scripts" / "check_lifecycle_tick_public_contract.py"
LIFECYCLE_DECISIONS = ROOT / "docs" / "lifecycle_ops_recovery_public_contract_decisions.json"
TICK_DECISIONS = ROOT / "docs" / "gameplay_tick_callbacks_public_contract_decisions.json"
SURFACES = ROOT / "docs" / "public_sdk_surfaces.json"
HEADER = ROOT / "include" / "obelisk" / "ObeliskApi.h"

SPEC = importlib.util.spec_from_file_location("lifecycle_tick_checker", CHECKER_PATH)
assert SPEC is not None
checker = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(checker)


class LifecycleTickPublicContractTests(unittest.TestCase):
    def run_checker(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CHECKER_PATH), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def load_lifecycle(self) -> dict:
        return json.loads(LIFECYCLE_DECISIONS.read_text(encoding="utf-8"))

    def load_tick(self) -> dict:
        return json.loads(TICK_DECISIONS.read_text(encoding="utf-8"))

    def load_surfaces(self) -> dict:
        return json.loads(SURFACES.read_text(encoding="utf-8"))

    def test_default_contracts_pass_candidate_only_consume_mode(self) -> None:
        result = self.run_checker("--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"])
        self.assertTrue(report["candidate_only"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertEqual(
            report["surfaces"],
            [
                "obelisk.lifecycle_ops_recovery.v1",
                "obelisk.gameplay_tick_callbacks.v1",
            ],
        )

    def test_fail_closed_readiness_flags(self) -> None:
        for flag in ("--promote", "--public-readiness", "--runtime-readiness"):
            with self.subTest(flag=flag):
                result = self.run_checker(flag)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("fail-closed", result.stderr)

    def test_lifecycle_decision_blocks_public_ops_recovery_opening(self) -> None:
        payload = self.load_lifecycle()
        payload["public_header_allowed"] = True
        payload["public_header_symbols_now"] = ["ObeliskPluginWatchdog"]
        payload["public_capability_bits_now"] = ["OBELISK_API_CAPABILITY_PLUGIN_WATCHDOG"]
        payload["public_ops_api_now"] = ["RegisterOperatorReloadWithOwnerTokenHandle"]
        payload["forbidden_public_contract"].remove("server recovery API")
        payload["required_before_public_header"][0]["status"] = "resolved"
        payload["separation_contract"]["not_satisfied_by_foundation"].remove("restart-state recovery API")

        errors = checker.validate_decisions(
            payload,
            label="lifecycle decisions",
            schema="obelisk.lifecycle-ops-recovery-public-contract-decisions.v1",
            surface="obelisk.lifecycle_ops_recovery.v1",
            required_ids=checker.LIFECYCLE_REQUIRED_IDS,
            forbidden_terms=checker.LIFECYCLE_FORBIDDEN,
            separation_key="separation_contract",
            separation_source_key="promoted_foundation_surface",
            separation_source="obelisk.lifecycle_config_logging.v1",
            separation_list_key="not_satisfied_by_foundation",
            extra_empty_lists=("public_ops_api_now",),
        )

        self.assertIn("lifecycle decisions: public_header_allowed must remain false", errors)
        self.assertIn("lifecycle decisions: public_header_symbols_now must remain an empty list", errors)
        self.assertIn("lifecycle decisions: public_capability_bits_now must remain an empty list", errors)
        self.assertIn("lifecycle decisions: public_ops_api_now must remain an empty list", errors)
        self.assertTrue(any("forbidden_public_contract missing" in error for error in errors), errors)
        self.assertTrue(any("is resolved before promotion" in error for error in errors), errors)
        self.assertTrue(any("not_satisfied_by_foundation missing" in error for error in errors), errors)

    def test_tick_decision_blocks_treating_timers_as_gameplay_ticks(self) -> None:
        payload = self.load_tick()
        payload["public_callback_abi_now"] = ["ObeliskGameplayTickCallback"]
        payload["forbidden_public_contract"].remove("server tick callback API")
        payload["separation_contract"]["promoted_timer_surface"] = "obelisk.gameplay_tick_callbacks.v1"
        payload["required_before_public_header"] = [
            item
            for item in payload["required_before_public_header"]
            if item["id"] != "separation.process_local_timers_not_gameplay_tick"
        ]

        errors = checker.validate_decisions(
            payload,
            label="tick decisions",
            schema="obelisk.gameplay-tick-callbacks-public-contract-decisions.v1",
            surface="obelisk.gameplay_tick_callbacks.v1",
            required_ids=checker.TICK_REQUIRED_IDS,
            forbidden_terms=checker.TICK_FORBIDDEN,
            separation_key="separation_contract",
            separation_source_key="promoted_timer_surface",
            separation_source="obelisk.process_local_timers.v1",
            separation_list_key="not_satisfied_by_process_local_timers",
        )

        self.assertIn("tick decisions: public_callback_abi_now must remain an empty list", errors)
        self.assertTrue(any("forbidden_public_contract missing" in error for error in errors), errors)
        self.assertTrue(any("required_before_public_header ids mismatch" in error for error in errors), errors)
        self.assertIn(
            "tick decisions: separation_contract.promoted_timer_surface must be obelisk.process_local_timers.v1",
            errors,
        )

    def test_surfaces_manifest_keeps_foundation_and_timers_separate(self) -> None:
        manifest = self.load_surfaces()
        surfaces = {surface["id"]: surface for surface in manifest["surfaces"]}
        surfaces["obelisk.lifecycle_ops_recovery.v1"]["public_contract"] = ["ObeliskPluginWatchdog"]
        surfaces["obelisk.lifecycle_config_logging.v1"]["exclusions"].remove("server recovery API")
        surfaces["obelisk.gameplay_tick_callbacks.v1"]["status"] = "promoted"
        surfaces["obelisk.process_local_timers.v1"]["exclusions"].remove("server tick callbacks")

        errors = checker.validate_surfaces(manifest)

        self.assertIn(
            "surfaces: obelisk.lifecycle_ops_recovery.v1 public_contract must remain empty",
            errors,
        )
        self.assertIn(
            "surfaces: obelisk.gameplay_tick_callbacks.v1 status must remain post-v1",
            errors,
        )
        self.assertTrue(any("lifecycle foundation exclusions missing" in error for error in errors), errors)
        self.assertTrue(any("timer exclusions missing" in error for error in errors), errors)

    def test_header_rejects_blocked_public_symbols(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            header = Path(tmp) / "ObeliskApi.h"
            header.write_text(
                "#pragma once\n"
                "typedef struct ObeliskPluginWatchdog { unsigned abi_version; } ObeliskPluginWatchdog;\n"
                "typedef void (*ObeliskGameplayTickCallback)(void* userData);\n"
                "#define OBELISK_API_CAPABILITY_SERVER_TICK 0x10000000u\n",
                encoding="utf-8",
            )

            errors = checker.validate_header(header)

        self.assertTrue(any("obelisk.lifecycle_ops_recovery.v1" in error for error in errors), errors)
        self.assertTrue(any("obelisk.gameplay_tick_callbacks.v1" in error for error in errors), errors)

    def test_json_output_reports_errors_for_temp_files(self) -> None:
        lifecycle = self.load_lifecycle()
        lifecycle["public_header_allowed"] = True
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lifecycle_path = root / "lifecycle.json"
            tick_path = root / "tick.json"
            surfaces_path = root / "surfaces.json"
            lifecycle_path.write_text(json.dumps(lifecycle), encoding="utf-8")
            tick_path.write_text(TICK_DECISIONS.read_text(encoding="utf-8"), encoding="utf-8")
            surfaces_path.write_text(SURFACES.read_text(encoding="utf-8"), encoding="utf-8")

            result = self.run_checker(
                "--lifecycle-decisions",
                str(lifecycle_path),
                "--tick-decisions",
                str(tick_path),
                "--surfaces",
                str(surfaces_path),
                "--json",
            )

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        self.assertIn("lifecycle decisions: public_header_allowed must remain false", report["errors"])


if __name__ == "__main__":
    unittest.main()
