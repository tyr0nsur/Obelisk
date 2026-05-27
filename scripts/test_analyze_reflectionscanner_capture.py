#!/usr/bin/env python3
"""Offline tests for analyze_reflectionscanner_capture.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYZER = REPO_ROOT / "scripts" / "analyze_reflectionscanner_capture.py"


def fname_probe(
    *,
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
        "[ReflectionScanner] candidate FName indirect-table probe: "
        f"table={table} score=7/7 readable_clues=3/3 "
        f"matched_clues={matched}/{matched_max} "
        f"num_elements={num_elements} num_chunks={num_chunks} "
        f"none='{none}' client_message='{client_message}' "
        f"server_chat='{server_chat}'"
    )


class ReflectionScannerAnalyzerStrictTests(unittest.TestCase):
    def run_analyzer(self, lines: list[str]) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "Obelisk.log"
            log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(ANALYZER), "--strict", str(log_path)],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

    def test_single_exact_hit_fails_strict(self) -> None:
        result = self.run_analyzer([fname_probe()])

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FName exact candidates: 1", result.stdout)
        self.assertIn("FName repeat-confirmed candidates: 0", result.stdout)

    def test_repeated_exact_hit_passes_strict(self) -> None:
        result = self.run_analyzer([fname_probe(), fname_probe()])

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("FName exact candidates: 2", result.stdout)
        self.assertIn("FName repeat-confirmed candidates: 2", result.stdout)

    def test_reject_marker_fails_strict_even_with_repeated_hit(self) -> None:
        result = self.run_analyzer(
            [
                fname_probe(),
                fname_probe(),
                "[ChatPlugin] discovery enabled in this copied log",
            ]
        )

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("reject markers:", result.stdout)
        self.assertIn("[ChatPlugin]", result.stdout)

    def test_bad_counts_fail_strict(self) -> None:
        result = self.run_analyzer(
            [
                fname_probe(num_elements=9622),
                fname_probe(num_elements=9622),
            ]
        )

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FName exact candidates: 0", result.stdout)
        self.assertIn("FName repeat-confirmed candidates: 0", result.stdout)


if __name__ == "__main__":
    unittest.main()
