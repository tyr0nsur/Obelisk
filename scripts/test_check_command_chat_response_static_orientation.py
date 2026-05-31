#!/usr/bin/env python3
"""Tests for check_command_chat_response_static_orientation.py."""

from __future__ import annotations

import hashlib
import json
import subprocess
import struct
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_command_chat_response_static_orientation.py"
DEFAULT_BINARY = Path(
    "/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/"
    "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/"
    "ShooterGameServer"
)

sys.path.insert(0, str(SCRIPT_DIR))
from check_command_chat_response_static_orientation import (  # noqa: E402
    CONTROLLER_CLASS_SLOT_VMA,
    REGISTRAR_CALL_VMA,
    RESPONSE_PATH_TARGETS,
)


class CheckCommandChatResponseStaticOrientationTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def write_synthetic_response_path_elf(self, path: Path, *, rodata_size_extra: int = 0) -> str:
        rodata_vaddr = 0x3F61740
        rodata_offset = RESPONSE_PATH_TARGETS[0].expected_ascii_file_offset - (
            RESPONSE_PATH_TARGETS[0].expected_ascii_vma - rodata_vaddr
        )
        file_size = max(
            target.expected_ascii_file_offset + len(target.ascii_name) + 1
            for target in RESPONSE_PATH_TARGETS
        )
        shoff = 0x200
        shstr_offset = 0x180
        shstrtab = b"\x00.text\x00.rodata\x00.shstrtab\x00"

        with path.open("wb") as handle:
            handle.truncate(file_size)

        def program_header(
            p_type: int,
            p_flags: int,
            p_offset: int,
            p_vaddr: int,
            p_filesz: int,
            p_memsz: int,
        ) -> bytes:
            return struct.pack(
                "<IIQQQQQQ",
                p_type,
                p_flags,
                p_offset,
                p_vaddr,
                0,
                p_filesz,
                p_memsz,
                0x1000,
            )

        def section_header(
            name_offset: int,
            section_type: int,
            flags: int,
            addr: int,
            offset: int,
            size: int,
            addralign: int = 1,
        ) -> bytes:
            return struct.pack(
                "<IIQQQQIIQQ",
                name_offset,
                section_type,
                flags,
                addr,
                offset,
                size,
                0,
                0,
                addralign,
                0,
            )

        with path.open("r+b") as handle:
            e_ident = b"\x7fELF" + bytes([2, 1, 1, 0]) + (b"\x00" * 8)
            handle.write(
                e_ident
                + struct.pack(
                    "<HHIQQQIHHHHHH",
                    2,
                    62,
                    1,
                    0x81DC59,
                    64,
                    shoff,
                    0,
                    64,
                    56,
                    3,
                    64,
                    4,
                    3,
                )
            )
            handle.seek(64)
            handle.write(program_header(1, 0x5, 0, 0, 0x1600000, 0x1600000))
            handle.write(
                program_header(
                    1,
                    0x4,
                    rodata_offset,
                    rodata_vaddr,
                    file_size - rodata_offset,
                    file_size - rodata_offset,
                )
            )
            handle.write(program_header(1, 0x6, 0, CONTROLLER_CLASS_SLOT_VMA & ~0xFFF, 0, 0x2000))

            handle.seek(shstr_offset)
            handle.write(shstrtab)
            handle.seek(shoff)
            handle.write(section_header(0, 0, 0, 0, 0, 0))
            handle.write(section_header(1, 1, 0x6, 0x648400, 0x648400, 0xF00000, 16))
            handle.write(
                section_header(
                    7,
                    1,
                    0x2,
                    rodata_vaddr,
                    rodata_offset,
                    file_size - rodata_offset + rodata_size_extra,
                    16,
                )
            )
            handle.write(section_header(15, 3, 0, 0, shstr_offset, len(shstrtab)))

            for target in RESPONSE_PATH_TARGETS:
                handle.seek(target.expected_ascii_file_offset)
                handle.write(target.ascii_name.encode("ascii") + b"\x00")

                handle.seek(target.expected_class_load_vma)
                class_disp = CONTROLLER_CLASS_SLOT_VMA - (target.expected_class_load_vma + 7)
                handle.write(b"\x48\x8b\x3d" + struct.pack("<i", class_disp))

                handle.seek(target.expected_registration_vma)
                call_vma = target.expected_registration_vma + 12
                call_disp = REGISTRAR_CALL_VMA - (call_vma + 5)
                handle.write(
                    b"\xbe"
                    + struct.pack("<I", target.expected_ascii_vma)
                    + b"\xba"
                    + struct.pack("<I", target.expected_thunk_vma)
                    + b"\x31\xc9\xe8"
                    + struct.pack("<i", call_disp)
                )

                handle.seek(target.expected_thunk_vma)
                handle.write(target.expected_thunk_prefix)

        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def test_synthetic_binary_is_valid_candidate_only_orientation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fake = Path(temp_dir) / "ShooterGameServer"
            fake_sha256 = self.write_synthetic_response_path_elf(fake)
            result = self.run_checker(
                str(fake),
                "--expected-binary-sha256",
                fake_sha256,
            )
        payload = json.loads(result.stdout)

        self.assertEqual(payload["schema"], "obelisk.command-chat-response-static-orientation-check.v1")
        self.assertEqual(payload["status"], "valid")
        self.assertTrue(payload["valid"])
        self.assertTrue(payload["accepted_for_orientation"])
        self.assertTrue(payload["not_artifact_gate"])
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertEqual(payload["planning_surface"], "obelisk.command_chat_response_path.v1")
        self.assertEqual(payload["blockers"], [])
        self.assertEqual(
            payload["target_names"],
            [
                "ShooterPlayerController.ClientChatMessage",
                "ShooterPlayerController.ClientServerChatDirectMessage",
                "ShooterPlayerController.ClientServerChatMessage",
            ],
        )

        observed = {target["target"]: target for target in payload["checked_targets"]}
        self.assertEqual(observed["ShooterPlayerController.ClientChatMessage"]["ascii_name_vma"], "0x4161a92")
        self.assertEqual(
            observed["ShooterPlayerController.ClientServerChatDirectMessage"]["registration_vmas"],
            ["0x136603e"],
        )
        self.assertEqual(
            observed["ShooterPlayerController.ClientServerChatMessage"]["thunk_candidates"],
            ["0x153f9c0"],
        )

        contract = payload["static_candidate_orientation_contract"]
        self.assertEqual(contract["schema"], "obelisk.static-candidate-orientation-contract.v1")
        self.assertEqual(contract["status"], "candidate_blocked")
        self.assertTrue(contract["not_artifact_gate"])
        self.assertFalse(contract["promotion_ready"])
        self.assertEqual(contract["scope"]["target_set"], "obelisk.command_chat_response_path.v1")
        self.assertTrue(all(subject["status"] == "candidate_only" for subject in contract["subjects"]))

        joined_non_claims = " ".join(payload["non_claims"]).lower()
        for phrase in (
            "does not claim replies",
            "send-chat api",
            "command router",
            "raw ue pointer exposure",
            "raw fstring exposure",
            "mutation",
            "return override",
            "runtime readiness",
            "public sdk promotion",
        ):
            self.assertIn(phrase, joined_non_claims)

    @unittest.skipUnless(DEFAULT_BINARY.exists(), "offline ShooterGameServer binary not available")
    def test_default_binary_smoke_candidate_only_orientation(self) -> None:
        result = self.run_checker("--json")
        payload = json.loads(result.stdout)

        self.assertEqual(payload["schema"], "obelisk.command-chat-response-static-orientation-check.v1")
        self.assertEqual(payload["status"], "valid")
        self.assertTrue(payload["accepted_for_orientation"])
        self.assertTrue(payload["not_artifact_gate"])
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertEqual(payload["planning_surface"], "obelisk.command_chat_response_path.v1")

    def test_wrong_hash_fails_closed_without_promoting_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fake = Path(temp_dir) / "ShooterGameServer"
            self.write_synthetic_response_path_elf(fake)
            result = self.run_checker(
                str(fake),
                "--expected-binary-sha256",
                "0" * 64,
                check=False,
            )
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["status"], "blocked")
        self.assertFalse(payload["valid"])
        self.assertFalse(payload["accepted_for_orientation"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertIn("binary_sha256_mismatch", {blocker["reason"] for blocker in payload["blockers"]})

    def test_protected_and_symlink_paths_are_rejected(self) -> None:
        result = self.run_checker("/servidor/ark/obelisk/dumps/ShooterGameServer", check=False)
        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("binary_path_rejected", {blocker["reason"] for blocker in payload["blockers"]})

        with tempfile.TemporaryDirectory() as temp_dir:
            fake = Path(temp_dir) / "real-ShooterGameServer"
            self.write_synthetic_response_path_elf(fake)
            link = Path(temp_dir) / "ShooterGameServer"
            link.symlink_to(fake)
            result = self.run_checker(str(link), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("binary_path_rejected", {blocker["reason"] for blocker in payload["blockers"]})

    def test_non_elf_input_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fake = Path(temp_dir) / "ShooterGameServer"
            fake.write_bytes(b"not an elf with ClientChatMessage")
            result = self.run_checker(
                str(fake),
                "--expected-binary-sha256",
                "a" * 64,
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["status"], "blocked")
        self.assertIn("elf_magic_invalid", {blocker["reason"] for blocker in payload["blockers"]})
        self.assertFalse(payload["accepted_for_orientation"])
        self.assertFalse(payload["promotion_ready"])

    def test_malformed_section_file_range_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fake = Path(temp_dir) / "ShooterGameServer"
            fake_sha256 = self.write_synthetic_response_path_elf(fake, rodata_size_extra=0x100)
            result = self.run_checker(
                str(fake),
                "--expected-binary-sha256",
                fake_sha256,
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["status"], "blocked")
        self.assertIn(
            "elf_section_file_range_out_of_bounds",
            {blocker["reason"] for blocker in payload["blockers"]},
        )
        self.assertFalse(payload["accepted_for_orientation"])
        self.assertFalse(payload["promotion_ready"])


if __name__ == "__main__":
    unittest.main()
