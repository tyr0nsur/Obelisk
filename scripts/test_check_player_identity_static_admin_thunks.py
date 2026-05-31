#!/usr/bin/env python3
"""Tests for check_player_identity_static_admin_thunks.py."""

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
SCRIPT = SCRIPT_DIR / "check_player_identity_static_admin_thunks.py"
DEFAULT_BINARY = Path(
    "/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/"
    "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/"
    "ShooterGameServer"
)
REGISTRAR_CALL_VMA = 0x1CCC140
FNAME_INIT_CALL_VMA = 0x1C892D0
CLASS_SLOT_VMA = 0x58EEBF0


SEGMENTS = [
    {"offset": 0x1000, "vaddr": 0x78D000, "filesz": 0x1000, "memsz": 0x1000, "flags": 0x5},
    {"offset": 0x2000, "vaddr": 0x1368000, "filesz": 0x2000, "memsz": 0x2000, "flags": 0x5},
    {"offset": 0x4000, "vaddr": 0x1547000, "filesz": 0x5000, "memsz": 0x5000, "flags": 0x5},
    {"offset": 0xA000, "vaddr": 0x3F63000, "filesz": 0x1000, "memsz": 0x1000, "flags": 0x4},
    {"offset": 0xB000, "vaddr": 0x40D7000, "filesz": 0x29000, "memsz": 0x29000, "flags": 0x4},
    {"offset": 0x35000, "vaddr": 0x4163000, "filesz": 0x1000, "memsz": 0x1000, "flags": 0x4},
    {"offset": 0x36000, "vaddr": 0x58446C0, "filesz": 0, "memsz": 0x1E14D0, "flags": 0x6},
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


def fname_init_bytes(init_vma: int, slot_vma: int, name_vma: int) -> bytes:
    return (
        b"\xbf"
        + struct.pack("<I", slot_vma)
        + b"\xbe"
        + struct.pack("<I", name_vma)
        + b"\xba\x01\x00\x00\x00"
        + b"\xb9\x01\x00\x00\x00"
        + call_bytes(init_vma + 20, FNAME_INIT_CALL_VMA)
    )


def make_fake_binary(path: Path, *, tamper_vma: int | None = None, tamper_byte: bytes = b"\x00") -> str:
    size = 0x37000
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
    write_vma(data, 0x40D7418, "AShooterPlayerController".encode("utf-32-le") + b"\x00\x00\x00\x00")
    write_vma(data, 0x40FD540, "ServerKickPlayer".encode("utf-32-le") + b"\x00\x00\x00\x00")
    write_vma(data, 0x40FD5E4, "ServerListPlayers".encode("utf-32-le") + b"\x00\x00\x00\x00")
    write_vma(data, 0x41632DA, b"ServerKickPlayer\x00")
    write_vma(data, 0x41632EB, b"ServerListPlayers\x00")

    write_vma(data, 0x1368F65, class_load_bytes(0x1368F65))
    write_vma(data, 0x1368F6C, registration_bytes(0x1368F6C, 0x41632DA, 0x1547320))
    write_vma(data, 0x1368FA2, class_load_bytes(0x1368FA2))
    write_vma(data, 0x1368FA9, registration_bytes(0x1368FA9, 0x41632EB, 0x1547450))

    write_vma(data, 0x78D778, fname_init_bytes(0x78D778, 0x58EAE60, 0x40FD540))
    write_vma(data, 0x78D7AA, fname_init_bytes(0x78D7AA, 0x58EAE68, 0x40FD5E4))

    write_vma(data, 0x1547320, bytes.fromhex("554889e54156534883ec20"))
    for call_vma, target_vma in (
        (0x154734A, 0x1D32C70),
        (0x154736A, 0x1D32CB0),
        (0x1547388, 0x1D32C70),
        (0x15473A8, 0x1D32CB0),
    ):
        write_vma(data, call_vma, call_bytes(call_vma, target_vma))
    write_vma(data, 0x15473C1, bytes.fromhex("498b06488b8028150000"))
    write_vma(
        data,
        0x1547450,
        bytes.fromhex("488b46204885c00f95c10fb6c94801c148894e20488b07ffa020150000"),
    )

    if tamper_vma is not None:
        write_vma(data, tamper_vma, tamper_byte)

    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


class CheckPlayerIdentityStaticAdminThunksTests(unittest.TestCase):
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
        self.assertEqual(payload["schema"], "obelisk.player-identity-static-admin-thunks-check.v1")
        self.assertEqual(payload["status"], "valid")
        self.assertTrue(payload["accepted_for_orientation"])
        self.assertTrue(payload["not_artifact_gate"])
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertEqual(payload["target_set"], "players-identity-lifecycle-intake")
        self.assertEqual(
            {target["target"] for target in payload["checked_targets"]},
            {
                "ShooterPlayerController.ServerKickPlayer",
                "ShooterPlayerController.ServerListPlayers",
            },
        )
        self.assertIn("does not prove UFunction object identity", " ".join(payload["non_claims"]))

    def test_registration_pattern_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            binary = Path(temp_dir) / "ShooterGameServer"
            digest = make_fake_binary(binary, tamper_vma=0x1368FAE, tamper_byte=b"\x51")

            result = self.run_checker(str(binary), "--expected-binary-sha256", digest, check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["status"], "blocked")
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("registration_thunk_immediate_mismatch", reasons)
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])

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

    def test_shared_name_terminator_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            binary = Path(temp_dir) / "ShooterGameServer"
            digest = make_fake_binary(binary, tamper_vma=0x3F63B7C + len("/Script/ShooterGame".encode("utf-32-le")), tamper_byte=b"\x20")

            result = self.run_checker(str(binary), "--expected-binary-sha256", digest, check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("script_name_utf32_mismatch", {blocker["reason"] for blocker in payload["blockers"]})

    def test_server_root_and_symlink_inputs_are_rejected(self) -> None:
        result = self.run_checker("/servidor/ark/ShooterGameServer", check=False)
        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("binary_path_rejected", {blocker["reason"] for blocker in payload["blockers"]})

        with tempfile.TemporaryDirectory() as temp_dir:
            binary = Path(temp_dir) / "ShooterGameServer"
            make_fake_binary(binary)
            link = Path(temp_dir) / "ShooterGameServer.link"
            link.symlink_to(binary)

            result = self.run_checker(str(link), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("binary_path_rejected", {blocker["reason"] for blocker in payload["blockers"]})

    @unittest.skipUnless(DEFAULT_BINARY.exists(), "offline ShooterGameServer artifact not present")
    def test_default_offline_binary_is_valid_candidate_only_orientation(self) -> None:
        result = self.run_checker("--json")
        payload = json.loads(result.stdout)

        self.assertEqual(payload["status"], "valid")
        self.assertTrue(payload["accepted_for_orientation"])
        self.assertEqual(payload["binary_sha256"], payload["expected_binary_sha256"])
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])


if __name__ == "__main__":
    unittest.main()
