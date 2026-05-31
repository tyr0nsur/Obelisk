#!/usr/bin/env python3
"""Tests for check_static_tooling.py."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_static_tooling as tool  # noqa: E402

SCRIPT = [sys.executable, "scripts/check_static_tooling.py"]


class CheckStaticToolingTests(unittest.TestCase):
    def run_tool(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [*SCRIPT, *args],
            cwd=REPO_ROOT,
            check=check,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_reports_missing_optional_tool_without_failing(self) -> None:
        result = self.run_tool("--tool", "radare2", "--json")

        payload = json.loads(result.stdout)
        self.assertEqual("obelisk.static-tooling-check.v1", payload["schema"])
        self.assertEqual("ok", payload["status"])
        self.assertIn("radare2", payload["tools"])
        self.assertEqual({}, payload["baseline_tools"])

    def test_can_report_baseline_offline_tools(self) -> None:
        result = self.run_tool("--tool", "radare2", "--include-baseline-tools", "--json")

        payload = json.loads(result.stdout)
        self.assertEqual("ok", payload["status"])
        for name in ("c++filt", "file", "nm", "objdump", "readelf", "sha256sum", "strings"):
            with self.subTest(tool=name):
                self.assertIn(name, payload["baseline_tools"])
                self.assertIn("available", payload["baseline_tools"][name])

    def test_required_missing_tool_blocks(self) -> None:
        result = self.run_tool(
            "--tool",
            "rizin",
            "--require-tool",
            "rizin",
            "--json",
            check=False,
        )

        payload = json.loads(result.stdout)
        if payload["tools"]["rizin"]["available"]:
            self.assertEqual(0, result.returncode)
            self.assertEqual([], payload["missing_required_tools"])
        else:
            self.assertEqual(2, result.returncode)
            self.assertEqual("blocked", payload["status"])
            self.assertEqual(["rizin"], payload["missing_required_tools"])

    def test_required_tool_is_checked_even_when_not_selected(self) -> None:
        result = self.run_tool("--tool", "radare2", "--require-tool", "rizin", "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertIn("radare2", payload["tools"])
        self.assertIn("rizin", payload["tools"])

    def test_smoke_requires_binary_and_output_root(self) -> None:
        result = self.run_tool("--run-smoke", "--json", check=False)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("--run-smoke requires --binary", result.stderr)

        with tempfile.TemporaryDirectory() as temp_dir:
            binary = Path(temp_dir) / "ShooterGameServer"
            binary.write_bytes(b"not really an elf")
            result = self.run_tool("--run-smoke", "--binary", str(binary), "--json", check=False)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("--run-smoke requires --output-root", result.stderr)

    def test_rejects_protected_binary_path(self) -> None:
        result = self.run_tool(
            "--binary",
            "/servidor/ark/obelisk/dumps/ShooterGameServer",
            "--json",
            check=False,
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("--binary must not read from protected server root", result.stderr)

    def test_rejects_symlinked_binary_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "ShooterGameServer.real"
            link = root / "ShooterGameServer"
            target.write_bytes(b"not really an elf")
            link.symlink_to(target)

            result = self.run_tool("--binary", str(link), "--json", check=False)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("--binary must not be a symlink", result.stderr)

    def test_rejects_binary_under_symlinked_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            real_dir = root / "real"
            real_dir.mkdir()
            (real_dir / "ShooterGameServer").write_bytes(b"not really an elf")
            link_dir = root / "linked"
            link_dir.symlink_to(real_dir, target_is_directory=True)

            result = self.run_tool("--binary", str(link_dir / "ShooterGameServer"), "--json", check=False)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("--binary must not be a symlink", result.stderr)

    def test_rejects_protected_smoke_output_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            binary = Path(temp_dir) / "ShooterGameServer"
            binary.write_bytes(b"not really an elf")

            result = self.run_tool(
                "--binary",
                str(binary),
                "--output-root",
                "/servidor/ark/obelisk/static-tooling-smoke",
                "--run-smoke",
                "--json",
                check=False,
            )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("--output-root must not write under protected server root", result.stderr)

    def test_rejects_smoke_output_root_under_symlinked_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            real_dir = root / "real-output-parent"
            link_dir = root / "linked-output-parent"
            binary.write_bytes(b"not really an elf")
            real_dir.mkdir()
            link_dir.symlink_to(real_dir, target_is_directory=True)

            result = self.run_tool(
                "--binary",
                str(binary),
                "--output-root",
                str(link_dir / "out"),
                "--run-smoke",
                "--json",
                check=False,
            )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("--output-root must not be a symlink", result.stderr)

    def test_rejects_symlinked_smoke_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "target.txt"
            link = root / "stdout.txt"
            target.write_text("before\n", encoding="utf-8")
            link.symlink_to(target)

            with self.assertRaises(SystemExit):
                tool.write_text(link, "after\n")

            self.assertEqual("before\n", target.read_text(encoding="utf-8"))

    def test_rejects_symlinked_smoke_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            output = root / "out"
            target = root / "target"
            smoke_link = output / "radare2-smoke"
            binary.write_bytes(b"not really an elf")
            output.mkdir()
            target.mkdir()
            smoke_link.symlink_to(target, target_is_directory=True)

            with self.assertRaises(SystemExit):
                tool.run_radare2_smoke(
                    {"available": True, "path": "/bin/true"},
                    binary,
                    output,
                    timeout_sec=1,
                )

    def test_ghidra_smoke_creates_project_root_before_import(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            output = root / "out"
            fake_ghidra = root / "analyzeHeadless"
            binary.write_bytes(b"not really an elf")
            fake_ghidra.write_text("#!/bin/sh\n[ -d \"$1\" ] || exit 42\nexit 0\n", encoding="utf-8")
            fake_ghidra.chmod(0o755)

            result = tool.run_ghidra_smoke(
                {"available": True, "path": str(fake_ghidra)},
                binary,
                output,
                timeout_sec=1,
            )

            self.assertEqual("ok", result["status"])
            self.assertTrue((output / "ghidra-smoke" / "project").is_dir())

    def test_rejects_symlinked_ghidra_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            output = root / "out"
            target = root / "project-target"
            fake_ghidra = root / "analyzeHeadless"
            binary.write_bytes(b"not really an elf")
            (output / "ghidra-smoke").mkdir(parents=True)
            target.mkdir()
            (output / "ghidra-smoke" / "project").symlink_to(target, target_is_directory=True)
            fake_ghidra.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            fake_ghidra.chmod(0o755)

            with self.assertRaises(SystemExit):
                tool.run_ghidra_smoke(
                    {"available": True, "path": str(fake_ghidra)},
                    binary,
                    output,
                    timeout_sec=1,
                )

    def test_analyze_headless_version_rc_one_is_available_probe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            executable = Path(temp_dir) / "analyzeHeadless"
            executable.write_text("#!/bin/sh\nprintf 'Headless Analyzer Usage\\n'\nexit 1\n", encoding="utf-8")
            executable.chmod(0o755)

            with mock.patch.dict(os.environ, {"PATH": temp_dir}):
                report = tool.tool_report("analyzeHeadless", timeout_sec=1)

        self.assertTrue(report["available"])
        self.assertEqual(1, report["version_probe"]["returncode"])
        self.assertEqual("ok", report["version_probe"]["status"])

    def test_smoke_records_skips_when_tools_missing_or_results_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            output = root / "out"
            binary.write_bytes(b"not really an elf")

            result = self.run_tool(
                "--tool",
                "radare2",
                "--tool",
                "analyzeHeadless",
                "--binary",
                str(binary),
                "--output-root",
                str(output),
                "--run-smoke",
                "--timeout-sec",
                "1",
                "--json",
                check=False,
            )

            payload = json.loads(result.stdout)
            self.assertEqual(str(output.resolve()), payload["output_root"])
            self.assertEqual(2, len(payload["smoke"]))
            self.assertTrue((output / "radare2-smoke").exists() or payload["smoke"][0]["status"] == "skipped")
            self.assertTrue((output / "ghidra-smoke").exists() or payload["smoke"][1]["status"] == "skipped")


if __name__ == "__main__":
    unittest.main()
