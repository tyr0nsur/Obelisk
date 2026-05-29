#!/usr/bin/env python3
"""Tests for build_weak_helper_provenance_bundle.py."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[0]
sys.path.insert(0, str(SCRIPT_DIR))

import build_weak_helper_provenance_bundle as builder  # noqa: E402


SCRIPT = [sys.executable, str(SCRIPT_DIR / "build_weak_helper_provenance_bundle.py")]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_source_provenance(path: Path, binary: Path, **overrides: object) -> None:
    payload = {
        "schema": "obelisk.test-weak-helper-source-provenance.v1",
        "verified": True,
        "producer": "unit-test",
        "tool": "objdump",
        "command": ["objdump", "-d", str(binary)],
        "binary_sha256": sha256_file(binary),
        "artifact_sha256": sha256_file(path),
    }
    payload.update(overrides)
    Path(f"{path}.provenance.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


class BuildWeakHelperProvenanceBundleTests(unittest.TestCase):
    def run_builder(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [*SCRIPT, *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def test_builds_bundle_with_verified_sidecars_and_validates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"weak helper binary")
            objdump = root / "weak-helper-family.objdump.txt"
            objdump.write_text("1d56ae0: test DWORD PTR [rax+0x8],0x100\n", encoding="utf-8")
            callers = root / "caller-windows.objdump.txt"
            callers.write_text("3522bc0: call 1d56ae0\n", encoding="utf-8")
            write_source_provenance(objdump, binary)
            write_source_provenance(callers, binary)
            output_dir = root / "bundle"

            result = self.run_builder(
                [
                    "--binary",
                    str(binary),
                    "--output-dir",
                    str(output_dir),
                    "--artifact",
                    f"weak-helper-family={objdump}",
                    "--artifact",
                    f"caller-windows={callers}",
                    "--json",
                ]
            )

            manifest = json.loads(result.stdout)
            written_manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema"], builder.BUNDLE_SCHEMA)
            self.assertEqual(written_manifest["binary"]["sha256"], sha256_file(binary))
            self.assertTrue(manifest["promotion_ready"])
            self.assertEqual(manifest["promotion_gate"]["blockers"], [])
            self.assertEqual([artifact["label"] for artifact in manifest["artifacts"]], ["weak-helper-family", "caller-windows"])
            for artifact in manifest["artifacts"]:
                with self.subTest(label=artifact["label"]):
                    copied_to = Path(artifact["copied_to"])
                    output_provenance = json.loads(Path(artifact["output_provenance"]).read_text(encoding="utf-8"))
                    self.assertTrue(copied_to.exists())
                    self.assertEqual(artifact["copied_sha256"], sha256_file(copied_to))
                    self.assertEqual(output_provenance["schema"], builder.BUNDLE_ARTIFACT_PROVENANCE_SCHEMA)
                    self.assertTrue(output_provenance["verified"])
                    self.assertEqual(output_provenance["artifact_sha256"], artifact["copied_sha256"])
                    self.assertTrue(artifact["source_provenance"]["verified"])

            validate = self.run_builder(["--validate", str(output_dir / "manifest.json"), "--json"])
            validation = json.loads(validate.stdout)
            self.assertTrue(validation["valid"])
            self.assertTrue(validation["promotion_ready"])
            self.assertEqual(validation["errors"], [])

    def test_missing_sidecar_is_archived_fail_closed_without_failing_build(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"weak helper binary")
            objdump = root / "weak-helper-family.objdump.txt"
            objdump.write_text("1d56c00: and eax,0x4100\n", encoding="utf-8")

            result = self.run_builder(
                [
                    "--binary",
                    str(binary),
                    "--output-dir",
                    str(root / "bundle"),
                    "--artifact",
                    f"weak-helper-family={objdump}",
                    "--json",
                ]
            )

            manifest = json.loads(result.stdout)
            self.assertFalse(manifest["promotion_ready"])
            self.assertEqual(
                manifest["promotion_gate"]["blockers"],
                [
                    {
                        "reason": "unverified_source_provenance",
                        "artifact": "weak-helper-family",
                        "detail": "missing_provenance_sidecar",
                    }
                ],
            )
            artifact = manifest["artifacts"][0]
            output_provenance = json.loads(Path(artifact["output_provenance"]).read_text(encoding="utf-8"))
            self.assertFalse(output_provenance["verified"])
            self.assertEqual(output_provenance["source_provenance"]["reason"], "missing_provenance_sidecar")

            validate = self.run_builder(["--validate", str(root / "bundle" / "manifest.json"), "--json"])
            validation = json.loads(validate.stdout)
            self.assertTrue(validation["valid"])
            self.assertFalse(validation["promotion_ready"])
            self.assertEqual(validation["blockers"][0]["detail"], "missing_provenance_sidecar")

    def test_validate_mode_rejects_tampered_copied_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"weak helper binary")
            objdump = root / "weak-helper-family.objdump.txt"
            objdump.write_text("original\n", encoding="utf-8")
            write_source_provenance(objdump, binary)
            output_dir = root / "bundle"
            build = self.run_builder(
                [
                    "--binary",
                    str(binary),
                    "--output-dir",
                    str(output_dir),
                    "--artifact",
                    f"weak-helper-family={objdump}",
                    "--json",
                ]
            )
            copied_to = Path(json.loads(build.stdout)["artifacts"][0]["copied_to"])
            copied_to.write_text("tampered\n", encoding="utf-8")

            validate = self.run_builder(["--validate", str(output_dir / "manifest.json"), "--json"], check=False)

            self.assertNotEqual(validate.returncode, 0)
            validation = json.loads(validate.stdout)
            self.assertFalse(validation["valid"])
            self.assertIn("artifact_sha256_mismatch", {error["reason"] for error in validation["errors"]})
            self.assertIn("output_provenance_artifact_sha256_mismatch", {error["reason"] for error in validation["errors"]})

    def test_sidecar_binary_mismatch_blocks_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"weak helper binary")
            artifact = root / "ghidra-headless-java.stdout"
            artifact.write_text("decompiler output\n", encoding="utf-8")
            write_source_provenance(artifact, binary, binary_sha256="0" * 64)

            result = self.run_builder(
                [
                    "--binary",
                    str(binary),
                    "--output-dir",
                    str(root / "bundle"),
                    "--artifact",
                    f"ghidra-stdout={artifact}",
                    "--json",
                ]
            )

            manifest = json.loads(result.stdout)
            self.assertFalse(manifest["promotion_ready"])
            self.assertEqual(manifest["artifacts"][0]["source_provenance"]["reason"], "provenance_binary_sha256_mismatch")

    def test_sidecar_recursive_protected_paths_block_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"weak helper binary")
            artifact = root / "direct-call-counts.txt"
            artifact.write_text("0x1d56ae0 7\n", encoding="utf-8")
            write_source_provenance(
                artifact,
                binary,
                source_provenance={"nested": [{"path": "/servidor/ark/obelisk/dumps/weak-helper.objdump"}]},
            )

            result = self.run_builder(
                [
                    "--binary",
                    str(binary),
                    "--output-dir",
                    str(root / "bundle"),
                    "--artifact",
                    f"direct-call-counts={artifact}",
                    "--json",
                ]
            )

            manifest = json.loads(result.stdout)
            self.assertFalse(manifest["promotion_ready"])
            source_provenance = manifest["artifacts"][0]["source_provenance"]
            self.assertEqual(source_provenance["reason"], "protected_path_in_provenance_sidecar")
            self.assertEqual(source_provenance["source_provenance_field"], "provenance_sidecar.source_provenance.nested[0].path")

    def test_rejects_protected_artifact_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"weak helper binary")

            result = self.run_builder(
                [
                    "--binary",
                    str(binary),
                    "--output-dir",
                    str(root / "bundle"),
                    "--artifact",
                    "weak-helper-family=/servidor/ark/obelisk/dumps/weak-helper.objdump",
                ],
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--artifact weak-helper-family must not read from protected server root /servidor/ark", result.stderr)

    def test_rejects_symlinked_protected_artifact_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"weak helper binary")
            link = root / "protected-link"
            link.symlink_to("/servidor/ark/obelisk/dumps/weak-helper.objdump")

            result = self.run_builder(
                [
                    "--binary",
                    str(binary),
                    "--output-dir",
                    str(root / "bundle"),
                    "--artifact",
                    f"weak-helper-family={link}",
                ],
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--artifact weak-helper-family must not read from protected server root /servidor/ark", result.stderr)


if __name__ == "__main__":
    unittest.main()
