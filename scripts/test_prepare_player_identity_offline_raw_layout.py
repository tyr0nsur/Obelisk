#!/usr/bin/env python3
"""Tests for prepare_player_identity_offline_raw_layout.py."""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import prepare_player_identity_offline_raw_layout as prep


class PreparePlayerIdentityOfflineRawLayoutTests(unittest.TestCase):
    def run_main(
        self,
        argv: list[str],
        *,
        binary_sha: str | None = None,
    ) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        patches = [mock.patch.object(sys, "argv", argv)]
        if binary_sha is not None:
            patches.append(mock.patch.object(prep, "sha256_file", return_value=binary_sha))
        with contextlib.ExitStack() as stack:
            for patch in patches:
                stack.enter_context(patch)
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = prep.main()
        return result, stdout.getvalue(), stderr.getvalue()

    def write_inputs(self, root: Path) -> tuple[Path, Path]:
        binary = root / "ShooterGameServer.source"
        core = root / "core.source"
        binary.write_bytes(b"binary")
        core.write_bytes(b"core")
        return binary, core

    def test_hardlinks_explicit_non_protected_inputs_into_raw_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            binary, core = self.write_inputs(root)
            artifact_root = root / "artifacts"

            result, stdout, stderr = self.run_main(
                [
                    "prepare_player_identity_offline_raw_layout.py",
                    "--binary",
                    str(binary),
                    "--core",
                    str(core),
                    "--artifact-root",
                    str(artifact_root),
                    "--run-id",
                    "run-1",
                ],
                binary_sha=prep.EXPECTED_SHOOTERGAME_SHA256,
            )

            self.assertEqual(result, 0, stderr)
            payload = json.loads(stdout)
            raw_dir = artifact_root / "player-identity-offline-run-1" / "raw"
            self.assertEqual(payload["schema"], "obelisk.player-identity-offline-raw-layout.v1")
            self.assertTrue(payload["ready_for_core_evidence_pack_command"])
            self.assertEqual(payload["mode"], "hardlink")
            self.assertEqual(Path(payload["binary"]["staged"]), raw_dir / "ShooterGameServer")
            self.assertEqual(Path(payload["core"]["staged"]), raw_dir / "core")
            self.assertEqual(os.stat(binary).st_ino, os.stat(raw_dir / "ShooterGameServer").st_ino)
            self.assertEqual(os.stat(core).st_ino, os.stat(raw_dir / "core").st_ino)
            self.assertIn("build_core_dump_evidence_pack.py", payload["next_command"])
            self.assertIn(
                "does not validate that the core is usable for player identity evidence",
                payload["non_claims"],
            )

    def test_copy_mode_copies_explicit_non_protected_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            binary, core = self.write_inputs(root)
            artifact_root = root / "artifacts"

            result, stdout, stderr = self.run_main(
                [
                    "prepare_player_identity_offline_raw_layout.py",
                    "--binary",
                    str(binary),
                    "--core",
                    str(core),
                    "--artifact-root",
                    str(artifact_root),
                    "--run-id",
                    "run-2",
                    "--mode",
                    "copy",
                ],
                binary_sha=prep.EXPECTED_SHOOTERGAME_SHA256,
            )

            self.assertEqual(result, 0, stderr)
            payload = json.loads(stdout)
            self.assertEqual(payload["mode"], "copy")
            self.assertEqual((artifact_root / "player-identity-offline-run-2" / "raw" / "core").read_bytes(), b"core")

    def test_rejects_protected_binary_before_staging(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, core = self.write_inputs(root)

            result, _, stderr = self.run_main(
                [
                    "prepare_player_identity_offline_raw_layout.py",
                    "--binary",
                    "/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer",
                    "--core",
                    str(core),
                    "--artifact-root",
                    str(root / "artifacts"),
                    "--run-id",
                    "run-3",
                ]
            )

            self.assertEqual(result, 2)
            self.assertIn("--binary must not read from protected server root /servidor/ark", stderr)
            self.assertFalse((root / "artifacts").exists())

    def test_rejects_protected_core_before_staging(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            binary, _ = self.write_inputs(root)

            result, _, stderr = self.run_main(
                [
                    "prepare_player_identity_offline_raw_layout.py",
                    "--binary",
                    str(binary),
                    "--core",
                    "/servidor/ark/serverfiles/core",
                    "--artifact-root",
                    str(root / "artifacts"),
                    "--run-id",
                    "run-4",
                ],
                binary_sha=prep.EXPECTED_SHOOTERGAME_SHA256,
            )

            self.assertEqual(result, 2)
            self.assertIn("--core must not read from protected server root /servidor/ark", stderr)
            self.assertFalse((root / "artifacts").exists())

    def test_rejects_symlinked_input_even_when_target_is_non_protected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            binary, core = self.write_inputs(root)
            binary_link = root / "ShooterGameServer.link"
            binary_link.symlink_to(binary)

            result, _, stderr = self.run_main(
                [
                    "prepare_player_identity_offline_raw_layout.py",
                    "--binary",
                    str(binary_link),
                    "--core",
                    str(core),
                    "--artifact-root",
                    str(root / "artifacts"),
                    "--run-id",
                    "run-5",
                ],
                binary_sha=prep.EXPECTED_SHOOTERGAME_SHA256,
            )

            self.assertEqual(result, 2)
            self.assertIn("--binary must not be a symlink", stderr)
            self.assertFalse((root / "artifacts").exists())

    def test_rejects_output_under_protected_root_before_staging(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            binary, core = self.write_inputs(root)

            result, _, stderr = self.run_main(
                [
                    "prepare_player_identity_offline_raw_layout.py",
                    "--binary",
                    str(binary),
                    "--core",
                    str(core),
                    "--artifact-root",
                    "/servidor/ark/obelisk/dumps/player-identity",
                    "--run-id",
                    "run-6",
                ],
                binary_sha=prep.EXPECTED_SHOOTERGAME_SHA256,
            )

            self.assertEqual(result, 2)
            self.assertIn("--artifact-root must not write under protected server root /servidor/ark", stderr)

    def test_rejects_existing_raw_symlink_before_staging(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            binary, core = self.write_inputs(root)
            artifact_root = root / "artifacts"
            outside = root / "outside"
            outside.mkdir()
            run_root = artifact_root / "player-identity-offline-run-7"
            run_root.parent.mkdir(parents=True)
            run_root.symlink_to(outside)

            result, _, stderr = self.run_main(
                [
                    "prepare_player_identity_offline_raw_layout.py",
                    "--binary",
                    str(binary),
                    "--core",
                    str(core),
                    "--artifact-root",
                    str(artifact_root),
                    "--run-id",
                    "run-7",
                ],
                binary_sha=prep.EXPECTED_SHOOTERGAME_SHA256,
            )

            self.assertEqual(result, 2)
            self.assertIn("run directory must not be a symlink", stderr)
            self.assertFalse((outside / "raw" / "core").exists())

    def test_rejects_binary_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            binary, core = self.write_inputs(root)

            result, _, stderr = self.run_main(
                [
                    "prepare_player_identity_offline_raw_layout.py",
                    "--binary",
                    str(binary),
                    "--core",
                    str(core),
                    "--artifact-root",
                    str(root / "artifacts"),
                    "--run-id",
                    "run-8",
                ],
                binary_sha="0" * 64,
            )

            self.assertEqual(result, 2)
            self.assertIn("--binary sha256 does not match the reviewed ShooterGameServer hash", stderr)
            self.assertFalse((root / "artifacts").exists())

    def test_rejects_existing_outputs_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            binary, core = self.write_inputs(root)
            raw_dir = root / "artifacts" / "player-identity-offline-run-9" / "raw"
            raw_dir.mkdir(parents=True)
            (raw_dir / "core").write_bytes(b"old")

            result, _, stderr = self.run_main(
                [
                    "prepare_player_identity_offline_raw_layout.py",
                    "--binary",
                    str(binary),
                    "--core",
                    str(core),
                    "--artifact-root",
                    str(root / "artifacts"),
                    "--run-id",
                    "run-9",
                ],
                binary_sha=prep.EXPECTED_SHOOTERGAME_SHA256,
            )

            self.assertEqual(result, 2)
            self.assertIn("output core already exists", stderr)
            self.assertFalse((raw_dir / "ShooterGameServer").exists())


if __name__ == "__main__":
    unittest.main()
