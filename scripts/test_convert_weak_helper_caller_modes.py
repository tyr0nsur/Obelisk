#!/usr/bin/env python3
"""Tests for redacted weak-helper caller-mode conversion."""

from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT = SCRIPT_DIR / "convert_weak_helper_caller_modes.py"
BINARY_SHA256 = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_provenance(path: Path, *, binary_sha256: str = BINARY_SHA256) -> None:
    payload = {
        "schema": "obelisk.offline-artifact-provenance.v1",
        "verified": True,
        "binary_sha256": binary_sha256,
        "artifact_sha256": sha256_bytes(path.read_bytes()),
    }
    path.with_name(path.name + ".provenance.json").write_text(json.dumps(payload), encoding="utf-8")


def ghidra_fixture() -> str:
    c70_callers = "\n".join(
        f"""
=== caller_1d56c70_{caller} 00{caller[2:]}..00{caller[2:]} ===
value = helper_get_maybe_pending_candidate(ptr,1);
MOV ESI,0x1
CALL 0x01d56c70
TEST RAX,RAX
"""
        for caller in ("83a340", "83a720", "83cde0", "9f80f0", "1d299b0", "1d29a20")
    )
    b60_callers = "\n".join(
        f"""
=== caller_1d56b60_{caller} 00{caller[2:]}..00{caller[2:]} ===
cVar1 = helper_is_stale_like_candidate();
cVar2 = helper_is_stale_like_candidate();
MOV ESI,0x0
MOV EDX,0x1
CALL 0x01d56b60
CMP AL,BL
"""
        for caller in ("2355acc", "2355b5c")
    )
    return f"""
=== helper_is_stale_like_candidate 01d56b60..01d56bf4 ===
decompile_completed=true
if ((flags & 0x100) != 0) return true;
if ((param_2 != 0) && ((flags & 0x4000) != 0)) return true;
if (param_3 != 0) return comparison;
01d56b99: TEST AH,0x40
=== helper_get_maybe_pending_candidate 01d56c70..01d56cf4 ===
decompile_completed=true
if ((flags & 0x100) != 0) return 0;
if ((sil == 0) && ((flags & 0x4000) != 0)) return 0;
{c70_callers}
{b60_callers}
"""


def r2_fixture() -> str:
    c70_windows = "\n".join(
        f"""
=== caller_1d56c70_{caller} ===
mov esi, 0x1
call 0x01d56c70
test rax, rax
"""
        for caller in ("83a340", "83a720", "83cde0", "9f80f0", "1d299b0", "1d29a20")
    )
    b60_windows = "\n".join(
        f"""
=== caller_1d56b60_{caller} ===
mov esi, 0x0
mov edx, 0x1
call 0x01d56b60
cmp al, bl
"""
        for caller in ("2355acc", "2355b5c")
    )
    return f"""
0x01d56b60 test ah, 1
0x01d56b70 test ah, 0x40
0x01d56c70 test ah, 1
0x01d56ce3 test dh, 0x40
{c70_windows}
{b60_windows}
"""


def counts_fixture() -> str:
    return """
0x1d56b60: 4 direct calls
0x1d56c70: 6 direct calls
"""


class ConvertWeakHelperCallerModesTests(unittest.TestCase):
    def run_converter(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            check=check,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def write_inputs(
        self,
        root: Path,
        *,
        ghidra_text: str | None = None,
        r2_text: str | None = None,
        counts_text: str | None = None,
    ) -> tuple[Path, Path, Path]:
        ghidra = root / "ghidra.txt"
        r2 = root / "r2.txt"
        counts = root / "counts.txt"
        ghidra.write_text(ghidra_text if ghidra_text is not None else ghidra_fixture(), encoding="utf-8")
        r2.write_text(r2_text if r2_text is not None else r2_fixture(), encoding="utf-8")
        counts.write_text(counts_text if counts_text is not None else counts_fixture(), encoding="utf-8")
        write_provenance(ghidra)
        write_provenance(r2)
        write_provenance(counts)
        return ghidra, r2, counts

    def test_emits_redacted_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ghidra, r2, counts = self.write_inputs(root)
            args = [
                "--ghidra-stdout",
                str(ghidra),
                "--r2-windows",
                str(r2),
                "--direct-call-counts",
                str(counts),
                "--binary-sha256",
                BINARY_SHA256,
                "--tool-version",
                "ghidra=12.1",
                "--tool-version",
                "radare2=5.5.0",
            ]
            first = self.run_converter(*args).stdout
            second = self.run_converter(*args).stdout

        self.assertEqual(first, second)
        payload = json.loads(first)
        self.assertEqual(payload["schema"], "obelisk.weak-helper-caller-mode-redacted.v1")
        self.assertEqual(payload["status"], "accepted_internal_static_evidence")
        self.assertIs(False, payload["builder_contract"]["promotion_gate_ready"])
        self.assertEqual(payload["direct_call_coverage"]["0x1d56b60"]["observed"], 4)
        self.assertEqual(payload["direct_call_coverage"]["0x1d56c70"]["observed"], 6)
        self.assertEqual(payload["helpers"]["0x1d56c70"]["mode_args"], ["sil"])
        self.assertEqual(payload["helpers"]["0x1d56b60"]["observed_direct_caller_mode"], {"sil": 0, "dl": 1})
        self.assertEqual(len(payload["caller_rows"]), 6)
        caller_hashes = {row["caller_address_sha256"] for row in payload["caller_rows"]}
        self.assertEqual(len(caller_hashes), 6)
        expected_helper_hash = hashlib.sha256(
            f"obelisk.weak-helper-caller-mode:{BINARY_SHA256}:0x1d56c70".encode("ascii")
        ).hexdigest()
        for row in payload["caller_rows"]:
            self.assertEqual(row["helper"], "0x1d56c70")
            self.assertEqual(row["helper_address_sha256"], expected_helper_hash)
            self.assertRegex(row["caller_address_sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(row["mode_args"], {"sil": {"source": "const", "value": 1}})
            self.assertEqual(row["return_use"], {"register": "rax", "nonzero_path": "kept_or_valid"})
            self.assertEqual(row["source_count"], 2)
            self.assertEqual(row["evidence"], ["ghidra", "radare2"])
            self.assertEqual(row["policy_observation"]["0x100"], "null_always")
            self.assertEqual(row["policy_observation"]["0x4000"], "not_rejected_in_observed_sil_1_callers")
            self.assertEqual(row["claim_level"], "static_caller_mode_candidate")
            self.assertIs(row["path_redacted"], True)
            self.assertEqual(row["lifecycle_names"], "not_promoted")
        for source in payload["sources"].values():
            self.assertIs(True, source["provenance"]["verified"])
            self.assertEqual(BINARY_SHA256, source["provenance"]["binary_sha256"])
            self.assertEqual(source["artifact_sha256"], source["provenance"]["artifact_sha256"])
            self.assertRegex(source["provenance"]["sidecar_sha256"], r"^[0-9a-f]{64}$")
            self.assertIs(True, source["provenance"]["path_redacted"])
        self.assertNotIn(str(root), first)
        for raw_caller in ("0x83a340", "0x83a720", "0x83cde0", "0x9f80f0", "0x1d299b0", "0x1d29a20"):
            self.assertNotIn(raw_caller, first.lower())
        self.assertNotIn("pending-kill", first.lower())
        self.assertNotIn("destroyed", first.lower())

    def test_fails_without_provenance_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ghidra, r2, counts = self.write_inputs(root)
            ghidra.with_name(ghidra.name + ".provenance.json").unlink()
            result = self.run_converter(
                "--ghidra-stdout",
                str(ghidra),
                "--r2-windows",
                str(r2),
                "--direct-call-counts",
                str(counts),
                "--binary-sha256",
                BINARY_SHA256,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--ghidra-stdout provenance", result.stderr)

    def test_fails_without_complete_direct_call_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ghidra, r2, counts = self.write_inputs(root, counts_text="0x1d56b60: 3 direct calls\n0x1d56c70: 6 direct calls\n")
            result = self.run_converter(
                "--ghidra-stdout",
                str(ghidra),
                "--r2-windows",
                str(r2),
                "--direct-call-counts",
                str(counts),
                "--binary-sha256",
                BINARY_SHA256,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("direct_call_count_1d56b60_complete", result.stderr)

    def test_fails_without_allow4000_caller(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ghidra, r2, counts = self.write_inputs(root, r2_text=r2_fixture().replace("mov esi, 0x1", "mov ecx, 0x1", 1))
            result = self.run_converter(
                "--ghidra-stdout",
                str(ghidra),
                "--r2-windows",
                str(r2),
                "--direct-call-counts",
                str(counts),
                "--binary-sha256",
                BINARY_SHA256,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("all_c70_callers_set_allow4000_and_use_nonnull", result.stderr)

    def test_rejects_protected_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ghidra, r2, counts = self.write_inputs(root)
            result = self.run_converter(
                "--ghidra-stdout",
                str(ghidra),
                "--r2-windows",
                str(r2),
                "--direct-call-counts",
                str(counts),
                "--binary-sha256",
                BINARY_SHA256,
                "--output",
                "/servidor/ark/obelisk/dumps/weak-helper.json",
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--output must not write under protected server root", result.stderr)


if __name__ == "__main__":
    unittest.main()
