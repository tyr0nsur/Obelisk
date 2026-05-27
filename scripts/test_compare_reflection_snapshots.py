#!/usr/bin/env python3
"""Tests for compare_reflection_snapshots.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


def base_snapshot() -> dict[str, object]:
    return {
        "schema": "obelisk.ufunction-chain.snapshot.v1",
        "evidence": {
            "ark_binary_sha256": "a" * 64,
            "obelisk_commit": "1111111",
            "source": "offline_core",
            "status": "candidate-only",
        },
        "metadata": {"object_count": 1, "max_object_scan": 10},
        "targets": [
            {
                "inspection_mode": "ufunction",
                "status": "candidate",
                "reject_reasons": [],
                "membership": {"target": "candidate-uobject", "class": "candidate-uobject", "outer": "candidate-uobject"},
                "target": {
                    "kind": "index",
                    "value": 10,
                    "object_index": 10,
                    "name": "CanUse",
                    "name_index": 100,
                    "class_name": "Function",
                    "class_name_index": 200,
                    "class_object_index": 300,
                    "outer_name": "PrimalItem",
                    "outer_name_index": 400,
                    "outer_class_name": "Class",
                    "outer_object_index": 500,
                },
                "num_parms": 2,
                "parms_size": 2,
                "function_flags": "0x204000",
                "return_value_offset": "0x1",
                "property_chain": {
                    "status": "candidate",
                    "reject_reasons": [],
                    "expected_count": 2,
                    "observed_count": 2,
                    "parms_size": 2,
                    "properties": [
                        {
                            "depth": 0,
                            "object_index": 11,
                            "name": "bIgnoreCooldown",
                            "name_index": 101,
                            "class_name": "BoolProperty",
                            "class_name_index": 201,
                            "class_object_index": 301,
                            "offset_internal": 0,
                            "element_size": 1,
                            "array_dim": 1,
                            "property_flags": "0x80",
                            "status": "candidate",
                            "reject_reasons": [],
                            "membership_status": "candidate-uobject",
                            "class_membership_status": "candidate-uobject",
                            "outer_membership_status": "candidate-uobject",
                        },
                        {
                            "depth": 1,
                            "object_index": 12,
                            "name": "ReturnValue",
                            "name_index": 102,
                            "class_name": "BoolProperty",
                            "class_name_index": 201,
                            "class_object_index": 301,
                            "offset_internal": 1,
                            "element_size": 1,
                            "array_dim": 1,
                            "property_flags": "0x80",
                            "status": "candidate",
                            "reject_reasons": [],
                            "membership_status": "candidate-uobject",
                            "class_membership_status": "candidate-uobject",
                            "outer_membership_status": "candidate-uobject",
                        },
                    ],
                },
            }
        ],
    }


def write_snapshot(root: Path, payload: dict[str, object], name: str = "PrimalItem.CanUse.snapshot.json") -> Path:
    path = root / name
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def run_compare(base: Path, candidate: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT_DIR / "compare_reflection_snapshots.py"),
            "--base-root",
            str(base),
            "--candidate-root",
            str(candidate),
            *extra,
        ],
        text=True,
        capture_output=True,
    )


class CompareReflectionSnapshotsTests(unittest.TestCase):
    def test_accepts_identical_layout_while_ignoring_indices_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            right = deepcopy(left)
            right["evidence"]["obelisk_commit"] = "2222222"  # type: ignore[index]
            right["metadata"]["object_count"] = 999  # type: ignore[index]
            right["targets"][0]["target"]["object_index"] = 999  # type: ignore[index]
            right["targets"][0]["target"]["name_index"] = 999  # type: ignore[index]
            right["targets"][0]["property_chain"]["properties"][0]["object_index"] = 999  # type: ignore[index]
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"], {"accepted": 1, "inconclusive": 0, "rejected": 0})

    def test_strict_identity_indices_rejects_index_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            right = deepcopy(left)
            right["targets"][0]["target"]["name_index"] = 999  # type: ignore[index]
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            result = run_compare(base, candidate, "--strict-identity-indices", "--json")

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"]["rejected"], 1)

    def test_rejects_layout_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            right = deepcopy(left)
            right["targets"][0]["property_chain"]["properties"][1]["offset_internal"] = 2  # type: ignore[index]
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"]["rejected"], 1)
        self.assertIn("offset_internal", report["results"][0]["diffs"][0]["path"])

    def test_marks_missing_or_raw_snapshot_inconclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            right = deepcopy(left)
            right["targets"][0]["object"] = "0x12345678"  # type: ignore[index]
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"]["inconclusive"], 1)
        self.assertTrue(any(reason.startswith("candidate:forbidden_key") for reason in report["results"][0]["reasons"]))

    def test_marks_ark_sha_mismatch_inconclusive_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            right = deepcopy(left)
            right["evidence"]["ark_binary_sha256"] = "b" * 64  # type: ignore[index]
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["results"][0]["reasons"], ["ark_binary_sha256_mismatch"])

    def test_marks_non_offline_candidate_evidence_inconclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            right = deepcopy(left)
            right["evidence"]["source"] = "runtime_probe"  # type: ignore[index]
            right["evidence"]["status"] = "accepted"  # type: ignore[index]
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"]["inconclusive"], 1)
        self.assertIn("candidate:evidence_source_runtime_probe", report["results"][0]["reasons"])
        self.assertIn("candidate:evidence_status_accepted", report["results"][0]["reasons"])

    def test_strict_identity_indices_rejects_nested_index_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            left["targets"][0]["property_chain"]["properties"][0]["array_inner_candidate"] = {  # type: ignore[index]
                "status": "candidate",
                "reject_reasons": [],
                "membership_status": "candidate-uobject",
                "inner_property": {
                    "object_index": 2000,
                    "name": "InventoryItems",
                    "name_index": 3000,
                    "class_name": "ObjectProperty",
                    "class_name_index": 4000,
                    "class_object_index": 5000,
                },
            }
            right = deepcopy(left)
            right["targets"][0]["property_chain"]["properties"][0]["array_inner_candidate"]["inner_property"]["name_index"] = 999  # type: ignore[index]
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            loose = run_compare(base, candidate, "--json")
            strict = run_compare(base, candidate, "--strict-identity-indices", "--json")

        self.assertEqual(loose.returncode, 0, loose.stderr + loose.stdout)
        self.assertEqual(strict.returncode, 1)
        report = json.loads(strict.stdout)
        self.assertEqual(report["counts"]["rejected"], 1)
        self.assertIn("array_inner_candidate.inner_property.name_index", report["results"][0]["diffs"][0]["path"])


if __name__ == "__main__":
    unittest.main()
