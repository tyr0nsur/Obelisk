#!/usr/bin/env python3
"""Tests for prepare_player_identity_offline_raw_layout.py."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import shlex
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import prepare_player_identity_offline_raw_layout as prep
import snapshot_evidence_pack


class PreparePlayerIdentityOfflineRawLayoutTests(unittest.TestCase):
    def run_main(
        self,
        argv: list[str],
        *,
        binary_sha: str | None = None,
    ) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        patches = [
            mock.patch.object(sys, "argv", argv),
            mock.patch.object(prep, "detect_obelisk_commit", return_value="test-commit"),
        ]
        if binary_sha is not None:
            def fake_sha256_file(path: Path) -> str:
                if path.name.startswith("ShooterGameServer"):
                    return binary_sha
                return hashlib.sha256(path.read_bytes()).hexdigest()

            patches.append(mock.patch.object(prep, "sha256_file", side_effect=fake_sha256_file))
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
            self.assertEqual(payload["binary"]["size_bytes"], len(b"binary"))
            self.assertEqual(payload["core"]["sha256"], hashlib.sha256(b"core").hexdigest())
            self.assertEqual(payload["core"]["size_bytes"], len(b"core"))
            self.assertEqual(payload["obelisk"]["commit"], "test-commit")
            self.assertEqual(
                Path(payload["core_evidence_pack"]["manifest"]),
                artifact_root / "player-identity-offline-run-1" / "core-evidence-pack" / "manifest.json",
            )
            self.assertEqual(os.stat(binary).st_ino, os.stat(raw_dir / "ShooterGameServer").st_ino)
            self.assertEqual(os.stat(core).st_ino, os.stat(raw_dir / "core").st_ino)
            self.assertIn("build_core_dump_evidence_pack.py", payload["next_command"])
            self.assertNotIn("<reviewed-obelisk-id>", payload["next_command"])
            self.assertEqual(payload["next_command_env"], {"PYTHONDONTWRITEBYTECODE": "1"})
            self.assertEqual(payload["next_command_argv"][0:2], ["python3", "scripts/build_core_dump_evidence_pack.py"])
            self.assertIn("test-commit", payload["next_command_argv"])
            self.assertEqual(
                payload["reviewed_seed_scope"],
                {
                    "binary_sha256": prep.EXPECTED_SHOOTERGAME_SHA256,
                    "fname_root_slot": "0x5956f30",
                    "fname_indices": {
                        "None": 0,
                        "ClientMessage": 4884,
                        "ServerChat": 9619,
                        "SetActiveMissionDebugFlags": 9622,
                    },
                    "gobjects_candidate": "0x595b7e0",
                    "gobjects_sample_indices": [0, 1, 25447],
                    "non_claim": "binary-hash-scoped reviewed seed only; not a stable offset or public SDK promotion",
                },
            )
            self.assertIn("verified_fname_root_slot=0x5956f30", payload["next_command_argv"])
            self.assertIn("gobjects=0x595b7e0", payload["next_command_argv"])
            self.assertEqual(payload["next_command_argv"].count("--gobjects-sample-index"), 3)
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

    def test_explicit_obelisk_commit_overrides_git_detected_checkpoint(self) -> None:
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
                    "run-reviewed",
                    "--obelisk-commit",
                    "reviewed12345",
                ],
                binary_sha=prep.EXPECTED_SHOOTERGAME_SHA256,
            )

            self.assertEqual(result, 0, stderr)
            payload = json.loads(stdout)
            self.assertEqual(payload["obelisk"]["commit"], "reviewed12345")
            self.assertEqual(payload["obelisk"]["commit_source"], "--obelisk-commit")
            self.assertIn("reviewed12345", payload["next_command_argv"])
            self.assertNotIn("test-commit", payload["next_command_argv"])

    def test_next_command_is_shell_safe_for_spaced_artifact_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            binary, core = self.write_inputs(root)
            artifact_root = root / "artifact root with spaces"

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
                    "run-spaces",
                ],
                binary_sha=prep.EXPECTED_SHOOTERGAME_SHA256,
            )

            self.assertEqual(result, 0, stderr)
            payload = json.loads(stdout)
            command_tokens = shlex.split(payload["next_command"])
            self.assertEqual(command_tokens[0], "PYTHONDONTWRITEBYTECODE=1")
            self.assertEqual(command_tokens[1:3], ["python3", "scripts/build_core_dump_evidence_pack.py"])
            self.assertIn(str(artifact_root / "player-identity-offline-run-spaces" / "raw" / "core"), command_tokens)
            self.assertIn(
                str(artifact_root / "player-identity-offline-run-spaces" / "core-evidence-pack"),
                command_tokens,
            )

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

    def test_accepts_workspace_offline_binary_direct_path_past_protected_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            protected = root / "server-root"
            workspace = protected / "workspace-offline"
            workspace.mkdir(parents=True)
            binary = workspace / "player-identity" / "ShooterGameServer"
            binary.parent.mkdir()
            binary.write_bytes(b"binary")
            _, core = self.write_inputs(root)

            with (
                mock.patch.object(snapshot_evidence_pack, "SERVER_ROOT", protected),
                mock.patch.object(snapshot_evidence_pack, "APPROVED_OFFLINE_WORKSPACE_ROOTS", (workspace,)),
            ):
                result, stdout, stderr = self.run_main(
                    [
                        "prepare_player_identity_offline_raw_layout.py",
                        "--binary",
                        str(binary),
                        "--core",
                        str(core),
                        "--artifact-root",
                        str(root / "artifacts"),
                        "--run-id",
                        "run-workspace-input",
                    ],
                    binary_sha=prep.EXPECTED_SHOOTERGAME_SHA256,
                )

            self.assertEqual(result, 0, stderr)
            payload = json.loads(stdout)
            self.assertEqual(payload["binary"]["source"], str(binary.resolve()))

    def test_accepts_workspace_offline_artifact_root_for_staging(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            protected = root / "server-root"
            workspace = protected / "workspace-offline"
            workspace.mkdir(parents=True)
            binary, core = self.write_inputs(root)
            artifact_root = workspace / "player-identity"

            with (
                mock.patch.object(snapshot_evidence_pack, "SERVER_ROOT", protected),
                mock.patch.object(snapshot_evidence_pack, "APPROVED_OFFLINE_WORKSPACE_ROOTS", (workspace,)),
            ):
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
                        "run-workspace-output",
                    ],
                    binary_sha=prep.EXPECTED_SHOOTERGAME_SHA256,
                )

            self.assertEqual(result, 0, stderr)
            payload = json.loads(stdout)
            self.assertEqual(
                payload["raw_dir"],
                str(artifact_root / "player-identity-offline-run-workspace-output" / "raw"),
            )

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

    def test_rejects_artifact_root_under_repository_before_staging(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            binary, core = self.write_inputs(root)
            repo_artifact_root = prep.REPO_ROOT / "local" / "player-identity-test-artifacts"

            result, _, stderr = self.run_main(
                [
                    "prepare_player_identity_offline_raw_layout.py",
                    "--binary",
                    str(binary),
                    "--core",
                    str(core),
                    "--artifact-root",
                    str(repo_artifact_root),
                    "--run-id",
                    "run-repo-root",
                ],
                binary_sha=prep.EXPECTED_SHOOTERGAME_SHA256,
            )

            self.assertEqual(result, 2)
            self.assertIn("--artifact-root must not be under repository root", stderr)
            self.assertFalse(repo_artifact_root.exists())

    def test_rejects_artifact_root_file_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            binary, core = self.write_inputs(root)
            artifact_root = root / "artifacts"
            artifact_root.write_bytes(b"not a directory")

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
                    "run-artifact-file",
                ],
                binary_sha=prep.EXPECTED_SHOOTERGAME_SHA256,
            )

            self.assertEqual(result, 2)
            self.assertIn("--artifact-root must be a directory", stderr)
            self.assertNotIn("Traceback", stderr)

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

    def test_rejects_existing_core_evidence_pack_before_staging(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            binary, core = self.write_inputs(root)
            run_root = root / "artifacts" / "player-identity-offline-run-stale"
            stale_pack = run_root / "core-evidence-pack"
            stale_pack.mkdir(parents=True)
            (stale_pack / "manifest.json").write_text("{}", encoding="utf-8")

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
                    "run-stale",
                ],
                binary_sha=prep.EXPECTED_SHOOTERGAME_SHA256,
            )

            self.assertEqual(result, 2)
            self.assertIn("output core evidence pack directory already exists", stderr)
            self.assertFalse((run_root / "raw" / "ShooterGameServer").exists())
            self.assertFalse((run_root / "raw" / "core").exists())

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
