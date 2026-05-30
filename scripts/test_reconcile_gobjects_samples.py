#!/usr/bin/env python3
"""Offline tests for reconcile_gobjects_samples.py."""

from __future__ import annotations

import hashlib
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
import enumerate_core_uobjects as enum
import reconcile_gobjects_samples as reconcile
import snapshot_evidence_pack
from test_scan_core_fname_tables import write_minimal_elf64_core


def build_core_fixture(path: Path) -> dict[str, int]:
    base = 0x20000000
    segment = bytearray(0x90000)
    addrs = {
        "base": base,
        "fname_root_slot": base + 0x100,
        "fname_table": base + 0x1000,
        "fname_chunk": base + 0x3000,
        "gobjects": base + 0x5000,
        "gobjects_chunks": base + 0x6000,
        "gobjects_chunk0": base + 0x7000,
        "package_object": base + 0x21000,
        "object_class": base + 0x21100,
        "package_class": base + 0x21200,
        "function_class": base + 0x21300,
        "chat_function": base + 0x21400,
        "mismatched_object": base + 0x21500,
    }

    def put_ptr(address: int, value: int) -> None:
        struct.pack_into("<Q", segment, address - base, value)

    def put_i32(address: int, value: int) -> None:
        struct.pack_into("<i", segment, address - base, value)

    def put_u32(address: int, value: int) -> None:
        struct.pack_into("<I", segment, address - base, value)

    def put_entry(index: int, text: bytes) -> None:
        entry = base + 0x4000 + index * 0x80
        put_ptr(addrs["fname_chunk"] + index * 8, entry)
        put_u32(entry, index * 2)
        segment[entry - base + 0x10 : entry - base + 0x10 + len(text)] = text

    def put_uobject(address: int, flags: int, internal_index: int, class_address: int, name_index: int, outer: int) -> None:
        put_u32(address + enum.UOBJECT_FLAGS_OFFSET, flags)
        put_i32(address + enum.UOBJECT_INTERNAL_INDEX_OFFSET, internal_index)
        put_ptr(address + enum.UOBJECT_CLASS_OFFSET, class_address)
        put_i32(address + enum.UOBJECT_NAME_INDEX_OFFSET, name_index)
        put_i32(address + enum.UOBJECT_NAME_NUMBER_OFFSET, 0)
        put_ptr(address + enum.UOBJECT_OUTER_OFFSET, outer)

    def put_item(index: int, object_address: int, dword_0x8: int, dword_0xc: int) -> None:
        item = addrs["gobjects_chunk0"] + index * enum.FUOBJECT_ITEM_SIZE
        put_ptr(item, object_address)
        put_u32(item + 0x8, dword_0x8)
        put_u32(item + 0xC, dword_0xc)

    put_ptr(addrs["fname_root_slot"], addrs["fname_table"])
    put_ptr(addrs["fname_table"], addrs["fname_chunk"])
    put_entry(0, b"None\x00")
    put_entry(1, b"/Script/CoreUObject\x00")
    put_entry(2, b"Object\x00")
    put_entry(3, b"Package\x00")
    put_entry(4, b"Function\x00")
    put_entry(5, b"ServerChat\x00")
    put_entry(6, b"Mismatched\x00")

    put_ptr(addrs["gobjects"] + enum.GOBJECTS_CHUNKS_OFFSET, addrs["gobjects_chunks"])
    put_i32(addrs["gobjects"] + enum.GOBJECTS_COUNT_OFFSET, 6)
    put_ptr(addrs["gobjects_chunks"], addrs["gobjects_chunk0"])

    put_uobject(addrs["package_object"], 1, 0, addrs["package_class"], 1, 0)
    put_uobject(addrs["object_class"], 1, 1, addrs["package_class"], 2, 0)
    put_uobject(addrs["package_class"], 1, 2, addrs["object_class"], 3, 0)
    put_uobject(addrs["function_class"], 1, 3, addrs["object_class"], 4, addrs["package_object"])
    put_uobject(addrs["chat_function"], 1, 4, addrs["function_class"], 5, addrs["package_object"])
    put_uobject(addrs["mismatched_object"], 1, 99, addrs["function_class"], 6, addrs["package_object"])

    put_item(0, addrs["package_object"], 0, 0x01020304)
    put_item(1, addrs["object_class"], 11, 0x11111111)
    put_item(2, addrs["package_class"], 12, 0x22222222)
    put_item(3, addrs["function_class"], 13, 0x33333333)
    put_item(4, addrs["chat_function"], 0, 0x11223344)
    put_item(5, addrs["mismatched_object"], 0, 0x55667788)

    write_minimal_elf64_core(path, base, bytes(segment))
    return addrs


def recompute_artifact_sha256(report: dict[str, object]) -> str:
    canonical_report = dict(report)
    identity = dict(canonical_report.pop("artifact_identity"))
    identity_without_hash = {
        "artifact_kind": identity["artifact_kind"],
        "capture_id": identity["capture_id"],
        "evidence_pack_id": identity["evidence_pack_id"],
    }
    canonical_material = {
        "artifact_identity": identity_without_hash,
        "report": canonical_report,
    }
    payload = json.dumps(canonical_material, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class ReconcileGObjectsSamplesTests(unittest.TestCase):
    def test_build_report_resolves_membership_and_static_reconciliation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            core = Path(temp_dir) / "core"
            addrs = build_core_fixture(core)

            report = reconcile.build_report(
                core,
                gobjects=addrs["gobjects"],
                fname_root_slot=addrs["fname_root_slot"],
                sample_indices=[("chat", 4)],
            )

        self.assertEqual(report["schema"], reconcile.REPORT_SCHEMA)
        self.assertEqual(
            report["artifact_identity"],
            {
                "artifact_kind": reconcile.REPORT_SCHEMA,
                "capture_id": reconcile.DEFAULT_CAPTURE_ID,
                "evidence_pack_id": reconcile.DEFAULT_EVIDENCE_PACK_ID,
                "artifact_sha256": recompute_artifact_sha256(report),
            },
        )
        self.assertEqual(report["summary"]["accepted_count"], 1)
        sample = report["samples"][0]
        self.assertEqual(sample["status"], "candidate-uobject")
        self.assertEqual(sample["fuobject_item"], hex(addrs["gobjects_chunk0"] + 4 * enum.FUOBJECT_ITEM_SIZE))
        self.assertEqual(sample["object"], hex(addrs["chat_function"]))
        self.assertEqual(sample["item_dword_0x8"], 0)
        self.assertEqual(sample["item_dword_0xc"], 0x11223344)
        self.assertEqual(sample["item_qword_0x8"], "0x1122334400000000")
        self.assertEqual(sample["uobject"]["internal_index"], 4)
        self.assertEqual(sample["object_name"], "ServerChat")
        self.assertEqual(sample["class_name"], "Function")
        self.assertEqual(sample["outer_name"], "/Script/CoreUObject")
        self.assertTrue(sample["membership"]["target"]["passes"])
        self.assertEqual(sample["membership"]["target"]["backref_object"], hex(addrs["chat_function"]))
        self.assertTrue(sample["membership"]["class"]["passes"])
        self.assertEqual(sample["membership"]["class"]["index"], 3)
        self.assertTrue(sample["membership"]["outer"]["passes"])
        self.assertEqual(
            sample["static_handle_accessor_reconciliation"]["compatibility"],
            "compatible_with_lazy_or_absent_serial_publication",
        )

    def test_build_report_rejects_internal_index_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            core = Path(temp_dir) / "core"
            addrs = build_core_fixture(core)

            report = reconcile.build_report(
                core,
                gobjects=addrs["gobjects"],
                fname_root_slot=addrs["fname_root_slot"],
                sample_indices=[("bad", 5)],
            )

        sample = report["samples"][0]
        self.assertEqual(sample["status"], "rejected")
        self.assertIn("internal_index_mismatch", sample["reject_reasons"])
        self.assertIn("membership_check_failed", sample["reject_reasons"])
        self.assertFalse(sample["membership"]["target"]["passes"])

    def test_build_report_rejects_out_of_bounds_without_item_read(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            core = Path(temp_dir) / "core"
            addrs = build_core_fixture(core)

            report = reconcile.build_report(
                core,
                gobjects=addrs["gobjects"],
                fname_root_slot=addrs["fname_root_slot"],
                sample_indices=[("too_high", 99)],
            )

        sample = report["samples"][0]
        self.assertEqual(sample["status"], "rejected")
        self.assertIn("sample_index_out_of_bounds", sample["reject_reasons"])
        self.assertNotIn("missing_gobjects_chunk", sample["reject_reasons"])
        self.assertIsNone(sample["fuobject_item"])
        self.assertIsNone(sample["object"])

    def test_cli_writes_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            output = root / "report.json"
            addrs = build_core_fixture(core)

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "reconcile_gobjects_samples.py"),
                    "--core",
                    str(core),
                    "--gobjects-candidate",
                    hex(addrs["gobjects"]),
                    "--fname-root-slot",
                    hex(addrs["fname_root_slot"]),
                    "--sample-index",
                    "chat=4",
                    "--output",
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(payload["inputs"]["sample_indices"], [{"label": "chat", "index": 4}])
        self.assertEqual(payload["summary"]["membership_pass_count"], 1)

    def test_cli_identity_hash_is_stable_across_output_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            output_a = root / "report-a.json"
            output_b = root / "nested" / "report-b.json"
            addrs = build_core_fixture(core)
            base_args = [
                sys.executable,
                str(SCRIPT_DIR / "reconcile_gobjects_samples.py"),
                "--core",
                str(core),
                "--gobjects-candidate",
                hex(addrs["gobjects"]),
                "--fname-root-slot",
                hex(addrs["fname_root_slot"]),
                "--artifact-kind",
                "obelisk.gobjects-sample-reconciliation.v1",
                "--capture-id",
                "capture_2026-05-30",
                "--evidence-pack-id",
                "evidence-pack.alpha_1",
                "--strict-artifact-identity",
                "--sample-index",
                "chat=4",
            ]

            subprocess.run([*base_args, "--output", str(output_a)], check=True, capture_output=True, text=True)
            subprocess.run([*base_args, "--output", str(output_b)], check=True, capture_output=True, text=True)

            payload_a = json.loads(output_a.read_text(encoding="utf-8"))
            payload_b = json.loads(output_b.read_text(encoding="utf-8"))

        self.assertEqual(payload_a["artifact_identity"]["capture_id"], "capture_2026-05-30")
        self.assertEqual(payload_a["artifact_identity"]["evidence_pack_id"], "evidence-pack.alpha_1")
        self.assertEqual(payload_a["artifact_identity"]["artifact_sha256"], recompute_artifact_sha256(payload_a))
        self.assertEqual(payload_b["artifact_identity"]["artifact_sha256"], recompute_artifact_sha256(payload_b))
        self.assertEqual(
            payload_a["artifact_identity"]["artifact_sha256"],
            payload_b["artifact_identity"]["artifact_sha256"],
        )

    def test_cli_strict_artifact_identity_rejects_default_ids_before_building_report(self) -> None:
        with mock.patch.object(
            sys,
            "argv",
            [
                "reconcile_gobjects_samples.py",
                "--core",
                "/tmp/nonexistent-core",
                "--gobjects-candidate",
                "0x595b7e0",
                "--fname-root-slot",
                "0x5956f30",
                "--sample-index",
                "0",
                "--strict-artifact-identity",
            ],
        ), mock.patch.object(reconcile, "build_report") as build_report:
            with self.assertRaisesRegex(
                SystemExit,
                "--strict-artifact-identity requires explicit --capture-id and --evidence-pack-id",
            ):
                reconcile.main()

        build_report.assert_not_called()

    def test_cli_strict_artifact_identity_allows_explicit_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            output = root / "report.json"
            addrs = build_core_fixture(core)

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "reconcile_gobjects_samples.py"),
                    "--core",
                    str(core),
                    "--gobjects-candidate",
                    hex(addrs["gobjects"]),
                    "--fname-root-slot",
                    hex(addrs["fname_root_slot"]),
                    "--capture-id",
                    "capture.strict_2026-05-30",
                    "--evidence-pack-id",
                    "evidence-pack.strict_1",
                    "--sample-index",
                    "chat=4",
                    "--strict-artifact-identity",
                    "--output",
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(payload["artifact_identity"]["capture_id"], "capture.strict_2026-05-30")
        self.assertEqual(payload["artifact_identity"]["evidence_pack_id"], "evidence-pack.strict_1")
        self.assertEqual(payload["artifact_identity"]["artifact_sha256"], recompute_artifact_sha256(payload))

    def test_cli_rejects_unsafe_identity_ids(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIR / "reconcile_gobjects_samples.py"),
                "--core",
                "/tmp/nonexistent-core",
                "--gobjects-candidate",
                "0x595b7e0",
                "--fname-root-slot",
                "0x5956f30",
                "--capture-id",
                "../bad",
                "--sample-index",
                "0",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--capture-id must not contain '..'", result.stderr)

    def test_cli_strict_artifact_identity_requires_capture_id(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIR / "reconcile_gobjects_samples.py"),
                "--core",
                "/tmp/nonexistent-core",
                "--gobjects-candidate",
                "0x595b7e0",
                "--fname-root-slot",
                "0x5956f30",
                "--evidence-pack-id",
                "evidence-pack.alpha_1",
                "--strict-artifact-identity",
                "--sample-index",
                "0",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires explicit --capture-id", result.stderr)

    def test_cli_strict_artifact_identity_requires_evidence_pack_id(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIR / "reconcile_gobjects_samples.py"),
                "--core",
                "/tmp/nonexistent-core",
                "--gobjects-candidate",
                "0x595b7e0",
                "--fname-root-slot",
                "0x5956f30",
                "--capture-id",
                "capture_2026-05-30",
                "--strict-artifact-identity",
                "--sample-index",
                "0",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires explicit --evidence-pack-id", result.stderr)

    def test_cli_rejects_protected_core_path(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIR / "reconcile_gobjects_samples.py"),
                "--core",
                "/servidor/ark/obelisk/dumps/core",
                "--gobjects-candidate",
                "0x595b7e0",
                "--fname-root-slot",
                "0x5956f30",
                "--sample-index",
                "0",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must not read from protected server root", result.stderr)

    def test_main_rejects_protected_output_before_building_report(self) -> None:
        with mock.patch.object(
            sys,
            "argv",
            [
                "reconcile_gobjects_samples.py",
                "--core",
                "/servidor/ark/workspace-offline/core",
                "--gobjects-candidate",
                "0x595b7e0",
                "--fname-root-slot",
                "0x5956f30",
                "--sample-index",
                "0",
                "--output",
                "/servidor/ark/blocked.json",
            ],
        ), mock.patch.object(reconcile, "build_report") as build_report:
            with self.assertRaises(SystemExit) as raised:
                reconcile.main()

        self.assertIn("must not write under protected server root", str(raised.exception))
        build_report.assert_not_called()

    def test_main_strict_artifact_identity_rejects_before_building_report(self) -> None:
        with mock.patch.object(
            sys,
            "argv",
            [
                "reconcile_gobjects_samples.py",
                "--core",
                "/tmp/nonexistent-core",
                "--gobjects-candidate",
                "0x595b7e0",
                "--fname-root-slot",
                "0x5956f30",
                "--strict-artifact-identity",
                "--sample-index",
                "0",
            ],
        ), mock.patch.object(reconcile, "build_report") as build_report:
            with self.assertRaises(SystemExit) as raised:
                reconcile.main()

        self.assertIn("requires explicit --capture-id and --evidence-pack-id", str(raised.exception))
        build_report.assert_not_called()

    def test_main_rejects_unignored_in_repo_output_before_building_report(self) -> None:
        with mock.patch.object(
            sys,
            "argv",
            [
                "reconcile_gobjects_samples.py",
                "--core",
                "/tmp/nonexistent-core",
                "--gobjects-candidate",
                "0x595b7e0",
                "--fname-root-slot",
                "0x5956f30",
                "--sample-index",
                "0",
                "--output",
                str(REPO_ROOT / "docs" / "gobjects-report.json"),
            ],
        ), mock.patch.object(reconcile, "build_report") as build_report:
            with self.assertRaisesRegex(SystemExit, "--output is inside the repository but is not ignored by Git"):
                reconcile.main()

        build_report.assert_not_called()

    def test_rejects_textually_protected_non_workspace_symlink_to_workspace_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            protected = root / "server-root"
            workspace = protected / "workspace-offline"
            blocked = protected / "obelisk"
            workspace.mkdir(parents=True)
            blocked.mkdir()
            core = workspace / "core"
            core.write_bytes(b"core")
            link = blocked / "core"
            link.symlink_to(core)

            with (
                mock.patch.object(snapshot_evidence_pack, "SERVER_ROOT", protected),
                mock.patch.object(snapshot_evidence_pack, "APPROVED_OFFLINE_WORKSPACE_ROOTS", (workspace,)),
                self.assertRaisesRegex(SystemExit, "--core must not read from protected server root"),
            ):
                reconcile.reject_protected_input_path(link, "--core")


if __name__ == "__main__":
    unittest.main()
