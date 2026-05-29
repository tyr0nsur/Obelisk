#!/usr/bin/env python3
"""Tests for redacted FUObjectArray field-window probe conversion."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT = SCRIPT_DIR / "convert_fuobjectarray_field_window_probe.py"
BINARY_SHA256 = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"


def ghidra_fixture() -> str:
    return """
=== static_init_caller 007a2780..007a27d8 ===
function=static_init_caller entry=007a2780
decompile_completed=true
func_0x01d474e0(0x595b7e0);
__cxa_atexit(&UNK_01d58fb0,0x595b7e0,0x5825088);
=== ctor_helper 01d474e0..01d47640 ===
*(undefined8 *)(param_1 + 0x10) = 0;
param_1[0x16] = 1000;
_DAT_05938bb0 = 0x595b7f0;
01d4752d: MOV dword ptr [RBX + 0x58],0x3e8
=== serial_accessor_a 01d56970..01d56a26 ===
if (iVar1 < _DAT_0595b804) {
  lVar2 = *(long *)(_DAT_0595b7f0 + index);
}
iVar1 = _DAT_0595b838 + 1;
XADD.LOCK dword ptr [0x0595b838],R15D
CMPXCHG.LOCK dword ptr [RBX],R15D
"""


def r2_fixture() -> str:
    return """
0x007a27a7      mov edi, 0x595b7e0
0x007a27ac      call 0x01d474e0
0x01d47511      movups xmmword [rbx + 0x10], xmm0
0x01d4752d      mov dword [rbx + 0x58], 0x3e8
0x01d47534      mov qword [0x05938bb0], 0x595b7f0
0x01d5698e      cmp dword [0x0595b804], eax
0x01d569b0      mov rdx, qword [0x0595b7f0]
0x01d569d3      lock xadd dword [0x0595b838], r15d
0x01d56a03      lock cmpxchg dword [rbx], r15d
"""


class ConvertFuObjectArrayFieldWindowProbeTests(unittest.TestCase):
    def run_converter(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            check=check,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def write_inputs(self, root: Path, *, ghidra_text: str | None = None, r2_text: str | None = None) -> tuple[Path, Path]:
        ghidra = root / "ghidra.txt"
        r2 = root / "r2.txt"
        ghidra.write_text(ghidra_text if ghidra_text is not None else ghidra_fixture(), encoding="utf-8")
        r2.write_text(r2_text if r2_text is not None else r2_fixture(), encoding="utf-8")
        return ghidra, r2

    def test_emits_deterministic_redacted_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ghidra, r2 = self.write_inputs(root)

            args = [
                "--ghidra-stdout",
                str(ghidra),
                "--r2-windows",
                str(r2),
                "--binary-sha256",
                BINARY_SHA256,
                "--candidate-address",
                "0x595b7e0",
                "--tool-version",
                "ghidra=12.1",
                "--tool-version",
                "radare2=5.5.0",
            ]
            first = self.run_converter(*args).stdout
            second = self.run_converter(*args).stdout

        self.assertEqual(first, second)
        payload = json.loads(first)
        self.assertEqual(payload["schema"], "obelisk.fuobjectarray-field-window-redacted.v1")
        self.assertTrue(payload["fuobjectarray_window"]["same_base_flow"]["proven"])
        self.assertEqual(payload["candidate"]["label"], "gobjects")
        self.assertNotIn("0x595b7e0", first)
        self.assertNotIn(str(root), first)

    def test_fails_without_r2_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ghidra, r2 = self.write_inputs(root, r2_text="0x007a27a7 mov edi, 0x595b7e0\n")
            result = self.run_converter(
                "--ghidra-stdout",
                str(ghidra),
                "--r2-windows",
                str(r2),
                "--binary-sha256",
                BINARY_SHA256,
                "--candidate-address",
                "0x595b7e0",
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("serial_accessors_use_same_field_family", result.stderr)

    def test_rejects_protected_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ghidra, r2 = self.write_inputs(root)
            result = self.run_converter(
                "--ghidra-stdout",
                str(ghidra),
                "--r2-windows",
                str(r2),
                "--binary-sha256",
                BINARY_SHA256,
                "--candidate-address",
                "0x595b7e0",
                "--output",
                "/servidor/ark/obelisk/dumps/fuobjectarray.json",
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--output must not write under protected server root", result.stderr)


if __name__ == "__main__":
    unittest.main()
