#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "scripts" / "check_ghidra_preflight_contract.py"


class GhidraPreflightContractTests(unittest.TestCase):
    def run_checker(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(CHECKER), *args],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def write_contract_script(
        self,
        path: Path,
        *,
        include_window_count: bool = True,
        include_unknown_reject: bool = True,
        include_zero_reject: bool = True,
        include_non_promotion_markers: bool = True,
    ) -> None:
        window_count_branch = (
            'else if (key.equals("expected_window_count")) { requireEquals(key, 7, windows.length); }'
            if include_window_count
            else ""
        )
        unknown_branch = (
            'else { throw new IllegalArgumentException("preflight_failed: unknown_arg=" + key); }'
            if include_unknown_reject
            else ""
        )
        zero_check = (
            'if (expectedImageBase == 0) { throw new IllegalStateException("must_not_be_zero"); }'
            if include_zero_reject
            else ""
        )
        non_promotion_markers = (
            """
                    println("status=candidate-only static orientation");
                    println("not_artifact_gate=true");
                    println("promotion_ready=false");
                    println("non_claim=Ghidra windows are offline navigation only; not consume or promote evidence");
            """
            if include_non_promotion_markers
            else ""
        )
        path.write_text(
            f"""
            class Script {{
                void validatePreflight() {{
                    {non_promotion_markers}
                    if (key.equals("expected_sha256")) {{ requireEquals(key, expected, actual); }}
                    else if (key.equals("expected_language")) {{ requireEquals(key, expected, actual); }}
                    else if (key.equals("expected_image_base")) {{
                        long expectedImageBase = parseExpectedLong(expected);
                        {zero_check}
                    }}
                    {window_count_branch}
                    {unknown_branch}
                }}
            }}
            """,
            encoding="utf-8",
        )

    def test_repo_contract_passes(self) -> None:
        result = self.run_checker()
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
                else { throw new IllegalArgumentException("preflight_failed: unknown_arg=" + key); }
                """,
                encoding="utf-8",
            )
            doc = root / "doc.md"
            doc.write_text("bad example: expected_image_base=" + "0x0\n", encoding="utf-8")
            result = self.run_checker("--script", str(script), "--scan-root", str(root))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden zero Ghidra image-base example", result.stderr)

    def test_blocks_java_preflight_contract_regressions(self) -> None:
        cases = (
            (
                "missing_required_key",
                {"include_window_count": False},
                "missing expected_window_count preflight key",
            ),
            (
                "missing_unknown_arg_reject",
                {"include_unknown_reject": False},
                "unknown preflight keys are not explicitly rejected",
            ),
            (
                "missing_zero_image_base_reject",
                {"include_zero_reject": False},
                "expected_image_base zero is not explicitly rejected",
            ),
            (
                "missing_non_promotion_markers",
                {"include_non_promotion_markers": False},
                "missing non-promotional marker status=candidate-only static orientation",
            ),
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, options, expected_blocker in cases:
                with self.subTest(name=name):
                    script = root / f"{name}.java"
                    self.write_contract_script(script, **options)
                    result = self.run_checker("--script", str(script), "--scan-root", str(root))
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(expected_blocker, result.stderr)


if __name__ == "__main__":
    unittest.main()
