#!/usr/bin/env python3
"""Tests for capture_radare2_static_orientation_windows.py."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "capture_radare2_static_orientation_windows.py"


class CaptureRadare2StaticOrientationWindowsTests(unittest.TestCase):
    def run_wrapper(
        self,
        *args: str,
        check: bool = True,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

    def write_fake_radare2(self, path: Path, *, version_sleeps: bool = False) -> None:
        version_body = "sleep 2\n" if version_sleeps else "echo 'radare2 5.5.0 fake-test'\n"
        path.write_text(
            "#!/bin/sh\n"
            "if [ \"$1\" = \"-v\" ]; then\n"
            f"  {version_body}"
            "  exit 0\n"
            "fi\n"
            "echo 'fake radare2 disassembly window'\n"
            "echo \"$@\"\n",
            encoding="utf-8",
        )
        path.chmod(0o755)

    def test_captures_candidate_only_admin_windows_under_output_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"offline test binary")
            digest = hashlib.sha256(binary.read_bytes()).hexdigest()
            fake_radare2 = root / "radare2"
            self.write_fake_radare2(fake_radare2)
            output_root = root / "out"

            result = self.run_wrapper(
                str(binary),
                "--expected-binary-sha256",
                digest,
                "--radare2",
                str(fake_radare2),
                "--output-root",
                str(output_root),
                "--run-id",
                "test-run",
                "--target-group",
                "admin",
                "--json",
            )

            payload = json.loads(result.stdout)
            manifest_payload = json.loads(
                Path(payload["manifest_path"]).read_text(encoding="utf-8")
            )
            self.assertEqual(payload, manifest_payload)
            self.assertEqual(payload["schema"], "obelisk.radare2-static-orientation-windows.v1")
            self.assertEqual(payload["status"], "candidate_only_orientation_captured")
            self.assertTrue(payload["not_artifact_gate"])
            self.assertFalse(payload["promotion_ready"])
            self.assertFalse(payload["public_sdk_ready"])
            self.assertFalse(payload["runtime_ready"])
            self.assertEqual(payload["artifact_gate"]["registered"], False)
            self.assertEqual(payload["scope"]["target_groups"], ["admin"])
            self.assertEqual(len(payload["windows_captured"]), 6)
            self.assertTrue(Path(payload["manifest_path"]).exists())
            for window in payload["windows_captured"]:
                output = Path(window["output"])
                self.assertTrue(output.exists())
                self.assertTrue(str(output).startswith(payload["output_dir"]))
                self.assertIn("candidate-only radare2 orientation window", output.read_text(encoding="utf-8"))
                self.assertEqual(window["radare2_status"], "ok")

    def test_sha_mismatch_writes_blocked_manifest_without_windows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"wrong binary")
            fake_radare2 = root / "radare2"
            self.write_fake_radare2(fake_radare2)
            output_root = root / "out"

            result = self.run_wrapper(
                str(binary),
                "--expected-binary-sha256",
                "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                "--radare2",
                str(fake_radare2),
                "--output-root",
                str(output_root),
                "--run-id",
                "sha-blocked",
                "--target-group",
                "admin",
                check=False,
            )

            manifest_path = output_root / "sha-blocked" / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(manifest["status"], "blocked")
        self.assertEqual(payload["windows_captured"], [])
        self.assertIn("binary_sha256_mismatch", {blocker["reason"] for blocker in payload["blockers"]})

    def test_rejects_protected_binary_and_output_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"offline test binary")
            digest = hashlib.sha256(binary.read_bytes()).hexdigest()
            fake_radare2 = root / "radare2"
            self.write_fake_radare2(fake_radare2)

            result = self.run_wrapper(
                "/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer",
                "--radare2",
                str(fake_radare2),
                "--output-root",
                str(root / "out"),
                "--target-group",
                "admin",
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--binary must not read from protected server root", result.stderr)

            result = self.run_wrapper(
                str(binary),
                "--expected-binary-sha256",
                digest,
                "--radare2",
                str(fake_radare2),
                "--output-root",
                "/servidor/ark/workspace-offline/r2-windows",
                "--target-group",
                "admin",
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--output-root must not write under protected server root", result.stderr)

    def test_rejects_symlinked_output_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"offline test binary")
            digest = hashlib.sha256(binary.read_bytes()).hexdigest()
            fake_radare2 = root / "radare2"
            self.write_fake_radare2(fake_radare2)
            real_output = root / "real-output"
            real_output.mkdir()
            linked_output = root / "linked-output"
            linked_output.symlink_to(real_output, target_is_directory=True)

            result = self.run_wrapper(
                str(binary),
                "--expected-binary-sha256",
                digest,
                "--radare2",
                str(fake_radare2),
                "--output-root",
                str(linked_output),
                "--target-group",
                "admin",
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--output-root must not be a symlink", result.stderr)

    def test_rejects_symlinked_manifest_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"offline test binary")
            digest = hashlib.sha256(binary.read_bytes()).hexdigest()
            fake_radare2 = root / "radare2"
            self.write_fake_radare2(fake_radare2)
            output_dir = root / "out" / "symlink-file"
            output_dir.mkdir(parents=True)
            real_manifest = root / "real-manifest.json"
            real_manifest.write_text("{}", encoding="utf-8")
            (output_dir / "manifest.json").symlink_to(real_manifest)

            result = self.run_wrapper(
                str(binary),
                "--expected-binary-sha256",
                digest,
                "--radare2",
                str(fake_radare2),
                "--output-root",
                str(root / "out"),
                "--run-id",
                "symlink-file",
                "--target-group",
                "admin",
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("orientation output file must not be a symlink", result.stderr)

    def test_rejects_unsafe_run_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"offline test binary")
            digest = hashlib.sha256(binary.read_bytes()).hexdigest()
            fake_radare2 = root / "radare2"
            self.write_fake_radare2(fake_radare2)

            for run_id in ("", ".", "bad/child", "bad..child"):
                with self.subTest(run_id=run_id):
                    result = self.run_wrapper(
                        str(binary),
                        "--expected-binary-sha256",
                        digest,
                        "--radare2",
                        str(fake_radare2),
                        "--output-root",
                        str(root / f"out-{len(run_id)}"),
                        "--run-id",
                        run_id,
                        "--target-group",
                        "admin",
                        check=False,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("--run-id contains unsafe characters", result.stderr)

    def test_rejects_protected_orientation_json_even_for_admin_only_capture(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"offline test binary")
            digest = hashlib.sha256(binary.read_bytes()).hexdigest()
            fake_radare2 = root / "radare2"
            self.write_fake_radare2(fake_radare2)

            result = self.run_wrapper(
                str(binary),
                "--expected-binary-sha256",
                digest,
                "--radare2",
                str(fake_radare2),
                "--output-root",
                str(root / "out"),
                "--run-id",
                "orientation-json-blocked",
                "--target-group",
                "admin",
                "--orientation-json",
                "/servidor/ark/serverfiles/orientation.json",
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--orientation-json must not read from protected server root", result.stderr)

    def test_missing_radare2_writes_blocked_manifest_and_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"offline test binary")
            digest = hashlib.sha256(binary.read_bytes()).hexdigest()
            output_root = root / "out"
            env = os.environ.copy()
            empty_path = root / "empty-path"
            empty_path.mkdir()
            env["PATH"] = str(empty_path)

            result = self.run_wrapper(
                str(binary),
                "--expected-binary-sha256",
                digest,
                "--output-root",
                str(output_root),
                "--run-id",
                "missing-radare2",
                "--target-group",
                "admin",
                check=False,
                env=env,
            )

            payload = json.loads(result.stdout)
            manifest = json.loads(
                (output_root / "missing-radare2" / "manifest.json").read_text(encoding="utf-8")
            )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload, manifest)
        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["windows_captured"], [])
        self.assertIn("radare2_not_found", {blocker["reason"] for blocker in payload["blockers"]})

    def test_rejects_protected_radare2_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"offline test binary")
            digest = hashlib.sha256(binary.read_bytes()).hexdigest()

            result = self.run_wrapper(
                str(binary),
                "--expected-binary-sha256",
                digest,
                "--radare2",
                "/servidor/ark/serverfiles/radare2",
                "--output-root",
                str(root / "out"),
                "--run-id",
                "protected-radare2",
                "--target-group",
                "admin",
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--radare2 must not read from protected server root", result.stderr)

    def test_radare2_version_timeout_blocks_manifest_without_windows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"offline test binary")
            digest = hashlib.sha256(binary.read_bytes()).hexdigest()
            fake_radare2 = root / "radare2"
            self.write_fake_radare2(fake_radare2, version_sleeps=True)
            output_root = root / "out"

            result = self.run_wrapper(
                str(binary),
                "--expected-binary-sha256",
                digest,
                "--radare2",
                str(fake_radare2),
                "--output-root",
                str(output_root),
                "--run-id",
                "timeout-radare2",
                "--target-group",
                "admin",
                "--timeout-sec",
                "1",
                check=False,
            )

            payload = json.loads(result.stdout)
            manifest = json.loads(
                (output_root / "timeout-radare2" / "manifest.json").read_text(encoding="utf-8")
            )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload, manifest)
        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["windows_captured"], [])
        self.assertIn(
            "radare2_version_probe_failed",
            {blocker["reason"] for blocker in payload["blockers"]},
        )
        self.assertEqual(payload["tool_provenance"]["radare2"]["version_probe"]["status"], "timeout")


if __name__ == "__main__":
    unittest.main()
