#!/usr/bin/env python3
"""Tests for build_redacted_scriptstruct_signatures.py."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_redacted_scriptstruct_signatures as tool


REPO_ROOT = Path(__file__).resolve().parent.parent


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class BuildRedactedScriptStructSignaturesTest(unittest.TestCase):
    def snapshot_payload(self) -> dict:
        return {
            "schema": tool.SUPPORTED_SNAPSHOT_SCHEMA,
            "targets": [
                {
                    "target": {
                        "outer_name": "PrimalLocalProfile",
                        "name": "ArkTributePlayerData",
                    },
                    "properties_size": 288,
                    "min_alignment": 0,
                    "property_chain": {
                        "status": "candidate",
                        "properties": [
                            {
                                "name": "PlayerDataID",
                                "class_name": "UInt64Property",
                                "status": "candidate",
                                "offset_internal": 8,
                                "element_size": 8,
                                "array_dim": 1,
                                "property_flags": "0x1040000200",
                                "membership_status": "candidate-uobject",
                                "class_membership_status": "candidate-uobject",
                                "outer_membership_status": "candidate-uobject",
                            },
                            {
                                "name": "PlayerDataBytes",
                                "class_name": "ArrayProperty",
                                "status": "candidate",
                                "offset_internal": 16,
                                "element_size": 16,
                                "array_dim": 1,
                                "property_flags": "0x200",
                                "membership_status": "candidate-uobject",
                                "class_membership_status": "candidate-uobject",
                                "outer_membership_status": "candidate-uobject",
                                "array_inner_candidate": {
                                    "membership_status": "candidate-uobject",
                                    "inner_property": {
                                        "name": "PlayerDataBytes",
                                        "class_name": "ByteProperty",
                                    },
                                },
                            },
                            {
                                "name": "bWithItems",
                                "class_name": "BoolProperty",
                                "status": "candidate",
                                "offset_internal": 273,
                                "element_size": 1,
                                "array_dim": 1,
                                "property_flags": "0x10001040002200",
                                "membership_status": "candidate-uobject",
                                "class_membership_status": "candidate-uobject",
                                "outer_membership_status": "candidate-uobject",
                                "native_bool": False,
                                "bool_field_size": 1,
                                "bool_byte_offset": 0,
                                "byte_mask": "0x1",
                                "field_mask": "0xff",
                            },
                        ],
                    },
                }
            ],
        }

    def test_builds_redacted_candidate_only_signature_from_direct_snapshot(self) -> None:
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
        self.assertEqual("PrimalLocalProfile.ArkTributePlayerData", signature["target"])
        self.assertEqual("snapshot-0001", signature["source_snapshot"])
        self.assertEqual(expected_sha256, signature["source_snapshot_sha256"])
        self.assertEqual(3, signature["property_count"])

        fields = signature["fields"]
        self.assertEqual("redacted_transfer_payload_scalar", fields[0]["type"])
        self.assertNotIn("PlayerDataID", fields[0]["type"])
        self.assertEqual("redacted_array", fields[1]["type"])
        self.assertEqual(
            {
                "source_property_class": "ByteProperty",
                "redaction": "array inner identity redacted",
            },
            fields[1]["array_inner"],
        )
        self.assertEqual("redacted_transfer_payload_bool", fields[2]["type"])
        self.assertEqual({"byte_mask": "0x01", "field_mask": "0xff"}, fields[2]["bool_masks"])
        self.assertEqual(1, fields[2]["bool_field_size"])
        self.assertEqual(0, fields[2]["bool_byte_offset"])
        self.assertEqual("0x01", fields[2]["byte_mask"])
        self.assertEqual("0xff", fields[2]["field_mask"])
        self.assertIs(False, fields[2]["native_bool"])
        self.assertIn("no_public_transfer_sdk", signature["promotion_blockers"])
        self.assertIn("transfer_scriptstruct_payload_decode_blocked", signature["promotion_blockers"])
        self.assertIn("no_public_transfer_sdk", fields[2]["promotion_blockers"])
        self.assertIn("transfer_scriptstruct_payload_decode_blocked", fields[2]["promotion_blockers"])

        safety = report["safety_summary"]
        self.assertEqual("candidate_only", safety["artifact_status"])
        self.assertIs(False, safety["promotion_ready"])
        self.assertEqual("offline_review_only", safety["intended_use"])
        self.assertEqual(3, safety["field_count_total"])
        self.assertEqual(0, safety["copied_scalar_count_total"])
        self.assertEqual({}, safety["copied_scalar_by_kind"])
        self.assertEqual(3, safety["redacted_count_total"])
        self.assertEqual(
            {"array": 1, "transfer_payload_bool": 1, "transfer_payload_scalar": 1},
            safety["redacted_by_reason"],
        )
        self.assertIn("public_scriptstruct_sdk", safety["not_promoted_surfaces"])
        self.assertIn("resource_handle", safety["not_promoted_surfaces"])

    def test_transfer_scriptstruct_target_set_uses_fixture_manifest_and_redacts_paths(self) -> None:
        fixture_root = REPO_ROOT / "tests" / "fixtures" / "scriptstruct_snapshots"

        report = tool.build_report(snapshot_root=fixture_root, target_sets=["transfer-scriptstruct"])

        self.assertEqual("redacted", report["snapshot_root"])
        self.assertEqual(["transfer-scriptstruct"], report["target_sets"])
        coverage = report["target_set_coverage"]
        self.assertEqual(tool.TARGET_SET_COVERAGE_SCHEMA, coverage["schema"])
        self.assertEqual("complete", coverage["status"])
        self.assertIs(True, coverage["complete"])
        self.assertEqual([], coverage["missing_targets"])
        self.assertEqual([], coverage["unexpected_targets"])
        self.assertEqual([], report["missing_targets"])
        self.assertEqual(2, report["snapshot_count"])
        self.assertEqual(2, report["signature_count"])
        self.assertEqual(
            [
                "PrimalLocalProfile.ARKTributeDino",
                "PrimalLocalProfile.ArkTributePlayerData",
            ],
            [signature["target"] for signature in report["signatures"]],
        )
        self.assertEqual("candidate_only", report["safety_summary"]["artifact_status"])
        self.assertIs(False, report["safety_summary"]["promotion_ready"])
        self.assertEqual(0, report["safety_summary"]["copied_scalar_count_total"])
        self.assertIn("transfer_payload_decoding", report["safety_summary"]["not_promoted_surfaces"])
        player_data = next(
            signature
            for signature in report["signatures"]
            if signature["target"] == "PrimalLocalProfile.ArkTributePlayerData"
        )
        bool_fields = {
            field["name"]: field
            for field in player_data["fields"]
            if field.get("source_property_class") == "BoolProperty"
        }
        self.assertEqual(
            {
                "bWasAllowDPCUpload",
                "bWithItems",
                "bForServerTransfer",
            },
            set(bool_fields),
        )
        for semantics in bool_fields.values():
            self.assertEqual("redacted_transfer_payload_bool", semantics["type"])
            self.assertEqual(1, semantics["bool_field_size"])
            self.assertEqual(0, semantics["bool_byte_offset"])
            self.assertEqual("0x01", semantics["byte_mask"])
            self.assertEqual("0xff", semantics["field_mask"])
            self.assertIs(False, semantics["native_bool"])
            self.assertIn("no_public_transfer_sdk", semantics["promotion_blockers"])
            self.assertIn("transfer_scriptstruct_payload_decode_blocked", semantics["promotion_blockers"])
        for signature in report["signatures"]:
            self.assertIn("no_public_transfer_sdk", signature["promotion_blockers"])
            self.assertIn("transfer_scriptstruct_payload_decode_blocked", signature["promotion_blockers"])

        serialized = json.dumps(report)
        self.assertNotIn(str(fixture_root), serialized)
        self.assertNotIn("tests/fixtures/scriptstruct_snapshots", serialized)
        self.assertNotIn("/servidor/ark", serialized)
        self.assertNotIn("object_index", serialized)
        self.assertNotIn("name_index", serialized)
        self.assertNotIn("class_object_index", serialized)

    def test_rejects_ufunction_only_target_set(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            tool.build_report(target_sets=["item-compact-intake"])

        self.assertIn("target set did not include ScriptStruct snapshots", str(raised.exception))

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

    def test_direct_snapshots_can_require_source_target_set_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / "ArkTributePlayerData.snapshot.json"
            write_json(snapshot, self.snapshot_payload())

            report = tool.build_report(snapshots=[snapshot], source_target_sets=["transfer-scriptstruct"])

        self.assertEqual(["PrimalLocalProfile.ARKTributeDino"], report["missing_targets"])
        self.assertEqual("incomplete", report["target_set_coverage"]["status"])
        self.assertFalse(report["target_set_coverage"]["complete"])


if __name__ == "__main__":
    unittest.main()
