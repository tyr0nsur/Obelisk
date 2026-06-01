#!/usr/bin/env python3
"""Tests for check_inventory_action_fixture_boundary.py."""

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
SCRIPT = SCRIPT_DIR / "check_inventory_action_fixture_boundary.py"
sys.path.insert(0, str(SCRIPT_DIR))

import check_inventory_action_fixture_boundary as checker


class CheckInventoryActionFixtureBoundaryTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def test_fixture_boundary_is_candidate_only_and_complete(self) -> None:
        result = self.run_checker("--json")
        payload = json.loads(result.stdout)

        self.assertEqual("obelisk.inventory-action-fixture-boundary-check.v1", payload["schema"])
        self.assertTrue(payload["ready"])
        self.assertTrue(payload["fixture_only"])
        self.assertFalse(payload["public_inventory_sdk_ready"])
        self.assertFalse(payload["inventory_action_sdk_ready"])
        self.assertFalse(payload["lookup_ready"])
        self.assertFalse(payload["mutation_ready"])
        self.assertFalse(payload["resource_handle_ready"])
        self.assertFalse(payload["return_override_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["promotion_ready"])
        self.assertEqual([], payload["blockers"])

        summary = payload["summary"]
        self.assertEqual(2, summary["signature_count"])
        self.assertEqual("complete", summary["target_set_coverage_status"])
        self.assertEqual("candidate_only", summary["artifact_status"])
        self.assertFalse(summary["promotion_ready"])
        self.assertEqual({"integer": 1}, summary["copied_scalar_by_kind"])
        self.assertEqual({"object_ref": 3, "struct": 2}, summary["redacted_by_reason"])
        self.assertEqual(
            ["ShooterPlayerController.ServerRequestInventoryUseItemWithActor.AdditionalData"],
            summary["copied_integer_fields"],
        )
        self.assertEqual(
            [
                "ShooterPlayerController.ServerRequestInventoryUseItem.ItemId",
                "ShooterPlayerController.ServerRequestInventoryUseItemWithActor.ItemID1",
            ],
            summary["redacted_struct_fields"],
        )
        self.assertEqual([], payload["public_contract_scan"]["offenders"])
        surface_summary = payload["public_contract_scan"]["surface_summary"]
        self.assertEqual(
            "promoted-experimental-only",
            surface_summary["obelisk.inventory_item_copied_signals.v1"]["status"],
        )
        self.assertEqual(5, surface_summary["obelisk.inventory_item_copied_signals.v1"]["public_contract_count"])
        self.assertEqual(5, surface_summary["obelisk.inventory_item_copied_signals.v1"]["payload_contract_count"])
        self.assertEqual("post-v1", surface_summary["obelisk.inventory_items_mutation.v1"]["status"])
        self.assertEqual(0, surface_summary["obelisk.inventory_items_mutation.v1"]["public_contract_count"])
        self.assertEqual(0, surface_summary["obelisk.inventory_items_mutation.v1"]["payload_contract_count"])
        self.assertTrue(
            surface_summary["obelisk.inventory_items_mutation.v1"][
                "must_remain_without_public_contract_until_promotion"
            ]
        )

    def test_mutated_fixture_counts_fail_closed(self) -> None:
        report = checker.build_fixture_report()
        mutated = copy.deepcopy(report)
        mutated["signature_count"] = 3
        mutated["target_set_coverage"]["status"] = "partial"
        mutated["safety_summary"]["promotion_ready"] = True
        mutated["safety_summary"]["copied_scalar_by_kind"] = {"integer": 2}
        mutated["safety_summary"]["redacted_by_reason"] = {"object_ref": 3, "struct": 1}

        blockers: list[dict] = []
        checker.validate_report(mutated, blockers)
        reasons = {blocker["reason"] for blocker in blockers}

        self.assertIn("signature_count_mismatch", reasons)
        self.assertIn("target_set_coverage_status_mismatch", reasons)
        self.assertIn("safety_value_mismatch", reasons)
        self.assertIn("copied_scalar_by_kind_mismatch", reasons)
        self.assertIn("redacted_by_reason_mismatch", reasons)

    def test_item_action_fields_crossing_public_contract_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest.write_text(
                json.dumps(
                    {
                        "surfaces": [
                            {
                                "id": "obelisk.inventory_item_copied_signals.v1",
                                "status": "promoted-experimental-only",
                                "public_contract": checker.EXPECTED_INVENTORY_COPIED_PUBLIC_CONTRACT,
                                "payload_contract": checker.EXPECTED_INVENTORY_COPIED_PAYLOAD_CONTRACT,
                                "exclusions": list(checker.REQUIRED_INVENTORY_COPIED_EXCLUSIONS),
                            },
                            {
                                "id": "obelisk.inventory_items_mutation.v1",
                                "status": "post-v1",
                                "public_contract": [],
                                "payload_contract": [],
                                "exclusions": list(checker.REQUIRED_INVENTORY_MUTATION_EXCLUSIONS),
                                "v1_decision_contract": {
                                    "current_decision": "blocked_until_promoted_or_explicitly_excluded",
                                    "must_remain_without_public_contract_until_promotion": True,
                                    "exclusion_requires": [
                                        "the v1 release statement states that no Inventory SDK, Items SDK, give item API, remove item API, kits/rewards API, engram/progression API, inventory lookup, item handles, item mutation, return override, or ResourceHandle API is included in v1"
                                    ],
                                },
                            },
                            {
                                "id": "synthetic.inventory",
                                "public_contract": ["ItemId"],
                                "payload_contract": ["AdditionalData"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            result = self.run_checker("--public-sdk-surfaces", str(manifest), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        self.assertIn("inventory_action_public_contract_leak", {b["reason"] for b in payload["blockers"]})
        offenders = payload["public_contract_scan"]["offenders"]
        self.assertEqual(
            {("public_contract", "ItemId"), ("payload_contract", "AdditionalData")},
            {(offender["field"], offender["token"]) for offender in offenders},
        )

    def test_public_inventory_surface_status_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest.write_text(
                json.dumps(
                    {
                        "surfaces": [
                            {
                                "id": "obelisk.inventory_item_copied_signals.v1",
                                "status": "promoted",
                                "public_contract": checker.EXPECTED_INVENTORY_COPIED_PUBLIC_CONTRACT,
                                "payload_contract": ["broader copied payload contract"],
                                "exclusions": ["Inventory SDK"],
                            },
                            {
                                "id": "obelisk.inventory_items_mutation.v1",
                                "status": "promoted",
                                "public_contract": ["GiveItem"],
                                "payload_contract": ["mutation payload"],
                                "exclusions": ["Inventory SDK"],
                                "v1_decision_contract": {
                                    "current_decision": "promoted",
                                    "must_remain_without_public_contract_until_promotion": False,
                                    "exclusion_requires": ["Inventory SDK"],
                                },
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            result = self.run_checker("--public-sdk-surfaces", str(manifest), check=False)

        payload = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("inventory_copied_signals_status_mismatch", reasons)
        self.assertIn("inventory_copied_signals_payload_contract_mismatch", reasons)
        self.assertIn("inventory_copied_signals_exclusions_incomplete", reasons)
        self.assertIn("inventory_mutation_status_mismatch", reasons)
        self.assertIn("inventory_mutation_public_contract_present", reasons)
        self.assertIn("inventory_mutation_payload_contract_present", reasons)
        self.assertIn("inventory_mutation_exclusions_incomplete", reasons)
        self.assertIn("inventory_mutation_v1_decision_current_decision_mismatch", reasons)
        self.assertIn("inventory_mutation_v1_decision_public_contract_guard_missing", reasons)
        self.assertIn("inventory_mutation_v1_decision_exclusion_requires_incomplete", reasons)

    def test_inventory_mutation_v1_decision_contract_mutations_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest.write_text(
                json.dumps(
                    {
                        "surfaces": [
                            {
                                "id": "obelisk.inventory_item_copied_signals.v1",
                                "status": "promoted-experimental-only",
                                "public_contract": checker.EXPECTED_INVENTORY_COPIED_PUBLIC_CONTRACT,
                                "payload_contract": checker.EXPECTED_INVENTORY_COPIED_PAYLOAD_CONTRACT,
                                "exclusions": list(checker.REQUIRED_INVENTORY_COPIED_EXCLUSIONS),
                            },
                            {
                                "id": "obelisk.inventory_items_mutation.v1",
                                "status": "post-v1",
                                "public_contract": [],
                                "payload_contract": [],
                                "exclusions": list(checker.REQUIRED_INVENTORY_MUTATION_EXCLUSIONS),
                                "v1_decision_contract": {
                                    "current_decision": "blocked_until_promoted_or_explicitly_excluded",
                                    "must_remain_without_public_contract_until_promotion": False,
                                    "exclusion_requires": [
                                        "the v1 release statement states that no Inventory SDK is included in v1"
                                    ],
                                },
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            result = self.run_checker("--public-sdk-surfaces", str(manifest), check=False)

        payload = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("inventory_mutation_v1_decision_public_contract_guard_missing", reasons)
        self.assertIn("inventory_mutation_v1_decision_exclusion_requires_incomplete", reasons)

    def test_item_id_and_additional_data_redaction_mutations_fail_closed(self) -> None:
        report = checker.build_fixture_report()
        mutated = copy.deepcopy(report)
        use_item = mutated["signatures"][0]["params"][1]
        use_item["type"] = "int32"
        with_actor = mutated["signatures"][1]["params"][3]
        with_actor["redaction"] = "public scalar contract"

        blockers: list[dict] = []
        checker.validate_report(mutated, blockers)
        reasons = {blocker["reason"] for blocker in blockers}

        self.assertIn("param_type_mismatch", reasons)
        self.assertIn("copied_scalar_redaction_mismatch", reasons)

    def test_function_and_param_shape_drift_fails_closed(self) -> None:
        report = checker.build_fixture_report()
        mutated = copy.deepcopy(report)
        mutated["signatures"][0]["function_flags"] = "0x0"
        mutated["signatures"][0]["num_parms"] = 3
        mutated["signatures"][0]["params"][1]["offset"] = 16
        mutated["signatures"][1]["params"][3]["element_size"] = 8
        mutated["signatures"][1]["params"][3]["property_flags"] = "0x0"

        blockers: list[dict] = []
        checker.validate_report(mutated, blockers)
        reasons = [blocker["reason"] for blocker in blockers]

        self.assertIn("function_shape_mismatch", reasons)
        self.assertGreaterEqual(reasons.count("param_shape_mismatch"), 3)

    def test_object_reference_redaction_mutation_fails_closed(self) -> None:
        report = checker.build_fixture_report()
        mutated = copy.deepcopy(report)
        inventory_comp = mutated["signatures"][0]["params"][0]
        inventory_comp["redaction"] = "public object reference"

        blockers: list[dict] = []
        checker.validate_report(mutated, blockers)
        reasons = {blocker["reason"] for blocker in blockers}

        self.assertIn("redacted_object_ref_redaction_mismatch", reasons)


if __name__ == "__main__":
    unittest.main()
