#!/usr/bin/env python3
"""Tests for validate_player_identity_raw_inputs.py."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import validate_player_identity_raw_inputs as validator


class ValidatePlayerIdentityRawInputsTests(unittest.TestCase):
    def run_main(
        self,
        argv: list[str],
        *,
        binary_sha: str | None = validator.EXPECTED_SHOOTERGAME_SHA256,
    ) -> tuple[int, dict[str, object], str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        patches = [mock.patch.object(sys, "argv", argv)]
        if binary_sha is not None:
            patches.append(mock.patch.object(validator, "sha256_file", return_value=binary_sha))
        with contextlib.ExitStack() as stack:
            for patch in patches:
                stack.enter_context(patch)
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = validator.main()
        payload = json.loads(stdout.getvalue())
        return result, payload, stderr.getvalue()

    def write_raw_layout(self, root: Path) -> Path:
        run_root = root / "player-identity-offline-run-1"
        raw_dir = run_root / "raw"
        raw_dir.mkdir(parents=True)
        (raw_dir / "ShooterGameServer").write_bytes(b"binary")
        (raw_dir / "core").write_bytes(b"core")
        return run_root

    def blocker_reasons(self, payload: dict[str, object]) -> set[str]:
        blockers = payload.get("blockers")
        self.assertIsInstance(blockers, list)
        return {blocker["reason"] for blocker in blockers if isinstance(blocker, dict)}

    def test_accepts_existing_raw_layout_without_reading_core_contents(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_root = self.write_raw_layout(Path(temp))

            result, payload, stderr = self.run_main(
                ["validate_player_identity_raw_inputs.py", "--root", str(run_root)]
            )

        self.assertEqual(result, 0, stderr)
        self.assertEqual(payload["schema"], validator.REPORT_SCHEMA)
        self.assertEqual(payload["status"], "accepted")
        self.assertTrue(payload["ready_for_core_evidence_pack_command"])
        self.assertEqual(payload["binary"]["sha256"], validator.EXPECTED_SHOOTERGAME_SHA256)
        self.assertEqual(payload["binary"]["size_bytes"], len(b"binary"))
        self.assertEqual(payload["core"]["sha256"], None)
        self.assertEqual(payload["core"]["content_read"], False)
        self.assertEqual(payload["core"]["metadata_only"], True)
        self.assertEqual(payload["core"]["size_bytes"], len(b"core"))
        self.assertIn("does not stage, copy, hardlink, create, delete, or modify files", payload["non_claims"])

    def test_accepts_explicit_sibling_raw_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_root = self.write_raw_layout(Path(temp))
            raw_dir = run_root / "raw"

            result, payload, stderr = self.run_main(
                [
                    "validate_player_identity_raw_inputs.py",
                    "--binary",
                    str(raw_dir / "ShooterGameServer"),
                    "--core",
                    str(raw_dir / "core"),
                ]
            )

        self.assertEqual(result, 0, stderr)
        self.assertEqual(payload["run_root"], str(run_root))
        self.assertEqual(payload["raw_dir"], str(raw_dir))

    def test_accepts_workspace_offline_root_as_offline_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            protected = Path(temp) / "server-root"
            workspace = protected / "workspace-offline"
            workspace.mkdir(parents=True)
            run_root = self.write_raw_layout(workspace)

            with (
                mock.patch.object(validator, "PROTECTED_ROOT", protected),
                mock.patch.object(validator, "APPROVED_OFFLINE_WORKSPACE_ROOTS", (workspace,)),
            ):
                result, payload, stderr = self.run_main(
                    ["validate_player_identity_raw_inputs.py", "--root", str(run_root)]
                )

        self.assertEqual(result, 0, stderr)
        self.assertEqual(payload["status"], "accepted")
        self.assertTrue(payload["ready_for_core_evidence_pack_command"])

    def test_rejects_protected_non_workspace_root_before_hashing(self) -> None:
        protected_run_root = Path("/servidor/ark/obelisk/player-identity-offline-run-2")
        with mock.patch.object(validator, "sha256_file") as sha256_file:
            result, payload, stderr = self.run_main(
                ["validate_player_identity_raw_inputs.py", "--root", str(protected_run_root)],
                binary_sha=None,
            )

        self.assertEqual(result, 1, stderr)
        self.assertIn("path_under_live_server_root", self.blocker_reasons(payload))
        sha256_file.assert_not_called()

    def test_rejects_symlinked_core_component(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_root = self.write_raw_layout(root)
            core = run_root / "raw" / "core"
            core.unlink()
            core.symlink_to(root / "copied-core")

            result, payload, stderr = self.run_main(
                ["validate_player_identity_raw_inputs.py", "--root", str(run_root)]
            )

        self.assertEqual(result, 1, stderr)
        self.assertIn("path_has_symlink_component", self.blocker_reasons(payload))

    def test_rejects_explicit_unpaired_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_root = self.write_raw_layout(root)
            other_run_root = root / "player-identity-offline-run-3"
            other_raw = other_run_root / "raw"
            other_raw.mkdir(parents=True)
            other_core = other_raw / "core"
            other_core.write_bytes(b"core")

            result, payload, stderr = self.run_main(
                [
                    "validate_player_identity_raw_inputs.py",
                    "--binary",
                    str(run_root / "raw" / "ShooterGameServer"),
                    "--core",
                    str(other_core),
                ]
            )

        self.assertEqual(result, 1, stderr)
        reasons = self.blocker_reasons(payload)
        self.assertIn("raw_inputs_not_siblings", reasons)
        self.assertIn("raw_inputs_not_under_run_root", reasons)

    def test_rejects_binary_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_root = self.write_raw_layout(Path(temp))

            result, payload, stderr = self.run_main(
                ["validate_player_identity_raw_inputs.py", "--root", str(run_root)],
                binary_sha="0" * 64,
            )

        self.assertEqual(result, 1, stderr)
        self.assertIn("binary_sha256_mismatch", self.blocker_reasons(payload))

    def test_rejects_wrong_raw_layout_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_root = root / "player-identity-offline-run-4"
            raw_dir = run_root / "inputs"
            raw_dir.mkdir(parents=True)
            binary = raw_dir / "ShooterGameServer"
            core = raw_dir / "core"
            binary.write_bytes(b"binary")
            core.write_bytes(b"core")

            result, payload, stderr = self.run_main(
                ["validate_player_identity_raw_inputs.py", "--binary", str(binary), "--core", str(core)]
            )

        self.assertEqual(result, 1, stderr)
        reasons = self.blocker_reasons(payload)
        self.assertIn("raw_layout_root_not_derivable", reasons)


if __name__ == "__main__":
    unittest.main()
