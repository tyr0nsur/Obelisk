#!/usr/bin/env python3
"""Tests for shared snapshot evidence-pack helpers."""

from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
