#!/usr/bin/env python3

import argparse
import json
import tempfile
import unittest
from pathlib import Path
import sys
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scan_resource_handle_serials as scan
import validate_offline_artifact_gate as gate


class ScanResourceHandleSerialsTests(unittest.TestCase):
    def test_summarizes_serial_and_flag_evidence(self) -> None:
        summary = scan.summarize_objects(
            [
                {
                    "index": 1,
                    "address": "0x1000",
                    "class_name": "Function",
                    "name": "Zero",
                    "flags": 0x81,
                    "fuobject_item": "0x2000",
                    "item_dword_0x8": 0,
                    "item_dword_0xC": 17,
                    "internal_index_matches": True,
                },
                {
                    "index": 2,
                    "address": "0x1010",
                    "class_name": "LinkerLoad",
                    "name": "Serial",
                    "flags": 0x100,
                    "fuobject_item": "0x2010",
                    "item_dword_0x8": 1001,
                    "item_dword_0xC": 23,
                    "internal_index_matches": True,
                },
                {
                    "index": 3,
                    "address": "0x1020",
                    "class_name": "LinkerLoad",
                    "name": "Serial2",
                    "flags": 0x4000,
                    "fuobject_item": "0x2020",
                    "item_dword_0x8": 1002,
                    "item_dword_0xC": 29,
                    "internal_index_matches": False,
                },
                {
                    "index": 4,
                    "address": "0x1030",
                    "class_name": "Class",
                    "name": "Missing",
                    "flags": None,
                    "fuobject_item": "0x2030",
                    "item_dword_0x8": None,
                    "item_dword_0xC": None,
                    "internal_index_matches": True,
                },
                {
                    "index": 5,
                    "address": "0x1040",
                    "class_name": "Class",
                    "name": "UnreachableMaskCandidate",
                    "flags": 0x8000,
                    "fuobject_item": "0x2040",
                    "item_dword_0x8": 1003,
                    "item_dword_0xC": 31,
                    "internal_index_matches": True,
                },
            ],
            sample_limit=1,
        )

        self.assertEqual(
            summary["totals"],
            {
                "objects_read": 5,
                "serial_zero": 1,
                "serial_nonzero": 3,
                "serial_missing": 1,
                "flags_0x100": 1,
                "flags_0x4000": 1,
                "flags_0x8000": 1,
                "flags_any": 3,
                "flags_none_of_masks": 2,
                "membership_pass_count": 4,
                "membership_fail_count": 1,
                "internal_index_mismatch": 1,
            },
        )
        self.assertEqual(summary["top_nonzero_serial_classes"], [("LinkerLoad", 2), ("Class", 1)])
        self.assertEqual(len(summary["nonzero_serial_samples"]), 1)
        self.assertEqual(summary["nonzero_serial_samples"][0]["item_dword_0x8"], 1001)
        self.assertEqual(summary["nonzero_serial_samples"][0]["membership"], "candidate-uobject")
        self.assertEqual(len(summary["flag_mask_samples"]), 1)
        self.assertEqual(summary["flag_mask_samples"][0]["flags"], 0x100)
        self.assertEqual(len(summary["flag_rejection_candidate_samples"]), 1)
        self.assertEqual(
            summary["flag_rejection_candidate_samples"][0],
            {
                "index": 2,
                "serial": 1001,
                "object_ptr_present": True,
                "gobjects_membership_pass": True,
                "flags": 0x100,
                "has_0x100": True,
                "has_0x4000": False,
                "has_0x8000": False,
                "policy_result_strict": "reject",
                "policy_result_allow4000": "reject",
            },
        )
        self.assertEqual(len(summary["negative_samples"]), 1)
        self.assertEqual(summary["negative_samples"][0]["item_dword_0x8"], 0)

    def test_flag_rejection_candidate_allows_0x4000_in_allow4000_mode(self) -> None:
        summary = scan.summarize_objects(
            [
                {
                    "index": 7,
                    "address": "0x7000",
                    "flags": 0x4000,
                    "fuobject_item": "0x2070",
                    "item_dword_0x8": 7001,
                    "internal_index_matches": True,
                },
            ]
        )

        self.assertEqual(
            summary["flag_rejection_candidate_samples"][0],
            {
                "index": 7,
                "serial": 7001,
                "object_ptr_present": True,
                "gobjects_membership_pass": True,
                "flags": 0x4000,
                "has_0x100": False,
                "has_0x4000": True,
                "has_0x8000": False,
                "policy_result_strict": "reject",
                "policy_result_allow4000": "allow_candidate",
            },
        )

    def test_does_not_call_membership_or_zero_serial_flag_hits_rejection_candidates(self) -> None:
        summary = scan.summarize_objects(
            [
                {
                    "index": 8,
                    "address": "0x8000",
                    "flags": 0x100,
                    "fuobject_item": "0x2080",
                    "item_dword_0x8": 0,
                    "internal_index_matches": True,
                },
                {
                    "index": 9,
                    "address": "0x9000",
                    "flags": 0x8000,
                    "fuobject_item": "0x2090",
                    "item_dword_0x8": 9001,
                    "internal_index_matches": False,
                },
            ]
        )

        self.assertEqual(summary["totals"]["flags_any"], 2)
        self.assertEqual(summary["flag_rejection_candidate_samples"], [])

    def test_rejects_negative_sample_limit(self) -> None:
        with self.assertRaises(ValueError):
            scan.summarize_objects([], sample_limit=-1)

    def test_classifies_membership_failures(self) -> None:
        self.assertEqual(scan.membership_status({"fuobject_item": None}), "missing-fuobject-item")
        self.assertEqual(
            scan.membership_status({"fuobject_item": "0x10", "address": "0x0"}),
            "missing-uobject-address",
        )
        self.assertEqual(
            scan.membership_status({"fuobject_item": "0x10", "address": "0x20", "internal_index_matches": False}),
            "internal-index-mismatch",
        )
        self.assertEqual(
            scan.membership_status({"fuobject_item": "0x10", "address": "0x20", "internal_index_matches": True}),
            "candidate-uobject",
        )

    def test_consume_gate_expectation_requires_identity_and_candidates(self) -> None:
        blocked = scan.consume_gate_expectation(
            {"flag_rejection_candidate_samples": []},
            core_sha256_verified=False,
            binary_sha256=None,
        )
        self.assertFalse(blocked["consume_ready"])
        self.assertFalse(blocked["promote_ready"])
        self.assertEqual(
            blocked["blockers"],
            [
                "core_sha256_not_verified",
                "binary_sha256_missing",
                "missing_flag_rejection_candidate_samples",
            ],
        )

        ready = scan.consume_gate_expectation(
            {"flag_rejection_candidate_samples": [{"index": 1}]},
            core_sha256_verified=True,
            binary_sha256="a" * 64,
        )
        self.assertTrue(ready["consume_ready"])
        self.assertFalse(ready["promote_ready"])
        self.assertEqual(ready["blockers"], [])

    def test_gate_ready_args_require_explicit_identity_and_output(self) -> None:
        args = argparse.Namespace(
            core_sha256=None,
            binary_sha256="a" * 64,
            gobjects=0x595B7E0,
            fname_root_slot=0x5956F30,
            offline_root=Path("/tmp/offline"),
        )

        with self.assertRaises(SystemExit) as raised:
            scan.validate_gate_ready_args(args, core=Path("/tmp/offline/core"), output=None)

        self.assertIn("--core-sha256", str(raised.exception))
        self.assertIn("--output", str(raised.exception))

    def test_gate_ready_args_require_core_and_output_under_offline_root(self) -> None:
        with self.assertRaises(SystemExit):
            scan.validate_gate_ready_args(
                argparse.Namespace(
                    core_sha256="a" * 64,
                    binary_sha256="b" * 64,
                    gobjects=0x595B7E0,
                    fname_root_slot=0x5956F30,
                    offline_root=Path("/tmp/offline"),
                ),
                core=Path("/tmp/other/core"),
                output=Path("/tmp/offline/out.json"),
            )

        scan.validate_gate_ready_args(
            argparse.Namespace(
                core_sha256="a" * 64,
                binary_sha256="b" * 64,
                gobjects=0x595B7E0,
                fname_root_slot=0x5956F30,
                offline_root=Path("/tmp/offline"),
            ),
            core=Path("/tmp/offline/core"),
            output=Path("/tmp/offline/out.json"),
        )

    def test_redacts_path_arguments_from_provenance_argv(self) -> None:
        self.assertEqual(
            scan.redact_argv(
                [
                    "scripts/scan_resource_handle_serials.py",
                    "--gate-ready",
                    "--core",
                    "/servidor/ark/workspace-offline/core",
                    "--output=/servidor/ark/workspace-offline/out.json",
                    "--label",
                    "vanilla",
                ]
            ),
            [
                "scripts/scan_resource_handle_serials.py",
                "--gate-ready",
                "--core",
                "<redacted-path>",
                "--output=<redacted-path>",
                "--label",
                "vanilla",
            ],
        )

    def test_build_report_output_is_accepted_by_offline_artifact_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            core = workspace / "core"
            report_path = workspace / "resource-handle-serial-scan.json"
            core.parent.mkdir(parents=True)
            core.write_bytes(b"offline copied core fixture\n")
            core_sha256 = scan.sha256_file(core)

            class FakeCoreMemory:
                def __init__(self, path: Path) -> None:
                    self.path = path

                def close(self) -> None:
                    pass

            def fake_iter_uobjects(
                _memory: FakeCoreMemory,
                *,
                gobjects: int,
                fname_root_slot: int,
                max_objects: int,
                resolve_names: bool = True,
            ):
                self.assertTrue(resolve_names)
                return (
                    {"source": "fixture", "max_objects": max_objects},
                    [
                        {
                            "index": 0,
                            "address": "0x1000",
                            "class_name": "Fixture",
                            "name": "Candidate",
                            "flags": 0x100,
                            "fuobject_item": "0x2000",
                            "item_dword_0x8": 1001,
                            "item_dword_0xC": 0,
                            "internal_index_matches": True,
                        }
                    ],
                )

            with (
                mock.patch.object(scan.uobjects, "CoreMemory", FakeCoreMemory),
                mock.patch.object(scan.uobjects, "iter_uobjects", fake_iter_uobjects),
            ):
                report = scan.build_report(
                    core,
                    gobjects=0x595B7E0,
                    fname_root_slot=0x5956F30,
                    max_objects=1,
                    label="unit-test",
                    core_sha256=core_sha256,
                    binary_sha256="a" * 64,
                    sample_limit=4,
                    argv=[
                        "scan_resource_handle_serials.py",
                        "--gate-ready",
                        "--core",
                        "/servidor/ark/workspace-offline/core",
                        "--output",
                        "/servidor/ark/workspace-offline/out.json",
                    ],
                    obelisk_commit="test-commit",
                )

            self.assertTrue(report["consume_gate_expectation"]["consume_ready"])
            self.assertNotIn("/servidor/ark", " ".join(report["provenance"]["argv"]))
            report_path.write_text(json.dumps(report), encoding="utf-8")
            result = gate.build_result(
                argparse.Namespace(
                    root=workspace,
                    protected_root=protected,
                    manifest=[report_path],
                    artifact=[],
                    expected_binary_sha256="a" * 64,
                    mode="consume",
                    strict_target_set_coverage=False,
                    json=True,
                )
            )

            self.assertEqual(result["blockers"], [])

    def test_build_report_can_skip_name_resolution_for_large_flag_scans(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            core = Path(tmp) / "core"
            core.write_bytes(b"offline copied core fixture\n")
            core_sha256 = scan.sha256_file(core)

            class FakeCoreMemory:
                def __init__(self, path: Path) -> None:
                    self.path = path

                def close(self) -> None:
                    pass

            def fake_iter_uobjects(
                _memory: FakeCoreMemory,
                *,
                gobjects: int,
                fname_root_slot: int,
                max_objects: int,
                resolve_names: bool = True,
            ):
                self.assertFalse(resolve_names)
                return (
                    {"source": "fixture", "max_objects": max_objects, "name_resolution": "disabled"},
                    [
                        {
                            "index": 0,
                            "address": "0x1000",
                            "class_name": None,
                            "name": None,
                            "flags": 0x4000,
                            "fuobject_item": "0x2000",
                            "item_dword_0x8": 1001,
                            "item_dword_0xC": 0,
                            "internal_index_matches": True,
                        }
                    ],
                )

            with (
                mock.patch.object(scan.uobjects, "CoreMemory", FakeCoreMemory),
                mock.patch.object(scan.uobjects, "iter_uobjects", fake_iter_uobjects),
            ):
                report = scan.build_report(
                    core,
                    gobjects=0x595B7E0,
                    fname_root_slot=0x5956F30,
                    max_objects=1,
                    label="unit-test",
                    core_sha256=core_sha256,
                    binary_sha256="a" * 64,
                    sample_limit=4,
                    resolve_names=False,
                )

        self.assertEqual(report["metadata"]["name_resolution"], "disabled")
        self.assertEqual(report["provenance"]["name_resolution"], "disabled")
        self.assertEqual(report["totals"]["serial_nonzero"], 1)
        self.assertEqual(report["totals"]["flags_0x4000"], 1)
        self.assertEqual(report["totals"]["membership_pass_count"], 1)
        self.assertEqual(report["top_nonzero_serial_classes"], [("<unknown>", 1)])
        self.assertEqual(
            report["nonzero_serial_samples"][0],
            {
                "index": 0,
                "address": "0x1000",
                "class_name": None,
                "name": None,
                "flags": 0x4000,
                "fuobject_item": "0x2000",
                "item_dword_0x8": 1001,
                "item_dword_0xC": 0,
                "internal_index_matches": True,
                "membership": "candidate-uobject",
                "membership_pass": True,
            },
        )
        self.assertEqual(
            report["flag_rejection_candidate_samples"][0],
            {
                "index": 0,
                "serial": 1001,
                "object_ptr_present": True,
                "gobjects_membership_pass": True,
                "flags": 0x4000,
                "has_0x100": False,
                "has_0x4000": True,
                "has_0x8000": False,
                "policy_result_strict": "reject",
                "policy_result_allow4000": "allow_candidate",
            },
        )

    def test_build_report_output_rejects_incoherent_rejection_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            core = workspace / "core"
            report_path = workspace / "resource-handle-serial-scan.json"
            core.parent.mkdir(parents=True)
            core.write_bytes(b"offline copied core fixture\n")
            core_sha256 = scan.sha256_file(core)

            base_report = {
                "schema": scan.REPORT_SCHEMA,
                "status": "candidate_blocked",
                "evidence_kind": "internal_offline_scan_candidate",
                "core_path": str(core),
                "core_sha256": core_sha256,
                "core_sha256_verified": True,
                "binary_sha256": "a" * 64,
                "gobjects": "0x595b7e0",
                "fname_root_slot": "0x5956f30",
                "totals": {
                    "objects_read": 2,
                    "serial_nonzero": 1,
                    "membership_pass_count": 1,
                    "flags_any": 1,
                },
                "interpretation": {
                    "public_resource_handle_ready": False,
                },
                "flag_rejection_candidate_samples": [
                    {
                        "index": 1,
                        "serial": 7001,
                        "object_ptr_present": True,
                        "gobjects_membership_pass": True,
                        "flags": 0x4000,
                        "has_0x100": False,
                        "has_0x4000": True,
                        "has_0x8000": False,
                        "policy_result_strict": "reject",
                        "policy_result_allow4000": "reject",
                    }
                ],
            }
            report_path.write_text(json.dumps(base_report), encoding="utf-8")
            result = gate.build_result(
                argparse.Namespace(
                    root=workspace,
                    protected_root=protected,
                    manifest=[report_path],
                    artifact=[],
                    expected_binary_sha256="a" * 64,
                    mode="consume",
                    strict_target_set_coverage=False,
                    json=True,
                )
            )
            self.assertIn(
                "resource_handle_serial_scan_candidate_allow4000_policy_mismatch",
                {blocker["reason"] for blocker in result["blockers"]},
            )

            incoherent_report = dict(base_report)
            incoherent_report["flag_rejection_candidate_samples"] = [
                dict(base_report["flag_rejection_candidate_samples"][0])
            ]
            incoherent_report["flag_rejection_candidate_samples"][0]["serial"] = 0
            incoherent_report["flag_rejection_candidate_samples"][0]["gobjects_membership_pass"] = False
            incoherent_report["flag_rejection_candidate_samples"][0]["policy_result_allow4000"] = "allow_candidate"
            report_path.write_text(json.dumps(incoherent_report), encoding="utf-8")
            result = gate.build_result(
                argparse.Namespace(
                    root=workspace,
                    protected_root=protected,
                    manifest=[report_path],
                    artifact=[],
                    expected_binary_sha256="a" * 64,
                    mode="consume",
                    strict_target_set_coverage=False,
                    json=True,
                )
            )
            reasons = {blocker["reason"] for blocker in result["blockers"]}
            self.assertIn("resource_handle_serial_scan_candidate_serial_invalid", reasons)
            self.assertIn("resource_handle_serial_scan_candidate_membership_failed", reasons)


if __name__ == "__main__":
    unittest.main()
