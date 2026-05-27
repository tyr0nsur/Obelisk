#!/usr/bin/env python3
"""Offline tests for analyze_reflectionscanner_capture.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYZER = REPO_ROOT / "scripts" / "analyze_reflectionscanner_capture.py"


def fname_probe(
    *,
    target: str = "candidate",
    source_global: str = "0x600000",
    table: str = "0x7f0000001000",
    matched: int = 3,
    matched_max: int = 3,
    num_elements: int = 10000,
    num_chunks: int = 1,
    none: str = "None",
    client_message: str = "ClientMessage",
    server_chat: str = "ServerChat",
) -> str:
    return (
        f"[ReflectionScanner] {target} FName indirect-table probe: "
        f"source_global={source_global} table={table} score=8/8 readable_clues=3/3 "
        f"matched_clues={matched}/{matched_max} "
        f"num_elements={num_elements} num_chunks={num_chunks} "
        f"none='{none}' client_message='{client_message}' "
        f"server_chat='{server_chat}'"
    )


def fname_reject(
    *,
    target: str = "candidate",
    source_global: str = "0x600000",
    table: str = "0x7f0000001000",
    reason: str = "unreadable_chunk_pointer",
    readable: int = 0,
    readable_max: int = 3,
    matched: int = 0,
    matched_max: int = 3,
    num_elements: int = 10000,
    num_chunks: int = 1,
    none: str = "",
    client_message: str = "",
    server_chat: str = "",
) -> str:
    return (
        f"[ReflectionScanner] {target} FName indirect-table reject: "
        f"source_global={source_global} table={table} reason={reason} "
        f"readable_clues={readable}/{readable_max} matched_clues={matched}/{matched_max} "
        f"num_elements={num_elements} num_chunks={num_chunks} "
        f"none='{none}' client_message='{client_message}' "
        f"server_chat='{server_chat}'"
    )


class ReflectionScannerAnalyzerStrictTests(unittest.TestCase):
    def run_analyzer(
        self,
        lines: list[str],
        *extra_args: str,
        objdump_text: str | None = None,
        binary_text: bytes | None = None,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "Obelisk.log"
            log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            args = [sys.executable, str(ANALYZER), *extra_args]
            if objdump_text is not None:
                objdump_path = Path(temp_dir) / "ShooterGameServer.objdump"
                objdump_path.write_text(objdump_text, encoding="utf-8")
                args.extend(["--objdump-xrefs", str(objdump_path)])
            if binary_text is not None:
                binary_path = Path(temp_dir) / "ShooterGameServer"
                binary_path.write_bytes(binary_text)
                args.extend(["--binary", str(binary_path)])
            args.append(str(log_path))
            return subprocess.run(
                args,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

    def test_single_exact_hit_fails_strict(self) -> None:
        result = self.run_analyzer([fname_probe()], "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FName exact candidates: 1", result.stdout)
        self.assertIn("FName repeat-confirmed candidates: 0", result.stdout)
        self.assertIn("status=rejected", result.stdout)
        self.assertIn("single-source evidence only", result.stdout)

    def test_repeated_exact_hit_passes_strict(self) -> None:
        result = self.run_analyzer(
            [
                fname_probe(source_global="0x600000"),
                fname_probe(source_global="0x600008"),
            ],
            "--strict",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("FName exact candidates: 2", result.stdout)
        self.assertIn("FName repeat-confirmed candidates: 2", result.stdout)
        self.assertIn("distinct_globals=2", result.stdout)
        self.assertIn("status=research-candidate", result.stdout)
        self.assertIn("repeat-confirmed exact clue match", result.stdout)

    def test_duplicate_exact_hit_fails_strict(self) -> None:
        result = self.run_analyzer([fname_probe(), fname_probe()], "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FName exact candidates: 2", result.stdout)
        self.assertIn("FName repeat-confirmed candidates: 0", result.stdout)
        self.assertIn("table_seen=2", result.stdout)

    def test_repeated_exact_hit_by_distinct_target_passes_strict(self) -> None:
        result = self.run_analyzer(
            [
                fname_probe(target="ServerChat"),
                fname_probe(target="ClientMessage"),
            ],
            "--strict",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("FName exact candidates: 2", result.stdout)
        self.assertIn("FName repeat-confirmed candidates: 2", result.stdout)
        self.assertIn("distinct_targets=2", result.stdout)

    def test_reject_marker_fails_strict_even_with_repeated_hit(self) -> None:
        result = self.run_analyzer(
            [
                fname_probe(source_global="0x600000"),
                fname_probe(source_global="0x600008"),
                "[LegacyPlugin] discovery enabled in this copied log",
            ],
            "--strict",
        )

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("reject markers:", result.stdout)
        self.assertIn("[LegacyPlugin]", result.stdout)

    def test_bad_counts_fail_strict(self) -> None:
        result = self.run_analyzer(
            [
                fname_probe(num_elements=9622),
                fname_probe(num_elements=9622),
            ],
            "--strict",
        )

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FName exact candidates: 0", result.stdout)
        self.assertIn("FName repeat-confirmed candidates: 0", result.stdout)
        self.assertIn("no plausible element/chunk count", result.stdout)

    def test_json_summarizes_gname_table_candidates(self) -> None:
        result = self.run_analyzer(
            [
                fname_probe(source_global="0x600000"),
                fname_probe(source_global="0x600008"),
                fname_probe(
                    table="0x7f0000002000",
                    none="None",
                    client_message="ServerChat",
                    server_chat="ClientMessage",
                ),
            ],
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["evidence_pack"]["status"], "research-candidate")
        self.assertEqual(summary["evidence_pack"]["gname_table_candidate_count"], 1)
        tables = {
            item["table"]: item
            for item in summary["gname_table_candidates"]
        }
        self.assertEqual(tables["0x7f0000001000"]["status"], "research-candidate")
        self.assertEqual(tables["0x7f0000001000"]["research_candidate_count"], 2)
        self.assertEqual(tables["0x7f0000002000"]["status"], "rejected")
        self.assertIn("preview mismatch observed", tables["0x7f0000002000"]["reason"])

    def test_json_summarizes_fname_rejects(self) -> None:
        result = self.run_analyzer(
            [
                fname_reject(reason="unreadable_chunk_pointer"),
                fname_reject(source_global="0x600008", reason="preview_mismatch"),
                fname_reject(source_global="0x600010", reason="preview_mismatch"),
            ],
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["evidence_pack"]["status"], "inconclusive")
        self.assertEqual(summary["evidence_pack"]["fname_probe_count"], 0)
        self.assertEqual(summary["evidence_pack"]["fname_reject_count"], 3)
        self.assertEqual(
            summary["evidence_pack"]["fname_reject_reason_counts"],
            {"preview_mismatch": 2, "unreadable_chunk_pointer": 1},
        )
        self.assertEqual(summary["fname_rejects"][0]["reason"], "unreadable_chunk_pointer")
        self.assertEqual(summary["fname_rejects"][1]["source_global"], "0x600008")

    def test_fname_rejects_do_not_satisfy_strict(self) -> None:
        result = self.run_analyzer(
            [
                fname_reject(reason="preview_mismatch"),
                fname_reject(source_global="0x600008", reason="preview_mismatch"),
            ],
            "--strict",
        )

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FName probes: 0", result.stdout)
        self.assertIn("FName rejects: 2", result.stdout)
        self.assertIn("preview_mismatch: 2", result.stdout)

    def test_json_annotates_static_xrefs_from_objdump_text(self) -> None:
        result = self.run_analyzer(
            [
                fname_probe(source_global="0x600000"),
                fname_probe(source_global="0x600008"),
            ],
            "--json",
            objdump_text="""
0000000000410000 <.text>:
  410010: 48 89 1d e9 ff 1e 00    mov    %rbx,0x1effe9(%rip)        # 0x600000
  410020: 48 8b 05 e1 ff 1e 00    mov    0x1effe1(%rip),%rax        # 0x600008
  410030: 48 8b 05 d9 ff 1e 00    mov    0x1effd9(%rip),%rax        # 0x600010
""",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(len(summary["static_xrefs"]["0x600000"]), 1)
        self.assertEqual(summary["static_xrefs"]["0x600000"][0]["access"], "store")
        self.assertEqual(len(summary["static_xrefs"]["0x600008"]), 1)
        self.assertEqual(summary["static_xrefs"]["0x600008"][0]["access"], "load")
        self.assertEqual(
            summary["evidence_pack"]["static_xref_access_counts"],
            {"load": 1, "store": 1},
        )
        self.assertNotIn("0x600010", summary["static_xrefs"])

    def test_json_classifies_intel_static_xref_access(self) -> None:
        result = self.run_analyzer(
            [
                fname_probe(source_global="0x600000"),
                fname_probe(source_global="0x600008"),
            ],
            "--json",
            objdump_text="""
0000000000410000 <.text>:
  410010: 48 89 1d e9 ff 1e 00    mov    QWORD PTR [rip+0x1effe9],rbx        # 0x600000
  410020: 48 8b 05 e1 ff 1e 00    mov    rax,QWORD PTR [rip+0x1effe1]        # 0x600008
  410028: 48 8d 05 d1 ff 1e 00    lea    rax,[rip+0x1effd1]                 # 0x600008
""",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["static_xrefs"]["0x600000"][0]["access"], "store")
        self.assertEqual(summary["static_xrefs"]["0x600008"][0]["access"], "load")
        self.assertEqual(summary["static_xrefs"]["0x600008"][1]["access"], "address")
        self.assertEqual(
            summary["evidence_pack"]["static_xref_access_counts"],
            {"address": 1, "load": 1, "store": 1},
        )

    def test_human_output_reports_static_xrefs(self) -> None:
        result = self.run_analyzer(
            [fname_probe(source_global="0x600000")],
            objdump_text=(
                "  410010: 48 89 1d e9 ff 1e 00    "
                "mov    %rbx,0x1effe9(%rip)        # 0x600000\n"
            ),
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("static xrefs:", result.stdout)
        self.assertIn("0x600000: 1 reference(s)", result.stdout)
        self.assertIn("0x410010", result.stdout)
        self.assertIn("access=store", result.stdout)

    def test_json_includes_evidence_pack_binary_metadata(self) -> None:
        result = self.run_analyzer(
            [
                fname_probe(source_global="0x600000"),
                fname_probe(source_global="0x600008"),
            ],
            "--json",
            "--obelisk-commit",
            "test-commit",
            binary_text=b"offline-test-binary",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        summary = json.loads(result.stdout)
        evidence_pack = summary["evidence_pack"]
        self.assertEqual(evidence_pack["obelisk_commit"], "test-commit")
        self.assertEqual(evidence_pack["binary"]["size_bytes"], 19)
        self.assertEqual(
            evidence_pack["binary"]["sha256"],
            "d936ee81753955ccd696878ea4beb9cf69db467d7c6e5fdc2ffd001c81b641e6",
        )
        self.assertIn("Never promote directly", evidence_pack["promotion_gate"])


if __name__ == "__main__":
    unittest.main()
