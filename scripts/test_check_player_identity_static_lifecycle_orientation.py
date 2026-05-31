#!/usr/bin/env python3
"""Tests for check_player_identity_static_lifecycle_orientation.py."""

from __future__ import annotations

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
SCRIPT = SCRIPT_DIR / "check_player_identity_static_lifecycle_orientation.py"
REGISTRAR_CALL_VMA = 0x1CCC140
CLASS_SLOT_VMA = 0x58F2BD0


SEGMENTS = [
    {"offset": 0x1000, "vaddr": 0x13CC000, "filesz": 0x1000, "memsz": 0x1000, "flags": 0x5},
    {"offset": 0x3000, "vaddr": 0x15D0000, "filesz": 0x3000, "memsz": 0x3000, "flags": 0x5},
    {"offset": 0x7000, "vaddr": 0x3F63000, "filesz": 0x1000, "memsz": 0x1000, "flags": 0x4},
    {"offset": 0x9000, "vaddr": 0x40E0000, "filesz": 0x2000, "memsz": 0x2000, "flags": 0x4},
    {"offset": 0xC000, "vaddr": 0x4170000, "filesz": 0x3000, "memsz": 0x3000, "flags": 0x4},
    {"offset": 0x10000, "vaddr": 0x58446C0, "filesz": 0, "memsz": 0x1E14D0, "flags": 0x6},
]


def vma_to_offset(vma: int, size: int = 1) -> int:
    for segment in SEGMENTS:
        start = segment["vaddr"]
        end = start + segment["filesz"]
        if start <= vma and vma + size <= end:
            return segment["offset"] + (vma - start)
    raise AssertionError(f"test fixture VMA is not file-backed: {hex(vma)}")


def write_vma(data: bytearray, vma: int, payload: bytes) -> None:
    offset = vma_to_offset(vma, len(payload))
    data[offset : offset + len(payload)] = payload


def call_bytes(call_vma: int, target_vma: int) -> bytes:
    return b"\xe8" + struct.pack("<i", target_vma - (call_vma + 5))


def class_load_bytes(load_vma: int) -> bytes:
    return b"\x48\x8b\x3d" + struct.pack("<i", CLASS_SLOT_VMA - (load_vma + 7))


def registration_bytes(registration_vma: int, name_vma: int, thunk_vma: int) -> bytes:
    return (
        b"\xbe"
        + struct.pack("<I", name_vma)
        + b"\xba"
        + struct.pack("<I", thunk_vma)
        + b"\x31\xc9"
        + call_bytes(registration_vma + 12, REGISTRAR_CALL_VMA)
    )


def make_fake_binary(path: Path, *, tamper_vma: int | None = None, tamper_byte: bytes = b"\x00") -> str:
    size = 0x12000
    data = bytearray(size)
    phoff = 64
    phentsize = 56
    phnum = len(SEGMENTS)
    data[:64] = struct.pack(
        "<16sHHIQQQIHHHHHH",
        b"\x7fELF\x02\x01\x01" + b"\x00" * 9,
        2,
        62,
        1,
        0x81DC59,
        phoff,
        0,
        0,
        64,
        phentsize,
        phnum,
        0,
        0,
        0,
    )
    for index, segment in enumerate(SEGMENTS):
        data[phoff + index * phentsize : phoff + (index + 1) * phentsize] = struct.pack(
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

    write_vma(data, 0x3F63B7C, "/Script/ShooterGame".encode("utf-32-le") + b"\x00\x00\x00\x00")
    write_vma(data, 0x40E0B24, "ShooterGameMode".encode("utf-32-le") + b"\x00\x00\x00\x00")
    write_vma(data, 0x4170122, b"HandleNewPlayer\x00")
    write_vma(data, 0x417024F, b"OnLogout\x00")
    write_vma(data, 0x13CC203, class_load_bytes(0x13CC203))
    write_vma(data, 0x13CC20A, registration_bytes(0x13CC20A, 0x4170122, 0x15D04C0))
    write_vma(data, 0x13CC559, class_load_bytes(0x13CC559))
    write_vma(data, 0x13CC560, registration_bytes(0x13CC560, 0x417024F, 0x15D1500))
    write_vma(data, 0x15D04C0, b"\x55\x48\x89\xe5")
    write_vma(data, 0x15D1500, b"\x55\x48\x89\xe5")

    if tamper_vma is not None:
        write_vma(data, tamper_vma, tamper_byte)

    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


class CheckPlayerIdentityStaticLifecycleOrientationTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def test_synthetic_binary_is_valid_candidate_only_orientation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            binary = Path(temp_dir) / "ShooterGameServer"
            digest = make_fake_binary(binary)

            result = self.run_checker(str(binary), "--expected-binary-sha256", digest, "--json")

        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema"], "obelisk.player-identity-static-lifecycle-orientation-check.v1")
        self.assertEqual(payload["status"], "valid")
        self.assertTrue(payload["accepted_for_orientation"])
        self.assertFalse(payload["accepted_lifecycle_anchors"])
        self.assertTrue(payload["not_artifact_gate"])
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertEqual(payload["target_set"], "players-identity-lifecycle-intake")
        self.assertEqual(
            {target["target"] for target in payload["checked_targets"]},
            {"ShooterGameMode.HandleNewPlayer", "ShooterGameMode.OnLogout"},
        )
        self.assertEqual(
            {target["target_set_status"] for target in payload["checked_targets"]},
            {"known_lifecycle_orientation_not_in_closed_target_set"},
        )
        self.assertIn(
            "known_lifecycle_orientation_targets_not_in_closed_target_set",
            payload["promotion_blockers"],
        )
        contract = payload["static_candidate_orientation_contract"]
        self.assertEqual(contract["status"], "candidate_blocked")
        self.assertFalse(contract["promotion_ready"])
        self.assertIn("does not prove accepted session-start", " ".join(payload["non_claims"]))
        self.assertIn("does not promote public identity", " ".join(payload["non_claims"]))

    def test_registration_pattern_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            binary = Path(temp_dir) / "ShooterGameServer"
            digest = make_fake_binary(binary, tamper_vma=0x13CC20F, tamper_byte=b"\x51")

            result = self.run_checker(str(binary), "--expected-binary-sha256", digest, check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["status"], "blocked")
        self.assertIn("registration_thunk_immediate_mismatch", {blocker["reason"] for blocker in payload["blockers"]})
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])

    def test_ascii_name_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            binary = Path(temp_dir) / "ShooterGameServer"
            digest = make_fake_binary(binary, tamper_vma=0x417024F, tamper_byte=b"X")

            result = self.run_checker(str(binary), "--expected-binary-sha256", digest, check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("lifecycle_ascii_name_mismatch", {blocker["reason"] for blocker in payload["blockers"]})

    def test_sha_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            binary = Path(temp_dir) / "ShooterGameServer"
            make_fake_binary(binary)

            result = self.run_checker(
                str(binary),
                "--expected-binary-sha256",
                "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("binary_sha256_mismatch", {blocker["reason"] for blocker in payload["blockers"]})


if __name__ == "__main__":
    unittest.main()
