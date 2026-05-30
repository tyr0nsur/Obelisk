#!/usr/bin/env python3
"""Tests for regenerate_ufunction_snapshots.py."""

from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from test_inspect_core_ufunctions import build_core_fixture  # noqa: E402


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RegenerateUFunctionSnapshotsTests(unittest.TestCase):
    SECOND_SOURCE_ARGS = [
        "--artifact-kind",
        "offline_core",
        "--artifact-sha256",
        "3" * 64,
        "--capture-id",
        "layout-check",
        "--evidence-pack-id",
        "layout-pack",
    ]

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

    def write_evidence_pack_manifest(
        self,
        path: Path,
        *,
        core: Path,
        fname_root_slot: int,
        gobjects: int,
        extra_gobjects: bool = False,
        binary_sha: str = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
        evidence_status: dict[str, object] | None = None,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        manifest = {
            "schema": "obelisk.core-dump-evidence-pack.v1",
            "binary": {
                "sha256": binary_sha,
            },
            "core": {
                "path": str(core),
                "sha256": sha256_file(core),
            },
            "evidence_status": evidence_status
            or {
                "status": "complete",
                "gdb_core_failed": False,
            },
            "fname_root_slots": [
                {
                    "label": "verified_fname_root_slot",
                    "address": hex(fname_root_slot),
                }
            ],
            "gobjects_candidates": [
                {
                    "label": "verified_gobjects",
                    "address": hex(gobjects),
                }
            ],
        }
        if extra_gobjects:
            manifest["gobjects_candidates"].append(  # type: ignore[index]
                {
                    "label": "alternate_gobjects",
                    "address": hex(gobjects + 0x1000),
                }
            )
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
                    *self.SECOND_SOURCE_ARGS,
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            output = output_root / "7e7ded49e0c6" / "sdk_test" / "PrimalStructure.AllowStructureAccess.snapshot.json"

        self.assertIn("would write", result.stdout)
        self.assertFalse(output.exists())

    def test_rejects_protected_direct_paths_before_core_open(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = root / "manifest.json"
            output_root = root / "out"
            self.write_manifest(manifest)
            cases = (
                ("--core", "/servidor/ark/obelisk/dumps/core", "--core must not read from protected server root"),
                ("--manifest", "/servidor/ark/obelisk/snapshots/manifest.json", "--manifest must not read from protected server root"),
                ("--output-root", "/servidor/ark/obelisk/snapshots", "--output-root must not write under protected server root"),
                (
                    "--evidence-pack-manifest",
                    "/servidor/ark/obelisk/evidence-pack/manifest.json",
                    "--evidence-pack-manifest must not read from protected server root",
                ),
            )
            for option, protected_path, expected in cases:
                with self.subTest(option=option):
                    args = [
                        sys.executable,
                        str(SCRIPT_DIR / "regenerate_ufunction_snapshots.py"),
                        "--core",
                        str(root / "missing-core"),
                        "--manifest",
                        str(manifest),
                        "--output-root",
                        str(output_root),
                        "--gobjects",
                        "0x1",
                        "--fname-root-slot",
                        "0x2",
                    ]
                    if option == "--core":
                        args[args.index("--core") + 1] = protected_path
                    elif option == "--manifest":
                        args[args.index("--manifest") + 1] = protected_path
                    elif option == "--output-root":
                        args[args.index("--output-root") + 1] = protected_path
                    else:
                        args.extend([option, protected_path])

                    result = subprocess.run(args, capture_output=True, text=True)

                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(expected, result.stderr)

    def test_rejects_symlinked_protected_output_root_before_core_open(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = root / "manifest.json"
            output_root = root / "snapshots-link"
            output_root.symlink_to("/servidor/ark/obelisk/snapshots")
            self.write_manifest(manifest)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "regenerate_ufunction_snapshots.py"),
                    "--core",
                    str(root / "missing-core"),
                    "--manifest",
                    str(manifest),
                    "--output-root",
                    str(output_root),
                    "--gobjects",
                    "0x1",
                    "--fname-root-slot",
                    "0x2",
                    *self.SECOND_SOURCE_ARGS,
                ],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--output-root must not write under protected server root /servidor/ark", result.stderr)

    def test_rejects_symlinked_protected_core_before_core_open(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = root / "manifest.json"
            core = root / "core-link"
            core.symlink_to("/servidor/ark/obelisk/dumps/core")
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
                    "0x1",
                    "--fname-root-slot",
                    "0x2",
                    *self.SECOND_SOURCE_ARGS,
                ],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--core must not read from protected server root /servidor/ark", result.stderr)

    def test_allows_paths_that_only_share_protected_prefix_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = root / "manifest.json"
            self.write_manifest(manifest)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "regenerate_ufunction_snapshots.py"),
                    "--core",
                    "/servidor/ark-not-live/offline-core",
                    "--manifest",
                    str(manifest),
                    "--output-root",
                    "/servidor/ark-not-live/snapshots",
                    "--gobjects",
                    "0x1",
                    "--fname-root-slot",
                    "0x2",
                    *self.SECOND_SOURCE_ARGS,
                ],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("/servidor/ark-not-live/offline-core", result.stderr)
        self.assertNotIn("protected server root", result.stderr)

    def test_target_set_expands_named_ufunction_targets(self) -> None:
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
                    "--target-set",
                    "minimal-second-source-intake",
                    *self.SECOND_SOURCE_ARGS,
                ],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("would write", result.stdout)
        self.assertIn("PrimalItem.CanUse", result.stderr)
        self.assertIn("PrimalItem.AllowRemoteAddToInventory", result.stderr)
        self.assertIn("PrimalStructure.IsAllowedToDemolish", result.stderr)

    def test_unknown_filter_fails_before_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            manifest = root / "manifest.json"
            output_root = root / "out"
            output = output_root / "7e7ded49e0c6" / "sdk_test" / "PrimalStructure.AllowStructureAccess.snapshot.json"
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
                    "--target",
                    "PrimalStructure.AllowStructureAccess",
                    "--target",
                    "PrimalStructure.MissingTarget",
                    *self.SECOND_SOURCE_ARGS,
                    "--write",
                ],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown target filter(s): PrimalStructure.MissingTarget", result.stderr)
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
                    *self.SECOND_SOURCE_ARGS,
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

    def test_fname_root_slot_is_required_with_artifact_identity(self) -> None:
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
                    *self.SECOND_SOURCE_ARGS,
                ],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--fname-root-slot is required when recording artifact identity", result.stderr)

    def test_snapshot_regeneration_requires_complete_evidence_metadata(self) -> None:
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
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("snapshot regeneration requires complete evidence metadata", result.stderr)

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

    def test_rejects_identity_values_that_compare_would_mark_inconclusive(self) -> None:
        cases = (
            (
                ["--artifact-kind", "runtime_probe"],
                "artifact-kind must be offline_core",
            ),
            (
                [
                    "--artifact-kind",
                    "offline_core",
                    "--artifact-sha256",
                    "2" * 64,
                    "--capture-id",
                    "unspecified-capture",
                    "--evidence-pack-id",
                    "second-pack",
                ],
                "capture-id must be a sanitized non-placeholder artifact id",
            ),
            (
                [
                    "--artifact-kind",
                    "offline_core",
                    "--artifact-sha256",
                    "2" * 64,
                    "--capture-id",
                    "second-core",
                    "--evidence-pack-id",
                    "static-global-default-pack",
                ],
                "evidence-pack-id must be a sanitized non-placeholder artifact id",
            ),
        )
        for identity_args, expected in cases:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                manifest = root / "manifest.json"
                self.write_manifest(manifest)

                result = subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPT_DIR / "regenerate_ufunction_snapshots.py"),
                        "--core",
                        str(root / "missing-core"),
                        "--manifest",
                        str(manifest),
                        "--output-root",
                        str(root / "out"),
                        "--gobjects",
                        "0x1",
                        "--fname-root-slot",
                        "0x2",
                        "--obelisk-commit",
                        "abcdef1",
                        *identity_args,
                        "--write",
                    ],
                    capture_output=True,
                    text=True,
                )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(expected, result.stderr)
            self.assertNotIn("No such file", result.stderr)

    def test_evidence_pack_manifest_supplies_identity_and_fname_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "second-core.1234"
            manifest = root / "manifest.json"
            evidence_pack = root / "second-pack" / "manifest.json"
            output_root = root / "out"
            output = output_root / "7e7ded49e0c6" / "sdk_test" / "PrimalStructure.AllowStructureAccess.snapshot.json"
            addrs = build_core_fixture(core)
            core_sha = sha256_file(core)
            self.write_manifest(manifest)
            self.write_evidence_pack_manifest(
                evidence_pack,
                core=core,
                fname_root_slot=addrs["fname_root_slot"],
                gobjects=addrs["gobjects"],
            )

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
                    "--obelisk-commit",
                    "abcdef1",
                    "--evidence-pack-manifest",
                    str(evidence_pack),
                    "--write",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertIn("wrote", result.stdout)
        self.assertEqual(payload["evidence"]["artifact_kind"], "offline_core")
        self.assertEqual(payload["evidence"]["artifact_sha256"], core_sha)
        self.assertEqual(payload["evidence"]["capture_id"], "second-core")
        self.assertEqual(payload["evidence"]["evidence_pack_id"], "second-pack")
        self.assertEqual(payload["evidence"]["generated_by"], "scripts/inspect_core_ufunctions.py --snapshot-json")

    def test_evidence_pack_manifest_rejects_conflicting_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "second-core"
            manifest = root / "manifest.json"
            evidence_pack = root / "second-pack" / "manifest.json"
            output_root = root / "out"
            addrs = build_core_fixture(core)
            self.write_manifest(manifest)
            self.write_evidence_pack_manifest(
                evidence_pack,
                core=core,
                fname_root_slot=addrs["fname_root_slot"],
                gobjects=addrs["gobjects"],
            )

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
                    "--evidence-pack-manifest",
                    str(evidence_pack),
                    "--artifact-sha256",
                    "5" * 64,
                    "--write",
                ],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--artifact-sha256 conflicts with --evidence-pack-manifest", result.stderr)

    def test_evidence_pack_manifest_rejects_wrong_binary_sha(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "second-core"
            manifest = root / "manifest.json"
            evidence_pack = root / "second-pack" / "manifest.json"
            output_root = root / "out"
            addrs = build_core_fixture(core)
            self.write_manifest(manifest)
            self.write_evidence_pack_manifest(
                evidence_pack,
                core=core,
                fname_root_slot=addrs["fname_root_slot"],
                gobjects=addrs["gobjects"],
                binary_sha="8" * 64,
            )

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
                    "--evidence-pack-manifest",
                    str(evidence_pack),
                    "--write",
                ],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("binary.sha256 conflicts with snapshot manifest", result.stderr)

    def test_evidence_pack_manifest_rejects_partial_gdb_failed_pack(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "second-core"
            manifest = root / "manifest.json"
            evidence_pack = root / "second-pack" / "manifest.json"
            output_root = root / "out"
            addrs = build_core_fixture(core)
            self.write_manifest(manifest)
            self.write_evidence_pack_manifest(
                evidence_pack,
                core=core,
                fname_root_slot=addrs["fname_root_slot"],
                gobjects=addrs["gobjects"],
                evidence_status={"status": "partial-gdb-failed", "gdb_core_failed": True},
            )

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
                    "--evidence-pack-manifest",
                    str(evidence_pack),
                    "--write",
                ],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("evidence pack status is not complete", result.stderr)

    def test_evidence_pack_manifest_requires_gdb_core_failed_false(self) -> None:
        invalid_values: list[object] = [True, None, "true", "false", 1, 0]
        for invalid_value in invalid_values:
            with self.subTest(gdb_core_failed=invalid_value), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                core = root / "second-core"
                manifest = root / "manifest.json"
                evidence_pack = root / "second-pack" / "manifest.json"
                output_root = root / "out"
                addrs = build_core_fixture(core)
                self.write_manifest(manifest)
                self.write_evidence_pack_manifest(
                    evidence_pack,
                    core=core,
                    fname_root_slot=addrs["fname_root_slot"],
                    gobjects=addrs["gobjects"],
                    evidence_status={"status": "complete", "gdb_core_failed": invalid_value},
                )

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
                        "--evidence-pack-manifest",
                        str(evidence_pack),
                        "--write",
                    ],
                    capture_output=True,
                    text=True,
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("gdb_core_failed=false", result.stderr)

    def test_evidence_pack_manifest_rejects_conflicting_gobjects(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "second-core"
            manifest = root / "manifest.json"
            evidence_pack = root / "second-pack" / "manifest.json"
            output_root = root / "out"
            addrs = build_core_fixture(core)
            self.write_manifest(manifest)
            self.write_evidence_pack_manifest(
                evidence_pack,
                core=core,
                fname_root_slot=addrs["fname_root_slot"],
                gobjects=addrs["gobjects"],
            )

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
                    hex(addrs["gobjects"] + 0x1000),
                    "--evidence-pack-manifest",
                    str(evidence_pack),
                    "--write",
                ],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--gobjects conflicts with --evidence-pack-manifest", result.stderr)

    def test_evidence_pack_manifest_requires_gobjects_label_when_ambiguous(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "second-core"
            manifest = root / "manifest.json"
            evidence_pack = root / "second-pack" / "manifest.json"
            output_root = root / "out"
            addrs = build_core_fixture(core)
            self.write_manifest(manifest)
            self.write_evidence_pack_manifest(
                evidence_pack,
                core=core,
                fname_root_slot=addrs["fname_root_slot"],
                gobjects=addrs["gobjects"],
                extra_gobjects=True,
            )

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
                    "--evidence-pack-manifest",
                    str(evidence_pack),
                    "--write",
                ],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("multiple gobjects_candidates found; pass --evidence-pack-gobjects-label", result.stderr)

    def test_evidence_pack_manifest_rejects_different_core_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_core = root / "manifest-core"
            cli_core = root / "cli-core"
            manifest = root / "manifest.json"
            evidence_pack = root / "second-pack" / "manifest.json"
            output_root = root / "out"
            addrs = build_core_fixture(manifest_core)
            cli_core.write_bytes(manifest_core.read_bytes())
            self.write_manifest(manifest)
            self.write_evidence_pack_manifest(
                evidence_pack,
                core=manifest_core,
                fname_root_slot=addrs["fname_root_slot"],
                gobjects=addrs["gobjects"],
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "regenerate_ufunction_snapshots.py"),
                    "--core",
                    str(cli_core),
                    "--manifest",
                    str(manifest),
                    "--output-root",
                    str(output_root),
                    "--evidence-pack-manifest",
                    str(evidence_pack),
                    "--write",
                ],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--core conflicts with --evidence-pack-manifest core.path", result.stderr)

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
                [*common_args, "--obelisk-commit", "abcdef1", *self.SECOND_SOURCE_ARGS, "--write"],
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
                [*common_args, "--obelisk-commit", "1234567", *self.SECOND_SOURCE_ARGS, "--check-layout"],
                check=False,
                capture_output=True,
                text=True,
            )
            full = subprocess.run(
                [*common_args, "--obelisk-commit", "1234567", *self.SECOND_SOURCE_ARGS, "--check"],
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

            subprocess.run([*common_args, *self.SECOND_SOURCE_ARGS, "--write"], check=True, capture_output=True, text=True)
            payload = json.loads(output.read_text(encoding="utf-8"))
            payload["targets"][0]["property_chain"]["properties"][0]["offset_internal"] = 4  # type: ignore[index]
            output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            result = subprocess.run(
                [*common_args, *self.SECOND_SOURCE_ARGS, "--check-layout"],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("layout diff", result.stdout)
        self.assertIn("layout drift detected", result.stderr)

    def test_check_layout_detects_target_membership_drift(self) -> None:
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

            subprocess.run([*common_args, *self.SECOND_SOURCE_ARGS, "--write"], check=True, capture_output=True, text=True)
            payload = json.loads(output.read_text(encoding="utf-8"))
            payload["targets"][0]["membership"]["target"] = "missing"  # type: ignore[index]
            payload["targets"][0]["reject_reasons"] = ["target_not_in_gobjects"]  # type: ignore[index]
            payload["targets"][0]["property_chain"]["reject_reasons"] = ["weak_target_membership"]  # type: ignore[index]
            output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            result = subprocess.run(
                [*common_args, *self.SECOND_SOURCE_ARGS, "--check-layout"],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("layout diff", result.stdout)
        self.assertIn("layout drift detected", result.stderr)

    def test_check_layout_requires_second_source_identity(self) -> None:
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
                    "--check-layout",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--check-layout is reserved for second-source layout validation", result.stderr)

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
                    *self.SECOND_SOURCE_ARGS,
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
                    *self.SECOND_SOURCE_ARGS,
                    "--write",
                ],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected exactly one target", result.stderr)


if __name__ == "__main__":
    unittest.main()
