#!/usr/bin/env python3
"""Tests for check_command_chat_response_static_orientation.py."""

from __future__ import annotations

import json
import subprocess
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


class CheckCommandChatResponseStaticOrientationTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def test_default_binary_is_valid_candidate_only_orientation(self) -> None:
        result = self.run_checker("--json")
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

    def test_wrong_hash_fails_closed_without_promoting_readiness(self) -> None:
        result = self.run_checker(
            str(DEFAULT_BINARY),
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
            link = Path(temp_dir) / "ShooterGameServer"
            link.symlink_to(DEFAULT_BINARY)
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


if __name__ == "__main__":
    unittest.main()
