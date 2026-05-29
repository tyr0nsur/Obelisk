#!/usr/bin/env python3
"""Offline tests for build_core_dump_evidence_pack.py command generation."""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import build_core_dump_evidence_pack as core_pack


class CoreDumpEvidencePackCommandTests(unittest.TestCase):
    def run_main_raw(self, argv: list[str]) -> tuple[int, str]:
        stderr = io.StringIO()
        with mock.patch.object(sys, "argv", argv), contextlib.redirect_stderr(stderr):
            result = core_pack.main()
        return result, stderr.getvalue()

    def run_main_with_gdb_status(
        self,
        gdb_returncode: int,
        extra_args: list[str] | None = None,
        scan_payload: dict[str, object] | None = None,
        create_scan_manifest: bool = False,
    ) -> tuple[int, Path]:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        temp_dir = Path(temp.name)
        binary = temp_dir / "ShooterGameServer"
        core = temp_dir / "core"
        output_dir = temp_dir / "pack"
        binary.write_bytes(b"binary")
        core.write_bytes(b"core")

        def fake_run_command(command: list[str], output_path: Path) -> dict[str, object]:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if command and str(command[0]) == sys.executable and "scan_core_fname_tables.py" in str(command[1]):
                payload = dict(scan_payload or {})
                if payload.pop("__use_manifest_out_path", False):
                    manifest_index = command.index("--manifest-out") + 1
                    candidate_manifest = dict(payload.get("candidate_manifest") or {})
                    candidate_manifest["path"] = command[manifest_index]
                    payload["candidate_manifest"] = candidate_manifest
                output_path.write_text(
                    core_pack.json.dumps(payload),
                    encoding="utf-8",
                )
                if create_scan_manifest:
                    manifest_index = command.index("--manifest-out") + 1
                    Path(command[manifest_index]).write_text(
                        core_pack.json.dumps({"schema": "obelisk.fname-index-manifest.v1", "names": []}),
                        encoding="utf-8",
                    )
            else:
                output_path.write_text("", encoding="utf-8")
            returncode = gdb_returncode if command and command[0] == "gdb" else 0
            stderr_path = output_path.with_suffix(output_path.suffix + ".stderr")
            if returncode:
                stderr_path.write_text("gdb failed\n", encoding="utf-8")
            return {
                "command": command,
                "returncode": returncode,
                "stdout": str(output_path),
                "stderr": str(stderr_path) if returncode else None,
            }

        argv = [
            "build_core_dump_evidence_pack.py",
            "--binary",
            str(binary),
            "--core",
            str(core),
            "--output-dir",
            str(output_dir),
            "--obelisk-commit",
            "test-commit",
        ]
        if extra_args:
            argv.extend(extra_args)

        with (
            mock.patch.object(sys, "argv", argv),
            mock.patch.object(core_pack.shutil, "which", return_value="/usr/bin/gdb"),
            mock.patch.object(core_pack, "run_command", side_effect=fake_run_command),
            mock.patch.object(core_pack, "sha256_file", return_value="sha256"),
        ):
            return core_pack.main(), output_dir

    def test_main_rejects_failed_gdb_by_default(self) -> None:
        result, output_dir = self.run_main_with_gdb_status(1)

        self.assertEqual(result, 1)
        self.assertFalse((output_dir / "manifest.json").exists())
        self.assertTrue((output_dir / "gdb-core.txt.stderr").exists())

    def test_rejects_protected_server_binary_input_before_file_checks(self) -> None:
        result, stderr = self.run_main_raw(
            [
                "build_core_dump_evidence_pack.py",
                "--binary",
                "/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer",
                "--core",
                "/tmp/offline-core",
                "--output-dir",
                "/tmp/offline-pack",
            ]
        )

        self.assertEqual(result, 2)
        self.assertIn("--binary must not read from protected server root /servidor/ark", stderr)

    def test_rejects_protected_server_core_input_before_file_checks(self) -> None:
        result, stderr = self.run_main_raw(
            [
                "build_core_dump_evidence_pack.py",
                "--binary",
                "/tmp/offline-ShooterGameServer",
                "--core",
                "/servidor/ark/serverfiles/core",
                "--output-dir",
                "/tmp/offline-pack",
            ]
        )

        self.assertEqual(result, 2)
        self.assertIn("--core must not read from protected server root /servidor/ark", stderr)

    def test_rejects_symlink_to_protected_server_binary_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            link = Path(temp_dir) / "ShooterGameServer"
            link.symlink_to("/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer")
            result, stderr = self.run_main_raw(
                [
                    "build_core_dump_evidence_pack.py",
                    "--binary",
                    str(link),
                    "--core",
                    "/tmp/offline-core",
                    "--output-dir",
                    "/tmp/offline-pack",
                ]
            )

        self.assertEqual(result, 2)
        self.assertIn("--binary must not read from protected server root /servidor/ark", stderr)

    def test_rejects_approved_dump_symlink_to_protected_server_binary_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            link = Path(temp_dir) / "ShooterGameServer"
            link.symlink_to("/servidor/ark/obelisk/dumps/second-source/raw/ShooterGameServer")
            result, stderr = self.run_main_raw(
                [
                    "build_core_dump_evidence_pack.py",
                    "--binary",
                    str(link),
                    "--core",
                    "/tmp/offline-core",
                    "--output-dir",
                    "/tmp/offline-pack",
                ]
            )

        self.assertEqual(result, 2)
        self.assertIn("--binary must not read from protected server root /servidor/ark", stderr)

    def test_rejects_protected_server_output_dir_before_file_checks(self) -> None:
        result, stderr = self.run_main_raw(
            [
                "build_core_dump_evidence_pack.py",
                "--binary",
                "/tmp/offline-ShooterGameServer",
                "--core",
                "/tmp/offline-core",
                "--output-dir",
                "/servidor/ark/obelisk/state/offline-pack",
            ]
        )

        self.assertEqual(result, 2)
        self.assertIn("--output-dir must not write under protected server root /servidor/ark", stderr)

    def test_rejects_unignored_in_repo_output_dir_before_writing_raw_artifacts(self) -> None:
        output_dir = core_pack.REPO_ROOT / "docs" / "raw-core-pack"
        result, stderr = self.run_main_raw(
            [
                "build_core_dump_evidence_pack.py",
                "--binary",
                "/tmp/offline-ShooterGameServer",
                "--core",
                "/tmp/offline-core",
                "--output-dir",
                str(output_dir),
            ]
        )

        self.assertEqual(result, 2)
        self.assertIn("--output-dir is inside the repository but is not ignored by Git", stderr)
        self.assertFalse(output_dir.exists())

    def test_rejects_symlink_to_protected_server_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            link = Path(temp_dir) / "pack"
            link.symlink_to("/servidor/ark/obelisk/state/offline-pack")
            result, stderr = self.run_main_raw(
                [
                    "build_core_dump_evidence_pack.py",
                    "--binary",
                    "/tmp/offline-ShooterGameServer",
                    "--core",
                    "/tmp/offline-core",
                    "--output-dir",
                    str(link),
                ]
            )

        self.assertEqual(result, 2)
        self.assertIn("--output-dir must not write under protected server root /servidor/ark", stderr)

    def test_rejects_approved_dump_symlink_to_protected_server_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            link = Path(temp_dir) / "pack"
            link.symlink_to("/servidor/ark/obelisk/dumps/second-source/intake/pack")
            result, stderr = self.run_main_raw(
                [
                    "build_core_dump_evidence_pack.py",
                    "--binary",
                    "/tmp/offline-ShooterGameServer",
                    "--core",
                    "/tmp/offline-core",
                    "--output-dir",
                    str(link),
                ]
            )

        self.assertEqual(result, 2)
        self.assertIn("--output-dir must not write under protected server root /servidor/ark", stderr)

    def test_rejects_server_dump_artifact_root_before_file_checks(self) -> None:
        result, stderr = self.run_main_raw(
            [
                "build_core_dump_evidence_pack.py",
                "--binary",
                "/servidor/ark/obelisk/dumps/second-source/raw/ShooterGameServer",
                "--core",
                "/servidor/ark/obelisk/dumps/second-source/raw/core",
                "--output-dir",
                "/servidor/ark/obelisk/dumps/second-source/intake/pack",
            ]
        )

        self.assertEqual(result, 2)
        self.assertIn("--binary must not read from protected server root /servidor/ark", stderr)

    def test_allows_paths_that_only_share_protected_prefix_text(self) -> None:
        result, stderr = self.run_main_raw(
            [
                "build_core_dump_evidence_pack.py",
                "--binary",
                "/servidor/ark-not-live/ShooterGameServer",
                "--core",
                "/tmp/offline-core",
                "--output-dir",
                "/tmp/offline-pack",
            ]
        )

        self.assertEqual(result, 2)
        self.assertIn("binary does not exist", stderr)
        self.assertNotIn("protected server root", stderr)

    def test_allows_output_paths_that_only_share_protected_prefix_text(self) -> None:
        result, stderr = self.run_main_raw(
            [
                "build_core_dump_evidence_pack.py",
                "--binary",
                "/tmp/offline-ShooterGameServer",
                "--core",
                "/tmp/offline-core",
                "--output-dir",
                "/servidor/ark-not-live/offline-pack",
            ]
        )

        self.assertEqual(result, 2)
        self.assertIn("binary does not exist", stderr)
        self.assertNotIn("protected server root", stderr)

    def test_allows_approved_offline_workspace_paths_under_server_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            protected = root / "server-root"
            workspace = protected / "workspace-offline"
            workspace.mkdir(parents=True)

            with (
                mock.patch.object(core_pack, "SERVER_ROOT", protected),
                mock.patch.object(core_pack, "APPROVED_OFFLINE_WORKSPACE_ROOTS", (workspace,)),
            ):
                core_pack.reject_protected_input_path(workspace / "ShooterGameServer", "--binary")
                core_pack.reject_protected_input_path(workspace / "core", "--core")
                core_pack.reject_protected_output_path(workspace / "pack", "--output-dir")

    def test_rejects_textually_protected_non_workspace_symlink_to_workspace_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            protected = root / "server-root"
            workspace = protected / "workspace-offline"
            blocked = protected / "obelisk"
            workspace.mkdir(parents=True)
            blocked.mkdir()
            binary = workspace / "ShooterGameServer"
            binary.write_bytes(b"binary")
            link = blocked / "ShooterGameServer"
            link.symlink_to(binary)

            with (
                mock.patch.object(core_pack, "SERVER_ROOT", protected),
                mock.patch.object(core_pack, "APPROVED_OFFLINE_WORKSPACE_ROOTS", (workspace,)),
            ):
                with self.assertRaises(SystemExit) as raised:
                    core_pack.reject_protected_input_path(link, "--binary")

        self.assertEqual(raised.exception.code, 2)

    def test_rejects_preexisting_symlink_output_child(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "pack"
            output_dir.mkdir()
            (output_dir / "gdb-core.txt").symlink_to("/servidor/ark/obelisk/state/gdb-core.txt")

            with self.assertRaises(SystemExit) as raised:
                core_pack.reject_preexisting_symlink_outputs(output_dir, "--output-dir")

        self.assertEqual(raised.exception.code, 2)

    def test_main_marks_allowed_gdb_failure_as_partial(self) -> None:
        result, output_dir = self.run_main_with_gdb_status(1, ["--allow-partial-gdb"])

        self.assertEqual(result, 0)
        manifest = core_pack.json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["evidence_status"]["status"], "partial-gdb-failed")
        self.assertTrue(manifest["evidence_status"]["gdb_core_failed"])
        self.assertTrue(manifest["evidence_status"]["allow_partial_gdb"])
        self.assertFalse(manifest["promotion_gate"]["ready"])
        blocker_reasons = {blocker["reason"] for blocker in manifest["promotion_gate"]["blockers"]}
        self.assertIn("single_core_artifact", blocker_reasons)
        self.assertIn("non_actionable_static_xrefs", blocker_reasons)
        self.assertIn("partial_gdb_failed", blocker_reasons)

    def test_main_marks_successful_gdb_as_complete(self) -> None:
        result, output_dir = self.run_main_with_gdb_status(0)

        self.assertEqual(result, 0)
        manifest = core_pack.json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["evidence_status"]["status"], "complete")
        self.assertFalse(manifest["evidence_status"]["gdb_core_failed"])
        self.assertFalse(manifest["evidence_status"]["allow_partial_gdb"])
        self.assertEqual(manifest["artifacts"]["fname_static_xrefs"], str(output_dir / "fname-static-xrefs.json"))
        self.assertTrue((output_dir / "fname-static-xrefs.json").exists())
        self.assertFalse(manifest["promotion_gate"]["ready"])
        blocker_reasons = {blocker["reason"] for blocker in manifest["promotion_gate"]["blockers"]}
        self.assertEqual(
            blocker_reasons,
            {
                "single_core_artifact",
                "needs_second_isolated_capture_or_static_path",
                "non_actionable_static_xrefs",
            },
        )

    def test_scan_fname_tables_receives_configured_indices(self) -> None:
        result, output_dir = self.run_main_with_gdb_status(
            0,
            [
                "--scan-fname-tables",
                "--no-default-fname-indices",
                "--fname-index",
                "ServerChat=9619",
                "--fname-index",
                "SetActiveMissionDebugFlags=9622",
            ],
        )

        self.assertEqual(result, 0)
        manifest = core_pack.json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
        command = manifest["commands"]["core_fname_table_scan"]["command"]
        self.assertIn("--index", command)
        self.assertIn("ServerChat=9619", command)
        self.assertIn("SetActiveMissionDebugFlags=9622", command)
        self.assertNotIn("None=0", command)
        self.assertNotIn("ClientMessage=4884", command)
        self.assertIn("--ark-binary-sha256", command)
        self.assertIn("--manifest-out", command)
        self.assertIn(str(output_dir / "core.fname-index-manifest.json"), command)
        self.assertIsNone(manifest["artifacts"]["core_fname_index_manifest"])
        self.assertEqual(manifest["fname_table_scan"]["candidate_manifest_status"], "requested")
        self.assertEqual(
            manifest["fname_table_scan"]["requested_indices"],
            [
                {"label": "ServerChat", "index": 9619},
                {"label": "SetActiveMissionDebugFlags", "index": 9622},
            ],
        )

    def test_scan_fname_tables_preserves_empty_configured_indices(self) -> None:
        result, output_dir = self.run_main_with_gdb_status(
            0,
            [
                "--scan-fname-tables",
                "--no-default-fname-indices",
            ],
        )

        self.assertEqual(result, 0)
        manifest = core_pack.json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
        command = manifest["commands"]["core_fname_table_scan"]["command"]
        self.assertIn("--no-default-indices", command)
        self.assertNotIn("--index", command)
        self.assertEqual(manifest["fname_indices"], [])

    def test_core_promotion_gate_omits_static_xref_blocker_when_actionable(self) -> None:
        gate = core_pack.core_promotion_gate(gdb_failed=False, static_xrefs_actionable=True)

        self.assertFalse(gate["ready"])
        blocker_reasons = {blocker["reason"] for blocker in gate["blockers"]}
        self.assertEqual(
            blocker_reasons,
            {
                "single_core_artifact",
                "needs_second_isolated_capture_or_static_path",
            },
        )

    def test_fname_candidate_manifest_status_tracks_scan_payload(self) -> None:
        self.assertEqual(core_pack.fname_candidate_manifest_status({}, False), "not_requested")
        self.assertEqual(core_pack.fname_candidate_manifest_status({}, True), "requested")
        self.assertEqual(
            core_pack.fname_candidate_manifest_status(
                {
                    "candidate_manifest": {
                        "name_count": 3,
                    }
                },
                True,
            ),
            "written",
        )
        self.assertEqual(
            core_pack.fname_candidate_manifest_status(
                {
                    "manifest_readiness": {
                        "blockers": ["ambiguous_ready_candidates"],
                    }
                },
                True,
            ),
            "blocked",
        )

    def test_scan_fname_tables_records_blocked_manifest_readiness_without_failing_pack(self) -> None:
        result, output_dir = self.run_main_with_gdb_status(
            0,
            ["--scan-fname-tables"],
            scan_payload={
                "manifest_readiness": {
                    "ready": False,
                    "blockers": ["ambiguous_ready_candidates"],
                },
                "candidate_manifest": {
                    "path": None,
                    "name_count": 0,
                },
            },
        )

        self.assertEqual(result, 0)
        manifest = core_pack.json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["fname_table_scan"]["candidate_manifest_status"], "blocked")
        self.assertEqual(
            manifest["fname_table_scan"]["manifest_readiness"]["blockers"],
            ["ambiguous_ready_candidates"],
        )
        self.assertIsNone(manifest["artifacts"]["core_fname_index_manifest"])

    def test_scan_fname_tables_records_manifest_artifact_only_when_written(self) -> None:
        result, output_dir = self.run_main_with_gdb_status(
            0,
            ["--scan-fname-tables"],
            scan_payload={
                "__use_manifest_out_path": True,
                "candidate_manifest": {
                    "name_count": 3,
                },
            },
            create_scan_manifest=True,
        )

        self.assertEqual(result, 0)
        manifest = core_pack.json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(
            manifest["artifacts"]["core_fname_index_manifest"],
            str(output_dir / "core.fname-index-manifest.json"),
        )

    def test_gdb_commands_include_direct_fname_entry_reads(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            command_file = Path(temp_dir) / "gdb.txt"

            core_pack.write_gdb_command_file(
                command_file,
                candidates=[],
                fname_root_slots=[("static_fname_root_slot", 0x5956F30)],
                fname_indices=[("ServerChat", 9619)],
                gobjects_candidates=[],
                gobjects_sample_indices=[],
                pointer_scan_values=[],
                pointer_scan_max_mapping_bytes=core_pack.DEFAULT_POINTER_SCAN_MAX_MAPPING_BYTES,
                pointer_scan_max_hits=core_pack.DEFAULT_POINTER_SCAN_MAX_HITS,
            )

            text = command_file.read_text(encoding="utf-8")
            self.assertIn("== fname root static_fname_root_slot slot @ 0x5956f30 ==", text)
            self.assertIn("set $fname_table = *(void**)0x5956f30", text)
            self.assertIn("-- fname index ServerChat [9619] --", text)
            self.assertIn("set $fname_chunk = *(void**)(((char*)$fname_table)+0x0)", text)
            self.assertIn("set $fname_entry = *(void**)(((char*)$fname_chunk)+0x12c98)", text)
            self.assertIn("x/s ((char*)$fname_entry)+0x10", text)

    def test_gdb_commands_include_gobjects_candidate_previews(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            command_file = Path(temp_dir) / "gdb.txt"

            core_pack.write_gdb_command_file(
                command_file,
                candidates=[],
                fname_root_slots=[],
                fname_indices=[],
                gobjects_candidates=[("gobjects_slot", 0x12345678)],
                gobjects_sample_indices=[],
                pointer_scan_values=[],
                pointer_scan_max_mapping_bytes=core_pack.DEFAULT_POINTER_SCAN_MAX_MAPPING_BYTES,
                pointer_scan_max_hits=core_pack.DEFAULT_POINTER_SCAN_MAX_HITS,
            )

            text = command_file.read_text(encoding="utf-8")
            self.assertIn("== gobjects candidate gobjects_slot slot @ 0x12345678 ==", text)
            self.assertIn("set $gobjects_root = *(void**)0x12345678", text)
            self.assertIn("x/96gx $gobjects_root", text)
            self.assertIn("-- gobjects root+0x10 pointer preview --", text)
            self.assertIn("set $gobjects_maybe_ptr = *(void**)(((char*)$gobjects_root)+0x10)", text)

    def test_gdb_commands_include_gobjects_sample_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            command_file = Path(temp_dir) / "gdb.txt"

            core_pack.write_gdb_command_file(
                command_file,
                candidates=[],
                fname_root_slots=[("static_fname_root_slot", 0x5956F30)],
                fname_indices=[],
                gobjects_candidates=[("gobjects", 0x595B7E0)],
                gobjects_sample_indices=[0, 1, 0x10000],
                pointer_scan_values=[],
                pointer_scan_max_mapping_bytes=core_pack.DEFAULT_POINTER_SCAN_MAX_MAPPING_BYTES,
                pointer_scan_max_hits=core_pack.DEFAULT_POINTER_SCAN_MAX_HITS,
            )

            text = command_file.read_text(encoding="utf-8")
            self.assertIn("== gobjects sample gobjects[0] direct @ 0x595b7e0 ==", text)
            self.assertIn("set $gobjects_direct = (char*)0x595b7e0", text)
            self.assertIn("set $gobjects_chunks = *(void**)($gobjects_direct+0x10)", text)
            self.assertIn("set $gobjects_count = *(int*)($gobjects_direct+0x24)", text)
            self.assertIn("set $gobjects_chunk = *(void**)(((char*)$gobjects_chunks)+0x0)", text)
            self.assertIn("set $fuobject_item = ((char*)$gobjects_chunk)+0x0", text)
            self.assertIn("== gobjects sample gobjects[1] direct @ 0x595b7e0 ==", text)
            self.assertIn("set $fuobject_item = ((char*)$gobjects_chunk)+0x10", text)
            self.assertIn("set $fuobject_qword_0x8 = *(unsigned long long*)(((char*)$fuobject_item)+0x8)", text)
            self.assertIn("set $fuobject_dword_0x8 = *(int*)(((char*)$fuobject_item)+0x8)", text)
            self.assertIn("set $fuobject_dword_0xc = *(int*)(((char*)$fuobject_item)+0xc)", text)
            self.assertNotIn("$fuobject_serial", text)
            self.assertIn("set $uobject_internal_index = *(int*)(((char*)$uobject)+0xc)", text)
            self.assertIn("set $uobject_class = *(void**)(((char*)$uobject)+0x10)", text)
            self.assertIn("set $uobject_name_index = *(int*)(((char*)$uobject)+0x18)", text)
            self.assertIn("set $uobject_outer = *(void**)(((char*)$uobject)+0x20)", text)
            self.assertIn("sample_index = 0 internal_index_match", text)
            self.assertIn("-- resolve sample names through static_fname_root_slot @ 0x5956f30 --", text)
            self.assertIn("object name: ", text)
            self.assertIn("class name: ", text)
            self.assertIn("== gobjects sample gobjects[65536] direct @ 0x595b7e0 ==", text)
            self.assertIn("set $gobjects_chunk = *(void**)(((char*)$gobjects_chunks)+0x8)", text)
            self.assertNotIn("set $gobjects_root = *(void**)0x595b7e0", text)
            self.assertNotIn("== gobjects candidate gobjects slot @ 0x595b7e0 ==", text)

    def test_gdb_commands_include_bounded_pointer_value_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            command_file = Path(temp_dir) / "gdb.txt"

            core_pack.write_gdb_command_file(
                command_file,
                candidates=[],
                fname_root_slots=[],
                fname_indices=[],
                gobjects_candidates=[],
                gobjects_sample_indices=[],
                pointer_scan_values=[("fname_table", 0x2AE5C660)],
                pointer_scan_max_mapping_bytes=0x2000,
                pointer_scan_max_hits=3,
            )

            text = command_file.read_text(encoding="utf-8")
            self.assertIn("== pointer value scans ==", text)
            self.assertIn("values = [('fname_table', 0x2ae5c660)]", text)
            self.assertIn("max_mapping_bytes = 8192", text)
            self.assertIn("max_hits = 3", text)
            self.assertIn("'r' not in perms or 'w' not in perms", text)
            self.assertIn("find /g 0x{start:x}, 0x{end:x}, 0x{value:x}", text)
            self.assertIn("hit {label} value=0x{value:x} slot={text}", text)

    def test_collects_gobjects_static_xrefs_from_objdump(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            objdump = Path(temp_dir) / "ShooterGameServer.objdump"
            objdump.write_text(
                """
0000000000000ff0 <LookupObjects>:
  1000: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x1]        # 595b7f0
  1007: 39 3d 00 00 00 00     cmp    DWORD PTR [rip+0x2],edi        # 595b804
  100d: f0 0f c1 05 00 00 00  lock xadd DWORD PTR [rip+0x3],eax     # 595b838
0000000000001010 <InitObjects>:
  1015: 48 8d 3d 00 00 00 00  lea    rdi,[rip+0x4]                  # 0x595b7e0
  1020: bf e0 b7 95 05        mov    edi,0x595b7e0
  1024: bf e0 b7 95 05        mov    edi,0x000000000595b7e0
  1028: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x5]        # 0x12345678
""",
                encoding="utf-8",
            )

            payload = core_pack.collect_static_xrefs(
                objdump,
                core_pack.gobjects_static_xref_targets([("gobjects", 0x595B7E0)]),
            )

        self.assertEqual(payload["access_counts"], {"address": 1, "load": 2, "other": 2, "store": 1})
        self.assertEqual(payload["xrefs"]["0x595b7e0"][0]["target_label"], "gobjects.root")
        self.assertEqual(payload["xrefs"]["0x595b7e0"][1]["instruction_address"], "0x1020")
        self.assertEqual(payload["xrefs"]["0x595b7e0"][2]["instruction_address"], "0x1024")
        self.assertEqual(payload["xrefs"]["0x595b7f0"][0]["target_label"], "gobjects.chunks")
        self.assertEqual(payload["xrefs"]["0x595b804"][0]["target_label"], "gobjects.count")
        self.assertEqual(payload["xrefs"]["0x595b838"][0]["target_label"], "gobjects.serial")
        self.assertEqual(payload["xrefs"]["0x595b7f0"][0]["function_label"], "LookupObjects")
        groups = {group["function_label"]: group for group in payload["function_groups"]}
        self.assertEqual(groups["LookupObjects"]["first_xref"], "0x1000")
        self.assertEqual(groups["LookupObjects"]["last_xref"], "0x100d")
        self.assertEqual(groups["LookupObjects"]["xref_span_bytes"], 0xD)
        self.assertFalse(groups["LookupObjects"]["oversized"])
        self.assertEqual(groups["LookupObjects"]["interpretation"], "concrete-instruction-window")
        self.assertTrue(groups["LookupObjects"]["recommended_for_decompile"])
        self.assertIsNone(groups["LookupObjects"]["reject_reason"])
        self.assertEqual(groups["LookupObjects"]["xref_count"], 3)
        self.assertEqual(groups["InitObjects"]["target_labels"], ["gobjects.root"])
        self.assertEqual(groups["InitObjects"]["xref_count"], 3)
        self.assertEqual(payload["anchor_groups"][0]["anchor_start"], "0x1000")
        self.assertEqual(payload["anchor_groups"][0]["anchor_end"], "0x1024")
        self.assertEqual(payload["anchor_groups"][0]["anchor_span_bytes"], 0x24)
        self.assertFalse(payload["anchor_groups"][0]["oversized"])
        self.assertEqual(payload["anchor_groups"][0]["interpretation"], "concrete-instruction-window")
        self.assertEqual(payload["anchor_groups"][0]["xref_count"], 6)
        self.assertTrue(core_pack.has_actionable_static_xrefs(payload))

    def test_collects_fname_root_static_xrefs_from_objdump(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            objdump = Path(temp_dir) / "ShooterGameServer.objdump"
            objdump.write_text(
                """
0000000000002000 <InitNames>:
  2000: 48 8d 3d 00 00 00 00  lea    rdi,[rip+0x4]                  # 0x1234000
  2007: 48 89 05 00 00 00 00  mov    QWORD PTR [rip+0x5],rax        # 0x1234000
  200e: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x6]        # 0x1234000
""",
                encoding="utf-8",
            )

            payload = core_pack.collect_static_xrefs(
                objdump,
                core_pack.fname_static_xref_targets([("verified_fname_root", 0x1234000)]),
            )

        refs = payload["xrefs"]["0x1234000"]
        self.assertEqual([ref["target_label"] for ref in refs], ["verified_fname_root.root_slot"] * 3)
        self.assertEqual(payload["access_counts"], {"address": 1, "load": 1, "store": 1})
        self.assertEqual(payload["anchor_groups"][0]["xref_count"], 3)
        self.assertTrue(core_pack.has_actionable_static_xrefs(payload))

    def test_static_xref_groups_mark_oversized_symbol_buckets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            objdump = Path(temp_dir) / "ShooterGameServer.objdump"
            objdump.write_text(
                """
0000000000010000 <HugeExportedSymbol>:
  1000: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x1]        # 0x595b7f0
 22000: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x2]        # 0x595b804
""",
                encoding="utf-8",
            )

            payload = core_pack.collect_static_xrefs(
                objdump,
                core_pack.gobjects_static_xref_targets([("gobjects", 0x595B7E0)]),
            )

        group = payload["function_groups"][0]
        self.assertEqual(group["function_label"], "HugeExportedSymbol")
        self.assertEqual(group["first_xref"], "0x1000")
        self.assertEqual(group["last_xref"], "0x22000")
        self.assertTrue(group["oversized"])
        self.assertEqual(group["interpretation"], "contaminated-nearest-symbol-bucket")
        self.assertFalse(group["recommended_for_decompile"])
        self.assertIn("anchor_groups", str(group["reject_reason"]))
        self.assertEqual(len(payload["anchor_groups"]), 2)
        self.assertEqual(payload["anchor_groups"][0]["xref_count"], 1)

    def test_anchor_groups_mark_contaminated_windows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            objdump = Path(temp_dir) / "ShooterGameServer.objdump"
            lines = ["0000000000010000 <DenseAnchor>:"]
            for index in range(core_pack.ANCHOR_GROUP_OVERSIZED_XREFS):
                address = 0x1000 + index
                lines.append(
                    f"  {address:x}: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x1]        # 0x595b7f0"
                )
            objdump.write_text("\n".join(lines) + "\n", encoding="utf-8")

            payload = core_pack.collect_static_xrefs(
                objdump,
                core_pack.gobjects_static_xref_targets([("gobjects", 0x595B7E0)]),
            )

        anchor_group = payload["anchor_groups"][0]
        self.assertEqual(anchor_group["xref_count"], core_pack.ANCHOR_GROUP_OVERSIZED_XREFS)
        self.assertTrue(anchor_group["oversized"])
        self.assertEqual(anchor_group["interpretation"], "contaminated-anchor-window")
        self.assertFalse(core_pack.has_actionable_static_xrefs(payload))

    def test_static_xref_gate_rejects_empty_xrefs(self) -> None:
        payload = {
            "anchor_groups": [],
            "function_groups": [],
            "xrefs": {"0x1234000": []},
        }

        self.assertFalse(core_pack.has_actionable_static_xrefs(payload))
        gate = core_pack.core_promotion_gate(gdb_failed=False, static_xrefs_actionable=False)
        blocker_reasons = {blocker["reason"] for blocker in gate["blockers"]}
        self.assertIn("non_actionable_static_xrefs", blocker_reasons)

    def test_gobjects_sample_options_require_candidate_and_fname_root(self) -> None:
        self.assertEqual(
            core_pack.validate_gobjects_sample_options([], [0], [("fname", 0x5956F30)]),
            "--gobjects-sample-index requires at least one --gobjects-candidate",
        )
        self.assertEqual(
            core_pack.validate_gobjects_sample_options([("gobjects", 0x595B7E0)], [0], []),
            "--gobjects-sample-index requires at least one --fname-root-slot for "
            "NamePrivate resolution",
        )
        self.assertIsNone(
            core_pack.validate_gobjects_sample_options(
                [("gobjects", 0x595B7E0)],
                [0],
                [("fname", 0x5956F30)],
            )
        )

    def test_gobjects_sample_options_require_explicit_fname_root_when_checked(self) -> None:
        self.assertEqual(
            core_pack.validate_gobjects_sample_options(
                [("gobjects", 0x595B7E0)],
                [0],
                [("static_fname_root_slot", 0x5956F30)],
                [],
            ),
            "--gobjects-sample-index requires an explicit --fname-root-slot for this "
            "artifact; do not rely on the primary-core default for NamePrivate resolution",
        )
        self.assertIsNone(
            core_pack.validate_gobjects_sample_options(
                [("gobjects", 0x595B7E0)],
                [0],
                [("verified_fname_root", 0x1234000)],
                [("verified_fname_root", 0x1234000)],
            )
        )

    def test_gobjects_sampling_uses_only_explicit_fname_roots(self) -> None:
        selected = core_pack.fname_roots_for_gobjects_sampling(
            [
                ("primary_default", 0x5956F30),
                ("second_source_verified", 0x1234000),
            ],
            [("second_source_verified", 0x1234000)],
            [0],
        )

        self.assertEqual(selected, [("second_source_verified", 0x1234000)])

    def test_default_fname_roots_remain_for_non_gobjects_sampling(self) -> None:
        selected = core_pack.fname_roots_for_gobjects_sampling(
            [
                ("primary_default", 0x5956F30),
                ("second_source_verified", 0x1234000),
            ],
            [("second_source_verified", 0x1234000)],
            [],
        )

        self.assertEqual(
            selected,
            [
                ("primary_default", 0x5956F30),
                ("second_source_verified", 0x1234000),
            ],
        )

    def test_gobjects_sample_options_are_bounded(self) -> None:
        self.assertEqual(
            core_pack.validate_gobjects_sample_options(
                [("gobjects", 0x595B7E0)],
                [-1],
                [("fname", 0x5956F30)],
            ),
            "--gobjects-sample-index must be non-negative",
        )
        self.assertEqual(
            core_pack.validate_gobjects_sample_options(
                [("gobjects", 0x595B7E0)],
                list(range(core_pack.MAX_GOBJECTS_SAMPLE_INDICES + 1)),
                [("fname", 0x5956F30)],
            ),
            "--gobjects-sample-index may be repeated at most "
            f"{core_pack.MAX_GOBJECTS_SAMPLE_INDICES} times",
        )

    def test_detect_obelisk_commit_reports_unknown_outside_git(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self.assertEqual(core_pack.detect_obelisk_commit(Path(temp_dir)), "unknown")


if __name__ == "__main__":
    unittest.main()
