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
sys.path.insert(0, str(SCRIPT_DIR))
import check_item_return_only_readiness as readiness  # noqa: E402


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
        snapshot_sources = {
            "PrimalItem.AllowEquipItem": ("snapshot-0001", "1" * 64),
            "PrimalItem.CanRepair": ("snapshot-0002", "2" * 64),
            "PrimalItem.CraftBlueprint": ("snapshot-0003", "3" * 64),
            "PrimalItem.UseItemOntoItem": ("snapshot-0004", "4" * 64),
        }

        def copied(target: str, offset: str) -> dict:
            source_snapshot, source_sha256 = snapshot_sources[target]
            return {
                "bool_masks": {"byte_mask": "0x01", "field_mask": "0xff"},
                "copied_field": f"{target}.ReturnValue",
                "direction": "return",
                "element_size": 1,
                "evidence_status": "copied-return-bool-only",
                "field": "ReturnValue",
                "offset": offset,
                "source_snapshot": source_snapshot,
                "source_snapshot_sha256": source_sha256,
                "target": target,
                "type": "bool",
            }

        def descriptor(target: str, name: str) -> dict:
            source_snapshot, source_sha256 = snapshot_sources[target]
            return {
                "assigned_event_kind": None,
                "assigned_event_kind_mask": None,
                "copied_field": f"{target}.ReturnValue",
                "descriptor": name,
                "direction": "return",
                "evidence_status": "descriptor-preflight-only",
                "field": "ReturnValue",
                "payload_policy": "copied_return_value_only",
                "promotion_ready": False,
                "public_promotion": False,
                "resource_backing": "inventory_backed",
                "resource_kind": "INVENTORY_ITEM",
                "source_snapshot": source_snapshot,
                "source_snapshot_sha256": source_sha256,
                "target": target,
                "type": "bool",
            }

        def excluded(target: str, field: str) -> dict:
            source_snapshot, _ = snapshot_sources[target]
            return {
                "excluded_field": f"{target}.{field}",
                "field": field,
                "reason": "unit_test_excluded",
                "source_snapshot": source_snapshot,
                "target": target,
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
                excluded("PrimalItem.AllowEquipItem", "toInventory"),
                excluded("PrimalItem.CanRepair", "bIgnoreInventoryRequirement"),
                excluded("PrimalItem.CraftBlueprint", "bConsumeResources"),
                excluded("PrimalItem.UseItemOntoItem", "DestinationItem"),
                excluded("PrimalItem.UseItemOntoItem", "AdditionalData"),
            ],
            "generated_from": {
                "snapshot_schema": "obelisk.ufunction-chain.snapshot.v1",
                "input_snapshots": [
                    {"id": snapshot_id, "sha256": sha256}
                    for snapshot_id, sha256 in (
                        snapshot_sources["PrimalItem.AllowEquipItem"],
                        snapshot_sources["PrimalItem.CanRepair"],
                        snapshot_sources["PrimalItem.CraftBlueprint"],
                        snapshot_sources["PrimalItem.UseItemOntoItem"],
                    )
                ],
            },
            "safety_summary": {
                "artifact_status": "evidence_only",
                "copied_bool_count": 3,
                "descriptor_preflight_count": 3,
                "excluded_field_count": 5,
                "intended_use": "offline_review_only",
                "promotion_ready": False,
            },
            "descriptor_preflight": {
                "assigned_event_kind": None,
                "assigned_event_kind_mask": None,
                "descriptor_count": 3,
                "descriptors": [
                    descriptor("PrimalItem.AllowEquipItem", "inventory_item.allow_equip_check"),
                    descriptor("PrimalItem.CanRepair", "inventory_item.can_repair_check"),
                    descriptor("PrimalItem.UseItemOntoItem", "inventory_item.use_onto_item_check"),
                ],
                "explicitly_not_assigned": [
                    "event_kind",
                    "event_kind_mask",
                    "public_metadata_json",
                    "runtime_dispatcher_tables",
                    "plugin_callbacks",
                ],
                "payload_policy": "copied_return_value_only",
                "promotion_ready": False,
                "public_promotion": False,
                "public_surface": False,
                "resource_backing": "inventory_backed",
                "resource_kind": "INVENTORY_ITEM",
                "return_value_only": True,
                "scope": "item-return-only-policy-slice",
                "status": "internal-evidence-only",
            },
            "non_claims": [
                "does not promote public SDK callbacks or public metadata helpers",
                "does not expose UE pointers, object identity, class identity, raw params, mutation, or return overrides",
                "does not copy CraftBlueprint, bIgnoreInventoryRequirement, bConsumeResources, toInventory, DestinationItem, or AdditionalData",
            ],
        }

    def make_public_gameplay_events(self) -> dict:
        def item_return_event(kind: str, stable_name: str) -> dict:
            return {
                "kind": kind,
                "stable_name": stable_name,
                "resource_kind": "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM",
                "event_kind_mask": readiness.EXPECTED_PUBLIC_ITEM_RETURN_EVENT_KIND_MASKS[kind],
                "field_mask": ["OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE"],
            }

        def inventory_policy_event(kind: str, stable_name: str, field_mask: list[str]) -> dict:
            return {
                "kind": kind,
                "stable_name": stable_name,
                "resource_kind": "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM",
                "event_kind_mask": kind.replace("_EVENT_KIND_", "_EVENT_MASK_"),
                "field_mask": field_mask,
            }

        return {
            "schema": "obelisk.public-gameplay-events.v1",
            "metadata_surfaces": [
                {
                    "surface_id": "obelisk.resource_kind_descriptors.v1",
                    "public_name": "DescribeResourceKind",
                    "descriptor_struct": "ObeliskResourceKindDescriptor",
                    "descriptor": "DescribeResourceKind",
                    "scope": (
                        "metadata-only resource category descriptors for routing/config; no identity, no lookup, "
                        "no handle, no cross-event correlation, no mutation, and no UE object access"
                    ),
                    "descriptor_fields": readiness.EXPECTED_DESCRIPTOR_SURFACES[
                        "obelisk.resource_kind_descriptors.v1"
                    ]["descriptor_fields"],
                    "not_promoted": sorted(
                        readiness.EXPECTED_DESCRIPTOR_SURFACES[
                            "obelisk.resource_kind_descriptors.v1"
                        ]["not_promoted"]
                    ),
                },
                {
                    "surface_id": "obelisk.gameplay_policy_event_descriptors.v1",
                    "public_name": "DescribeGameplayPolicyEventKind",
                    "descriptor_struct": "ObeliskGameplayPolicyEventDescriptor",
                    "descriptor": "DescribeGameplayPolicyEventKind",
                    "scope": (
                        "metadata-only descriptors for promoted GameplayPolicyEvent kinds; no identity, no lookup, "
                        "no cross-event correlation, no mutation, no return override, and no UE object access"
                    ),
                    "descriptor_fields": readiness.EXPECTED_DESCRIPTOR_SURFACES[
                        "obelisk.gameplay_policy_event_descriptors.v1"
                    ]["descriptor_fields"],
                    "not_promoted": sorted(
                        readiness.EXPECTED_DESCRIPTOR_SURFACES[
                            "obelisk.gameplay_policy_event_descriptors.v1"
                        ]["not_promoted"]
                    ),
                },
            ],
            "promoted_events": [
                {
                    "event_id": "obelisk.gameplay_policy.v1",
                    "item_return_backing_target_set": "item-return-only-policy-slice",
                    "target_sets": [
                        "structure-observer-intake",
                        "minimal-second-source-intake",
                        "item-return-only-policy-slice",
                    ],
                    "target_set_evidence": [
                        {
                            "target_set": "item-return-only-policy-slice",
                            "scope": "second-source accepted copied ReturnValue-only item backing",
                        }
                    ],
                    "inventory_sdk": "not promoted; inventory-backed policy signals are exposed only through GameplayPolicyEvent",
                    "item_module_sdk": "not promoted; item-return-backed policy signals are exposed only through GameplayPolicyEvent",
                    "event_kinds": [
                        inventory_policy_event(
                            "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK",
                            "inventory.remote_add_check",
                            [
                                "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE",
                                "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER",
                            ],
                        ),
                        inventory_policy_event(
                            "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK",
                            "inventory.use_check",
                            [
                                "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE",
                                "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN",
                            ],
                        ),
                        item_return_event(
                            "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_ALLOW_EQUIP_ITEM_CHECK",
                            "inventory_item.allow_equip_check",
                        ),
                        item_return_event(
                            "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_CAN_REPAIR_CHECK",
                            "inventory_item.can_repair_check",
                        ),
                        item_return_event(
                            "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK",
                            "inventory_item.use_onto_item_check",
                        ),
                    ],
                }
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
        self.assertEqual(payload["public_gameplay_events"]["item_return_backing_target_set"], "item-return-only-policy-slice")
        self.assertEqual(len(payload["public_gameplay_events"]["item_return_event_kinds"]), 3)
        reconciliation = payload["descriptor_reconciliation"]
        self.assertEqual(reconciliation["status"], "accepted")
        self.assertEqual(reconciliation["item_return_only_preflight"]["policy_status"], "evidence-only")
        self.assertIsNone(reconciliation["item_return_only_preflight"]["assigned_event_kind"])
        self.assertIsNone(reconciliation["item_return_only_preflight"]["assigned_event_kind_mask"])
        self.assertFalse(reconciliation["item_return_only_preflight"]["public_surface"])
        self.assertEqual(len(reconciliation["public_gameplay_policy_item_return_descriptors"]), 3)
        self.assertTrue(
            all(
                descriptor["field_mask"] == ["OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE"]
                for descriptor in reconciliation["public_gameplay_policy_item_return_descriptors"]
            )
        )
        self.assertTrue(reconciliation["dispatcher_boundary"]["preserved"])
        self.assertEqual(
            reconciliation["dispatcher_boundary"]["ItemReturnEventDispatcher"]["event_kinds"],
            sorted(readiness.EXPECTED_PUBLIC_ITEM_RETURN_EVENT_KINDS),
        )
        self.assertEqual(
            reconciliation["dispatcher_boundary"]["InventoryPolicyEventDispatcher"]["event_kinds"],
            sorted(readiness.EXPECTED_PUBLIC_INVENTORY_POLICY_EVENT_KINDS),
        )

    def test_public_gameplay_events_accepts_three_return_value_only_item_events(self) -> None:
        blockers: list[dict] = []
        summary = readiness.validate_public_gameplay_events(self.make_public_gameplay_events(), blockers)

        self.assertEqual(blockers, [])
        self.assertEqual(
            summary["descriptor_surface_ids"],
            sorted(readiness.EXPECTED_METADATA_SURFACE_IDS),
        )
        self.assertEqual(summary["item_return_backing_target_set"], "item-return-only-policy-slice")
        self.assertEqual(
            summary["item_return_event_kinds"],
            sorted(readiness.EXPECTED_PUBLIC_ITEM_RETURN_EVENT_KINDS),
        )
        self.assertEqual(
            summary["inventory_policy_event_kinds"],
            sorted(readiness.EXPECTED_PUBLIC_INVENTORY_POLICY_EVENT_KINDS),
        )

    def test_public_gameplay_events_rejects_descriptor_surface_overclaims(self) -> None:
        public_events = self.make_public_gameplay_events()
        resource_surface = public_events["metadata_surfaces"][0]
        event_surface = public_events["metadata_surfaces"][1]
        resource_surface["descriptor_fields"] = [
            *resource_surface["descriptor_fields"],
            "resource_handle",
        ]
        event_surface["scope"] = "metadata-only descriptors with return override authority"
        event_surface["not_promoted"] = [
            item for item in event_surface["not_promoted"] if item != "return override"
        ]
        blockers: list[dict] = []

        readiness.validate_public_gameplay_events(public_events, blockers)

        reasons = {blocker["reason"] for blocker in blockers}
        self.assertIn("public_descriptor_fields_mismatch", reasons)
        self.assertIn("public_descriptor_forbidden_field", reasons)
        self.assertIn("public_descriptor_scope_missing_guardrail", reasons)
        self.assertIn("public_descriptor_not_promoted_missing", reasons)

    def test_public_gameplay_events_rejects_extra_item_kind_and_non_return_value_field(self) -> None:
        public_events = self.make_public_gameplay_events()
        event = public_events["promoted_events"][0]
        event["event_kinds"][2]["field_mask"].append("OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN")
        event["event_kinds"].append(
            {
                "kind": "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_CRAFT_BLUEPRINT_CHECK",
                "stable_name": "inventory_item.craft_blueprint_check",
                "resource_kind": "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM",
                "event_kind_mask": "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_CRAFT_BLUEPRINT_CHECK",
                "field_mask": ["OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE"],
            }
        )
        blockers: list[dict] = []

        readiness.validate_public_gameplay_events(public_events, blockers)

        reasons = {blocker["reason"] for blocker in blockers}
        self.assertIn("public_item_return_field_mask_not_return_value_only", reasons)
        self.assertIn("public_item_return_event_kind_coverage_mismatch", reasons)
        self.assertIn("public_item_return_event_kind_count_mismatch", reasons)

    def test_public_gameplay_events_rejects_inventory_and_item_sdk_claims(self) -> None:
        public_events = self.make_public_gameplay_events()
        event = public_events["promoted_events"][0]
        event["inventory_sdk"] = "promoted standalone Inventory SDK"
        event["item_module_sdk"] = "promoted standalone item module SDK"
        blockers: list[dict] = []

        readiness.validate_public_gameplay_events(public_events, blockers)

        reasons = {blocker["reason"] for blocker in blockers}
        self.assertIn("public_inventory_sdk_non_claim_missing", reasons)
        self.assertIn("public_item_module_sdk_non_claim_missing", reasons)

    def test_public_gameplay_events_rejects_item_return_claim_fields(self) -> None:
        public_events = self.make_public_gameplay_events()
        event = public_events["promoted_events"][0]
        event["item_return_runtime_validated"] = True
        event["event_kinds"][0]["identity"] = "item identity available"
        event["event_kinds"][1]["return_override"] = True
        event["event_kinds"][2]["v1_completion"] = "ready"
        blockers: list[dict] = []

        readiness.validate_public_gameplay_events(public_events, blockers)

        reasons = {blocker["reason"] for blocker in blockers}
        self.assertIn("public_item_return_forbidden_claim_field", reasons)
        self.assertIn("public_item_return_unexpected_field", reasons)

    def test_public_gameplay_events_rejects_generic_runtime_or_v1_readiness_claims(self) -> None:
        public_events = self.make_public_gameplay_events()
        event = public_events["promoted_events"][0]
        event["runtime_ready"] = True
        event["v1_ready"] = True
        event["runtime_readiness"] = "inventory/item copied signals runtime ready; v1 completion ready"
        blockers: list[dict] = []

        readiness.validate_public_gameplay_events(public_events, blockers)

        readiness_blockers = [
            blocker for blocker in blockers if blocker["reason"] == "public_gameplay_events_readiness_claim_enabled"
        ]
        self.assertEqual(3, len(readiness_blockers), blockers)
        self.assertEqual(
            {
                "$.promoted_events[0].runtime_ready",
                "$.promoted_events[0].v1_ready",
                "$.promoted_events[0].runtime_readiness",
            },
            {blocker["path"] for blocker in readiness_blockers},
        )

    def test_policy_rejects_sdk_runtime_and_v1_claim_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["v1_completion_ready"] = True
            payload["coverage"]["runtime_validated"] = True
            payload["safety_summary"]["items_sdk_ready"] = True
            payload["copied_return_bools"][0]["identity"] = "item identity available"
            payload["excluded_fields"][0]["return_override"] = False
            manifest, sha256 = self.write_pack(root, payload)
            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("policy_unexpected_field", reasons)
        self.assertIn("coverage_unexpected_field", reasons)
        self.assertIn("safety_summary_unexpected_field", reasons)
        self.assertIn("copied_return_bool_entry_unexpected_field", reasons)
        self.assertIn("excluded_field_entry_unexpected_field", reasons)

    def test_descriptor_reconciliation_requires_unassigned_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            del payload["descriptor_preflight"]
            manifest, sha256 = self.write_pack(root, payload)
            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["descriptor_reconciliation"]["status"], "blocked")
        self.assertIn("descriptor_reconciliation_preflight_missing", {b["reason"] for b in report["blockers"]})

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

    def test_copied_return_source_snapshot_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["copied_return_bools"][0]["source_snapshot_sha256"] = "f" * 64
            payload["copied_return_bools"][1]["source_snapshot"] = "snapshot-0004"
            manifest, sha256 = self.write_pack(root, payload)
            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertEqual(result.returncode, 1)
        self.assertIn("copied_return_bool_entry_source_snapshot_sha256_mismatch", reasons)
        self.assertIn("copied_return_bool_entry_source_snapshot_target_mismatch", reasons)

    def test_excluded_field_source_snapshot_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["excluded_fields"][0]["source_snapshot"] = "unknown-snapshot"
            payload["excluded_fields"][1]["target"] = "PrimalItem.UseItemOntoItem"
            manifest, sha256 = self.write_pack(root, payload)
            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertEqual(result.returncode, 1)
        self.assertIn("excluded_field_entry_source_snapshot_unknown", reasons)
        self.assertIn("excluded_field_entry_source_snapshot_target_mismatch", reasons)

    def test_descriptor_source_snapshot_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["descriptor_preflight"]["descriptors"][0]["source_snapshot_sha256"] = "f" * 64
            payload["descriptor_preflight"]["descriptors"][1]["target"] = "PrimalItem.AllowEquipItem"
            manifest, sha256 = self.write_pack(root, payload)
            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertEqual(result.returncode, 1)
        self.assertIn("descriptor_preflight_descriptor_source_snapshot_sha256_mismatch", reasons)
        self.assertIn("descriptor_preflight_descriptor_source_snapshot_target_mismatch", reasons)

    def test_generated_from_snapshot_identity_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["generated_from"]["input_snapshots"][0]["id"] = "snapshot-9999"
            manifest, sha256 = self.write_pack(root, payload)
            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertEqual(result.returncode, 1)
        self.assertIn("input_snapshot_id_unexpected", reasons)
        self.assertIn("input_snapshot_ids_mismatch", reasons)

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
