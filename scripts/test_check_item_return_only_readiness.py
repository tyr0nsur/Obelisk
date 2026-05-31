#!/usr/bin/env python3
"""Tests for check_item_return_only_readiness.py."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_item_return_only_readiness.py"


class CheckItemReturnOnlyReadinessTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def make_policy(self) -> dict:
        def copied(target: str, offset: str) -> dict:
            return {
                "bool_masks": {"byte_mask": "0x01", "field_mask": "0xff"},
                "copied_field": f"{target}.ReturnValue",
                "direction": "return",
                "element_size": 1,
                "evidence_status": "copied-return-bool-only",
                "field": "ReturnValue",
                "offset": offset,
                "target": target,
                "type": "bool",
            }

        return {
            "schema": "obelisk.item-return-only-policy-slice.v1",
            "input_target_set": "item-compact-intake",
            "output_target_set": "item-return-only-policy-slice",
            "policy_status": "evidence-only",
            "coverage": {
                "status": "complete",
                "input_targets": [
                    "PrimalItem.AllowEquipItem",
                    "PrimalItem.CanRepair",
                    "PrimalItem.CraftBlueprint",
                    "PrimalItem.UseItemOntoItem",
                ],
                "copied_targets": [
                    "PrimalItem.AllowEquipItem",
                    "PrimalItem.CanRepair",
                    "PrimalItem.UseItemOntoItem",
                ],
                "copied_fields": [
                    "PrimalItem.AllowEquipItem.ReturnValue",
                    "PrimalItem.CanRepair.ReturnValue",
                    "PrimalItem.UseItemOntoItem.ReturnValue",
                ],
                "excluded_fields": [
                    "PrimalItem.AllowEquipItem.toInventory",
                    "PrimalItem.CanRepair.bIgnoreInventoryRequirement",
                    "PrimalItem.CraftBlueprint.bConsumeResources",
                    "PrimalItem.UseItemOntoItem.DestinationItem",
                    "PrimalItem.UseItemOntoItem.AdditionalData",
                ],
            },
            "copied_return_bools": [
                copied("PrimalItem.AllowEquipItem", "0x8"),
                copied("PrimalItem.CanRepair", "0x1"),
                copied("PrimalItem.UseItemOntoItem", "0xc"),
            ],
            "excluded_fields": [
                {"excluded_field": "PrimalItem.AllowEquipItem.toInventory"},
                {"excluded_field": "PrimalItem.CanRepair.bIgnoreInventoryRequirement"},
                {"excluded_field": "PrimalItem.CraftBlueprint.bConsumeResources"},
                {"excluded_field": "PrimalItem.UseItemOntoItem.DestinationItem"},
                {"excluded_field": "PrimalItem.UseItemOntoItem.AdditionalData"},
            ],
            "safety_summary": {
                "artifact_status": "evidence_only",
                "copied_bool_count": 3,
                "excluded_field_count": 5,
                "intended_use": "offline_review_only",
                "promotion_ready": False,
            },
            "non_claims": [
                "does not promote public SDK callbacks or public metadata helpers",
                "does not expose UE pointers, object identity, class identity, raw params, mutation, or return overrides",
                "does not copy CraftBlueprint, bIgnoreInventoryRequirement, bConsumeResources, toInventory, DestinationItem, or AdditionalData",
            ],
        }

    def write_pack(self, root: Path, payload: dict | None = None) -> tuple[Path, str]:
        root.mkdir(parents=True, exist_ok=True)
        manifest = root / "item-return-only-policy-slice.json"
        content = json.dumps(payload if payload is not None else self.make_policy(), sort_keys=True).encode("utf-8")
        manifest.write_bytes(content)
        return manifest, hashlib.sha256(content).hexdigest()

    def checker_args(self, root: Path, manifest: Path, sha256: str) -> list[str]:
        return [
            "--root",
            str(root),
            "--manifest",
            str(manifest),
            "--expected-manifest-sha256",
            sha256,
            "--skip-artifact-gates",
        ]

    def test_policy_fixture_is_candidate_ready_but_not_public_or_runtime_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            manifest, sha256 = self.write_pack(root)
            result = self.run_checker(*self.checker_args(root, manifest, sha256), "--json")

        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema"], "obelisk.item-return-only-readiness-check.v1")
        self.assertTrue(payload["ready"])
        self.assertFalse(payload["public_inventory_sdk_ready"])
        self.assertFalse(payload["public_items_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["promotion_ready"])
        self.assertEqual(payload["summary"]["copied_return_bool_count"], 3)
        self.assertEqual(len(payload["summary"]["excluded_fields"]), 5)

    def test_craftblueprint_copied_field_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["coverage"]["copied_fields"].append("PrimalItem.CraftBlueprint.ReturnValue")
            payload["copied_return_bools"].append(
                {
                    **payload["copied_return_bools"][0],
                    "target": "PrimalItem.CraftBlueprint",
                    "copied_field": "PrimalItem.CraftBlueprint.ReturnValue",
                }
            )
            manifest, sha256 = self.write_pack(root, payload)
            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("copied_field_coverage_mismatch", reasons)
        self.assertIn("forbidden_copied_field", reasons)

    def test_non_return_bool_metadata_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["copied_return_bools"][0]["direction"] = "in"
            manifest, sha256 = self.write_pack(root, payload)
            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("copied_return_bool_entry_metadata_mismatch", {b["reason"] for b in report["blockers"]})

    def test_protected_and_symlink_inputs_are_rejected(self) -> None:
        result = self.run_checker(
            "--root",
            "/servidor/ark/obelisk/artifacts/item",
            "--manifest",
            "/servidor/ark/obelisk/artifacts/item/manifest.json",
            check=False,
        )
        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("path_rejected", {blocker["reason"] for blocker in report["blockers"]})

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            manifest, sha256 = self.write_pack(root)
            link = Path(temp_dir) / "manifest-link.json"
            link.symlink_to(manifest)
            result = self.run_checker(*self.checker_args(root, link, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("path_rejected", {blocker["reason"] for blocker in report["blockers"]})


if __name__ == "__main__":
    unittest.main()
