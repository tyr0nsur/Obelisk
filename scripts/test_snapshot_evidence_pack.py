#!/usr/bin/env python3
"""Tests for shared snapshot evidence-pack helpers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from snapshot_evidence_pack import evidence_pack_defaults, merge_manifest_default


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
        sha: str = "4" * 64,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "core": {
                "path": str(core_path),
                "sha256": sha,
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

            defaults = evidence_pack_defaults(manifest, None, None, parse_int)

        self.assertEqual(defaults.artifact_kind, "offline_core")
        self.assertEqual(defaults.artifact_sha256, "4" * 64)
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
                evidence_pack_defaults(manifest, None, None, parse_int)

            defaults = evidence_pack_defaults(manifest, None, "alternate_gobjects", parse_int)

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
                evidence_pack_defaults(manifest, None, None, parse_int)


if __name__ == "__main__":
    unittest.main()
