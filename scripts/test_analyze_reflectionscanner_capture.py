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


class ReflectionScannerAnalyzerStrictTests(unittest.TestCase):
    def run_analyzer(self, lines: list[str], *extra_args: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "Obelisk.log"
            log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(ANALYZER), *extra_args, str(log_path)],
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
        tables = {
            item["table"]: item
            for item in summary["gname_table_candidates"]
        }
        self.assertEqual(tables["0x7f0000001000"]["status"], "research-candidate")
        self.assertEqual(tables["0x7f0000001000"]["research_candidate_count"], 2)
        self.assertEqual(tables["0x7f0000002000"]["status"], "rejected")
        self.assertIn("preview mismatch observed", tables["0x7f0000002000"]["reason"])


if __name__ == "__main__":
    unittest.main()
