#!/usr/bin/env python3
"""Offline tests for scan_core_fname_tables.py."""

from __future__ import annotations

import contextlib
import io
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
import scan_core_fname_tables as scanner
import validate_fname_index_manifest as manifest_validator


ARK_SHA = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"


def write_minimal_elf64_core(path: Path, segment_vaddr: int, segment: bytes) -> None:
    header_size = 64
    phoff = header_size
    phentsize = 56
    segment_offset = 0x1000

    data = bytearray(segment_offset + len(segment))
    data[0:4] = b"\x7fELF"
    data[4] = 2
    data[5] = 1
    data[6] = 1
    struct.pack_into("<H", data, 0x10, 4)
    struct.pack_into("<H", data, 0x12, 0x3E)
    struct.pack_into("<I", data, 0x14, 1)
    struct.pack_into("<Q", data, 0x20, phoff)
    struct.pack_into("<H", data, 0x34, header_size)
    struct.pack_into("<H", data, 0x36, phentsize)
    struct.pack_into("<H", data, 0x38, 1)

    struct.pack_into(
        "<IIQQQQQQ",
        data,
        phoff,
        scanner.PT_LOAD,
        6,
        segment_offset,
        segment_vaddr,
        0,
        len(segment),
        len(segment),
        0x1000,
    )
    data[segment_offset : segment_offset + len(segment)] = segment
    path.write_bytes(data)


class ScanCoreFNameTablesTests(unittest.TestCase):
    def build_core_fixture(self, core: Path) -> dict[str, int]:
        segment_vaddr = 0x10000000
        table = segment_vaddr + 0x1000
        chunk0 = segment_vaddr + 0x3000
        entry0 = segment_vaddr + 0x5000
        client_entry = segment_vaddr + 0x5100
        server_entry = segment_vaddr + 0x5200
        mission_entry = segment_vaddr + 0x5300
        root_slot = segment_vaddr + 0x8000
        segment = bytearray(0x20000)

        def put_ptr(address: int, value: int) -> None:
            struct.pack_into("<Q", segment, address - segment_vaddr, value)

        def put_u32(address: int, value: int) -> None:
            struct.pack_into("<I", segment, address - segment_vaddr, value)

        def put_entry(address: int, index: int, name: bytes) -> None:
            put_u32(address, index * 2)
            segment[address - segment_vaddr + 0x10 : address - segment_vaddr + 0x10 + len(name)] = name

        put_ptr(table, chunk0)
        put_ptr(root_slot, table)
        put_u32(table + 0x800, 10000)
        put_u32(table + 0x804, 1)
        put_ptr(chunk0, entry0)
        put_ptr(chunk0 + 4884 * 8, client_entry)
        put_ptr(chunk0 + 9619 * 8, server_entry)
        put_ptr(chunk0 + 9622 * 8, mission_entry)
        put_entry(entry0, 0, b"None\x00")
        put_entry(client_entry, 4884, b"ClientMessage\x00")
        put_entry(server_entry, 9619, b"ServerChat\x00")
        put_entry(mission_entry, 9622, b"SetActiveMissionDebugFlags\x00")
        write_minimal_elf64_core(core, segment_vaddr, bytes(segment))
        return {
            "table": table,
            "chunk0": chunk0,
            "root_slot": root_slot,
        }

    def test_scans_legacy_fname_table_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            core = Path(temp_dir) / "core"
            fixture = self.build_core_fixture(core)

            memory = scanner.CoreMemory(core)
            try:
                candidates = scanner.scan_fname_tables(
                    memory,
                    indices=scanner.DEFAULT_INDICES,
                    max_none_hits=16,
                    max_pointer_hits=16,
                )
            finally:
                memory.close()

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["table"], hex(fixture["table"]))
        self.assertEqual(candidates[0]["chunk0"], hex(fixture["chunk0"]))
        self.assertEqual(candidates[0]["header_index_ok"], 4)
        names = {item["label"]: item["name"] for item in candidates[0]["resolved_indices"]}
        self.assertEqual(names["None"], "None")
        self.assertEqual(names["ClientMessage"], "ClientMessage")
        self.assertEqual(names["ServerChat"], "ServerChat")
        self.assertEqual(names["SetActiveMissionDebugFlags"], "SetActiveMissionDebugFlags")

    def test_validates_direct_fname_root_slot_without_broad_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            output = root / "root-validation.json"
            fixture = self.build_core_fixture(core)

            with contextlib.redirect_stdout(io.StringIO()):
                result = scanner.main_from_args(
                    [
                        "--core",
                        str(core),
                        "--root-slot",
                        hex(fixture["root_slot"]),
                        "--require-exact-root",
                        "--no-default-indices",
                        "--index",
                        "None=0",
                        "--index",
                        "ServerChat=9619",
                        "--json",
                        "--json-out",
                        str(output),
                    ]
                )

            payload = scanner.json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(result, 0)
        self.assertEqual(payload["schema"], "obelisk.core-fname-root-validation.v1")
        self.assertEqual(payload["candidates"], [])
        self.assertTrue(payload["manifest_readiness"]["ready"])
        self.assertEqual(payload["manifest_readiness"]["exact_match_count"], 2)
        self.assertEqual(payload["root_validation"]["root_slot"], hex(fixture["root_slot"]))
        self.assertEqual(payload["root_validation"]["table"], hex(fixture["table"]))
        names = {
            item["label"]: item["name"]
            for item in payload["root_validation"]["resolved_indices"]
        }
        self.assertEqual(names["None"], "None")
        self.assertEqual(names["ServerChat"], "ServerChat")

    def test_direct_fname_root_validation_fails_closed_on_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            fixture = self.build_core_fixture(core)

            with self.assertRaises(SystemExit) as raised:
                with contextlib.redirect_stdout(io.StringIO()):
                    scanner.main_from_args(
                        [
                            "--core",
                            str(core),
                            "--root-slot",
                            hex(fixture["root_slot"]),
                            "--require-exact-root",
                            "--no-default-indices",
                            "--index",
                            "NotServerChat=9619",
                            "--json",
                        ]
                    )

        self.assertIn("FName root validation failed", str(raised.exception))
        self.assertIn("requested_index_mismatch", str(raised.exception))

    def test_direct_fname_root_validation_rejects_protected_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            fixture = self.build_core_fixture(core)

            with self.assertRaises(SystemExit) as raised:
                scanner.main_from_args(
                    [
                        "--core",
                        str(core),
                        "--root-slot",
                        hex(fixture["root_slot"]),
                        "--json-out",
                        "/servidor/ark/obelisk/state/root-validation.json",
                    ]
                )

        self.assertIn(
            "--json-out must not write under protected server root /servidor/ark",
            str(raised.exception),
        )

    def test_no_default_indices_preserves_empty_index_set(self) -> None:
        args = scanner.parse_args(["--core", "/tmp/core", "--no-default-indices"])

        self.assertTrue(args.no_default_indices)
        self.assertEqual(args.index, [])

    def test_rejects_protected_server_core_path(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            scanner.main_from_args(
                [
                    "--core",
                    "/servidor/ark/serverfiles/core",
                    "--json",
                ]
            )

        self.assertIn(
            "--core must not read from protected server root /servidor/ark",
            str(raised.exception),
        )

    def test_rejects_symlink_to_protected_server_core_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            link = Path(temp_dir) / "core"
            link.symlink_to("/servidor/ark/serverfiles/core")

            with self.assertRaises(SystemExit) as raised:
                scanner.main_from_args(["--core", str(link), "--json"])

        self.assertIn(
            "--core must not read from protected server root /servidor/ark",
            str(raised.exception),
        )

    def test_rejects_approved_dump_symlink_to_protected_server_core_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            link = Path(temp_dir) / "core-link"
            link.symlink_to("/servidor/ark/obelisk/dumps/second-source/raw/core")
            with self.assertRaises(SystemExit) as raised:
                scanner.main_from_args(["--core", str(link), "--json"])

        self.assertIn(
            "--core must not read from protected server root /servidor/ark",
            str(raised.exception),
        )

    def test_rejects_protected_server_manifest_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            self.build_core_fixture(core)

            with self.assertRaises(SystemExit) as raised:
                scanner.main_from_args(
                    [
                        "--core",
                        str(core),
                        "--ark-binary-sha256",
                        ARK_SHA,
                        "--manifest-out",
                        "/servidor/ark/obelisk/state/fname-manifest.json",
                    ]
                )

        self.assertIn(
            "--manifest-out must not write under protected server root /servidor/ark",
            str(raised.exception),
        )

    def test_rejects_server_dump_artifact_root(self) -> None:
        with self.assertRaisesRegex(SystemExit, "--core must not read from protected server root"):
            with mock.patch("builtins.print"):
                scanner.main_from_args(
                    [
                        "--core",
                        "/servidor/ark/obelisk/dumps/second-source/raw/core",
                        "--max-none-hits",
                        "16",
                        "--max-pointer-hits",
                        "16",
                        "--ark-binary-sha256",
                        ARK_SHA,
                        "--manifest-out",
                        "/servidor/ark/obelisk/dumps/second-source/fname-manifest.json",
                        "--json",
                    ]
                )

    def test_allows_approved_offline_workspace_paths_under_server_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            protected = root / "server-root"
            workspace = protected / "workspace-offline"
            workspace.mkdir(parents=True)

            with (
                mock.patch.object(scanner, "SERVER_ROOT", protected),
                mock.patch.object(scanner, "PROTECTED_ROOTS", (protected,)),
                mock.patch.object(scanner, "APPROVED_OFFLINE_WORKSPACE_ROOTS", (workspace,)),
            ):
                scanner.reject_protected_path(workspace / "core", "--core", "read from")
                scanner.reject_protected_path(workspace / "manifest.json", "--manifest-out", "write under")

    def test_json_out_rejects_unignored_in_repo_path_before_scanning(self) -> None:
        with self.assertRaisesRegex(SystemExit, "--json-out is inside the repository but is not ignored by Git"):
            with mock.patch("builtins.print"):
                scanner.main_from_args(
                    [
                        "--core",
                        "/tmp/nonexistent-core",
                        "--json-out",
                        str(REPO_ROOT / "docs" / "fname-scan.json"),
                    ]
                )

    def test_manifest_out_rejects_unignored_in_repo_path_before_scanning(self) -> None:
        with self.assertRaisesRegex(SystemExit, "--manifest-out is inside the repository but is not ignored by Git"):
            with mock.patch("builtins.print"):
                scanner.main_from_args(
                    [
                        "--core",
                        "/tmp/nonexistent-core",
                        "--manifest-out",
                        str(REPO_ROOT / "docs" / "fname-manifest.json"),
                    ]
                )

    def test_rejects_textually_protected_non_workspace_symlink_to_workspace_core_path(self) -> None:
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
                mock.patch.object(scanner, "SERVER_ROOT", protected),
                mock.patch.object(scanner, "PROTECTED_ROOTS", (protected,)),
                mock.patch.object(scanner, "APPROVED_OFFLINE_WORKSPACE_ROOTS", (workspace,)),
                self.assertRaisesRegex(SystemExit, "--core must not read from protected server root"),
            ):
                scanner.reject_protected_path(link, "--core", "read from")

    def test_writes_candidate_only_manifest_for_single_exact_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            manifest = root / "fname-manifest.json"
            self.build_core_fixture(core)

            with mock.patch("builtins.print"):
                result = scanner.main_from_args(
                    [
                        "--core",
                        str(core),
                        "--max-none-hits",
                        "16",
                        "--max-pointer-hits",
                        "16",
                        "--ark-binary-sha256",
                        ARK_SHA,
                        "--manifest-out",
                        str(manifest),
                        "--manifest-evidence",
                        "offline-test-evidence",
                        "--json",
                    ]
                )

            self.assertEqual(result, 0)
            payload = scanner.json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema"], "obelisk.fname-index-manifest.v1")
            self.assertEqual(payload["evidence_status"], "candidate-only")
            names = {item["name"]: item["index"] for item in payload["names"]}
            self.assertEqual(names["ClientMessage"], 4884)
            self.assertEqual(names["ServerChat"], 9619)
            self.assertEqual(names["SetActiveMissionDebugFlags"], 9622)
            self.assertNotIn("None", names)
            validated = manifest_validator.validate_manifest(payload, ARK_SHA)
            self.assertEqual(len(validated), 3)

    def test_manifest_out_requires_lowercase_binary_sha(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            self.build_core_fixture(core)

            with self.assertRaises(SystemExit) as raised:
                scanner.main_from_args(
                    [
                        "--core",
                        str(core),
                        "--ark-binary-sha256",
                        ARK_SHA.upper(),
                        "--manifest-out",
                        str(root / "manifest.json"),
                    ]
                )

        self.assertIn("lowercase SHA256", str(raised.exception))

    def test_manifest_out_requires_binary_sha(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            self.build_core_fixture(core)

            with self.assertRaises(SystemExit) as raised:
                scanner.main_from_args(
                    [
                        "--core",
                        str(core),
                        "--manifest-out",
                        str(root / "manifest.json"),
                    ]
                )

        self.assertIn("--manifest-out requires --ark-binary-sha256", str(raised.exception))

    def test_manifest_readiness_blocks_no_exact_names(self) -> None:
        readiness = scanner.candidate_manifest_readiness(
            [
                {
                    "table": "0x1000",
                    "resolved_indices": [
                        {
                            "label": "ServerChat",
                            "index": 9619,
                            "header_index_ok": True,
                            "name_matches_label": False,
                        }
                    ],
                }
            ],
            "offline-test-evidence",
        )

        self.assertFalse(readiness["ready"])
        self.assertEqual(readiness["blockers"], ["no_exact_name_matches"])

    def test_manifest_out_does_not_fail_when_readiness_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            self.build_core_fixture(core)
            manifest = root / "manifest.json"

            with contextlib.redirect_stdout(io.StringIO()):
                result = scanner.main_from_args(
                    [
                        "--core",
                        str(core),
                        "--index",
                        "NotServerChat=9619",
                        "--ark-binary-sha256",
                        "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                        "--manifest-out",
                        str(manifest),
                        "--json",
                    ]
                )

            self.assertEqual(result, 0)
            self.assertFalse(manifest.exists())

    def test_manifest_readiness_blocks_ambiguous_candidates(self) -> None:
        candidate = {
            "table": "0x1000",
            "resolved_indices": [
                {
                    "label": "ServerChat",
                    "index": 9619,
                    "header_index_ok": True,
                    "name_matches_label": True,
                }
            ],
        }
        other_candidate = {
            **candidate,
            "table": "0x2000",
        }

        readiness = scanner.candidate_manifest_readiness(
            [candidate, other_candidate],
            "offline-test-evidence",
        )

        self.assertFalse(readiness["ready"])
        self.assertEqual(readiness["blockers"], ["ambiguous_ready_candidates"])


if __name__ == "__main__":
    unittest.main()
