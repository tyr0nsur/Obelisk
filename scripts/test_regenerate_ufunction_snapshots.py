#!/usr/bin/env python3
"""Tests for regenerate_ufunction_snapshots.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from test_inspect_core_ufunctions import build_core_fixture  # noqa: E402


class RegenerateUFunctionSnapshotsTests(unittest.TestCase):
    def write_manifest(
        self,
        path: Path,
        *,
        module: str = "sdk_test",
        name: str = "AllowStructureAccess",
        filename: str = "PrimalStructure.AllowStructureAccess.snapshot.json",
    ) -> None:
        manifest = {
            "schema": "obelisk.ufunction-snapshot-manifest.v1",
            "ark_binary_sha256": "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
            "sha_prefix": "7e7ded49e0c6",
            "source": "offline_core",
            "status": "candidate-only",
            "max_object_scan": 128,
            "targets": [
                {
                    "module": module,
                    "outer": "PrimalStructure",
                    "name": name,
                    "file": filename,
                }
            ],
        }
        path.write_text(json.dumps(manifest), encoding="utf-8")

    def test_dry_run_reports_manifest_outputs_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            manifest = root / "manifest.json"
            output_root = root / "out"
            addrs = build_core_fixture(core)
            self.write_manifest(manifest)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "regenerate_ufunction_snapshots.py"),
                    "--core",
                    str(core),
                    "--manifest",
                    str(manifest),
                    "--output-root",
                    str(output_root),
                    "--gobjects",
                    hex(addrs["gobjects"]),
                    "--fname-root-slot",
                    hex(addrs["fname_root_slot"]),
                    "--obelisk-commit",
                    "abcdef1",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            output = output_root / "7e7ded49e0c6" / "sdk_test" / "PrimalStructure.AllowStructureAccess.snapshot.json"

        self.assertIn("would write", result.stdout)
        self.assertFalse(output.exists())

    def test_write_generates_sanitized_snapshot_from_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            manifest = root / "manifest.json"
            output_root = root / "out"
            output = output_root / "7e7ded49e0c6" / "sdk_test" / "PrimalStructure.AllowStructureAccess.snapshot.json"
            addrs = build_core_fixture(core)
            self.write_manifest(manifest)

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "regenerate_ufunction_snapshots.py"),
                    "--core",
                    str(core),
                    "--manifest",
                    str(manifest),
                    "--output-root",
                    str(output_root),
                    "--gobjects",
                    hex(addrs["gobjects"]),
                    "--fname-root-slot",
                    hex(addrs["fname_root_slot"]),
                    "--obelisk-commit",
                    "abcdef1",
                    "--artifact-kind",
                    "offline_core",
                    "--artifact-sha256",
                    "2" * 64,
                    "--capture-id",
                    "second-core",
                    "--evidence-pack-id",
                    "second-pack",
                    "--write",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(
            payload["evidence"]["ark_binary_sha256"],
            "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
        )
        self.assertEqual(payload["evidence"]["obelisk_commit"], "abcdef1")
        self.assertEqual(payload["evidence"]["artifact_kind"], "offline_core")
        self.assertEqual(payload["evidence"]["artifact_sha256"], "2" * 64)
        self.assertEqual(payload["evidence"]["capture_id"], "second-core")
        self.assertEqual(payload["evidence"]["evidence_pack_id"], "second-pack")
        self.assertEqual(payload["targets"][0]["target"]["name"], "AllowStructureAccess")
        self.assertEqual(payload["targets"][0]["target"]["outer_name"], "PrimalStructure")

    def test_check_detects_snapshot_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            manifest = root / "manifest.json"
            output_root = root / "out"
            output = output_root / "7e7ded49e0c6" / "sdk_test" / "PrimalStructure.AllowStructureAccess.snapshot.json"
            addrs = build_core_fixture(core)
            self.write_manifest(manifest)
            output.parent.mkdir(parents=True)
            output.write_text("{}\n", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "regenerate_ufunction_snapshots.py"),
                    "--core",
                    str(core),
                    "--manifest",
                    str(manifest),
                    "--output-root",
                    str(output_root),
                    "--gobjects",
                    hex(addrs["gobjects"]),
                    "--fname-root-slot",
                    hex(addrs["fname_root_slot"]),
                    "--obelisk-commit",
                    "abcdef1",
                    "--check",
                ],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("snapshot drift detected", result.stderr)

    def test_artifact_identity_requires_explicit_fname_root_slot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            manifest = root / "manifest.json"
            output_root = root / "out"
            addrs = build_core_fixture(core)
            self.write_manifest(manifest)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "regenerate_ufunction_snapshots.py"),
                    "--core",
                    str(core),
                    "--manifest",
                    str(manifest),
                    "--output-root",
                    str(output_root),
                    "--gobjects",
                    hex(addrs["gobjects"]),
                    "--obelisk-commit",
                    "abcdef1",
                    "--artifact-kind",
                    "offline_core",
                    "--artifact-sha256",
                    "2" * 64,
                    "--capture-id",
                    "second-core",
                    "--evidence-pack-id",
                    "second-pack",
                    "--write",
                ],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--fname-root-slot is required when recording artifact identity", result.stderr)

    def test_artifact_identity_requires_all_fields_together(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            manifest = root / "manifest.json"
            output_root = root / "out"
            addrs = build_core_fixture(core)
            self.write_manifest(manifest)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "regenerate_ufunction_snapshots.py"),
                    "--core",
                    str(core),
                    "--manifest",
                    str(manifest),
                    "--output-root",
                    str(output_root),
                    "--gobjects",
                    hex(addrs["gobjects"]),
                    "--fname-root-slot",
                    hex(addrs["fname_root_slot"]),
                    "--obelisk-commit",
                    "abcdef1",
                    "--artifact-kind",
                    "offline_core",
                    "--artifact-sha256",
                    "2" * 64,
                    "--capture-id",
                    "second-core",
                    "--write",
                ],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("artifact identity must include", result.stderr)

    def test_check_layout_ignores_evidence_and_identity_index_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            manifest = root / "manifest.json"
            output_root = root / "out"
            output = output_root / "7e7ded49e0c6" / "sdk_test" / "PrimalStructure.AllowStructureAccess.snapshot.json"
            addrs = build_core_fixture(core)
            self.write_manifest(manifest)
            common_args = [
                sys.executable,
                str(SCRIPT_DIR / "regenerate_ufunction_snapshots.py"),
                "--core",
                str(core),
                "--manifest",
                str(manifest),
                "--output-root",
                str(output_root),
                "--gobjects",
                hex(addrs["gobjects"]),
                "--fname-root-slot",
                hex(addrs["fname_root_slot"]),
            ]

            subprocess.run(
                [*common_args, "--obelisk-commit", "abcdef1", "--write"],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(output.read_text(encoding="utf-8"))
            payload["evidence"]["obelisk_commit"] = "different"  # type: ignore[index]
            payload["targets"][0]["target"]["object_index"] = 9001  # type: ignore[index]
            payload["targets"][0]["target"]["name_index"] = 9002  # type: ignore[index]
            payload["targets"][0]["target"]["class_name_index"] = 9003  # type: ignore[index]
            payload["targets"][0]["target"]["class_object_index"] = 9004  # type: ignore[index]
            payload["targets"][0]["target"]["outer_name_index"] = 9005  # type: ignore[index]
            payload["targets"][0]["target"]["outer_object_index"] = 9006  # type: ignore[index]
            prop = payload["targets"][0]["property_chain"]["properties"][0]  # type: ignore[index]
            prop["object_index"] = 9010
            prop["name_index"] = 9011
            prop["class_name_index"] = 9012
            prop["class_object_index"] = 9013
            output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            layout = subprocess.run(
                [*common_args, "--obelisk-commit", "1234567", "--check-layout"],
                check=False,
                capture_output=True,
                text=True,
            )
            full = subprocess.run(
                [*common_args, "--obelisk-commit", "1234567", "--check"],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(layout.returncode, 0, layout.stderr)
        self.assertIn("layout ok", layout.stdout)
        self.assertNotEqual(full.returncode, 0)
        self.assertIn("snapshot drift detected", full.stderr)

    def test_check_layout_detects_property_layout_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            manifest = root / "manifest.json"
            output_root = root / "out"
            output = output_root / "7e7ded49e0c6" / "sdk_test" / "PrimalStructure.AllowStructureAccess.snapshot.json"
            addrs = build_core_fixture(core)
            self.write_manifest(manifest)
            common_args = [
                sys.executable,
                str(SCRIPT_DIR / "regenerate_ufunction_snapshots.py"),
                "--core",
                str(core),
                "--manifest",
                str(manifest),
                "--output-root",
                str(output_root),
                "--gobjects",
                hex(addrs["gobjects"]),
                "--fname-root-slot",
                hex(addrs["fname_root_slot"]),
                "--obelisk-commit",
                "abcdef1",
            ]

            subprocess.run([*common_args, "--write"], check=True, capture_output=True, text=True)
            payload = json.loads(output.read_text(encoding="utf-8"))
            payload["targets"][0]["property_chain"]["properties"][0]["offset_internal"] = 4  # type: ignore[index]
            output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            result = subprocess.run([*common_args, "--check-layout"], check=False, capture_output=True, text=True)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("layout diff", result.stdout)
        self.assertIn("layout drift detected", result.stderr)

    def test_check_layout_is_mutually_exclusive_with_full_check(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            manifest = root / "manifest.json"
            addrs = build_core_fixture(core)
            self.write_manifest(manifest)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "regenerate_ufunction_snapshots.py"),
                    "--core",
                    str(core),
                    "--manifest",
                    str(manifest),
                    "--output-root",
                    str(root / "out"),
                    "--gobjects",
                    hex(addrs["gobjects"]),
                    "--fname-root-slot",
                    hex(addrs["fname_root_slot"]),
                    "--obelisk-commit",
                    "abcdef1",
                    "--check",
                    "--check-layout",
                ],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("choose only one of --check, --check-layout, or --write", result.stderr)

    def test_rejects_manifest_output_that_escapes_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            manifest = root / "manifest.json"
            addrs = build_core_fixture(core)
            self.write_manifest(manifest, module="../escape")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "regenerate_ufunction_snapshots.py"),
                    "--core",
                    str(core),
                    "--manifest",
                    str(manifest),
                    "--output-root",
                    str(root / "out"),
                    "--gobjects",
                    hex(addrs["gobjects"]),
                    "--fname-root-slot",
                    hex(addrs["fname_root_slot"]),
                    "--obelisk-commit",
                    "abcdef1",
                    "--write",
                ],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsafe module", result.stderr)

    def test_rejects_ambiguous_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            manifest = root / "manifest.json"
            addrs = build_core_fixture(core)
            self.write_manifest(manifest, name="MissingFunction")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "regenerate_ufunction_snapshots.py"),
                    "--core",
                    str(core),
                    "--manifest",
                    str(manifest),
                    "--output-root",
                    str(root / "out"),
                    "--gobjects",
                    hex(addrs["gobjects"]),
                    "--fname-root-slot",
                    hex(addrs["fname_root_slot"]),
                    "--obelisk-commit",
                    "abcdef1",
                    "--write",
                ],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected exactly one target", result.stderr)


if __name__ == "__main__":
    unittest.main()
