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
            self.assertIn("set $fuobject_metadata = *(unsigned long long*)(((char*)$fuobject_item)+0x8)", text)
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
