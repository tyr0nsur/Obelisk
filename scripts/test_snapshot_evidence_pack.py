#!/usr/bin/env python3
"""Tests for shared snapshot evidence-pack helpers."""

from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import snapshot_evidence_pack
from snapshot_evidence_pack import evidence_pack_defaults, merge_manifest_default


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_int(value: str) -> int:
    return int(value, 0)


class SnapshotEvidencePackTests(unittest.TestCase):
    def write_pack(
        self,
        path: Path,
        *,
        core_path: Path,
        fname_roots: list[dict[str, str]] | None = None,
        gobjects: list[dict[str, str]] | None = None,
        sha: str | None = None,
        binary_sha: str = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
        evidence_status: dict[str, object] | None = None,
        write_core: bool = True,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if write_core and not core_path.exists():
            core_path.write_bytes(b"snapshot evidence pack core fixture")
        if sha is None:
            sha = sha256_bytes(core_path.read_bytes()) if core_path.exists() else "4" * 64
        payload = {
            "binary": {
                "sha256": binary_sha,
            },
            "core": {
                "path": str(core_path),
                "sha256": sha,
            },
            "evidence_status": evidence_status
            or {
                "status": "complete",
                "gdb_core_failed": False,
            },
            "fname_root_slots": fname_roots
            or [
                {
                    "label": "primary_fname_root",
                    "address": "0x1000",
                }
            ],
            "gobjects_candidates": gobjects
            or [
                {
                    "label": "primary_gobjects",
                    "address": "0x2000",
                }
            ],
        }
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_defaults_select_single_entries_and_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            manifest = root / "pack-A" / "manifest.json"
            self.write_pack(manifest, core_path=core)

            defaults = evidence_pack_defaults(
                manifest,
                None,
                None,
                "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                parse_int,
            )

        self.assertEqual(defaults.artifact_kind, "offline_core")
        self.assertEqual(defaults.artifact_sha256, sha256_bytes(b"snapshot evidence pack core fixture"))
        self.assertEqual(defaults.capture_id, "core")
        self.assertEqual(defaults.evidence_pack_id, "pack-A")
        self.assertEqual(defaults.core_path, core.resolve())
        self.assertEqual(defaults.fname_root_slot, 0x1000)
        self.assertEqual(defaults.gobjects, 0x2000)

    def test_multiple_gobjects_candidates_require_label(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = root / "pack-A" / "manifest.json"
            self.write_pack(
                manifest,
                core_path=root / "core",
                gobjects=[
                    {"label": "primary_gobjects", "address": "0x2000"},
                    {"label": "alternate_gobjects", "address": "0x3000"},
                ],
            )

            with self.assertRaisesRegex(SystemExit, "--evidence-pack-gobjects-label"):
                evidence_pack_defaults(
                    manifest,
                    None,
                    None,
                    "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                    parse_int,
                )

            defaults = evidence_pack_defaults(
                manifest,
                None,
                "alternate_gobjects",
                "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                parse_int,
            )

        self.assertEqual(defaults.gobjects, 0x3000)

    def test_merge_manifest_default_rejects_conflict(self) -> None:
        self.assertEqual(merge_manifest_default(None, "offline_core", "--artifact-kind"), "offline_core")
        self.assertEqual(merge_manifest_default("offline_core", "offline_core", "--artifact-kind"), "offline_core")
        with self.assertRaisesRegex(SystemExit, "--artifact-kind conflicts"):
            merge_manifest_default("runtime_log", "offline_core", "--artifact-kind")

    def test_invalid_identity_component_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = root / "bad..pack" / "manifest.json"
            self.write_pack(manifest, core_path=root / "core")

            with self.assertRaisesRegex(SystemExit, "unsafe evidence-pack-id"):
                evidence_pack_defaults(
                    manifest,
                    None,
                    None,
                    "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                    parse_int,
                )

    def test_rejects_wrong_binary_sha(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = root / "pack-A" / "manifest.json"
            self.write_pack(manifest, core_path=root / "core", binary_sha="8" * 64)

            with self.assertRaisesRegex(SystemExit, "binary.sha256 conflicts"):
                evidence_pack_defaults(
                    manifest,
                    None,
                    None,
                    "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                    parse_int,
                )

    def test_rejects_evidence_pack_manifest_under_protected_server_root_before_reading(self) -> None:
        with self.assertRaisesRegex(SystemExit, "--evidence-pack-manifest must not read"):
            evidence_pack_defaults(
                Path("/servidor/ark/obelisk/evidence/manifest.json"),
                None,
                None,
                "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                parse_int,
            )

    def test_rejects_evidence_pack_manifest_symlinked_to_protected_server_root_before_reading(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = root / "manifest-link.json"
            manifest.symlink_to("/servidor/ark/obelisk/evidence/manifest.json")

            with self.assertRaisesRegex(SystemExit, "--evidence-pack-manifest must not read"):
                evidence_pack_defaults(
                    manifest,
                    None,
                    None,
                    "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                    parse_int,
                )

    def test_rejects_evidence_pack_manifest_symlinked_to_offline_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            real_manifest = root / "pack-A" / "manifest.json"
            core = root / "core"
            self.write_pack(real_manifest, core_path=core)
            manifest_link = root / "manifest-link.json"
            manifest_link.symlink_to(real_manifest)

            with self.assertRaisesRegex(SystemExit, "--evidence-pack-manifest must not be a symlink"):
                evidence_pack_defaults(
                    manifest_link,
                    None,
                    None,
                    "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                    parse_int,
                )

    def test_rejects_partial_gdb_failed_pack(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = root / "pack-A" / "manifest.json"
            self.write_pack(
                manifest,
                core_path=root / "core",
                evidence_status={"status": "partial-gdb-failed", "gdb_core_failed": True},
            )

            with self.assertRaisesRegex(SystemExit, "status is not complete"):
                evidence_pack_defaults(
                    manifest,
                    None,
                    None,
                    "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                    parse_int,
                )

    def test_rejects_complete_pack_without_boolean_gdb_core_failed_false(self) -> None:
        invalid_values: list[object] = [True, None, "true", 1, 0]
        for invalid_value in invalid_values:
            with self.subTest(gdb_core_failed=invalid_value), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                manifest = root / "pack-A" / "manifest.json"
                self.write_pack(
                    manifest,
                    core_path=root / "core",
                    evidence_status={"status": "complete", "gdb_core_failed": invalid_value},
                )

                with self.assertRaisesRegex(SystemExit, "gdb_core_failed=false"):
                    evidence_pack_defaults(
                        manifest,
                        None,
                        None,
                        "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                        parse_int,
                    )

    def test_rejects_complete_pack_missing_gdb_core_failed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = root / "pack-A" / "manifest.json"
            self.write_pack(
                manifest,
                core_path=root / "core",
                evidence_status={"status": "complete"},
            )

            with self.assertRaisesRegex(SystemExit, "gdb_core_failed=false"):
                evidence_pack_defaults(
                    manifest,
                    None,
                    None,
                    "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                    parse_int,
                )

    def test_rejects_core_sha_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = root / "pack-A" / "manifest.json"
            self.write_pack(manifest, core_path=root / "core", sha="5" * 64)

            with self.assertRaisesRegex(SystemExit, "core.sha256 does not match"):
                evidence_pack_defaults(
                    manifest,
                    None,
                    None,
                    "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                    parse_int,
                )

    def test_rejects_missing_core_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = root / "pack-A" / "manifest.json"
            self.write_pack(manifest, core_path=root / "missing-core", write_core=False)

            with self.assertRaisesRegex(SystemExit, "core.path does not exist"):
                evidence_pack_defaults(
                    manifest,
                    None,
                    None,
                    "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                    parse_int,
                )

    def test_rejects_manifest_core_path_under_protected_server_root_outside_dump_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = root / "pack-A" / "manifest.json"
            self.write_pack(
                manifest,
                core_path=Path("/servidor/ark/serverfiles/core"),
                sha="4" * 64,
                write_core=False,
            )

            with self.assertRaisesRegex(SystemExit, "core.path must not read from protected server root"):
                evidence_pack_defaults(
                    manifest,
                    None,
                    None,
                    "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                    parse_int,
                )

    def test_rejects_manifest_core_path_symlink_to_protected_server_root_outside_dump_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core_link = root / "core-link"
            core_link.symlink_to("/servidor/ark/serverfiles/core")
            manifest = root / "pack-A" / "manifest.json"
            self.write_pack(manifest, core_path=core_link, sha="4" * 64, write_core=False)

            with self.assertRaisesRegex(SystemExit, "core.path must not read from protected server root"):
                evidence_pack_defaults(
                    manifest,
                    None,
                    None,
                    "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                    parse_int,
                )

    def test_rejects_manifest_core_path_symlink_to_offline_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core_target = root / "core-target"
            core_target.write_bytes(b"core")
            core_link = root / "core-link"
            core_link.symlink_to(core_target)
            manifest = root / "pack-A" / "manifest.json"
            self.write_pack(manifest, core_path=core_link, sha=sha256_bytes(b"core"), write_core=False)

            with self.assertRaisesRegex(SystemExit, "core.path must not be a symlink"):
                evidence_pack_defaults(
                    manifest,
                    None,
                    None,
                    "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                    parse_int,
                )

    def test_rejects_manifest_core_path_under_server_dump_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = root / "pack-A" / "manifest.json"
            self.write_pack(
                manifest,
                core_path=Path("/servidor/ark/obelisk/dumps/second-source/core"),
                sha="4" * 64,
                write_core=False,
            )

            with self.assertRaisesRegex(SystemExit, "core.path must not read from protected server root"):
                evidence_pack_defaults(
                    manifest,
                    None,
                    None,
                    "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                    parse_int,
                )

    def test_manifest_core_path_prefix_only_is_not_overblocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = root / "pack-A" / "manifest.json"
            self.write_pack(
                manifest,
                core_path=Path("/servidor/ark-not-live/core"),
                sha="4" * 64,
                write_core=False,
            )

            with self.assertRaisesRegex(SystemExit, "core.path does not exist"):
                evidence_pack_defaults(
                    manifest,
                    None,
                    None,
                    "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                    parse_int,
                )

    def test_allows_approved_offline_workspace_core_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            protected = root / "server-root"
            workspace = protected / "workspace-offline"
            workspace.mkdir(parents=True)
            core = workspace / "core"
            core.write_bytes(b"core")
            manifest = workspace / "pack" / "manifest.json"
            self.write_pack(manifest, core_path=core, sha=sha256_bytes(b"core"), write_core=False)

            with (
                mock.patch.object(snapshot_evidence_pack, "SERVER_ROOT", protected),
                mock.patch.object(snapshot_evidence_pack, "APPROVED_OFFLINE_WORKSPACE_ROOTS", (workspace,)),
            ):
                defaults = evidence_pack_defaults(
                    manifest,
                    None,
                    None,
                    "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                    parse_int,
                )

        self.assertEqual(defaults.core_path, core.resolve())


if __name__ == "__main__":
    unittest.main()
