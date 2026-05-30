#!/usr/bin/env python3
"""Tests for the weak-helper static polarity report builder."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT = SCRIPT_DIR / "build_weak_helper_static_polarity_report.py"
GATE = SCRIPT_DIR / "validate_offline_artifact_gate.py"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_fixture(
    root: Path,
    *,
    provenance: bool = True,
    provenance_updates: dict[str, object] | None = None,
) -> tuple[Path, Path]:
    binary = root / "ShooterGameServer"
    artifact = root / "weak-helper-family.objdump.txt"
    binary_bytes = b"offline binary fixture\n"
    artifact_bytes = b"1d56c70: f6 c6 40              test   dh,0x40\n"
    binary.write_bytes(binary_bytes)
    artifact.write_bytes(artifact_bytes)
    if provenance:
        payload: dict[str, object] = {
            "schema": "obelisk.offline-artifact-provenance.v1",
            "verified": True,
            "binary_sha256": sha256_bytes(binary_bytes),
            "artifact_sha256": sha256_bytes(artifact_bytes),
        }
        payload.update(provenance_updates or {})
        artifact.with_name(artifact.name + ".provenance.json").write_text(json.dumps(payload), encoding="utf-8")
    return binary, artifact


class BuildWeakHelperStaticPolarityReportTests(unittest.TestCase):
    def run_builder(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            check=check,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_emits_candidate_blocked_redacted_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary, artifact = write_fixture(root)
            output = root / "polarity-report.json"
            result = self.run_builder(
                "--binary",
                str(binary),
                "--artifact",
                f"weak-helper-family={artifact}",
                "--output",
                str(output),
            )

            self.assertEqual(result.stdout, "")
            payload = json.loads(output.read_text(encoding="utf-8"))

        rendered = json.dumps(payload)
        self.assertEqual(payload["schema"], "obelisk.weak-helper-static-polarity-report.v1")
        self.assertEqual(payload["status"], "candidate_blocked")
        self.assertIs(payload["promotion_ready"], False)
        self.assertIs(payload["builder_contract"]["promotion_ready"], False)
        self.assertIs(payload["builder_contract"]["requires_live_server"], False)
        self.assertIs(payload["builder_contract"]["lookup_promotion"], False)
        self.assertIs(payload["builder_contract"]["mutation_promotion"], False)
        self.assertIs(payload["builder_contract"]["return_override_promotion"], False)
        self.assertEqual(payload["binary"]["byte_count"], len(b"offline binary fixture\n"))
        self.assertEqual(payload["source_pack"]["id"], "weak-helper-family")
        self.assertEqual(payload["source_pack"]["bytes"], len(b"1d56c70: f6 c6 40              test   dh,0x40\n"))
        observed = payload["inputs"]["weak-helper-family"]
        self.assertEqual(observed["bytes"], len(b"1d56c70: f6 c6 40              test   dh,0x40\n"))
        self.assertEqual(observed["provenance"]["schema"], "obelisk.offline-artifact-provenance.v1")
        self.assertRegex(observed["provenance"]["sidecar_sha256"], r"^[0-9a-f]{64}$")
        self.assertNotIn(str(root), rendered)
        self.assertNotIn("pending-kill", rendered.lower())
        self.assertNotIn("ResourceHandle", rendered)

    def test_emitted_report_passes_offline_artifact_gate_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary, artifact = write_fixture(root)
            output = root / "polarity-report.json"
            self.run_builder(
                "--binary",
                str(binary),
                "--artifact",
                f"weak-helper-family={artifact}",
                "--output",
                str(output),
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(GATE),
                    "--root",
                    str(root),
                    "--protected-root",
                    str(root / "protected-server"),
                    "--manifest",
                    str(output),
                    "--expected-binary-sha256",
                    sha256_bytes(b"offline binary fixture\n"),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("accepted mode=consume blockers=0", result.stdout)

    def test_fails_closed_when_provenance_sidecar_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary, artifact = write_fixture(root, provenance=False)
            output = root / "polarity-report.json"
            result = self.run_builder(
                "--binary",
                str(binary),
                "--artifact",
                f"weak-helper-family={artifact}",
                "--output",
                str(output),
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--artifact weak-helper-family provenance does not exist", result.stderr)
            self.assertFalse(output.exists())

    def test_fails_closed_when_provenance_artifact_sha_mismatches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary, artifact = write_fixture(root, provenance_updates={"artifact_sha256": "0" * 64})
            output = root / "polarity-report.json"
            result = self.run_builder(
                "--binary",
                str(binary),
                "--artifact",
                f"weak-helper-family={artifact}",
                "--output",
                str(output),
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("provenance_artifact_sha256_mismatch", result.stderr)
            self.assertFalse(output.exists())

    def test_fails_closed_when_provenance_contains_protected_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary, artifact = write_fixture(
                root,
                provenance_updates={"source_path": "/servidor/ark/obelisk/dumps/weak-helper.objdump.txt"},
            )
            output = root / "polarity-report.json"
            result = self.run_builder(
                "--binary",
                str(binary),
                "--artifact",
                f"weak-helper-family={artifact}",
                "--output",
                str(output),
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("provenance_protected_path_field:$.source_path", result.stderr)
            self.assertFalse(output.exists())

    def test_fails_closed_when_provenance_contains_protected_path_list(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary, artifact = write_fixture(
                root,
                provenance_updates={"source": ["/servidor/ark/obelisk/dumps/weak-helper.objdump.txt"]},
            )
            output = root / "polarity-report.json"
            result = self.run_builder(
                "--binary",
                str(binary),
                "--artifact",
                f"weak-helper-family={artifact}",
                "--output",
                str(output),
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("provenance_protected_path_field:$.source[0]", result.stderr)
            self.assertFalse(output.exists())

    def test_rejects_protected_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary, artifact = write_fixture(root)
            result = self.run_builder(
                "--binary",
                str(binary),
                "--artifact",
                f"weak-helper-family={artifact}",
                "--output",
                "/servidor/ark/obelisk/dumps/weak-helper-static-polarity.json",
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--output must not write under protected server root", result.stderr)


if __name__ == "__main__":
    unittest.main()
