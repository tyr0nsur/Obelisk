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
EXPECTED_ARTIFACT_SHA = "1c4bf8876706b3af40bd9b73fbeb907a31356e62d6c9ff93aed0158d2cb2fe5e"
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
GENERATED_BY = "scripts/inspect_core_ufunctions.py --snapshot-json"


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

    def manifest_entries_by_path(self) -> dict[Path, dict[str, object]]:
        manifest = self.manifest()
        sha_prefix = manifest["sha_prefix"]
        entries: dict[Path, dict[str, object]] = {}
        for entry in manifest["targets"]:
            relative = Path(sha_prefix) / entry["module"] / entry["file"]
            entries[FIXTURE_ROOT / relative] = entry
        return entries

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
        for module in sorted({entry["module"] for entry in manifest["targets"]}):
            with self.subTest(module=module):
                self.assertIn(f"`{module.replace('_', '.')}`", doc)

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
        entries_by_path = self.manifest_entries_by_path()
        for path in self.fixture_paths():
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                manifest_entry = entries_by_path[path]
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(payload["schema"], SNAPSHOT_SCHEMA)

                evidence = payload.get("evidence")
                self.assertIsInstance(evidence, dict)
                self.assertEqual(evidence.get("ark_binary_sha256"), EXPECTED_ARK_SHA)
                self.assertRegex(str(evidence.get("obelisk_commit")), r"^[0-9a-f]{7,40}$")
                self.assertEqual(evidence.get("source"), "offline_core")
                self.assertEqual(evidence.get("status"), "candidate-only")
                self.assertEqual(evidence.get("artifact_kind"), "offline_core")
                self.assertEqual(evidence.get("artifact_sha256"), EXPECTED_ARTIFACT_SHA)
                self.assertEqual(evidence.get("capture_id"), "primary_core_20260527T031311Z")
                self.assertEqual(evidence.get("evidence_pack_id"), "primary_core_pack_20260527T031311Z")
                self.assertEqual(evidence.get("generated_by"), GENERATED_BY)

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
                self.assertEqual(target.get("status"), "candidate")
                self.assertEqual(target.get("reject_reasons"), [])
                self.assertEqual(
                    target.get("membership"),
                    {"target": "candidate-uobject", "class": "candidate-uobject", "outer": "candidate-uobject"},
                )
                target_identity = target.get("target", {})
                self.assertEqual(target_identity.get("class_name"), "ScriptStruct")
                for field in (
                    "object_index",
                    "name_index",
                    "class_name_index",
                    "class_object_index",
                    "outer_name_index",
                    "outer_object_index",
                ):
                    self.assertIsInstance(target_identity.get(field), int)
                self.assertEqual(target_identity.get("name"), manifest_entry["name"])
                self.assertEqual(target_identity.get("outer_name"), manifest_entry["outer"])
                self.assertIsInstance(target.get("properties_size"), int)
                properties_size = target.get("properties_size")
                chain = target.get("property_chain")
                self.assertIsInstance(chain, dict)
                self.assertEqual(chain.get("status"), "candidate")
                self.assertEqual(chain.get("reject_reasons"), [])
                self.assertIsNone(chain.get("expected_count"))
                self.assertEqual(chain.get("properties_size"), properties_size)
                properties = chain.get("properties")
                self.assertIsInstance(properties, list)
                self.assertEqual(len(properties), chain.get("observed_count"))
                for prop in properties:
                    self.assertIsInstance(prop.get("object_index"), int)
                    self.assertIsInstance(prop.get("name_index"), int)
                    self.assertIsInstance(prop.get("class_name_index"), int)
                    self.assertIsInstance(prop.get("class_object_index"), int)
                    self.assertEqual(prop.get("membership_status"), "candidate-uobject")
                    self.assertEqual(prop.get("class_membership_status"), "candidate-uobject")
                    self.assertEqual(prop.get("outer_membership_status"), "candidate-uobject")
                    offset = prop.get("offset_internal")
                    size = prop.get("element_size")
                    array_dim = prop.get("array_dim")
                    self.assertIsInstance(offset, int)
                    self.assertIsInstance(size, int)
                    self.assertIsInstance(array_dim, int)
                    array_inner_candidate = prop.get("array_inner_candidate")
                    if array_inner_candidate is not None:
                        self.assertEqual(array_inner_candidate.get("status"), "candidate")
                        self.assertEqual(array_inner_candidate.get("reject_reasons"), [])
                        self.assertEqual(array_inner_candidate.get("membership_status"), "candidate-uobject")
                        inner_property = array_inner_candidate.get("inner_property")
                        self.assertIsInstance(inner_property, dict)
                        self.assertIsInstance(inner_property.get("object_index"), int)
                        self.assertIsInstance(inner_property.get("name"), str)
                        self.assertIsInstance(inner_property.get("name_index"), int)
                        self.assertIsInstance(inner_property.get("class_name"), str)
                        self.assertIsNone(ADDRESS_RE.search(inner_property["name"]), inner_property["name"])
                        self.assertIsNone(ADDRESS_RE.search(inner_property["class_name"]), inner_property["class_name"])
                    struct_type_candidate = prop.get("struct_type_candidate")
                    if struct_type_candidate is not None:
                        self.assertEqual(struct_type_candidate.get("status"), "candidate")
                        self.assertEqual(struct_type_candidate.get("reject_reasons"), [])
                        self.assertEqual(struct_type_candidate.get("membership_status"), "candidate-uobject")
                        struct_type = struct_type_candidate.get("struct_type")
                        self.assertIsInstance(struct_type, dict)
                        self.assertIsInstance(struct_type.get("object_index"), int)
                        self.assertIsInstance(struct_type.get("name"), str)
                        self.assertIsInstance(struct_type.get("name_index"), int)
                        self.assertIsInstance(struct_type.get("class_name"), str)
                        self.assertIsNone(ADDRESS_RE.search(struct_type["name"]), struct_type["name"])
                        self.assertIsNone(ADDRESS_RE.search(struct_type["class_name"]), struct_type["class_name"])
                    if prop.get("status") == "candidate":
                        self.assertLessEqual(offset + (size * array_dim), properties_size)


if __name__ == "__main__":
    unittest.main()
