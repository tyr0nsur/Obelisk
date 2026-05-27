#!/usr/bin/env python3
"""Offline tests for build_core_dump_evidence_pack.py command generation."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import build_core_dump_evidence_pack as core_pack


class CoreDumpEvidencePackCommandTests(unittest.TestCase):
    def test_gdb_commands_include_direct_fname_entry_reads(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            command_file = Path(temp_dir) / "gdb.txt"

            core_pack.write_gdb_command_file(
                command_file,
                candidates=[],
                fname_root_slots=[("static_fname_root_slot", 0x5956F30)],
                fname_indices=[("ServerChat", 9619)],
                gobjects_candidates=[],
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

    def test_gdb_commands_include_bounded_pointer_value_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            command_file = Path(temp_dir) / "gdb.txt"

            core_pack.write_gdb_command_file(
                command_file,
                candidates=[],
                fname_root_slots=[],
                fname_indices=[],
                gobjects_candidates=[],
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


if __name__ == "__main__":
    unittest.main()
