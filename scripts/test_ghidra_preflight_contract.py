#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "scripts" / "check_ghidra_preflight_contract.py"


class GhidraPreflightContractTests(unittest.TestCase):
    def test_repo_contract_passes(self) -> None:
        result = subprocess.run(
            ["python3", str(CHECKER)],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ghidra preflight contract ok", result.stdout)

    def test_blocks_zero_image_base_examples(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "Script.java"
            script.write_text(
                """
                if (key.equals("expected_sha256")) {}
                if (key.equals("expected_language")) {}
                if (key.equals("expected_image_base")) {
                    long expectedImageBase = 1;
                    if (expectedImageBase == 0) { throw new IllegalStateException("must_not_be_zero"); }
                }
                if (key.equals("expected_window_count")) {}
                """,
                encoding="utf-8",
            )
            doc = root / "doc.md"
            doc.write_text("bad example: expected_image_base=" + "0x0\n", encoding="utf-8")
            result = subprocess.run(
                ["python3", str(CHECKER), "--script", str(script), "--scan-root", str(root)],
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden zero Ghidra image-base example", result.stderr)


if __name__ == "__main__":
    unittest.main()
