#!/usr/bin/env python3

import argparse
import json
import hashlib
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_resource_handle_zero_serial_negative_samples as samples


class FakeMemory:
    def __init__(self) -> None:
        self.ptrs = {
            0x595B7E0 + samples.uobjects.GOBJECTS_CHUNKS_OFFSET: 0x200000,
            0x5956F30: 0x300000,
            0x200000: 0x400000,
        }
        for index in range(12):
            self.ptrs[0x400000 + index * samples.uobjects.FUOBJECT_ITEM_SIZE] = 0x500000 + index * 0x100

    def read_ptr(self, address: int) -> int | None:
        return self.ptrs.get(address)


class BuildResourceHandleZeroSerialNegativeSamplesTests(unittest.TestCase):
    def test_collects_zero_serial_samples_and_positive_anchor(self) -> None:
        memory = FakeMemory()

        def fake_read_i32(_memory: FakeMemory, address: int) -> int | None:
            if address == 0x595B7E0 + samples.uobjects.GOBJECTS_COUNT_OFFSET:
                return 12
            index = (address - 0x400000 - 0xC) // samples.uobjects.FUOBJECT_ITEM_SIZE
            return index if index >= 0 else None

        def fake_read_u32(_memory: FakeMemory, address: int) -> int | None:
            index = (address - 0x400000 - 0x8) // samples.uobjects.FUOBJECT_ITEM_SIZE
            return 1001 if index == 8 else 0

        def fake_read_uobject(
            _memory: FakeMemory,
            object_address: int,
            _fname_table: int | None,
            *,
            resolve_names: bool = True,
        ):
            index = (object_address - 0x500000) // 0x100
            return {
                "flags": 0x81,
                "internal_index": index,
                "class_name": "FixtureClass" if resolve_names else None,
                "name": f"Fixture{index}" if resolve_names else None,
            }

        with (
            mock.patch.object(samples.uobjects, "read_i32", fake_read_i32),
            mock.patch.object(samples.uobjects, "read_u32", fake_read_u32),
            mock.patch.object(samples.uobjects, "read_uobject", fake_read_uobject),
        ):
            report = samples.collect_samples(
                memory,
                gobjects=0x595B7E0,
                fname_root_slot=0x5956F30,
                anchor_index=8,
                negative_limit=3,
                max_scan_index=8,
                resolve_names=True,
            )

        self.assertEqual(report["scan_totals"]["indices_scanned"], 9)
        self.assertEqual([item["index"] for item in report["zero_serial_negative_samples"]], [0, 1, 2])
        self.assertEqual(report["zero_serial_negative_samples"][0]["membership"], "candidate-uobject")
        self.assertEqual(report["positive_anchor"]["index"], 8)
        self.assertEqual(report["positive_anchor"]["item_dword_0x8"], 1001)

    def test_report_stays_candidate_blocked(self) -> None:
        args = argparse.Namespace(
            core=["fixture=/tmp/core"],
            core_sha256=[],
            gobjects=0x595B7E0,
            fname_root_slot=0x5956F30,
            anchor_index=8,
            negative_limit=1,
            max_scan_index=8,
            skip_name_resolution=True,
            capture_id=None,
            evidence_pack_id=None,
            require_output_artifact_identity=False,
            output=None,
        )
        source = {
            "source_label": "fixture",
            "deterministic_negative_cohort": True,
            "blockers": [],
            "zero_serial_negative_samples": [{"index": 0}],
            "positive_anchor": {"index": 8, "item_dword_0x8": 1001},
        }

        with mock.patch.object(samples, "build_source_report", return_value=source):
            report = samples.build_report(args)

        self.assertEqual(report["status"], "candidate_blocked")
        self.assertTrue(report["deterministic_negative_cohort"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_resource_handle_ready"])
        self.assertFalse(report["post_callback_resource_handle_ready"])
        self.assertEqual(report["promotion_gate"]["ready"], False)
        self.assertIn("does not prove runtime reuse", report["non_claims"][1])

    def test_rejects_bad_labeled_args(self) -> None:
        with self.assertRaises(argparse.ArgumentTypeError):
            samples.parse_core_arg("/tmp/core")
        with self.assertRaises(argparse.ArgumentTypeError):
            samples.parse_hash_arg("core=not-a-sha")

    def test_build_source_report_marks_missing_hash_as_blocker(self) -> None:
        with (
            mock.patch.object(samples, "sha256_file", return_value="a" * 64),
            mock.patch.object(samples.uobjects, "CoreMemory"),
            mock.patch.object(
                samples,
                "collect_samples",
                return_value={
                    "metadata": {},
                    "scan_totals": {},
                    "zero_serial_negative_samples": [{"index": 0}],
                    "positive_anchor": {"index": 8, "item_dword_0x8": 1001},
                },
            ),
        ):
            report = samples.build_source_report(
                label="fixture",
                core=Path("/tmp/core"),
                expected_core_sha256=None,
                gobjects=0x595B7E0,
                fname_root_slot=0x5956F30,
                anchor_index=8,
                negative_limit=1,
                max_scan_index=8,
                resolve_names=False,
            )

        self.assertFalse(report["deterministic_negative_cohort"])
        self.assertEqual(report["blockers"], ["core_sha256_not_provided"])
        self.assertNotIn("core_path", report)
        self.assertTrue(report["core_path_redacted"])

    def test_output_artifact_identity_binds_canonical_report(self) -> None:
        args = argparse.Namespace(
            core=["fixture=/tmp/core"],
            core_sha256=[],
            gobjects=0x595B7E0,
            fname_root_slot=0x5956F30,
            anchor_index=8,
            negative_limit=1,
            max_scan_index=8,
            skip_name_resolution=True,
            capture_id="zero-serial-test",
            evidence_pack_id="zero-serial-pack",
            require_output_artifact_identity=True,
            output=None,
        )
        source = {
            "source_label": "fixture",
            "core_path_redacted": True,
            "core_sha256": "a" * 64,
            "core_sha256_verified": True,
            "deterministic_negative_cohort": True,
            "blockers": [],
            "metadata": {},
            "scan_totals": {},
            "zero_serial_negative_samples": [{"index": 0}],
            "positive_anchor": {"index": 8, "item_dword_0x8": 1001},
        }

        with mock.patch.object(samples, "build_source_report", return_value=source):
            report = samples.build_report(args)

        identity = report["output_artifact_identity"]
        self.assertEqual(identity["artifact_kind"], samples.REPORT_SCHEMA)
        self.assertEqual(identity["capture_id"], "zero-serial-test")
        self.assertEqual(identity["evidence_pack_id"], "zero-serial-pack")
        expected_hash = hashlib.sha256(
            samples.canonical_json_bytes(
                {
                    "artifact_identity": {
                        "artifact_kind": samples.REPORT_SCHEMA,
                        "capture_id": "zero-serial-test",
                        "evidence_pack_id": "zero-serial-pack",
                    },
                    "report": samples.canonical_report(report),
                }
            )
        ).hexdigest()
        self.assertEqual(identity["artifact_sha256"], expected_hash)
        serialized = json.dumps(report)
        self.assertNotIn("/tmp/core", serialized)

    def test_rejects_partial_or_unsafe_output_identity_args(self) -> None:
        with self.assertRaises(SystemExit):
            samples.validate_output_identity_args(
                argparse.Namespace(
                    capture_id="zero-serial-test",
                    evidence_pack_id=None,
                    require_output_artifact_identity=False,
                )
            )
        with self.assertRaises(SystemExit):
            samples.validate_output_identity_args(
                argparse.Namespace(
                    capture_id="../bad",
                    evidence_pack_id="zero-serial-pack",
                    require_output_artifact_identity=False,
                )
            )


if __name__ == "__main__":
    unittest.main()
