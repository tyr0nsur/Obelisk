#!/usr/bin/env python3
"""Tests for check_reflection_property_redaction_coverage.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_reflection_property_redaction_coverage.py"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def run_checker(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class ReflectionPropertyRedactionCoverageTests(unittest.TestCase):
    def complete_snapshot(self) -> dict:
        return {
            "schema": "obelisk.ufunction-chain.snapshot.v1",
            "targets": [
                {
                    "target": {"outer_name": "SyntheticOuter", "name": "SyntheticFunction"},
                    "num_parms": 9,
                    "parms_size": 96,
                    "return_value_offset": "0xffff",
                    "property_chain": {
                        "expected_count": 9,
                        "observed_count": 9,
                        "properties": [
                            {
                                "name": "bAllowed",
                                "class_name": "BoolProperty",
                                "status": "candidate",
                                "offset_internal": 0,
                                "element_size": 1,
                                "array_dim": 1,
                                "byte_mask": "0x01",
                                "field_mask": "0x01",
                            },
                            {
                                "name": "Controller",
                                "class_name": "ObjectProperty",
                                "status": "candidate",
                                "offset_internal": 8,
                                "element_size": 8,
                                "array_dim": 1,
                                "property_class_name": "SensitiveController",
                            },
                            {
                                "name": "Count",
                                "class_name": "IntProperty",
                                "status": "candidate",
                                "offset_internal": 16,
                                "element_size": 4,
                                "array_dim": 1,
                            },
                            {
                                "name": "Items",
                                "class_name": "ArrayProperty",
                                "status": "candidate",
                                "offset_internal": 24,
                                "element_size": 16,
                                "array_dim": 1,
                                "array_inner_candidate": {
                                    "membership_status": "candidate-uobject",
                                    "inner_property": {
                                        "name": "Items",
                                        "class_name": "StrProperty",
                                        "object_index": 1234,
                                    },
                                },
                            },
                            {
                                "name": "Message",
                                "class_name": "StrProperty",
                                "status": "candidate",
                                "offset_internal": 40,
                                "element_size": 16,
                                "array_dim": 1,
                            },
                            {
                                "name": "Placement",
                                "class_name": "StructProperty",
                                "status": "candidate",
                                "offset_internal": 56,
                                "element_size": 8,
                                "array_dim": 1,
                                "struct_name": "SensitivePlacementStruct",
                            },
                            {
                                "name": "ActorClass",
                                "class_name": "ClassProperty",
                                "status": "candidate",
                                "offset_internal": 64,
                                "element_size": 8,
                                "array_dim": 1,
                                "property_class_name": "SensitiveActorClass",
                            },
                            {
                                "name": "Mode",
                                "class_name": "ByteProperty",
                                "status": "candidate",
                                "offset_internal": 72,
                                "element_size": 1,
                                "array_dim": 1,
                                "enum_name": "SensitiveEnum",
                            },
                            {
                                "name": "MonotonicCounter",
                                "class_name": "UInt64Property",
                                "status": "candidate",
                                "offset_internal": 80,
                                "element_size": 8,
                                "array_dim": 1,
                            },
                        ],
                    },
                }
            ],
        }

    def test_complete_snapshot_covers_generic_property_redaction_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / "complete.snapshot.json"
            write_json(snapshot, self.complete_snapshot())

            result = run_checker("--artifact", str(snapshot), "--require-default-coverage", "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual("obelisk.reflection-property-redaction-coverage-check.v1", report["schema"])
        for key in (
            "BoolProperty",
            "ObjectProperty",
            "IntProperty",
            "ArrayProperty",
            "ArrayProperty.Inner",
            "StrProperty",
            "StructProperty",
            "ClassProperty",
            "ByteProperty",
            "UInt64Property",
        ):
            self.assertGreaterEqual(report["coverage"].get(key, 0), 1)
        fields = {field["name"]: field for field in report["fields"]}
        self.assertEqual("fstring_redacted", fields["Message"]["policy"])
        self.assertEqual("struct_redacted", fields["Placement"]["policy"])
        self.assertEqual("class_ref_redacted", fields["ActorClass"]["policy"])
        self.assertEqual("metadata_only_identity_redacted", fields["Mode"]["enum_metadata_policy"])
        self.assertIs(False, fields["Items.Inner"]["payload_decode_claim"])
        self.assertIn("does not decode UE parameter payloads or FString contents", report["non_claims"])

        serialized = json.dumps(report)
        self.assertNotIn("SensitiveController", serialized)
        self.assertNotIn("SensitivePlacementStruct", serialized)
        self.assertNotIn("SensitiveActorClass", serialized)
        self.assertNotIn("SensitiveEnum", serialized)

    def test_missing_required_class_blocks_report(self) -> None:
        snapshot_payload = self.complete_snapshot()
        props = snapshot_payload["targets"][0]["property_chain"]["properties"]
        snapshot_payload["targets"][0]["property_chain"]["properties"] = [
            prop for prop in props if prop["class_name"] != "UInt64Property"
        ]

        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / "missing.snapshot.json"
            write_json(snapshot, snapshot_payload)

            result = run_checker("--artifact", str(snapshot), "--require-default-coverage", "--json")

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        self.assertIn(
            {"reason": "required_property_class_missing", "class": "UInt64Property"},
            report["blockers"],
        )

    def test_ufunction_bounds_use_parms_size(self) -> None:
        snapshot_payload = self.complete_snapshot()
        snapshot_payload["targets"][0]["parms_size"] = 12

        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / "overflow.snapshot.json"
            write_json(snapshot, snapshot_payload)

            result = run_checker("--artifact", str(snapshot), "--json")

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("property_exceeds_target_bounds", reasons)
        overflow = next(
            blocker
            for blocker in report["blockers"]
            if blocker["reason"] == "property_exceeds_target_bounds"
        )
        self.assertEqual("ParmsSize", overflow["bound_name"])
        self.assertEqual(12, overflow["bound"])

    def test_sensitive_uint64_name_is_redacted_not_scalar_metadata(self) -> None:
        snapshot_payload = self.complete_snapshot()
        last_prop = snapshot_payload["targets"][0]["property_chain"]["properties"][-1]
        last_prop["name"] = "PlayerDataID"

        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / "sensitive.snapshot.json"
            write_json(snapshot, snapshot_payload)

            result = run_checker("--artifact", str(snapshot), "--require-class", "UInt64Property", "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        fields = {field["name"]: field for field in report["fields"]}
        self.assertEqual("redacted_sensitive_scalar", fields["PlayerDataID"]["policy"])
        self.assertEqual("identity-like scalar redacted by name", fields["PlayerDataID"]["policy_reason"])

    def test_rejects_protected_live_server_snapshot_root(self) -> None:
        result = run_checker("--snapshot-root", "/servidor/ark/not-approved/snapshots")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("snapshot root must not read from protected live-server path", result.stderr)


if __name__ == "__main__":
    unittest.main()
