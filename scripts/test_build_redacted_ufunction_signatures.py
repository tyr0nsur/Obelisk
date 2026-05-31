#!/usr/bin/env python3
"""Tests for build_redacted_ufunction_signatures.py."""

from __future__ import annotations

import json
import hashlib
import contextlib
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_redacted_ufunction_signatures as tool

REPO_ROOT = Path(__file__).resolve().parent.parent


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class BuildRedactedUFunctionSignaturesTest(unittest.TestCase):
    def snapshot_payload(self) -> dict:
        return {
            "schema": tool.SUPPORTED_SNAPSHOT_SCHEMA,
            "targets": [
                {
                    "target": {"outer_name": "ShooterGameMode", "name": "CanRespawn"},
                    "function_flags": "0x400",
                    "num_parms": 4,
                    "parms_size": 24,
                    "return_value_offset": 16,
                    "property_chain": {
                        "expected_count": 4,
                        "observed_count": 4,
                        "properties": [
                            {
                                "name": "Player",
                                "class_name": "ObjectProperty",
                                "status": "candidate",
                                "offset_internal": 0,
                                "element_size": 8,
                                "array_dim": 1,
                                "property_flags_low": 0x80,
                                "property_class_name": "PrimalPlayerController",
                            },
                            {
                                "name": "Reason",
                                "class_name": "ByteProperty",
                                "status": "candidate",
                                "offset_internal": 8,
                                "element_size": 1,
                                "array_dim": 1,
                                "property_flags_low": 0x80,
                                "enum_name": "ERespawnReason",
                            },
                            {
                                "name": "ReturnValue",
                                "class_name": "BoolProperty",
                                "status": "candidate",
                                "offset_internal": 16,
                                "element_size": 1,
                                "array_dim": 1,
                                "property_flags_low": 0x480,
                                "byte_mask": "0x01",
                                "field_mask": "0x01",
                            },
                            {
                                "name": "UnsafeStruct",
                                "class_name": "StructProperty",
                                "status": "rejected",
                                "offset_internal": 20,
                                "element_size": 4,
                                "array_dim": 1,
                                "struct_name": "UnsafeStruct",
                            },
                        ]
                    },
                }
            ],
        }

    def test_builds_redacted_candidate_only_signature(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / "snapshot.json"
            write_json(snapshot, self.snapshot_payload())
            expected_sha256 = hashlib.sha256(snapshot.read_bytes()).hexdigest()

            report = tool.build_report(snapshots=[snapshot])

        self.assertEqual(tool.OUTPUT_SCHEMA, report["schema"])
        self.assertEqual("redacted", report["snapshot_root"])
        self.assertEqual(
            {
                "snapshot_schema": tool.SUPPORTED_SNAPSHOT_SCHEMA,
                "input_snapshots": [{"id": "snapshot-0001", "sha256": expected_sha256}],
            },
            report["generated_from"],
        )
        self.assertNotIn(str(snapshot.parent), json.dumps(report))
        self.assertEqual(1, report["signature_count"])
        signature = report["signatures"][0]
        self.assertEqual("ShooterGameMode.CanRespawn", signature["target"])
        self.assertEqual("snapshot-0001", signature["source_snapshot"])
        self.assertEqual(expected_sha256, signature["source_snapshot_sha256"])
        self.assertEqual(3, len(signature["params"]))
        self.assertEqual(1, len(signature["blocked_properties"]))

        safety = report["safety_summary"]
        self.assertEqual("candidate_only", safety["artifact_status"])
        self.assertIs(False, safety["promotion_ready"])
        self.assertEqual("offline_review_only", safety["intended_use"])
        self.assertEqual(3, safety["param_count_total"])
        self.assertEqual(0, safety["zero_param_signature_count"])
        self.assertEqual(2, safety["copied_scalar_count_total"])
        self.assertEqual({"bool": 1, "byte_or_enum_like": 1}, safety["copied_scalar_by_kind"])
        self.assertEqual(1, safety["redacted_count_total"])
        self.assertEqual({"object_ref": 1}, safety["redacted_by_reason"])
        self.assertEqual(1, safety["blocked_count_total"])
        self.assertTrue(safety["unknown_or_blocked_present"])
        self.assertGreater(safety["promotion_blocker_count_total"], 0)
        self.assertIn("function_flags_not_bound_to_exact_target_gate", safety["promotion_blockers_by_reason"])
        self.assertIn("membership_status_not_candidate_uobject", safety["promotion_blockers_by_reason"])
        self.assertIn("public_sdk", safety["not_promoted_surfaces"])

        player = signature["params"][0]
        self.assertEqual("redacted_uobject_ref", player["type"])
        self.assertIn("property_class_name_redacted", player["redacted_identity_fields"])
        self.assertNotIn("PrimalPlayerController", json.dumps(player))

        reason = signature["params"][1]
        self.assertEqual("byte_or_enum", reason["type"])
        self.assertIn("enum_name_redacted", reason["redacted_identity_fields"])
        self.assertNotIn("ERespawnReason", json.dumps(reason))

        ret = signature["params"][2]
        self.assertEqual("return", ret["direction"])
        self.assertEqual("bool", ret["type"])
        self.assertEqual({"byte_mask": "0x01", "field_mask": "0x01"}, ret["bool_masks"])

    def test_item_compact_target_set_uses_fixture_manifest_and_redacts_paths(self) -> None:
        fixture_root = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"

        report = tool.build_report(snapshot_root=fixture_root, target_sets=["item-compact-intake"])

        self.assertEqual("redacted", report["snapshot_root"])
        self.assertEqual(["item-compact-intake"], report["target_sets"])
        self.assertEqual([], report["source_target_sets"])
        coverage = report["target_set_coverage"]
        self.assertEqual(tool.TARGET_SET_COVERAGE_SCHEMA, coverage["schema"])
        self.assertEqual("complete", coverage["status"])
        self.assertIs(True, coverage["complete"])
        self.assertEqual([], coverage["missing_targets"])
        self.assertEqual([], coverage["unexpected_targets"])
        self.assertEqual(["item-compact-intake"], [entry["name"] for entry in coverage["declared_target_sets"]])
        self.assertEqual("manifest", coverage["declared_target_sets"][0]["source"])
        self.assertEqual([], report["missing_targets"])
        self.assertEqual(4, report["snapshot_count"])
        self.assertEqual(4, report["signature_count"])
        self.assertEqual(
            [
                "PrimalItem.AllowEquipItem",
                "PrimalItem.CanRepair",
                "PrimalItem.CraftBlueprint",
                "PrimalItem.UseItemOntoItem",
            ],
            [signature["target"] for signature in report["signatures"]],
        )
        self.assertEqual(4, len(report["generated_from"]["input_snapshots"]))
        self.assertTrue(
            all(
                set(snapshot.keys()) == {"id", "sha256"}
                for snapshot in report["generated_from"]["input_snapshots"]
            )
        )
        serialized = json.dumps(report)
        self.assertNotIn(str(fixture_root), serialized)
        self.assertNotIn("tests/fixtures/ufunction_snapshots", serialized)
        self.assertEqual("candidate_only", report["safety_summary"]["artifact_status"])
        self.assertIs(False, report["safety_summary"]["promotion_ready"])
        self.assertEqual("offline_review_only", report["safety_summary"]["intended_use"])

    def test_item_return_only_policy_slice_emits_only_allowed_return_bools(self) -> None:
        fixture_root = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"

        report = tool.build_item_return_only_policy_slice(snapshot_root=fixture_root)

        self.assertEqual(tool.ITEM_RETURN_ONLY_POLICY_SCHEMA, report["schema"])
        self.assertEqual("redacted", report["snapshot_root"])
        self.assertEqual("item-compact-intake", report["input_target_set"])
        self.assertEqual("item-return-only-policy-slice", report["output_target_set"])
        self.assertEqual("complete", report["coverage"]["status"])
        self.assertEqual(
            [
                "PrimalItem.AllowEquipItem.ReturnValue",
                "PrimalItem.CanRepair.ReturnValue",
                "PrimalItem.UseItemOntoItem.ReturnValue",
            ],
            [entry["copied_field"] for entry in report["copied_return_bools"]],
        )
        self.assertEqual(
            ["0x8", "0x1", "0xc"],
            [entry["offset"] for entry in report["copied_return_bools"]],
        )
        self.assertTrue(all(entry["type"] == "bool" for entry in report["copied_return_bools"]))
        self.assertTrue(all(entry["direction"] == "return" for entry in report["copied_return_bools"]))
        self.assertTrue(all(entry["bool_masks"] for entry in report["copied_return_bools"]))
        self.assertEqual(
            [
                "PrimalItem.AllowEquipItem.toInventory",
                "PrimalItem.CanRepair.bIgnoreInventoryRequirement",
                "PrimalItem.CraftBlueprint.bConsumeResources",
                "PrimalItem.UseItemOntoItem.DestinationItem",
                "PrimalItem.UseItemOntoItem.AdditionalData",
            ],
            [entry["excluded_field"] for entry in report["excluded_fields"]],
        )
        self.assertEqual(3, report["safety_summary"]["copied_bool_count"])
        self.assertEqual(3, report["safety_summary"]["descriptor_preflight_count"])
        self.assertEqual(5, report["safety_summary"]["excluded_field_count"])
        self.assertIs(False, report["safety_summary"]["promotion_ready"])
        self.assertIn("public_sdk", report["safety_summary"]["explicitly_excluded"])
        self.assertIn("return_override", report["safety_summary"]["explicitly_excluded"])
        self.assertIn("object_refs", report["safety_summary"]["explicitly_excluded"])
        self.assertIn("event_kind_assignment", report["safety_summary"]["explicitly_excluded"])
        self.assertIn("event_kind_mask_assignment", report["safety_summary"]["explicitly_excluded"])

        serialized = json.dumps(report)
        self.assertNotIn(str(fixture_root), serialized)
        self.assertNotIn("tests/fixtures/ufunction_snapshots", serialized)
        copied_serialized = json.dumps(report["copied_return_bools"])
        self.assertNotIn("bIgnoreInventoryRequirement", copied_serialized)
        self.assertNotIn("bConsumeResources", copied_serialized)
        self.assertNotIn("toInventory", copied_serialized)
        self.assertNotIn("DestinationItem", copied_serialized)
        self.assertNotIn("AdditionalData", copied_serialized)

    def test_item_return_only_descriptor_preflight_is_internal_and_descriptor_only(self) -> None:
        fixture_root = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"

        report = tool.build_item_return_only_policy_slice(snapshot_root=fixture_root)
        preflight = report["descriptor_preflight"]

        self.assertEqual("internal-evidence-only", preflight["status"])
        self.assertEqual("item-return-only-policy-slice", preflight["scope"])
        self.assertEqual("INVENTORY_ITEM", preflight["resource_kind"])
        self.assertEqual("inventory_backed", preflight["resource_backing"])
        self.assertEqual("copied_return_value_only", preflight["payload_policy"])
        self.assertIs(True, preflight["return_value_only"])
        self.assertIsNone(preflight["assigned_event_kind"])
        self.assertIsNone(preflight["assigned_event_kind_mask"])
        self.assertIs(False, preflight["promotion_ready"])
        self.assertIs(False, preflight["public_promotion"])
        self.assertIs(False, preflight["public_surface"])
        self.assertEqual(3, preflight["descriptor_count"])
        self.assertEqual(
            [
                "inventory_item.allow_equip_check",
                "inventory_item.can_repair_check",
                "inventory_item.use_onto_item_check",
            ],
            [entry["descriptor"] for entry in preflight["descriptors"]],
        )
        self.assertEqual(
            [
                "PrimalItem.AllowEquipItem",
                "PrimalItem.CanRepair",
                "PrimalItem.UseItemOntoItem",
            ],
            [entry["target"] for entry in preflight["descriptors"]],
        )
        self.assertEqual(
            [entry["copied_field"] for entry in report["copied_return_bools"]],
            [entry["copied_field"] for entry in preflight["descriptors"]],
        )
        self.assertTrue(all(entry["resource_kind"] == "INVENTORY_ITEM" for entry in preflight["descriptors"]))
        self.assertTrue(all(entry["resource_backing"] == "inventory_backed" for entry in preflight["descriptors"]))
        self.assertTrue(all(entry["payload_policy"] == "copied_return_value_only" for entry in preflight["descriptors"]))
        self.assertTrue(all(entry["direction"] == "return" for entry in preflight["descriptors"]))
        self.assertTrue(all(entry["type"] == "bool" for entry in preflight["descriptors"]))
        self.assertTrue(all(entry["assigned_event_kind"] is None for entry in preflight["descriptors"]))
        self.assertTrue(all(entry["assigned_event_kind_mask"] is None for entry in preflight["descriptors"]))
        self.assertTrue(all(entry["promotion_ready"] is False for entry in preflight["descriptors"]))
        self.assertTrue(all(entry["public_promotion"] is False for entry in preflight["descriptors"]))
        self.assertIn("event_kind", preflight["explicitly_not_assigned"])
        self.assertIn("event_kind_mask", preflight["explicitly_not_assigned"])
        self.assertIn("public_metadata_json", preflight["explicitly_not_assigned"])
        self.assertIn("runtime_dispatcher_tables", preflight["explicitly_not_assigned"])
        self.assertIn("plugin_callbacks", preflight["explicitly_not_assigned"])

        serialized = json.dumps(preflight)
        self.assertNotIn("OBELISK_GAMEPLAY_POLICY_EVENT_KIND", serialized)
        self.assertNotIn("OBELISK_GAMEPLAY_POLICY_FIELD_MASK", serialized)
        self.assertNotIn("ResourceHandle", serialized)
        self.assertNotIn("Inventory SDK", serialized)

    def test_item_return_only_target_set_excludes_craftblueprint(self) -> None:
        from reflection_target_sets import TARGET_SETS

        self.assertEqual(
            (
                "obelisk.ufunction-chain.snapshot.v1:PrimalItem.AllowEquipItem",
                "obelisk.ufunction-chain.snapshot.v1:PrimalItem.CanRepair",
                "obelisk.ufunction-chain.snapshot.v1:PrimalItem.UseItemOntoItem",
            ),
            TARGET_SETS["item-return-only-policy-slice"],
        )

    def test_item_return_only_cli_mode_returns_success(self) -> None:
        original_argv = sys.argv
        try:
            sys.argv = [
                "build_redacted_ufunction_signatures.py",
                "--item-return-only-policy-slice",
                "--json",
            ]
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(0, tool.main())
            self.assertIn(tool.ITEM_RETURN_ONLY_POLICY_SCHEMA, stdout.getvalue())
        finally:
            sys.argv = original_argv

    def test_transfer_baccept_only_policy_slice_emits_only_allowed_input_bool(self) -> None:
        fixture_root = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"

        report = tool.build_transfer_baccept_only_policy_slice(snapshot_root=fixture_root)

        self.assertEqual(tool.TRANSFER_BACCEPT_ONLY_POLICY_SCHEMA, report["schema"])
        self.assertEqual("redacted", report["snapshot_root"])
        self.assertEqual("transfer-ufunction-intake", report["input_target_set"])
        self.assertEqual("transfer-baccept-only-policy-slice", report["output_target_set"])
        self.assertEqual("evidence-only", report["policy_status"])
        self.assertEqual([], report["missing_targets"])
        self.assertEqual("complete", report["coverage"]["status"])
        self.assertEqual(
            ["ShooterPlayerController.ServerTransferredPlayerConfirmationResult.bAccept"],
            report["coverage"]["copied_fields"],
        )
        self.assertEqual(
            ["ShooterPlayerController.ServerTransferredPlayerConfirmationResult"],
            report["coverage"]["copied_targets"],
        )
        self.assertEqual(set(tool.TRANSFER_BACCEPT_ONLY_EXCLUDED_REASONS), set(report["coverage"]["forbidden_fields"]))
        self.assertEqual(7, len(report["generated_from"]["input_snapshots"]))
        self.assertEqual(
            "ShooterPlayerController.ServerTransferredPlayerConfirmationResult.bAccept",
            report["copied_bool"]["copied_field"],
        )
        copied = report["copied_bool"]
        self.assertEqual("in", copied["direction"])
        self.assertEqual("bool", copied["type"])
        self.assertEqual("0x0", copied["offset"])
        self.assertEqual(0, copied["offset_internal"])
        self.assertEqual(1, copied["element_size"])
        self.assertEqual(1, copied["array_dim"])
        self.assertEqual("0x01", copied["byte_mask"])
        self.assertEqual("0xff", copied["field_mask"])
        self.assertIs(False, copied["native_bool"])
        self.assertEqual("0x220cc0", copied["function_flags"])
        self.assertEqual(1, copied["num_parms"])
        self.assertEqual(1, copied["parms_size"])
        self.assertEqual("0xffff", copied["return_value_offset"])
        self.assertEqual("0x1040000280", copied["property_flags"])
        self.assertEqual("BoolProperty", copied["property_class"])
        self.assertEqual("copied-bool-only", copied["evidence_status"])
        input_snapshots = {
            snapshot["id"]: snapshot["sha256"]
            for snapshot in report["generated_from"]["input_snapshots"]
        }
        self.assertEqual(
            sorted(report["coverage"]["input_targets"]),
            sorted(snapshot["target"] for snapshot in report["generated_from"]["input_snapshots"]),
        )
        self.assertEqual(input_snapshots[copied["source_snapshot"]], copied["source_snapshot_sha256"])

        self.assertEqual(1, report["safety_summary"]["copied_bool_count"])
        self.assertEqual(10, report["safety_summary"]["forbidden_field_count"])
        self.assertIs(False, report["safety_summary"]["promotion_ready"])
        self.assertIn("runtime_hook_wiring", report["safety_summary"]["explicitly_excluded"])
        self.assertIn("dispatcher_wiring", report["safety_summary"]["explicitly_excluded"])
        self.assertIn("ARKTributeDino", report["safety_summary"]["explicitly_excluded"])
        self.assertIn("public_sdk", report["safety_summary"]["explicitly_excluded"])
        self.assertIn("mutation", report["safety_summary"]["explicitly_excluded"])
        self.assertIn("return_override", report["safety_summary"]["explicitly_excluded"])
        self.assertIn("object_refs", report["safety_summary"]["explicitly_excluded"])
        self.assertIn("class_refs", report["safety_summary"]["explicitly_excluded"])
        self.assertIn("ids", report["safety_summary"]["explicitly_excluded"])
        self.assertIn(
            "does not promote runtime hook wiring, dispatcher wiring, transfer payload decoding, or public Transfer SDK",
            report["non_claims"],
        )
        self.assertIn(
            "does not expose UE pointers, object identity, class identity, raw params, mutation, or return overrides",
            report["non_claims"],
        )
        self.assertEqual(
            {
                "target",
                "field",
                "copied_field",
                "direction",
                "type",
                "offset",
                "offset_internal",
                "element_size",
                "array_dim",
                "byte_mask",
                "field_mask",
                "native_bool",
                "function_flags",
                "num_parms",
                "parms_size",
                "return_value_offset",
                "property_flags",
                "property_class",
                "source_snapshot",
                "source_snapshot_sha256",
                "evidence_status",
            },
            set(copied),
        )

        self.assertEqual(
            [
                "PrimalDinoCharacter.IsAllowedToTransfer.ReturnValue",
                "PrimalDinoCharacter.IsAllowedToTransfer.WorldContextObject",
                "ShooterGameState.AllowDownloadDino.ReturnValue",
                "ShooterGameState.AllowDownloadDino.TheDinoClass",
                "ShooterPlayerController.ServerDownloadTransferredPlayer.SpawnPointID",
                "ShooterPlayerController.ServerDownloadTransferredPlayer.spawnPointRegionIndex",
                "ShooterPlayerController.ServerUploadCurrentCharacterAndItems.InventoryComp",
                "ShooterPlayerController.ServerUploadDino.DownloadedDino",
                "ShooterPlayerState.ServerRequestSpawnPointsForDownloadedCharacters.IgnoreBedID",
                "ShooterPlayerState.ServerRequestSpawnPointsForDownloadedCharacters.PlayerDataID",
            ],
            sorted(entry["forbidden_field"] for entry in report["forbidden_transfer_fields"]),
        )
        self.assertTrue(
            all(
                entry["source_snapshot"] in input_snapshots
                and input_snapshots[entry["source_snapshot"]] == entry["source_snapshot_sha256"]
                and isinstance(entry["property_flags"], str)
                and isinstance(entry["offset"], str)
                and isinstance(entry["offset_internal"], int)
                and isinstance(entry["element_size"], int)
                and isinstance(entry["array_dim"], int)
                for entry in report["forbidden_transfer_fields"]
            )
        )
        self.assertEqual(
            sorted(report["coverage"]["input_targets"]),
            sorted({entry["target"] for entry in report["forbidden_transfer_fields"]} | {
                "ShooterPlayerController.ServerTransferredPlayerConfirmationResult"
            }),
        )

        serialized = json.dumps(report)
        self.assertNotIn(str(fixture_root), serialized)
        self.assertNotIn("tests/fixtures/ufunction_snapshots", serialized)
        copied_serialized = json.dumps(report["copied_bool"])
        self.assertNotIn("SpawnPointID", copied_serialized)
        self.assertNotIn("PlayerDataID", copied_serialized)
        self.assertNotIn("DownloadedDino", copied_serialized)
        self.assertNotIn("ReturnValue", copied_serialized)
        self.assertNotIn("Transfer SDK", copied_serialized)
        self.assertNotIn("payload", copied_serialized)
        self.assertNotIn("identity", copied_serialized)
        self.assertNotIn("mutation", copied_serialized)
        self.assertNotIn("return_override", copied_serialized)

    def test_transfer_baccept_only_policy_slice_rejects_extra_or_native_bool_shape(self) -> None:
        fixture_root = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"
        with tempfile.TemporaryDirectory() as temp_dir:
            copied_root = Path(temp_dir) / "ufunction_snapshots"
            shutil.copytree(fixture_root, copied_root)
            snapshot = (
                copied_root
                / "7e7ded49e0c6"
                / "sdk_transfers"
                / "ShooterPlayerController.ServerTransferredPlayerConfirmationResult.snapshot.json"
            )
            payload = json.loads(snapshot.read_text(encoding="utf-8"))
            target = payload["targets"][0]
            prop = target["property_chain"]["properties"][0]
            prop["native_bool"] = True
            target["property_chain"]["expected_count"] = 2
            target["property_chain"]["observed_count"] = 2
            target["property_chain"]["properties"].append({**prop, "name": "ReturnValue"})
            write_json(snapshot, payload)

            with self.assertRaisesRegex(SystemExit, "property count drifted"):
                tool.build_transfer_baccept_only_policy_slice(snapshot_root=copied_root)

    def test_transfer_baccept_only_target_set_contains_single_confirmation_target(self) -> None:
        from reflection_target_sets import TARGET_SETS

        self.assertEqual(
            (
                "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerTransferredPlayerConfirmationResult",
            ),
            TARGET_SETS["transfer-baccept-only-policy-slice"],
        )

    def test_transfer_baccept_only_cli_mode_returns_success(self) -> None:
        original_argv = sys.argv
        try:
            sys.argv = [
                "build_redacted_ufunction_signatures.py",
                "--transfer-baccept-only-policy-slice",
                "--json",
            ]
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(0, tool.main())
            self.assertIn(tool.TRANSFER_BACCEPT_ONLY_POLICY_SCHEMA, stdout.getvalue())
        finally:
            sys.argv = original_argv

    def test_mission_copied_bool_policy_slice_emits_only_allowed_bools(self) -> None:
        fixture_root = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"

        report = tool.build_mission_copied_bool_policy_slice(snapshot_root=fixture_root)

        expected_copied_fields = [
            "MissionType.AddPlayerToMission.bForceAdd",
            "MissionType.AddPlayerToMission.ReturnValue",
            "MissionType.BPAllowPlayerToLeaveMission.ReturnValue",
            "MissionType.BPOnPlayerRemovedFromMission.bFromMissionCompleteEvent",
            "MissionType.BPOnPlayerRemovedFromMission.bLastPhaseSuccess",
        ]
        expected_redacted_fields = [
            "MissionType.AddPlayerToMission.PlayerCharacter",
            "MissionType.BPAllowPlayerToLeaveMission.PlayerPawn",
            "MissionType.BPOnPlayerRemovedFromMission.Controller",
            "MissionType.BPOnPlayerRemovedFromMission.Player",
            "MissionType.GetPlayerUsableItems.Character",
            "MissionType.GetPlayerUsableItems.OutItemIDs",
        ]

        self.assertEqual(tool.MISSION_COPIED_BOOL_POLICY_SCHEMA, report["schema"])
        self.assertEqual("redacted", report["snapshot_root"])
        self.assertEqual("mission-compact-intake", report["input_target_set"])
        self.assertEqual("mission-copied-bool-policy-slice", report["output_target_set"])
        self.assertEqual("complete", report["coverage"]["status"])
        self.assertEqual(4, len(report["generated_from"]["input_snapshots"]))
        self.assertEqual(expected_copied_fields, [entry["copied_field"] for entry in report["copied_bools"]])
        self.assertEqual(set(tool.MISSION_COPIED_BOOL_FIELDS), {entry["copied_field"] for entry in report["copied_bools"]})
        self.assertEqual(expected_redacted_fields, sorted(entry["redacted_field"] for entry in report["redacted_mission_fields"]))
        self.assertEqual(set(tool.MISSION_REDACTED_FIELD_REASONS), {entry["redacted_field"] for entry in report["redacted_mission_fields"]})
        self.assertEqual(
            [
                "MissionType.AddPlayerToMission",
                "MissionType.BPAllowPlayerToLeaveMission",
                "MissionType.BPOnPlayerRemovedFromMission",
                "MissionType.GetPlayerUsableItems",
            ],
            report["coverage"]["input_targets"],
        )
        self.assertEqual(
            [
                "MissionType.AddPlayerToMission",
                "MissionType.BPAllowPlayerToLeaveMission",
                "MissionType.BPOnPlayerRemovedFromMission",
            ],
            report["coverage"]["copied_targets"],
        )
        self.assertEqual(5, report["safety_summary"]["copied_bool_count"])
        self.assertEqual(6, report["safety_summary"]["redacted_field_count"])
        self.assertIs(False, report["safety_summary"]["promotion_ready"])
        self.assertIn("Mission SDK", report["safety_summary"]["explicitly_excluded"])
        self.assertIn("resource_handle", report["safety_summary"]["explicitly_excluded"])
        self.assertIn("return_override", report["safety_summary"]["explicitly_excluded"])
        self.assertTrue(all(entry["type"] == "bool" for entry in report["copied_bools"]))
        self.assertTrue(all(entry["bool_field_size"] == 1 for entry in report["copied_bools"]))
        self.assertTrue(all(entry["bool_byte_offset"] == 0 for entry in report["copied_bools"]))
        self.assertTrue(all(entry["byte_mask"] == "0x01" for entry in report["copied_bools"]))
        self.assertTrue(all(entry["field_mask"] == "0xff" for entry in report["copied_bools"]))
        self.assertTrue(all(entry["target"] != "MissionType.GetPlayerUsableItems" for entry in report["copied_bools"]))
        self.assertTrue(all(entry["evidence_status"] == "recognition-only-redacted" for entry in report["redacted_mission_fields"]))
        self.assertEqual(
            {"object_ref_excluded", "array_payload_excluded"},
            {entry["reason"] for entry in report["redacted_mission_fields"]},
        )

        snapshots = {
            snapshot["id"]: snapshot
            for snapshot in report["generated_from"]["input_snapshots"]
        }
        self.assertEqual(
            sorted(report["coverage"]["input_targets"]),
            sorted(snapshot["target"] for snapshot in snapshots.values()),
        )
        self.assertTrue(
            all(
                entry["source_snapshot"] in snapshots
                and snapshots[entry["source_snapshot"]]["sha256"] == entry["source_snapshot_sha256"]
                and snapshots[entry["source_snapshot"]]["target"] == entry["target"]
                for entry in [*report["copied_bools"], *report["redacted_mission_fields"]]
            )
        )

        serialized = json.dumps(report)
        self.assertNotIn(str(fixture_root), serialized)
        self.assertNotIn("tests/fixtures/ufunction_snapshots", serialized)
        copied_serialized = json.dumps(report["copied_bools"])
        self.assertNotIn("PlayerCharacter", copied_serialized)
        self.assertNotIn("PlayerPawn", copied_serialized)
        self.assertNotIn("Controller", copied_serialized)
        self.assertNotIn("Character", copied_serialized)
        self.assertNotIn("GetPlayerUsableItems", copied_serialized)
        self.assertNotIn("OutItemIDs", copied_serialized)

    def test_mission_copied_bool_policy_slice_rejects_bool_tail_drift(self) -> None:
        fixture_root = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"
        with tempfile.TemporaryDirectory() as temp_dir:
            copied_root = Path(temp_dir) / "ufunction_snapshots"
            shutil.copytree(fixture_root, copied_root)
            snapshot = (
                copied_root
                / "7e7ded49e0c6"
                / "sdk_missions"
                / "MissionType.AddPlayerToMission.snapshot.json"
            )
            payload = json.loads(snapshot.read_text(encoding="utf-8"))
            prop = payload["targets"][0]["property_chain"]["properties"][1]
            prop["bool_byte_offset"] = 1
            prop["bool_property_semantics"]["bool_byte_offset"] = 1
            write_json(snapshot, payload)

            with self.assertRaisesRegex(SystemExit, "copied bool shape drifted"):
                tool.build_mission_copied_bool_policy_slice(snapshot_root=copied_root)

    def test_mission_copied_bool_target_set_excludes_metadata_only_target(self) -> None:
        from reflection_target_sets import TARGET_SETS

        self.assertEqual(
            (
                "obelisk.ufunction-chain.snapshot.v1:MissionType.AddPlayerToMission",
                "obelisk.ufunction-chain.snapshot.v1:MissionType.BPAllowPlayerToLeaveMission",
                "obelisk.ufunction-chain.snapshot.v1:MissionType.BPOnPlayerRemovedFromMission",
            ),
            TARGET_SETS["mission-copied-bool-policy-slice"],
        )

    def test_mission_copied_bool_cli_mode_returns_success(self) -> None:
        original_argv = sys.argv
        try:
            sys.argv = [
                "build_redacted_ufunction_signatures.py",
                "--mission-copied-bool-policy-slice",
                "--json",
            ]
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(0, tool.main())
            self.assertIn(tool.MISSION_COPIED_BOOL_POLICY_SCHEMA, stdout.getvalue())
        finally:
            sys.argv = original_argv

    def test_structure_return_only_policy_slice_emits_only_allowed_return_bools(self) -> None:
        fixture_root = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"

        report = tool.build_structure_return_only_policy_slice(snapshot_root=fixture_root)

        self.assertEqual(tool.STRUCTURE_RETURN_ONLY_POLICY_SCHEMA, report["schema"])
        self.assertEqual("redacted", report["snapshot_root"])
        self.assertEqual("structure-observer-intake", report["input_target_set"])
        self.assertEqual("structure-return-only-policy-slice", report["output_target_set"])
        self.assertEqual("complete", report["coverage"]["status"])
        self.assertEqual(6, len(report["generated_from"]["input_snapshots"]))
        self.assertEqual(
            [
                "PrimalStructure.AllowStructureAccess.ReturnValue",
                "PrimalStructure.IsAllowedToDemolish.ReturnValue",
            ],
            [entry["copied_field"] for entry in report["copied_return_bools"]],
        )
        self.assertEqual(
            [
                "PrimalStructure.AllowStructureAccess.ForPC",
                "PrimalStructure.IsAllowedToDemolish.ForPC",
            ],
            [entry["redacted_field"] for entry in report["redacted_structure_fields"]],
        )
        self.assertEqual(
            [
                "PrimalStructure.SetVariant",
                "PrimalStructureItemContainer.AllowToggleActivation",
                "PrimalStructureItemContainer.VerifyPinCode",
                "PrimalStructureSeating.CanSeat",
            ],
            sorted(entry["deferred_target"] for entry in report["deferred_structure_targets"]),
        )
        self.assertEqual(2, report["safety_summary"]["copied_bool_count"])
        self.assertEqual(2, report["safety_summary"]["redacted_field_count"])
        self.assertEqual(4, report["safety_summary"]["deferred_target_count"])
        self.assertIs(False, report["safety_summary"]["promotion_ready"])
        self.assertIn("resource_handle", report["safety_summary"]["explicitly_excluded"])
        self.assertIn("return_override", report["safety_summary"]["explicitly_excluded"])
        self.assertIn("ForPC", report["safety_summary"]["explicitly_excluded"])
        self.assertTrue(all(entry["direction"] == "return" for entry in report["copied_return_bools"]))
        self.assertTrue(all(entry["type"] == "bool" for entry in report["copied_return_bools"]))
        self.assertTrue(all(entry["byte_mask"] == "0x01" for entry in report["copied_return_bools"]))
        self.assertTrue(all(entry["field_mask"] == "0xff" for entry in report["copied_return_bools"]))

        snapshots = {
            snapshot["id"]: snapshot
            for snapshot in report["generated_from"]["input_snapshots"]
        }
        self.assertEqual(
            sorted(report["coverage"]["input_targets"]),
            sorted(snapshot["target"] for snapshot in snapshots.values()),
        )
        self.assertTrue(
            all(
                entry["source_snapshot"] in snapshots
                and snapshots[entry["source_snapshot"]]["sha256"] == entry["source_snapshot_sha256"]
                and snapshots[entry["source_snapshot"]]["target"] == entry["target"]
                for entry in [
                    *report["copied_return_bools"],
                    *report["redacted_structure_fields"],
                    *report["deferred_structure_targets"],
                ]
            )
        )

        serialized = json.dumps(report)
        self.assertNotIn(str(fixture_root), serialized)
        self.assertNotIn("tests/fixtures/ufunction_snapshots", serialized)
        copied_serialized = json.dumps(report["copied_return_bools"])
        self.assertNotIn("ForPC", copied_serialized)
        self.assertNotIn("pinCode", copied_serialized)
        self.assertNotIn("AllowToggleActivation", copied_serialized)
        self.assertNotIn("SetVariant", copied_serialized)
        self.assertNotIn("CanSeat", copied_serialized)

    def test_structure_return_only_policy_slice_rejects_forpc_copy_drift(self) -> None:
        fixture_root = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"
        with tempfile.TemporaryDirectory() as temp_dir:
            copied_root = Path(temp_dir) / "ufunction_snapshots"
            shutil.copytree(fixture_root, copied_root)
            snapshot = (
                copied_root
                / "7e7ded49e0c6"
                / "sdk_structures"
                / "PrimalStructure.AllowStructureAccess.snapshot.json"
            )
            payload = json.loads(snapshot.read_text(encoding="utf-8"))
            prop = payload["targets"][0]["property_chain"]["properties"][0]
            prop["class_name"] = "BoolProperty"
            write_json(snapshot, payload)

            with self.assertRaisesRegex(SystemExit, "property shape drifted"):
                tool.build_structure_return_only_policy_slice(snapshot_root=copied_root)

    def test_structure_return_only_target_set_contains_only_return_policy_targets(self) -> None:
        from reflection_target_sets import TARGET_SETS

        self.assertEqual(
            (
                "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.AllowStructureAccess",
                "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToDemolish",
            ),
            TARGET_SETS["structure-return-only-policy-slice"],
        )

    def test_structure_return_only_cli_mode_returns_success(self) -> None:
        original_argv = sys.argv
        try:
            sys.argv = [
                "build_redacted_ufunction_signatures.py",
                "--structure-return-only-policy-slice",
                "--json",
            ]
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(0, tool.main())
            self.assertIn(tool.STRUCTURE_RETURN_ONLY_POLICY_SCHEMA, stdout.getvalue())
        finally:
            sys.argv = original_argv

    def test_structure_nonpin_copied_scalar_policy_slice_is_evidence_only(self) -> None:
        fixture_root = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"

        report = tool.build_structure_nonpin_copied_scalar_policy_slice(snapshot_root=fixture_root)

        self.assertEqual(tool.STRUCTURE_NONPIN_COPIED_SCALAR_POLICY_SCHEMA, report["schema"])
        self.assertEqual("structure-nonpin-copied-scalar-policy-slice", report["input_target_set"])
        self.assertEqual("structure-nonpin-copied-scalar-policy-slice", report["output_target_set"])
        self.assertEqual(3, len(report["generated_from"]["input_snapshots"]))
        self.assertEqual(
            [
                "PrimalStructure.SetVariant",
                "PrimalStructureItemContainer.AllowToggleActivation",
                "PrimalStructureSeating.CanSeat",
            ],
            report["coverage"]["input_targets"],
        )
        self.assertEqual(
            [
                "PrimalStructure.SetVariant.VariantIndex",
                "PrimalStructure.SetVariant.bForceSet",
                "PrimalStructure.SetVariant.ReturnValue",
                "PrimalStructureItemContainer.AllowToggleActivation.ReturnValue",
                "PrimalStructureSeating.CanSeat.bForce",
                "PrimalStructureSeating.CanSeat.ReturnValue",
            ],
            [entry["copied_field"] for entry in report["copied_scalars"]],
        )
        self.assertEqual(
            [
                "PrimalStructureItemContainer.AllowToggleActivation.ForPC",
                "PrimalStructureSeating.CanSeat.ForPC",
                "PrimalStructureSeating.CanSeat.forCharacter",
            ],
            [entry["redacted_field"] for entry in report["redacted_structure_fields"]],
        )
        self.assertEqual(6, report["safety_summary"]["copied_scalar_count"])
        self.assertEqual(3, report["safety_summary"]["redacted_field_count"])
        self.assertIs(False, report["safety_summary"]["promotion_ready"])
        self.assertIn("VerifyPinCode", report["safety_summary"]["explicitly_excluded"])

        copied_by_field = {entry["copied_field"]: entry for entry in report["copied_scalars"]}
        self.assertEqual("int32", copied_by_field["PrimalStructure.SetVariant.VariantIndex"]["type"])
        self.assertEqual("0x0", copied_by_field["PrimalStructure.SetVariant.VariantIndex"]["offset"])
        self.assertEqual(4, copied_by_field["PrimalStructure.SetVariant.VariantIndex"]["element_size"])
        self.assertEqual("in", copied_by_field["PrimalStructure.SetVariant.bForceSet"]["direction"])
        self.assertEqual("return", copied_by_field["PrimalStructure.SetVariant.ReturnValue"]["direction"])
        self.assertEqual("0x10", copied_by_field["PrimalStructureSeating.CanSeat.bForce"]["offset"])
        self.assertEqual("0x11", copied_by_field["PrimalStructureSeating.CanSeat.ReturnValue"]["offset"])
        bool_entries = [entry for entry in report["copied_scalars"] if entry["type"] == "bool"]
        self.assertEqual(5, len(bool_entries))
        self.assertTrue(all(entry["byte_mask"] == "0x01" for entry in bool_entries))
        self.assertTrue(all(entry["field_mask"] == "0xff" for entry in bool_entries))
        self.assertTrue(all(entry["native_bool"] is False for entry in bool_entries))

        serialized = json.dumps(report)
        self.assertNotIn(str(fixture_root), serialized)
        self.assertNotIn("tests/fixtures/ufunction_snapshots", serialized)
        payload_without_boundaries = json.dumps(
            {
                key: value
                for key, value in report.items()
                if key not in {"non_claims", "safety_summary"}
            }
        )
        self.assertNotIn("VerifyPinCode", payload_without_boundaries)

    def test_structure_nonpin_target_set_excludes_verify_pin_code(self) -> None:
        from reflection_target_sets import TARGET_SETS

        targets = TARGET_SETS["structure-nonpin-copied-scalar-policy-slice"]
        self.assertEqual(
            (
                "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.SetVariant",
                "obelisk.ufunction-chain.snapshot.v1:PrimalStructureItemContainer.AllowToggleActivation",
                "obelisk.ufunction-chain.snapshot.v1:PrimalStructureSeating.CanSeat",
            ),
            targets,
        )
        self.assertNotIn("VerifyPinCode", json.dumps(targets))

    def test_structure_nonpin_cli_mode_returns_success(self) -> None:
        original_argv = sys.argv
        try:
            sys.argv = [
                "build_redacted_ufunction_signatures.py",
                "--structure-nonpin-copied-scalar-policy-slice",
                "--json",
            ]
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(0, tool.main())
            self.assertIn(tool.STRUCTURE_NONPIN_COPIED_SCALAR_POLICY_SCHEMA, stdout.getvalue())
        finally:
            sys.argv = original_argv

    def test_dino_compact_descriptor_preflight_copies_exact_fixture_scalars(self) -> None:
        fixture_root = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"

        report = tool.build_report(snapshot_root=fixture_root, target_sets=["dino-compact-intake"])
        preflight = report["descriptor_preflight"]

        self.assertEqual("internal-evidence-only", preflight["status"])
        self.assertEqual("dino-compact-intake", preflight["scope"])
        self.assertEqual("dino_character_recognition_only", preflight["resource_scope"])
        self.assertEqual("recognition_only_object_refs_excluded", preflight["resource_backing"])
        self.assertEqual("copied_scalar_descriptor_only", preflight["payload_policy"])
        self.assertIsNone(preflight["assigned_resource_kind"])
        self.assertIs(False, preflight["return_value_only"])
        self.assertEqual(2, preflight["descriptor_count"])
        self.assertEqual(
            [
                "dino_character.add_passenger",
                "dino_character.allow_carry_character",
            ],
            [entry["descriptor"] for entry in preflight["descriptors"]],
        )
        self.assertEqual(
            [
                "PrimalDinoCharacter.AddPassenger",
                "PrimalDinoCharacter.AllowCarryCharacter",
            ],
            [entry["target"] for entry in preflight["descriptors"]],
        )
        self.assertEqual(
            [
                "PrimalDinoCharacter.AddPassenger.PassengerSeatIndex",
                "PrimalDinoCharacter.AddPassenger.bForcePassenger",
                "PrimalDinoCharacter.AddPassenger.bAllowFlyersAndWaterDinos",
                "PrimalDinoCharacter.AddPassenger.bSkipLineTrace",
                "PrimalDinoCharacter.AddPassenger.ReturnValue",
                "PrimalDinoCharacter.AllowCarryCharacter.ReturnValue",
            ],
            [entry["copied_field"] for entry in preflight["copied_scalars"]],
        )
        self.assertEqual(
            [
                "PrimalDinoCharacter.AddPassenger.PassengerSeatIndex",
                "PrimalDinoCharacter.AddPassenger.bForcePassenger",
                "PrimalDinoCharacter.AddPassenger.bAllowFlyersAndWaterDinos",
                "PrimalDinoCharacter.AddPassenger.bSkipLineTrace",
                "PrimalDinoCharacter.AddPassenger.ReturnValue",
            ],
            preflight["descriptors"][0]["copied_fields"],
        )
        self.assertEqual(
            ["PrimalDinoCharacter.AllowCarryCharacter.ReturnValue"],
            preflight["descriptors"][1]["copied_fields"],
        )

        copied_by_field = {entry["copied_field"]: entry for entry in preflight["copied_scalars"]}
        self.assertEqual("int32", copied_by_field["PrimalDinoCharacter.AddPassenger.PassengerSeatIndex"]["type"])
        self.assertEqual("in", copied_by_field["PrimalDinoCharacter.AddPassenger.PassengerSeatIndex"]["direction"])
        self.assertEqual(4, copied_by_field["PrimalDinoCharacter.AddPassenger.PassengerSeatIndex"]["element_size"])
        bool_entries = [entry for entry in preflight["copied_scalars"] if entry["type"] == "bool"]
        self.assertEqual(5, len(bool_entries))
        self.assertTrue(all(entry["byte_mask"] == "0x01" for entry in bool_entries))
        self.assertTrue(all(entry["field_mask"] == "0xff" for entry in bool_entries))
        self.assertTrue(all(entry["native_bool"] is False for entry in bool_entries))
        self.assertEqual("return", copied_by_field["PrimalDinoCharacter.AddPassenger.ReturnValue"]["direction"])
        self.assertEqual("return", copied_by_field["PrimalDinoCharacter.AllowCarryCharacter.ReturnValue"]["direction"])

    def test_dino_compact_descriptor_preflight_excludes_refs_and_is_not_promoted(self) -> None:
        fixture_root = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"

        report = tool.build_report(snapshot_root=fixture_root, target_sets=["dino-compact-intake"])
        preflight = report["descriptor_preflight"]

        self.assertEqual(
            [
                "PrimalDinoCharacter.AddPassenger.ACharacter",
                "PrimalDinoCharacter.AllowCarryCharacter.CanCarryPawn",
            ],
            [entry["excluded_field"] for entry in preflight["excluded_object_refs"]],
        )
        self.assertEqual(
            ["PrimalDinoCharacter.AddPassenger.ACharacter"],
            preflight["descriptors"][0]["excluded_object_refs"],
        )
        self.assertEqual(
            ["PrimalDinoCharacter.AllowCarryCharacter.CanCarryPawn"],
            preflight["descriptors"][1]["excluded_object_refs"],
        )
        self.assertTrue(
            all(
                entry["evidence_status"] == "recognition-only-object-ref-excluded"
                for entry in preflight["excluded_object_refs"]
            )
        )
        self.assertIsNone(preflight["assigned_event_kind"])
        self.assertIsNone(preflight["assigned_event_kind_mask"])
        self.assertIs(False, preflight["promotion_ready"])
        self.assertIs(False, preflight["public_promotion"])
        self.assertIs(False, preflight["public_surface"])
        self.assertIs(False, report["safety_summary"]["promotion_ready"])
        self.assertEqual("candidate_only", report["safety_summary"]["artifact_status"])
        self.assertIn("event_kind", preflight["explicitly_not_assigned"])
        self.assertIn("event_kind_mask", preflight["explicitly_not_assigned"])
        self.assertIn("resource_kind", preflight["explicitly_not_assigned"])
        self.assertIn("resource_handle", preflight["explicitly_not_assigned"])
        self.assertIn("identity", preflight["explicitly_not_assigned"])
        self.assertIn("public_sdk", preflight["safety_summary"]["explicitly_excluded"])
        self.assertIn("return_override", preflight["safety_summary"]["explicitly_excluded"])
        self.assertIn("ue_function_calls", preflight["safety_summary"]["explicitly_excluded"])

        serialized = json.dumps(preflight)
        self.assertNotIn("OBELISK_GAMEPLAY_POLICY_EVENT_KIND", serialized)
        self.assertNotIn("OBELISK_GAMEPLAY_POLICY_FIELD_MASK", serialized)
        self.assertNotIn("ResourceHandle", serialized)
        self.assertNotIn("Dino SDK", serialized)
        self.assertNotIn("ACharacter", json.dumps(preflight["copied_scalars"]))
        self.assertNotIn("CanCarryPawn", json.dumps(preflight["copied_scalars"]))

    def test_inventory_action_compact_target_set_stays_candidate_only_and_redacted(self) -> None:
        fixture_root = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"

        report = tool.build_report(snapshot_root=fixture_root, target_sets=["inventory-action-compact-intake"])

        self.assertEqual("redacted", report["snapshot_root"])
        self.assertEqual(["inventory-action-compact-intake"], report["target_sets"])
        self.assertEqual([], report["source_target_sets"])
        self.assertEqual(tool.TARGET_SET_COVERAGE_SCHEMA, report["target_set_coverage"]["schema"])
        self.assertEqual("complete", report["target_set_coverage"]["status"])
        self.assertIs(True, report["target_set_coverage"]["complete"])
        self.assertEqual([], report["missing_targets"])
        self.assertEqual(2, report["snapshot_count"])
        self.assertEqual(2, report["signature_count"])
        self.assertEqual(
            [
                "ShooterPlayerController.ServerRequestInventoryUseItem",
                "ShooterPlayerController.ServerRequestInventoryUseItemWithActor",
            ],
            [signature["target"] for signature in report["signatures"]],
        )
        safety = report["safety_summary"]
        self.assertEqual("candidate_only", safety["artifact_status"])
        self.assertIs(False, safety["promotion_ready"])
        self.assertEqual("offline_review_only", safety["intended_use"])
        self.assertEqual(6, safety["param_count_total"])
        self.assertEqual(1, safety["copied_scalar_count_total"])
        self.assertEqual({"integer": 1}, safety["copied_scalar_by_kind"])
        self.assertEqual(5, safety["redacted_count_total"])
        self.assertEqual({"object_ref": 3, "struct": 2}, safety["redacted_by_reason"])
        self.assertIn("function_flags_not_bound_to_exact_target_gate", safety["promotion_blockers_by_reason"])
        self.assertIn("property_flags_unknown_bits", safety["promotion_blockers_by_reason"])

        serialized = json.dumps(report)
        self.assertNotIn(str(fixture_root), serialized)
        self.assertNotIn("tests/fixtures/ufunction_snapshots", serialized)
        self.assertNotIn("ItemNetID", serialized)
        self.assertNotIn("UPrimalInventoryComponent", serialized)
        self.assertNotIn("struct_type", serialized)
        self.assertNotIn("struct_type_candidate", serialized)

        use_item = report["signatures"][0]
        self.assertEqual("ItemId", use_item["params"][1]["name"])
        self.assertEqual("redacted_struct", use_item["params"][1]["type"])
        self.assertEqual("StructProperty", use_item["params"][1]["source_property_class"])

        with_actor = report["signatures"][1]
        self.assertEqual("ItemID1", with_actor["params"][2]["name"])
        self.assertEqual("redacted_struct", with_actor["params"][2]["type"])
        self.assertEqual("StructProperty", with_actor["params"][2]["source_property_class"])
        self.assertEqual("AdditionalData", with_actor["params"][3]["name"])
        self.assertEqual("int32", with_actor["params"][3]["type"])
        self.assertEqual(["AdditionalData"], [
            param["name"]
            for signature in report["signatures"]
            for param in signature["params"]
            if param["type"] == "int32"
        ])

    def test_source_target_set_covers_direct_snapshot_inputs(self) -> None:
        fixture_root = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"
        paths, missing = tool.snapshot_paths_from_target_sets(fixture_root, ["item-compact-intake"])
        self.assertEqual([], missing)

        report = tool.build_report(snapshots=paths, source_target_sets=["item-compact-intake"])

        self.assertEqual([], report["target_sets"])
        self.assertEqual(["item-compact-intake"], report["source_target_sets"])
        self.assertEqual(4, report["signature_count"])
        self.assertEqual(1, report["safety_summary"]["target_set_count"])
        coverage = report["target_set_coverage"]
        self.assertEqual(tool.TARGET_SET_COVERAGE_SCHEMA, coverage["schema"])
        self.assertEqual("complete", coverage["status"])
        self.assertIs(True, coverage["complete"])
        self.assertEqual([], coverage["missing_targets"])
        self.assertEqual([], coverage["unexpected_targets"])
        self.assertEqual(coverage["expected_targets"], coverage["emitted_targets"])
        self.assertEqual("snapshot", coverage["declared_target_sets"][0]["source"])

    def test_source_target_set_fails_closed_when_direct_snapshots_do_not_match(self) -> None:
        fixture_root = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"
        paths, missing = tool.snapshot_paths_from_target_sets(fixture_root, ["item-compact-intake"])
        self.assertEqual([], missing)

        with self.assertRaises(SystemExit):
            tool.build_report(snapshots=paths[:1], source_target_sets=["item-compact-intake"])

    def test_source_target_set_rejects_unknown_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / "snapshot.json"
            write_json(snapshot, self.snapshot_payload())

            with self.assertRaises(SystemExit):
                tool.build_report(snapshots=[snapshot], source_target_sets=["not-a-target-set"])

    def test_safety_summary_counts_zero_param_signatures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / "snapshot.json"
            write_json(
                snapshot,
                {
                    "schema": tool.SUPPORTED_SNAPSHOT_SCHEMA,
                    "targets": [
                        {
                            "target": {"outer_name": "SyntheticOuter", "name": "NoParams"},
                            "function_flags": "0x400",
                            "num_parms": 0,
                            "parms_size": 0,
                            "return_value_offset": "0xffff",
                            "property_chain": {"expected_count": 0, "observed_count": 0, "properties": []},
                        }
                    ],
                },
            )

            report = tool.build_report(snapshots=[snapshot])

        self.assertEqual(1, report["signature_count"])
        self.assertEqual(1, report["safety_summary"]["zero_param_signature_count"])
        self.assertEqual(0, report["safety_summary"]["param_count_total"])
        self.assertNotIn("zero_param_shape_not_proven", report["safety_summary"]["promotion_blockers_by_reason"])

    def test_zero_param_without_chain_counts_is_not_promotion_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / "snapshot.json"
            write_json(
                snapshot,
                {
                    "schema": tool.SUPPORTED_SNAPSHOT_SCHEMA,
                    "targets": [
                        {
                            "target": {"outer_name": "SyntheticOuter", "name": "NoParams"},
                            "function_flags": "0x400",
                            "num_parms": 0,
                            "parms_size": 0,
                            "return_value_offset": "0xffff",
                            "property_chain": {"properties": []},
                        }
                    ],
                },
            )

            report = tool.build_report(snapshots=[snapshot])

        self.assertEqual(1, report["safety_summary"]["zero_param_signature_count"])
        self.assertIn("zero_param_shape_not_proven", report["signatures"][0]["promotion_blockers"])
        self.assertIn("zero_param_shape_not_proven", report["safety_summary"]["promotion_blockers_by_reason"])

    def test_rejects_unsupported_snapshot_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / "snapshot.json"
            write_json(snapshot, {"schema": "wrong", "targets": []})

            with self.assertRaises(SystemExit):
                tool.build_report(snapshots=[snapshot])

    def test_rejects_live_server_paths(self) -> None:
        with self.assertRaises(SystemExit):
            tool.reject_protected_input_path("snapshot", Path("/servidor/ark/live/snapshot.json"))

    def test_allows_approved_offline_workspace_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protected = root / "server"
            workspace = protected / "workspace-offline"
            workspace.mkdir(parents=True)
            path = workspace / "snapshot.json"
            path.write_text("{}", encoding="utf-8")

            with (
                mock.patch.object(tool, "PROTECTED_SERVER_ROOT", protected),
                mock.patch.object(tool, "APPROVED_OFFLINE_WORKSPACE_ROOTS", (workspace,)),
            ):
                tool.reject_protected_input_path("snapshot", path)

    def test_rejects_textually_protected_workspace_symlink_resolving_outside(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protected = root / "server"
            workspace = protected / "workspace-offline"
            workspace.mkdir(parents=True)
            outside = root / "outside.snapshot.json"
            outside.write_text("{}", encoding="utf-8")
            link = workspace / "outward.snapshot.json"
            link.symlink_to(outside)

            with (
                mock.patch.object(tool, "PROTECTED_SERVER_ROOT", protected),
                mock.patch.object(tool, "APPROVED_OFFLINE_WORKSPACE_ROOTS", (workspace,)),
                self.assertRaises(SystemExit),
            ):
                tool.reject_protected_input_path("snapshot", link)

    def test_labels_reference_out_array_flags(self) -> None:
        prop = {
            "name": "UnfilteredItemsList",
            "class_name": "ArrayProperty",
            "status": "candidate",
            "offset_internal": 0,
            "element_size": 16,
            "array_dim": 1,
            "property_flags_low": 0x8000382,
        }

        field = tool.classify_property(prop, return_value_offset=None)

        self.assertEqual("out", field["direction"])
        self.assertEqual("redacted_array", field["type"])
        self.assertEqual("0x8000382", field["property_flags"])
        self.assertIn("ConstParm", field["property_flag_labels"])
        self.assertIn("OutParm", field["property_flag_labels"])
        self.assertIn("ReferenceParm", field["property_flag_labels"])

    def test_reference_label_does_not_expose_ref_direction(self) -> None:
        prop = {
            "name": "CandidateRef",
            "class_name": "ObjectProperty",
            "status": "candidate",
            "offset_internal": 0,
            "element_size": 8,
            "array_dim": 1,
            "property_flags_low": 0x08000080,
            "property_class_name": "SensitiveClass",
        }

        field = tool.classify_property(prop, return_value_offset=None)

        self.assertEqual("in", field["direction"])
        self.assertEqual("redacted_uobject_ref", field["type"])
        self.assertIn("ReferenceParm", field["property_flag_labels"])
        self.assertNotIn("SensitiveClass", json.dumps(field))

    def test_return_value_offset_accepts_hex_string(self) -> None:
        prop = {
            "name": "Result",
            "class_name": "BoolProperty",
            "status": "candidate",
            "offset_internal": 16,
            "element_size": 1,
            "array_dim": 1,
            "property_flags_low": 0x80,
        }

        field = tool.classify_property(prop, return_value_offset="0x10")

        self.assertEqual("return", field["direction"])

    def test_bool_without_mask_or_native_marker_gets_promotion_blocker(self) -> None:
        prop = {
            "name": "bForceSet",
            "class_name": "BoolProperty",
            "status": "candidate",
            "offset_internal": 0,
            "element_size": 1,
            "array_dim": 1,
            "property_flags_low": 0x80,
            "membership_status": "candidate-uobject",
            "class_membership_status": "candidate-uobject",
            "outer_membership_status": "candidate-uobject",
        }

        field = tool.classify_property(prop, return_value_offset=None)

        self.assertIn(
            "bool_semantics_missing_mask_or_native_bool_marker",
            field["promotion_blockers"],
        )

    def test_invalid_bool_mask_does_not_clear_promotion_blocker(self) -> None:
        prop = {
            "name": "bForceSet",
            "class_name": "BoolProperty",
            "status": "candidate",
            "offset_internal": 0,
            "element_size": 1,
            "array_dim": 1,
            "property_flags_low": 0x80,
            "byte_mask": "garbage",
            "field_mask": "0x00",
            "membership_status": "candidate-uobject",
            "class_membership_status": "candidate-uobject",
            "outer_membership_status": "candidate-uobject",
        }

        field = tool.classify_property(prop, return_value_offset=None)

        self.assertNotIn("bool_masks", field)
        self.assertIn(
            "bool_semantics_missing_mask_or_native_bool_marker",
            field["promotion_blockers"],
        )

    def test_complete_membership_removes_membership_blockers(self) -> None:
        prop = {
            "name": "bEnabled",
            "class_name": "BoolProperty",
            "status": "candidate",
            "offset_internal": 0,
            "element_size": 1,
            "array_dim": 1,
            "property_flags_low": 0x80,
            "byte_mask": "0x01",
            "field_mask": "0x01",
            "membership_status": "candidate-uobject",
            "class_membership_status": "candidate-uobject",
            "outer_membership_status": "candidate-uobject",
        }

        field = tool.classify_property(prop, return_value_offset=None)

        self.assertNotIn("membership_status_not_candidate_uobject", field.get("promotion_blockers", []))
        self.assertNotIn("class_membership_status_not_candidate_uobject", field.get("promotion_blockers", []))
        self.assertNotIn("outer_membership_status_not_candidate_uobject", field.get("promotion_blockers", []))

    def test_pin_code_is_redacted_despite_scalar_type(self) -> None:
        prop = {
            "name": "pinCode",
            "class_name": "IntProperty",
            "status": "candidate",
            "offset_internal": 0,
            "element_size": 4,
            "array_dim": 1,
            "property_flags_low": 0x80,
        }

        field = tool.classify_property(prop, return_value_offset=None)

        self.assertEqual("in", field["direction"])
        self.assertEqual("redacted_sensitive_scalar", field["type"])
        self.assertEqual("credential-like scalar redacted by name", field["redaction"])

    def test_tribe_permission_is_redacted_despite_enum_type(self) -> None:
        prop = {
            "name": "TribeGroupPermission",
            "class_name": "ByteProperty",
            "status": "candidate",
            "offset_internal": 0,
            "element_size": 1,
            "array_dim": 1,
            "property_flags_low": 0x80,
        }

        field = tool.classify_property(prop, return_value_offset=None)

        self.assertEqual("in", field["direction"])
        self.assertEqual("redacted_sensitive_scalar", field["type"])
        self.assertEqual("credential-like scalar redacted by name", field["redaction"])

    def test_redacts_array_struct_enum_and_bool_mask_identities(self) -> None:
        sensitive_values = [
            "SensitiveArrayInner",
            "SensitiveStructIdentity",
            "SensitiveByteEnum",
            "SensitiveEnumIdentity",
        ]
        payload = {
            "target": {"outer_name": "SyntheticOuter", "name": "SyntheticFunction"},
            "function_flags": "0x400",
            "num_parms": 5,
            "parms_size": 40,
            "return_value_offset": 32,
            "property_chain": {
                "properties": [
                    {
                        "name": "Items",
                        "class_name": "ArrayProperty",
                        "status": "candidate",
                        "offset_internal": 0,
                        "element_size": 16,
                        "array_dim": 1,
                        "property_flags_low": 0x80,
                        "inner_class_name": "SensitiveArrayInner",
                    },
                    {
                        "name": "Shape",
                        "class_name": "StructProperty",
                        "status": "candidate",
                        "offset_internal": 16,
                        "element_size": 8,
                        "array_dim": 1,
                        "property_flags_low": 0x80,
                        "struct_name": "SensitiveStructIdentity",
                    },
                    {
                        "name": "ByteMode",
                        "class_name": "ByteProperty",
                        "status": "candidate",
                        "offset_internal": 24,
                        "element_size": 1,
                        "array_dim": 1,
                        "property_flags_low": 0x80,
                        "enum_name": "SensitiveByteEnum",
                    },
                    {
                        "name": "EnumMode",
                        "class_name": "EnumProperty",
                        "status": "candidate",
                        "offset_internal": 28,
                        "element_size": 1,
                        "array_dim": 1,
                        "property_flags_low": 0x80,
                        "enum_name": "SensitiveEnumIdentity",
                    },
                    {
                        "name": "ReturnValue",
                        "class_name": "BoolProperty",
                        "status": "candidate",
                        "offset_internal": 32,
                        "element_size": 1,
                        "array_dim": 1,
                        "property_flags": "0x480",
                        "byte_mask": "0x01",
                        "field_mask": "0x01",
                        "bool_byte_mask": "0x02",
                        "bool_field_mask": "0x02",
                        "bitmask": "0x04",
                        "mask": "0x08",
                    },
                ]
            },
        }

        signature = tool.build_target_signature(
            payload,
            Path("synthetic_snapshot.json"),
            {"id": "snapshot-test", "sha256": "synthetic-sha256"},
        )

        self.assertEqual(5, len(signature["params"]))
        self.assertEqual([], signature["blocked_properties"])
        self.assertEqual("redacted_array", signature["params"][0]["type"])
        self.assertIn("inner_class_name_redacted", signature["params"][0]["redacted_identity_fields"])
        self.assertEqual("redacted_struct", signature["params"][1]["type"])
        self.assertIn("struct_name_redacted", signature["params"][1]["redacted_identity_fields"])
        self.assertEqual("byte_or_enum", signature["params"][2]["type"])
        self.assertIn("enum_name_redacted", signature["params"][2]["redacted_identity_fields"])
        self.assertEqual("enum", signature["params"][3]["type"])
        self.assertIn("enum_name_redacted", signature["params"][3]["redacted_identity_fields"])
        self.assertEqual("return", signature["params"][4]["direction"])
        self.assertEqual(
            {
                "byte_mask": "0x01",
                "field_mask": "0x01",
                "bool_byte_mask": "0x02",
                "bool_field_mask": "0x02",
                "bitmask": "0x04",
                "mask": "0x08",
            },
            signature["params"][4]["bool_masks"],
        )

        serialized = json.dumps(signature)
        for sensitive_value in sensitive_values:
            self.assertNotIn(sensitive_value, serialized)


if __name__ == "__main__":
    unittest.main()
