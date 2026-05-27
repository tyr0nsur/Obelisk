#!/usr/bin/env python3
"""Validate committed sanitized ScriptStruct snapshot fixtures."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "scriptstruct_snapshots"
READINESS_DOC = REPO_ROOT / "docs" / "research" / "2026-05-27-module-readiness-matrix.md"
EXPECTED_ARK_SHA = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
MANIFEST_SCHEMA = "obelisk.scriptstruct-snapshot-manifest.v1"
SNAPSHOT_SCHEMA = "obelisk.scriptstruct-chain.snapshot.v1"
ADDRESS_RE = re.compile(r"0x[0-9a-fA-F]{8,}")
FORBIDDEN_KEYS = {
    "object",
    "address",
    "first_property",
    "next_field",
    "next_property",
    "pointer_window",
    "integer_window",
    "gobjects",
    "fname_table",
    "chunks",
    "native_func_candidate",
}
FORBIDDEN_SUBSTRINGS = [
    "/servidor/ark",
    "arkserver-",
    "core-pack-",
    "ShooterGame/Binaries",
]
HEX_METADATA_KEYS = {"property_flags"}


def walk_json(value: object) -> list[tuple[str | None, object]]:
    items: list[tuple[str | None, object]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            items.append((key, child))
            items.extend(walk_json(child))
    elif isinstance(value, list):
        for child in value:
            items.extend(walk_json(child))
    return items


class ScriptStructSnapshotFixtureTests(unittest.TestCase):
    def manifest(self) -> dict[str, object]:
        return json.loads((FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8"))

    def fixture_paths(self) -> list[Path]:
        return sorted(FIXTURE_ROOT.glob("**/*.snapshot.json"))

    def test_manifest_shape_and_readiness_gate(self) -> None:
        manifest = self.manifest()
        self.assertEqual(manifest["schema"], MANIFEST_SCHEMA)
        self.assertEqual(manifest["ark_binary_sha256"], EXPECTED_ARK_SHA)
        self.assertEqual(manifest["sha_prefix"], EXPECTED_ARK_SHA[: len(manifest["sha_prefix"])])
        self.assertEqual(manifest["source"], "offline_core")
        self.assertEqual(manifest["status"], "candidate-only")
        self.assertIsInstance(manifest["targets"], list)

        doc = READINESS_DOC.read_text(encoding="utf-8")
        self.assertIn("ScriptStruct fixture manifest", doc)

    def test_manifest_covers_all_committed_scriptstruct_snapshots(self) -> None:
        manifest = self.manifest()
        sha_prefix = manifest["sha_prefix"]
        expected_paths = set()
        for entry in manifest["targets"]:
            with self.subTest(entry=entry):
                self.assertEqual(entry["file"], f"{entry['safe_outer']}.{entry['name']}.snapshot.json")
                relative = Path(sha_prefix) / entry["module"] / entry["file"]
                expected_paths.add(FIXTURE_ROOT / relative)

        actual_paths = set(self.fixture_paths())
        self.assertEqual(
            sorted(path.relative_to(FIXTURE_ROOT).as_posix() for path in actual_paths),
            sorted(path.relative_to(FIXTURE_ROOT).as_posix() for path in expected_paths),
        )

    def test_scriptstruct_snapshots_are_sanitized_when_present(self) -> None:
        for path in self.fixture_paths():
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(payload["schema"], SNAPSHOT_SCHEMA)
                serialized = json.dumps(payload, sort_keys=True)
                for forbidden in FORBIDDEN_SUBSTRINGS:
                    self.assertNotIn(forbidden, serialized)
                for key, value in walk_json(payload):
                    self.assertNotIn(key, FORBIDDEN_KEYS)
                    if isinstance(value, str) and key not in HEX_METADATA_KEYS:
                        self.assertIsNone(ADDRESS_RE.search(value), value)

                targets = payload.get("targets")
                self.assertIsInstance(targets, list)
                self.assertEqual(len(targets), 1)
                target = targets[0]
                self.assertEqual(target.get("inspection_mode"), "script_struct")
                self.assertEqual(target.get("target", {}).get("class_name"), "ScriptStruct")
                self.assertIsInstance(target.get("properties_size"), int)
                chain = target.get("property_chain")
                self.assertIsInstance(chain, dict)
                self.assertIsNone(chain.get("expected_count"))
                self.assertEqual(chain.get("properties_size"), target.get("properties_size"))


if __name__ == "__main__":
    unittest.main()
