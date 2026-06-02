#!/usr/bin/env python3
"""Guardrail for the Inventory/Items public-contract boundary."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_API_ROOT = REPO_ROOT / "include" / "obelisk"
PUBLIC_GAMEPLAY_EVENTS_MANIFEST = REPO_ROOT / "docs" / "public_gameplay_events.json"
PUBLIC_SDK_SURFACES_MANIFEST = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
PUBLIC_CONTRACT_DOCS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "CONTRIBUTING.md",
    REPO_ROOT / "docs" / "README.md",
    REPO_ROOT / "docs" / "PLUGIN_ARCHITECTURE.md",
    REPO_ROOT / "docs" / "PLUGIN_HUB_CAPABILITY_MATRIX.md",
    REPO_ROOT / "docs" / "PLUGIN_HUB_CONTRIBUTOR_PATH.md",
    REPO_ROOT / "docs" / "PLUGIN_HUB_FOUNDATION_V1.md",
    REPO_ROOT / "docs" / "PLUGIN_HUB_PACKAGE_MANIFEST_SCHEMA.md",
    REPO_ROOT / "docs" / "PLUGIN_HUB_PACKAGE_TEMPLATE.md",
    REPO_ROOT / "docs" / "PLUGIN_HUB_SEED_BOUNDARY.md",
    REPO_ROOT / "docs" / "RELEASE.md",
    REPO_ROOT / "docs" / "SDK_V1_COMPATIBILITY.md",
    REPO_ROOT / "docs" / "STATUS.md",
    REPO_ROOT / "docs" / "VERSIONING.md",
    REPO_ROOT / "examples" / "sdk_inventory_policy_audit" / "README.md",
    REPO_ROOT / "plugins" / "README.md",
]

PUBLIC_JSON_CONTRACT_KEYS = {
    "public_contract",
    "payload_contract",
    "resource_contract",
    "scope",
    "public_fields",
    "descriptor_fields",
    "candidate_public_contract",
    "contract",
    "inventory_sdk",
    "item_module_sdk",
    "support_tier",
}
PUBLIC_JSON_ALLOW_NEGATIVE_KEYS = {
    "blockers",
    "exclusions",
    "guardrails",
    "non_claims",
    "not_promoted",
    "release_guardrails",
    "v1_decision_contract",
}
RAW_INVENTORY_ITEM_IDENTIFIERS = {
    "InventoryComp",
    "ItemId",
    "ItemID1",
    "AdditionalData",
    "ItemNetID",
    "ObeliskItemId",
    "ObeliskInventoryId",
    "anActor",
    "inventory_comp",
    "an_actor",
    "item_id",
    "inventory_id",
    "additional_data",
}
OBJECT_REFERENCE_TOKENS = {
    "UObject",
    "UFunction",
    "GObject",
    "GObjects",
    "GUObjectArray",
    "FName",
    "FNamePool",
    "ResourceHandle",
    "ObjectRef",
    "ObjectReference",
    "object_ref",
}
AUTHORITY_OR_LOOKUP_TOKENS = {
    "GetInventory",
    "ResolveInventory",
    "LookupInventory",
    "FindInventory",
    "GetItem",
    "ResolveItem",
    "LookupItem",
    "FindItem",
    "MutateInventory",
    "MutateItem",
    "SetInventory",
    "SetItem",
    "OverrideReturn",
    "ReturnOverride",
    "SetReturnOverride",
    "return_override",
}
PUBLIC_CONTRACT_FORBIDDEN_TERMS = (
    *sorted(RAW_INVENTORY_ITEM_IDENTIFIERS),
    *sorted(OBJECT_REFERENCE_TOKENS),
    *sorted(AUTHORITY_OR_LOOKUP_TOKENS),
    "Inventory SDK",
    "Items SDK",
    "inventory identity",
    "item identity",
    "object identity",
    "lookup",
    "mutation",
    "return override",
    "return-override",
)
STANDALONE_INVENTORY_ITEMS_SDK_RE = re.compile(
    r"\b(?:Inventory|Items?)\s+SDK\b|\bInventory/Items\s+SDK\b",
    re.IGNORECASE,
)
POSITIVE_CLAIM_RE = re.compile(
    r"\b(?:"
    r"available|complete|exposes?|implements?|included|promotes?|promoted|provides?|"
    r"public|ready|released|ships?|shipped|stable|supported|supports?"
    r")\b",
    re.IGNORECASE,
)
NEGATED_OR_BOUNDARY_RE = re.compile(
    r"\b(?:"
    r"absent|anti-promises|blocked|cannot|does\s+not|do\s+not|excluded|excludes?|"
    r"future|must\s+not|no|not|outside|post-v1|prevent|prevents|remain|remains|"
    r"until|without"
    r")\b",
    re.IGNORECASE,
)


def strip_c_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//.*", "", text)


def json_values_at_contract_keys(value: Any, path: str = "$") -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in PUBLIC_JSON_ALLOW_NEGATIVE_KEYS:
                continue
            if key in PUBLIC_JSON_CONTRACT_KEYS:
                values.extend(json_string_values(child, child_path))
                continue
            values.extend(json_values_at_contract_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            values.extend(json_values_at_contract_keys(child, f"{path}[{index}]"))
    return values


def json_string_values(value: Any, path: str) -> list[tuple[str, str]]:
    if isinstance(value, str):
        return [(path, value)]
    if isinstance(value, dict):
        values: list[tuple[str, str]] = []
        for key, child in value.items():
            values.extend(json_string_values(child, f"{path}.{key}"))
        return values
    if isinstance(value, list):
        values = []
        for index, child in enumerate(value):
            values.extend(json_string_values(child, f"{path}[{index}]"))
        return values
    return []


def sentence_like_segments(text: str) -> list[tuple[int, str]]:
    return [
        (match.start(), match.group(0))
        for match in re.finditer(r"[^.!?;\n]+(?:[.!?;]|\n|$)", text)
        if match.group(0).strip()
    ]


def normalized(text: str) -> str:
    return " ".join(text.split())


class InventoryItemsPublicContractBoundaryTests(unittest.TestCase):
    def test_public_abi_header_has_no_raw_inventory_item_identity_or_authority_tokens(self) -> None:
        offenders: list[str] = []
        forbidden = (
            *sorted(RAW_INVENTORY_ITEM_IDENTIFIERS),
            *sorted(OBJECT_REFERENCE_TOKENS),
            *sorted(AUTHORITY_OR_LOOKUP_TOKENS),
        )

        for path in sorted(PUBLIC_API_ROOT.rglob("*")):
            if not path.is_file() or path.suffix not in {".h", ".hpp"}:
                continue
            text = strip_c_comments(path.read_text(encoding="utf-8"))
            for token in forbidden:
                if re.search(rf"\b{re.escape(token)}\b", text):
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")

        self.assertEqual(offenders, [])

    def test_public_manifest_contract_fields_do_not_expose_raw_inventory_item_shape(self) -> None:
        offenders: list[str] = []
        for path in (PUBLIC_GAMEPLAY_EVENTS_MANIFEST, PUBLIC_SDK_SURFACES_MANIFEST):
            data = json.loads(path.read_text(encoding="utf-8"))
            for value_path, value in json_values_at_contract_keys(data):
                for term in PUBLIC_CONTRACT_FORBIDDEN_TERMS:
                    if not re.search(rf"\b{re.escape(term)}\b", value, re.IGNORECASE):
                        continue
                    if NEGATED_OR_BOUNDARY_RE.search(value):
                        continue
                    offenders.append(
                        f"{path.relative_to(REPO_ROOT)}:{value_path}: {term}: {value}"
                    )

        self.assertEqual(offenders, [])

    def test_public_docs_do_not_claim_standalone_inventory_or_items_sdk(self) -> None:
        offenders: list[str] = []
        for path in PUBLIC_CONTRACT_DOCS:
            text = path.read_text(encoding="utf-8")
            for segment_start, segment in sentence_like_segments(text):
                if not STANDALONE_INVENTORY_ITEMS_SDK_RE.search(segment):
                    continue
                if not POSITIVE_CLAIM_RE.search(segment):
                    continue
                match = STANDALONE_INVENTORY_ITEMS_SDK_RE.search(segment)
                if match is None:
                    continue
                absolute_match_start = segment_start + match.start()
                absolute_match_end = segment_start + match.end()
                context = text[max(0, absolute_match_start - 500): absolute_match_end + 160]
                if NEGATED_OR_BOUNDARY_RE.search(context):
                    continue
                line = text.count("\n", 0, segment_start) + 1
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{line}: {normalized(segment)}")

        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
