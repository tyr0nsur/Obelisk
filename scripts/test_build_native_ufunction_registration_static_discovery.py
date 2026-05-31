#!/usr/bin/env python3
"""Tests for build_native_ufunction_registration_static_discovery.py."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "build_native_ufunction_registration_static_discovery.py"
sys.path.insert(0, str(SCRIPT_DIR))

import validate_offline_artifact_gate as gate  # noqa: E402


def call_bytes(call_vma: int, target_vma: int) -> bytes:
    return b"\xe8" + struct.pack("<i", target_vma - (call_vma + 5))


class SyntheticElf:
    def __init__(self, *, base: int) -> None:
        self.base = base
        self.segments = [
            {"offset": 0x1000, "vaddr": base + 0x1000, "filesz": 0x3000, "memsz": 0x3000, "flags": 0x5},
            {"offset": 0x5000, "vaddr": base + 0x9000, "filesz": 0x3000, "memsz": 0x3000, "flags": 0x4},
        ]
        self.data = bytearray(0x9000)
        self._write_header()

    def _write_header(self) -> None:
        phoff = 64
        phentsize = 56
        self.data[:64] = struct.pack(
            "<16sHHIQQQIHHHHHH",
            b"\x7fELF\x02\x01\x01" + b"\x00" * 9,
            2,
            62,
            1,
            self.base + 0x1000,
            phoff,
            0,
            0,
            64,
            phentsize,
            len(self.segments),
            0,
            0,
            0,
        )
        for index, segment in enumerate(self.segments):
            self.data[phoff + index * phentsize : phoff + (index + 1) * phentsize] = struct.pack(
                "<IIQQQQQQ",
                1,
                segment["flags"],
                segment["offset"],
                segment["vaddr"],
                segment["vaddr"],
                segment["filesz"],
                segment["memsz"],
                0x1000,
            )

    def vma_to_offset(self, vma: int, size: int = 1) -> int:
        for segment in self.segments:
            if segment["vaddr"] <= vma and vma + size <= segment["vaddr"] + segment["filesz"]:
                return segment["offset"] + (vma - segment["vaddr"])
        raise AssertionError(f"fixture VMA not file-backed: {hex(vma)}")

    def write_vma(self, vma: int, value: bytes) -> None:
        offset = self.vma_to_offset(vma, len(value))
        self.data[offset : offset + len(value)] = value

    def add_target(
        self,
        *,
        name: str,
        string_vma: int,
        registration_vma: int,
        thunk_vma: int,
        registrar_vma: int | None = None,
        thunk_bytes: bytes = b"\x55\x48\x89\xe5\xc3",
    ) -> None:
        self.write_vma(string_vma, name.encode("ascii") + b"\x00")
        self.write_vma(thunk_vma, thunk_bytes)
        self.write_vma(
            registration_vma,
            b"\xbe"
            + struct.pack("<I", string_vma)
            + b"\xba"
            + struct.pack("<I", thunk_vma)
            + b"\x31\xc9"
            + call_bytes(registration_vma + 12, registrar_vma if registrar_vma is not None else self.base + 0x2220),
        )

    def write(self, path: Path) -> str:
        path.write_bytes(self.data)
        return hashlib.sha256(self.data).hexdigest()


class BuildNativeUFunctionRegistrationStaticDiscoveryTests(unittest.TestCase):
    def run_script(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def gate_args(
        self,
        *,
        root: Path,
        protected_root: Path,
        manifest: Path,
        mode: str = "consume",
    ) -> argparse.Namespace:
        return argparse.Namespace(
            root=root,
            protected_root=protected_root,
            manifest=[manifest],
            artifact=[],
            expected_binary_sha256=None,
            mode=mode,
            strict_target_set_coverage=False,
            json=True,
        )

    def test_rediscovers_registration_without_fixed_vmas(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            elf = SyntheticElf(base=0x240000)
            elf.add_target(
                name="ServerListPlayers",
                string_vma=0x249120,
                registration_vma=0x241180,
                thunk_vma=0x242400,
            )
            digest = elf.write(binary)

            result = self.run_script(
                "--binary",
                str(binary),
                "--expected-binary-sha256",
                digest,
                "--target",
                "ShooterPlayerController.ServerListPlayers",
                "--run-id",
                "synthetic-vma-shift",
                "--json",
            )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema"], "obelisk.native-ufunction-registration-static-discovery.v1")
        self.assertIn(payload["schema"], gate.STATIC_ORIENTATION_REPORT_SCHEMAS)
        self.assertNotIn(payload["schema"], gate.SUPPORTED_MANIFEST_SCHEMAS)
        self.assertEqual(payload["status"], "candidate")
        self.assertTrue(payload["accepted_for_orientation"])
        self.assertTrue(payload["not_artifact_gate"])
        self.assertFalse(payload["artifact_gate_eligible"])
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertEqual(payload["inputs"]["input_addresses"], [])
        target = payload["targets"][0]
        self.assertEqual(target["target"], "ShooterPlayerController.ServerListPlayers")
        self.assertEqual(target["registration_candidates"][0]["thunk_vma"], "0x242400")
        self.assertEqual(target["registration_candidates"][0]["registrar_target_vma"], "0x242220")
        self.assertEqual(target["registration_candidates"][0]["source_string_hit"]["encoding"], "ascii")
        self.assertEqual(target["selected_candidate"]["thunk_vma"], "0x242400")
        self.assertIn("thunk_prefix_code_like", target["selected_candidate"]["selection_reasons"])
        self.assertIn("does_not_promote_public_sdk", payload["non_claims"])

    def test_prefers_code_like_thunk_over_string_table_false_positive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            elf = SyntheticElf(base=0x2A0000)
            elf.add_target(
                name="ServerKickPlayer",
                string_vma=0x2A9100,
                registration_vma=0x2A1140,
                thunk_vma=0x2A2700,
            )
            elf.add_target(
                name="ServerKickPlayer",
                string_vma=0x2A9100,
                registration_vma=0x2A1200,
                thunk_vma=0x2A2800,
                registrar_vma=0x2A3330,
                thunk_bytes=b"/\x00\x00\x00S\x00\x00\x00",
            )
            digest = elf.write(binary)

            result = self.run_script(
                "--binary",
                str(binary),
                "--expected-binary-sha256",
                digest,
                "--target",
                "ShooterPlayerController.ServerKickPlayer",
                "--run-id",
                "false-positive-ranking",
            )

        payload = json.loads(result.stdout)
        target = payload["targets"][0]
        self.assertEqual(target["status"], "candidate")
        self.assertEqual(len([c for c in target["registration_candidates"] if c["status"] == "candidate"]), 2)
        self.assertEqual(target["selected_candidate"]["thunk_vma"], "0x2a2700")
        self.assertTrue(target["selected_candidate"]["thunk_prefix_code_like"])

    def test_utf32_hits_are_reported_but_not_used_for_registration_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            elf = SyntheticElf(base=0x2C0000)
            elf.write_vma(0x2C9100, "ServerKickPlayer".encode("utf-32-le") + b"\x00\x00\x00\x00")
            elf.write_vma(0x2C2700, b"\x55\x48\x89\xe5\xc3")
            elf.write_vma(
                0x2C1140,
                b"\xbe"
                + struct.pack("<I", 0x2C9100)
                + b"\xba"
                + struct.pack("<I", 0x2C2700)
                + b"\x31\xc9"
                + call_bytes(0x2C114C, 0x2C2220),
            )
            digest = elf.write(binary)

            result = self.run_script(
                "--binary",
                str(binary),
                "--expected-binary-sha256",
                digest,
                "--target",
                "ShooterPlayerController.ServerKickPlayer",
                "--run-id",
                "utf32-not-registration",
                check=False,
            )

        payload = json.loads(result.stdout)
        target = payload["targets"][0]
        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(target["string_hits"][0]["encoding"], "utf32le")
        self.assertFalse(target["string_hits"][0]["used_for_registration_candidates"])
        self.assertEqual(target["registration_candidates"], [])
        self.assertIn(
            "ascii_target_name_string_not_found",
            {blocker["reason"] for blocker in target["blockers"]},
        )

    def test_rejects_address_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            binary = Path(temp_dir) / "ShooterGameServer"
            elf = SyntheticElf(base=0x260000)
            digest = elf.write(binary)
            result = self.run_script(
                "--binary",
                str(binary),
                "--expected-binary-sha256",
                digest,
                "--target",
                "0x241180",
                check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("targets must be names, not addresses", result.stderr)

    def test_writes_manifest_when_output_root_is_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            output = root / "out"
            elf = SyntheticElf(base=0x280000)
            elf.add_target(
                name="ServerKickPlayer",
                string_vma=0x289100,
                registration_vma=0x281140,
                thunk_vma=0x282700,
            )
            digest = elf.write(binary)

            result = self.run_script(
                "--binary",
                str(binary),
                "--expected-binary-sha256",
                digest,
                "--target",
                "ShooterPlayerController.ServerKickPlayer",
                "--output-root",
                str(output),
                "--run-id",
                "manifest-out",
            )

            payload = json.loads(result.stdout)
            manifest = Path(payload["manifest_path"])
            self.assertTrue(manifest.is_file())
            written = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(written["schema"], payload["schema"])
            self.assertEqual(written["status"], "candidate")

    def test_generated_manifest_is_rejected_by_artifact_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            output = root / "out"
            protected = root / "protected"
            elf = SyntheticElf(base=0x2A0000)
            elf.add_target(
                name="ServerListPlayers",
                string_vma=0x2A9100,
                registration_vma=0x2A1140,
                thunk_vma=0x2A2700,
            )
            digest = elf.write(binary)

            result = self.run_script(
                "--binary",
                str(binary),
                "--expected-binary-sha256",
                digest,
                "--target",
                "ShooterPlayerController.ServerListPlayers",
                "--output-root",
                str(output),
                "--run-id",
                "artifact-gate-blocked",
            )

            manifest = Path(json.loads(result.stdout)["manifest_path"])
            for mode in ("consume", "promote"):
                with self.subTest(mode=mode):
                    gate_result = gate.build_result(
                        self.gate_args(root=root, protected_root=protected, manifest=manifest, mode=mode)
                    )
                    reasons = {blocker["reason"] for blocker in gate_result["blockers"]}
                    self.assertEqual(gate_result["status"], "blocked")
                    self.assertIn("static_orientation_report_not_artifact_gate", reasons)
                    self.assertIn("unsupported_manifest_schema", reasons)

    def test_manipulated_manifest_overclaims_are_rejected_by_artifact_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            output = root / "out"
            protected = root / "protected"
            elf = SyntheticElf(base=0x2C0000)
            elf.add_target(
                name="ServerKickPlayer",
                string_vma=0x2C9100,
                registration_vma=0x2C1140,
                thunk_vma=0x2C2700,
            )
            digest = elf.write(binary)

            result = self.run_script(
                "--binary",
                str(binary),
                "--expected-binary-sha256",
                digest,
                "--target",
                "ShooterPlayerController.ServerKickPlayer",
                "--output-root",
                str(output),
                "--run-id",
                "artifact-gate-overclaim",
            )

            manifest = Path(json.loads(result.stdout)["manifest_path"])
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["promotion_ready"] = True
            payload["public_sdk_ready"] = True
            payload["runtime_ready"] = True
            payload["inputs"]["input_addresses"] = ["0x2c1140"]
            manifest.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

            gate_result = gate.build_result(self.gate_args(root=root, protected_root=protected, manifest=manifest))

        reasons = {blocker["reason"] for blocker in gate_result["blockers"]}
        labels = {blocker["label"] for blocker in gate_result["blockers"] if "label" in blocker}
        self.assertEqual(gate_result["status"], "blocked")
        self.assertIn("static_orientation_report_not_artifact_gate", reasons)
        self.assertIn("static_orientation_report_readiness_overclaim", reasons)
        self.assertIn("static_orientation_report_input_addresses_overclaim", reasons)
        self.assertIn("promotion_ready_overclaim", reasons)
        self.assertTrue(any(label.endswith("$.promotion_ready") for label in labels))
        self.assertTrue(any(label.endswith("$.public_sdk_ready") for label in labels))
        self.assertTrue(any(label.endswith("$.runtime_ready") for label in labels))


if __name__ == "__main__":
    unittest.main()
