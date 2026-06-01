#!/usr/bin/env python3
"""Tests for check_inventory_action_redacted_observer_gate.py."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_inventory_action_redacted_observer_gate.py"
sys.path.insert(0, str(SCRIPT_DIR))

import check_inventory_action_fixture_boundary as fixture_boundary
import check_inventory_action_redacted_observer_gate as checker


SUPPORTED_SHA = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
REQUIRED_GATE_ARGS = [
    "--gate-enabled",
    "--observer-profile",
    "observer-debug",
    "--marker",
    "allow-observer-debug-window",
    "--marker",
    "allow-experimental-observers",
    "--marker",
    "enable-inventory-action-redacted-observer",
    "--marker",
    "enable-process-event-hook",
    "--marker",
    "disable-plugins",
    "--ark-binary-sha256",
    SUPPORTED_SHA,
    "--fname-index",
    "2651",
    "--dispatch-budget",
    "0",
]


class CheckInventoryActionRedactedObserverGateTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def test_candidate_gate_accepts_exact_fixture_shape_without_runtime_promotion(self) -> None:
        result = self.run_checker("--json", *REQUIRED_GATE_ARGS)
        payload = json.loads(result.stdout)

        self.assertEqual("obelisk.inventory-action-redacted-observer-gate-check.v1", payload["schema"])
        self.assertTrue(payload["ready"])
        self.assertEqual("accepted_candidate_offline_gate", payload["status"])
        self.assertTrue(payload["candidate_only"])
        self.assertTrue(payload["fixture_only"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["public_inventory_sdk_ready"])
        self.assertFalse(payload["inventory_action_sdk_ready"])
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["dispatch_ready"])
        self.assertEqual([], payload["blockers"])

        self.assertEqual("inventory-action-compact-intake", payload["target_set"])
        self.assertEqual(list(fixture_boundary.EXPECTED_TARGETS), payload["expected_targets"])
        self.assertEqual([2651, 2652], payload["gate"]["allowed_fname_indices"])
        self.assertEqual(0, payload["gate"]["dispatch_budget"])
        self.assertEqual(
            ["ShooterPlayerController.ServerRequestInventoryUseItemWithActor.AdditionalData"],
            payload["fixture_summary"]["copied_integer_fields"],
        )
        self.assertEqual(
            [
                "ShooterPlayerController.ServerRequestInventoryUseItem.ItemId",
                "ShooterPlayerController.ServerRequestInventoryUseItemWithActor.ItemID1",
            ],
            payload["fixture_summary"]["redacted_struct_fields"],
        )
        self.assertEqual(
            [
                "ShooterPlayerController.ServerRequestInventoryUseItem.InventoryComp",
                "ShooterPlayerController.ServerRequestInventoryUseItemWithActor.anActor",
                "ShooterPlayerController.ServerRequestInventoryUseItemWithActor.InventoryComp",
            ],
            payload["fixture_summary"]["redacted_object_fields"],
        )

    def test_default_invocation_fails_closed_before_any_runtime_window(self) -> None:
        result = self.run_checker("--json", check=False)
        payload = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}

        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        self.assertIn("disabled_gate", reasons)
        self.assertIn("invalid_profile", reasons)
        self.assertIn("missing_marker", reasons)
        self.assertIn("missing_supported_sha", reasons)
        self.assertIn("missing_fname_index", reasons)
        self.assertIn("missing_dispatch_budget", reasons)
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["promotion_ready"])

    def test_missing_marker_fails_closed(self) -> None:
        args = [arg for arg in REQUIRED_GATE_ARGS]
        marker_index = args.index("enable-inventory-action-redacted-observer")
        del args[marker_index - 1 : marker_index + 1]

        result = self.run_checker("--json", *args, check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(1, result.returncode)
        self.assertIn(
            {"reason": "missing_marker", "marker": "enable-inventory-action-redacted-observer"},
            payload["blockers"],
        )

    def test_unsupported_sha_and_non_target_fname_fail_closed(self) -> None:
        args = list(REQUIRED_GATE_ARGS)
        args[args.index(SUPPORTED_SHA)] = "0" * 64
        args[args.index("2651")] = "999999"

        result = self.run_checker("--json", *args, check=False)
        payload = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}

        self.assertEqual(1, result.returncode)
        self.assertIn("unsupported_sha", reasons)
        self.assertIn("non_target_fname", reasons)

    def test_nonzero_dispatch_budget_fails_closed(self) -> None:
        args = list(REQUIRED_GATE_ARGS)
        args[args.index("0")] = "1"

        result = self.run_checker("--json", *args, check=False)
        payload = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}

        self.assertEqual(1, result.returncode)
        self.assertIn("dispatch_budget_not_zero", reasons)

    def test_public_contract_leak_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest.write_text(
                json.dumps(
                    {
                        "surfaces": [
                            {
                                "id": "obelisk.inventory_item_copied_signals.v1",
                                "status": "promoted-experimental-only",
                                "public_contract": fixture_boundary.EXPECTED_INVENTORY_COPIED_PUBLIC_CONTRACT,
                                "payload_contract": fixture_boundary.EXPECTED_INVENTORY_COPIED_PAYLOAD_CONTRACT,
                                "exclusions": list(fixture_boundary.REQUIRED_INVENTORY_COPIED_EXCLUSIONS),
                            },
                            {
                                "id": "obelisk.inventory_items_mutation.v1",
                                "status": "post-v1",
                                "public_contract": [],
                                "payload_contract": [],
                                "exclusions": list(fixture_boundary.REQUIRED_INVENTORY_MUTATION_EXCLUSIONS),
                                "v1_decision_contract": {
                                    "current_decision": "blocked_until_promoted_or_explicitly_excluded",
                                    "must_remain_without_public_contract_until_promotion": True,
                                    "exclusion_requires": [
                                        "the v1 release statement states that no Inventory SDK, Items SDK, "
                                        "give item API, remove item API, kits/rewards API, engram/progression API, "
                                        "inventory lookup, item handles, item mutation, return override, or "
                                        "ResourceHandle API is included in v1"
                                    ],
                                },
                            },
                            {
                                "id": "synthetic.inventory_action",
                                "public_contract": ["ServerRequestInventoryUseItem ItemId"],
                                "payload_contract": ["AdditionalData"],
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            result = self.run_checker(
                "--json",
                "--public-sdk-surfaces",
                str(manifest),
                *REQUIRED_GATE_ARGS,
                check=False,
            )

        payload = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}

        self.assertEqual(1, result.returncode)
        self.assertIn("fixture_boundary_failed", reasons)
        self.assertIn("public_contract_leak", reasons)

    def test_mutated_fixture_boundary_redaction_and_runtime_flags_fail_closed(self) -> None:
        fixture_report = fixture_boundary.build_check(
            fixture_boundary.DEFAULT_SNAPSHOT_ROOT,
            fixture_boundary.PUBLIC_SDK_SURFACES_MANIFEST,
        )
        mutated = copy.deepcopy(fixture_report)
        mutated["summary"]["target_set_coverage_status"] = "partial"
        mutated["summary"]["redacted_struct_fields"] = []
        mutated["summary"]["copied_integer_fields"] = [
            "ShooterPlayerController.ServerRequestInventoryUseItemWithActor.AdditionalData",
            "ShooterPlayerController.ServerRequestInventoryUseItem.ItemId",
        ]
        mutated["runtime_ready"] = True
        mutated["promotion_ready"] = True

        payload = checker.build_check(
            gate_enabled=True,
            observer_profile="observer-debug",
            markers=list(checker.REQUIRED_MARKERS),
            ark_binary_sha256=SUPPORTED_SHA,
            fname_index=2651,
            dispatch_budget=0,
            fixture_report=mutated,
        )
        reasons = {blocker["reason"] for blocker in payload["blockers"]}

        self.assertFalse(payload["ready"])
        self.assertIn("coverage_incomplete", reasons)
        self.assertIn("redaction_contract_mismatch", reasons)
        self.assertIn("scalar_contract_mismatch", reasons)
        self.assertIn("public_or_runtime_flag_promoted", reasons)


if __name__ == "__main__":
    unittest.main()
