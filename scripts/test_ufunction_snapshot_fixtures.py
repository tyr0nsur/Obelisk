#!/usr/bin/env python3
"""Validate committed sanitized UFunction snapshot fixtures."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"
READINESS_DOC = REPO_ROOT / "docs" / "research" / "2026-05-27-module-readiness-matrix.md"
EXPECTED_ARK_SHA = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
MANIFEST_SCHEMA = "obelisk.ufunction-snapshot-manifest.v1"
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
ADDRESS_RE = re.compile(r"0x[0-9a-fA-F]{8,}")
HEX_METADATA_KEYS = {"function_flags", "property_flags", "return_value_offset"}


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


class UFunctionSnapshotFixtureTests(unittest.TestCase):
    def fixture_paths(self) -> list[Path]:
        return sorted(FIXTURE_ROOT.glob("**/*.snapshot.json"))

    def manifest(self) -> dict[str, object]:
        return json.loads((FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8"))

    def test_manifest_covers_all_committed_snapshot_fixtures(self) -> None:
        manifest = self.manifest()
        self.assertEqual(manifest["schema"], MANIFEST_SCHEMA)
        self.assertEqual(manifest["ark_binary_sha256"], EXPECTED_ARK_SHA)
        sha_prefix = manifest["sha_prefix"]
        self.assertEqual(sha_prefix, EXPECTED_ARK_SHA[: len(sha_prefix)])

        entries = manifest["targets"]
        self.assertIsInstance(entries, list)
        expected_paths = set()
        for entry in entries:
            relative = Path(sha_prefix) / entry["module"] / entry["file"]
            expected_paths.add(FIXTURE_ROOT / relative)
            self.assertEqual(entry["file"], f"{entry['outer']}.{entry['name']}.snapshot.json")

        actual_paths = set(self.fixture_paths())
        self.assertEqual(
            sorted(path.relative_to(FIXTURE_ROOT).as_posix() for path in actual_paths),
            sorted(path.relative_to(FIXTURE_ROOT).as_posix() for path in expected_paths),
        )

    def test_manifest_modules_are_reflected_in_readiness_matrix(self) -> None:
        manifest = self.manifest()
        doc = READINESS_DOC.read_text(encoding="utf-8")

        modules = sorted({entry["module"] for entry in manifest["targets"]})
        for module in modules:
            with self.subTest(module=module):
                self.assertIn(f"`{module.replace('_', '.')}`", doc)

    def test_snapshot_fixtures_are_sanitized_and_bounded(self) -> None:
        paths = self.fixture_paths()
        self.assertGreaterEqual(len(paths), 3)

        for path in paths:
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(payload["schema"], "obelisk.ufunction-chain.snapshot.v1")

                evidence = payload.get("evidence")
                self.assertIsInstance(evidence, dict)
                self.assertEqual(evidence.get("ark_binary_sha256"), EXPECTED_ARK_SHA)
                self.assertRegex(str(evidence.get("obelisk_commit")), r"^[0-9a-f]{7,40}$")
                self.assertEqual(evidence.get("source"), "offline_core")
                self.assertEqual(evidence.get("status"), "candidate-only")
                self.assertEqual(
                    evidence.get("generated_by"),
                    "scripts/inspect_core_ufunctions.py --snapshot-json",
                )

                serialized = json.dumps(payload, sort_keys=True)
                for forbidden in FORBIDDEN_SUBSTRINGS:
                    self.assertNotIn(forbidden, serialized)
                for key, value in walk_json(payload):
                    self.assertNotIn(key, FORBIDDEN_KEYS)
                    if isinstance(value, str):
                        if key not in HEX_METADATA_KEYS:
                            self.assertIsNone(ADDRESS_RE.search(value), value)

                targets = payload.get("targets")
                self.assertIsInstance(targets, list)
                self.assertEqual(len(targets), 1)
                target = targets[0]
                self.assertIn(target.get("status"), {"candidate", "rejected"})
                target_identity = target.get("target", {})
                self.assertEqual(target_identity.get("class_name"), "Function")
                for field in ("object_index", "name_index", "class_name_index", "class_object_index", "outer_name_index", "outer_object_index"):
                    self.assertIsInstance(target_identity.get(field), int)
                self.assertEqual(
                    target.get("membership"),
                    {"target": "candidate-uobject", "class": "candidate-uobject", "outer": "candidate-uobject"},
                )

                chain = target.get("property_chain")
                self.assertIsInstance(chain, dict)
                self.assertEqual(chain.get("expected_count"), chain.get("observed_count"))
                parms_size = chain.get("parms_size")
                self.assertIsInstance(parms_size, int)
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
                    self.assertIsInstance(offset, int)
                    self.assertIsInstance(size, int)
                    enum_candidate = prop.get("enum_candidate")
                    if enum_candidate is not None:
                        self.assertEqual(enum_candidate.get("status"), "candidate")
                        self.assertEqual(enum_candidate.get("reject_reasons"), [])
                        enum_values = enum_candidate.get("values")
                        self.assertIsInstance(enum_values, list)
                        self.assertGreater(len(enum_values), 0)
                        for value in enum_values:
                            self.assertIsInstance(value, str)
                            self.assertNotEqual(value.strip(), "")
                            self.assertIsNone(ADDRESS_RE.search(value), value)
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
                        self.assertLessEqual(offset + size, parms_size)

                if path.name.endswith(".rejected.snapshot.json"):
                    rejected = target.get("status") == "rejected" or chain.get("status") == "rejected"
                    self.assertTrue(rejected)
                    chain_reasons = chain.get("reject_reasons") or []
                    prop_reasons = [
                        reason
                        for prop in properties
                        for reason in prop.get("reject_reasons", [])
                    ]
                    self.assertTrue(chain_reasons or prop_reasons)


if __name__ == "__main__":
    unittest.main()
