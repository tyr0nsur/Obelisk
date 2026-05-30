#!/usr/bin/env python3
"""Tests for shared offline artifact identity helpers."""

from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from artifact_identity import (
    artifact_identity_placeholder_fields,
    canonical_json_bytes,
    complete_artifact_identity,
    is_safe_artifact_id,
    is_sha256,
)


class ArtifactIdentityTests(unittest.TestCase):
    def test_sha256_requires_lowercase_hex(self) -> None:
        self.assertTrue(is_sha256("a" * 64))
        self.assertFalse(is_sha256("A" * 64))
        self.assertFalse(is_sha256("not-a-sha"))

    def test_accepts_safe_ids_used_by_fixtures(self) -> None:
        for value in (
            "offline_core",
            "primary_core_20260527T031311Z",
            "primary-core",
            "second-core",
            "capture_2026-05-30",
            "evidence-pack.alpha_1",
        ):
            with self.subTest(value=value):
                self.assertTrue(is_safe_artifact_id(value))

    def test_rejects_path_like_empty_and_placeholder_ids(self) -> None:
        for value in (
            "",
            "../bad",
            "bad/path",
            "pack\\id",
            "unspecified-capture",
            "Unspecified-evidence-pack",
            "static-global-default-capture",
            "Static-Global-Default-pack",
        ):
            with self.subTest(value=value):
                self.assertFalse(is_safe_artifact_id(value))

    def test_placeholder_fields_reports_nested_paths(self) -> None:
        self.assertEqual(
            artifact_identity_placeholder_fields({
                "capture_id": "unspecified-capture",
                "child": [{"pack": "static-global-default-pack"}],
            }),
            ["capture_id", "child.[0].pack"],
        )

    def test_complete_artifact_identity_normalizes_valid_identity(self) -> None:
        identity, errors = complete_artifact_identity(
            {
                "artifact_identity": {
                    "artifact_kind": "offline_core",
                    "artifact_sha256": "b" * 64,
                    "capture_id": "primary-core",
                    "evidence_pack_id": "pack.alpha_1",
                }
            },
            allowed_artifact_kinds={"offline_core"},
        )
        self.assertEqual(errors, [])
        self.assertEqual(identity["capture_id"] if identity else None, "primary-core")

    def test_complete_artifact_identity_reports_shape_errors(self) -> None:
        _, errors = complete_artifact_identity(
            {
                "artifact_identity": {
                    "artifact_kind": "offline_core",
                    "artifact_sha256": "not-a-sha",
                    "capture_id": "../bad",
                    "evidence_pack_id": "unspecified-pack",
                }
            },
            allowed_artifact_kinds={"offline_core"},
        )
        self.assertEqual(
            errors,
            ["artifact_sha256_invalid", "capture_id_invalid", "evidence_pack_id_invalid"],
        )

    def test_canonical_json_bytes_is_stable(self) -> None:
        self.assertEqual(canonical_json_bytes({"b": 1, "a": 2}), b'{"a":2,"b":1}')


if __name__ == "__main__":
    unittest.main()
