#!/usr/bin/env python3
"""Tests for check_inventory_item_copied_signals_stability.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_inventory_item_copied_signals_stability.py"
sys.path.insert(0, str(SCRIPT_DIR))
import check_inventory_item_copied_signals_stability as stability  # noqa: E402


class InventoryItemCopiedSignalsStabilityTests(unittest.TestCase):
    def run_checker(self, root: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--decisions",
                str(root / "inventory_item_copied_signals_public_contract_decisions.json"),
                "--public-sdk-surfaces",
                str(root / "public_sdk_surfaces.json"),
                "--public-gameplay-events",
                str(root / "public_gameplay_events.json"),
                "--public-header",
                str(root / "ObeliskApi.h"),
                "--json",
            ],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if check and result.returncode != 0:
            self.fail(f"checker failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def make_decisions(self) -> dict:
        return {
            "schema": stability.DECISIONS_SCHEMA,
            "surface": stability.SURFACE,
            "status": "promoted-experimental-only",
            "decision": "copied_signal_only",
            "support_tier": "promoted-experimental-only copied-data seed",
            "depends_on": [stability.GAMEPLAY_POLICY_EVENT_SURFACE],
            "public_header_allowed": True,
            "public_header": "include/obelisk/ObeliskApi.h",
            "public_header_symbols_now": sorted(stability.EXPECTED_HEADER_SYMBOLS),
            "public_contract": {
                "event_family": "GameplayPolicyEvent",
                "resource_kind": stability.RESOURCE_KIND,
                "resource_contract": "category-only metadata; no identity, no lookup, no handle, persistence, or cross-event correlation",
                "payload_contract": stability.EXPECTED_DECISIONS_PAYLOAD_CONTRACT,
                "public_fields": [
                    "abi_version",
                    "struct_size",
                    "event_kind",
                    "resource_kind",
                    "flags",
                    "field_mask",
                    "bool_values",
                    "int32_values",
                ],
                "required_flags": sorted(stability.EXPECTED_REQUIRED_FLAGS),
            },
            "allowed_signals": [dict(signal) for signal in stability.EXPECTED_ALLOWED_SIGNALS],
            "blocked_public_contract": {
                "standalone_inventory_sdk_allowed": False,
                "standalone_items_sdk_allowed": False,
                "forbidden_terms": sorted(stability.REQUIRED_FORBIDDEN_TERMS),
            },
            "v1_completion_contract": {
                "claim_effect": "does_not_complete_v1_sdk",
                "required_before_stable_sdk_claim": [
                    "release wording stays scoped to the five allowed_signals",
                ],
            },
        }

    def make_public_gameplay_events(self) -> dict:
        return {
            "schema": stability.PUBLIC_GAMEPLAY_EVENTS_SCHEMA,
            "metadata_surfaces": [
                {
                    "surface_id": "obelisk.resource_kind_descriptors.v1",
                    "scope": (
                        "metadata-only resource category descriptors for routing/config; no identity, "
                        "no lookup, no handle, no cross-event correlation, no mutation, and no UE object access"
                    ),
                    "flags": [
                        "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY",
                        "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY",
                        "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP",
                    ],
                    "resource_kinds": [
                        {
                            "kind": stability.RESOURCE_KIND,
                            "stable_name": "inventory_item",
                            "supported_gameplay_policy_event_mask": stability.ALL_INVENTORY_MASK,
                            "supported_gameplay_policy_field_mask": sorted(stability.EXPECTED_SIGNAL_FIELDS),
                        }
                    ],
                },
                {
                    "surface_id": "obelisk.gameplay_policy_event_descriptors.v1",
                    "scope": (
                        "metadata-only descriptors for promoted GameplayPolicyEvent kinds; no identity, "
                        "no lookup, no cross-event correlation, no mutation, no return override, and no UE object access"
                    ),
                    "flags": [
                        "OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD",
                        "OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED",
                        "OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED",
                    ],
                },
            ],
            "promoted_events": [
                {
                    "event_id": stability.GAMEPLAY_POLICY_EVENT,
                    "v1_sdk_status": "promoted-experimental-only",
                    "v1_completion_evidence": False,
                    "resource_contract": "kind-only, no identity, no lookup, no persistent handle, no cross-event correlation",
                    "payload": "copied POD scalar fields only",
                    "inventory_backing_target_set": stability.EXPECTED_INVENTORY_TARGET_SET,
                    "item_return_backing_target_set": stability.EXPECTED_ITEM_RETURN_TARGET_SET,
                    "event_kinds": [
                        {
                            **dict(signal),
                            "resource_kind": stability.RESOURCE_KIND,
                            "required_flags": sorted(stability.EXPECTED_REQUIRED_FLAGS),
                        }
                        for signal in stability.EXPECTED_ALLOWED_SIGNALS
                    ],
                    "target_sets": [
                        "structure-observer-intake",
                        stability.EXPECTED_INVENTORY_TARGET_SET,
                        stability.EXPECTED_ITEM_RETURN_TARGET_SET,
                    ],
                    "target_set_evidence": [
                        {"target_set": "structure-observer-intake"},
                        {
                            "target_set": stability.EXPECTED_INVENTORY_TARGET_SET,
                            "reports": ["docs/research/2026-05-29-minimal-second-source-readiness.md"],
                            "scope": "layout-only compact inventory/structure backing; no standalone module-specific inventory or structure surface",
                        },
                        {
                            "target_set": stability.EXPECTED_ITEM_RETURN_TARGET_SET,
                            "reports": ["docs/research/2026-05-30-item-return-only-policy-slice.md"],
                            "scope": "second-source accepted copied ReturnValue-only item backing for AllowEquipItem, CanRepair, and UseItemOntoItem; no standalone item or inventory module surface, no identity, no lookup, no mutation, no return override, and no ResourceHandle",
                        },
                    ],
                    "excluded_target_sets": [
                        {"target_set": stability.EXCLUDED_INVENTORY_ACTION_TARGET_SET}
                    ],
                }
            ],
        }

    def make_public_sdk_surfaces(self) -> dict:
        return {
            "schema": stability.PUBLIC_SDK_SURFACES_SCHEMA,
            "v1_completion_required": False,
            "stable_release_contract": {"claim_allowed": False},
            "promoted_surfaces": [],
            "experimental_surfaces": [stability.SURFACE],
            "surfaces": [
                {
                    "id": stability.SURFACE,
                    "status": "promoted-experimental-only",
                    "support_tier": "promoted-experimental-only copied-data seed",
                    "public_contract": list(stability.EXPECTED_PUBLIC_CONTRACT),
                    "payload_contract": list(stability.EXPECTED_SURFACE_PAYLOAD_CONTRACT),
                    "evidence": {
                        "release_readiness_target_sets": list(
                            stability.EXPECTED_INVENTORY_RELEASE_READINESS_TARGET_SETS
                        )
                    },
                    "exclusions": sorted(stability.REQUIRED_FORBIDDEN_TERMS),
                },
                {
                    "id": stability.INVENTORY_MUTATION_SURFACE,
                    "status": "post-v1",
                    "public_contract": [],
                },
                {
                    "id": stability.RESOURCE_HANDLE_SURFACE,
                    "status": "post-v1",
                    "public_contract": [],
                },
            ],
        }

    def make_header(self) -> str:
        define_lines = [
            "#define OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS (1ull << 6)",
            "#define OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS (1ull << 8)",
            "#define OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD (1ull << 0)",
            "#define OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED (1ull << 2)",
            "#define OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE (1ull << 0)",
            "#define OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER (1ull << 4)",
            "#define OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN (1ull << 5)",
        ]
        for index, signal in enumerate(stability.EXPECTED_ALLOWED_SIGNALS, start=6):
            define_lines.append(f"#define {signal['event_kind_mask']} (1ull << {index})")
        define_lines.append("#define OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY \\")
        for index, signal in enumerate(stability.EXPECTED_ALLOWED_SIGNALS):
            suffix = " | \\" if index < len(stability.EXPECTED_ALLOWED_SIGNALS) - 1 else ""
            define_lines.append(f"    ({signal['event_kind_mask']}){suffix}")

        enum_values = "\n".join(
            f"    {signal['kind']} = {index},"
            for index, signal in enumerate(stability.EXPECTED_ALLOWED_SIGNALS, start=7)
        )
        return (
            "#pragma once\n"
            "#include <stdint.h>\n"
            + "\n".join(define_lines)
            + "\n"
            "typedef enum ObeliskGameplayPolicyResourceKind {\n"
            "    OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM = 2,\n"
            "} ObeliskGameplayPolicyResourceKind;\n"
            "typedef enum ObeliskGameplayPolicyEventKind {\n"
            f"{enum_values}\n"
            "} ObeliskGameplayPolicyEventKind;\n"
            "typedef struct ObeliskGameplayPolicyEvent { uint32_t event_kind; } ObeliskGameplayPolicyEvent;\n"
            "typedef struct ObeliskGameplayPolicyEventDescriptor { uint32_t event_kind; } ObeliskGameplayPolicyEventDescriptor;\n"
            "typedef void (*ObeliskGameplayPolicyEventCallback)(const ObeliskGameplayPolicyEvent* event, void* user_data);\n"
            "typedef struct ObeliskApi {\n"
            "    uint64_t (*RegisterGameplayPolicyEventWithOwnerTokenHandle)(uint64_t ownerToken, uint64_t eventKindMask, ObeliskGameplayPolicyEventCallback callback, void* userData);\n"
            "    bool (*UnregisterGameplayPolicyEventWithOwnerToken)(uint64_t ownerToken, uint64_t registrationId);\n"
            "    bool (*DescribeGameplayPolicyEventKind)(uint32_t eventKind, ObeliskGameplayPolicyEventDescriptor* out);\n"
            "} ObeliskApi;\n"
        )

    def write_fixture(self, root: Path, fixtures: dict[str, Any]) -> None:
        (root / "inventory_item_copied_signals_public_contract_decisions.json").write_text(
            json.dumps(fixtures["decisions"], indent=2, sort_keys=True),
            encoding="utf-8",
        )
        (root / "public_sdk_surfaces.json").write_text(
            json.dumps(fixtures["public_sdk_surfaces"], indent=2, sort_keys=True),
            encoding="utf-8",
        )
        (root / "public_gameplay_events.json").write_text(
            json.dumps(fixtures["public_gameplay_events"], indent=2, sort_keys=True),
            encoding="utf-8",
        )
        (root / "ObeliskApi.h").write_text(fixtures["header"], encoding="utf-8")

    def make_fixture(self) -> dict[str, Any]:
        return {
            "decisions": self.make_decisions(),
            "public_sdk_surfaces": self.make_public_sdk_surfaces(),
            "public_gameplay_events": self.make_public_gameplay_events(),
            "header": self.make_header(),
        }

    def run_fixture(self, fixtures: dict[str, Any], check: bool = True) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_fixture(root, fixtures)
            return self.run_checker(root, check=check)

    def test_valid_fixture_passes_as_experimental_copied_signal_only(self) -> None:
        result = self.run_fixture(self.make_fixture())
        payload = json.loads(result.stdout)

        self.assertTrue(payload["ready"])
        self.assertEqual(payload["surface"], stability.SURFACE)
        self.assertEqual(payload["summary"]["allowed_signal_count"], 5)
        self.assertFalse(payload["summary"]["public_sdk_ready"])
        self.assertFalse(payload["summary"]["v1_completion_ready"])
        self.assertEqual(payload["blockers"], [])

    def test_extra_inventory_signal_fails_closed_across_manifests_and_header(self) -> None:
        fixtures = self.make_fixture()
        extra = {
            "stable_name": "inventory_item.craft_blueprint_check",
            "kind": "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_CRAFT_BLUEPRINT_CHECK",
            "event_kind_mask": "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_CRAFT_BLUEPRINT_CHECK",
            "field_mask": [stability.RETURN_VALUE],
        }
        fixtures["decisions"]["allowed_signals"].append(extra)
        fixtures["public_gameplay_events"]["promoted_events"][0]["event_kinds"].append(
            {**extra, "resource_kind": stability.RESOURCE_KIND}
        )
        fixtures["header"] += (
            "\n#define OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_CRAFT_BLUEPRINT_CHECK (1ull << 11)\n"
            "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_CRAFT_BLUEPRINT_CHECK\n"
        )

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        reasons = set(payload["blockers"])
        self.assertIn("decisions_allowed_signals_mismatch", reasons)
        self.assertIn("public_gameplay_inventory_event_kinds_mismatch", reasons)
        self.assertIn("public_header_inventory_event_kinds_mismatch", reasons)
        self.assertIn("public_header_inventory_event_masks_mismatch", reasons)

    def test_resource_kind_must_remain_category_only_metadata(self) -> None:
        fixtures = self.make_fixture()
        descriptor = fixtures["public_gameplay_events"]["metadata_surfaces"][0]
        descriptor["flags"] = ["OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP"]
        descriptor["scope"] = "resource descriptors provide identity and lookup"
        fixtures["decisions"]["public_contract"]["resource_contract"] = "identity-capable lookup metadata"

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        reasons = set(payload["blockers"])
        self.assertIn("decisions_resource_contract_guardrail_missing", reasons)
        self.assertIn("resource_descriptor_scope_guardrail_missing", reasons)
        self.assertIn("resource_descriptor_category_only_flags_missing", reasons)

    def test_required_copied_inventory_flags_must_stay_declared(self) -> None:
        fixtures = self.make_fixture()
        fixtures["decisions"]["public_contract"]["required_flags"] = [
            "OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD"
        ]

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        reasons = set(payload["blockers"])
        self.assertIn("decisions_required_flags_mismatch", reasons)

    def test_gameplay_event_descriptor_must_keep_inventory_flags(self) -> None:
        fixtures = self.make_fixture()
        descriptor = fixtures["public_gameplay_events"]["metadata_surfaces"][1]
        descriptor["flags"].remove("OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED")

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        reasons = set(payload["blockers"])
        self.assertIn("gameplay_policy_event_descriptor_required_flags_missing", reasons)

    def test_inventory_event_required_flags_must_match_public_manifest(self) -> None:
        fixtures = self.make_fixture()
        event = fixtures["public_gameplay_events"]["promoted_events"][0]["event_kinds"][0]
        event["required_flags"] = ["OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD"]

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        reasons = set(payload["blockers"])
        self.assertIn("public_gameplay_inventory_required_flags_mismatch", reasons)

    def test_inventory_event_required_flags_must_not_be_replaced_by_flags_alias(self) -> None:
        fixtures = self.make_fixture()
        event = fixtures["public_gameplay_events"]["promoted_events"][0]["event_kinds"][0]
        expected_flags = list(event["required_flags"])
        del event["required_flags"]
        event["flags"] = expected_flags

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        reasons = set(payload["blockers"])
        self.assertIn("public_gameplay_inventory_required_flags_mismatch", reasons)

    def test_inventory_target_set_provenance_must_stay_pinned(self) -> None:
        fixtures = self.make_fixture()
        event = fixtures["public_gameplay_events"]["promoted_events"][0]
        event["inventory_backing_target_set"] = "inventory-action-compact-intake"
        event["item_return_backing_target_set"] = "inventory-action-compact-intake"
        event["target_sets"] = ["structure-observer-intake", "inventory-action-compact-intake"]
        event["target_set_evidence"] = [{"target_set": "structure-observer-intake"}]
        event["excluded_target_sets"] = []

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        reasons = set(payload["blockers"])
        self.assertIn("inventory_backing_target_set_mismatch", reasons)
        self.assertIn("item_return_backing_target_set_mismatch", reasons)
        self.assertIn("gameplay_policy_inventory_target_sets_missing", reasons)
        self.assertIn("gameplay_policy_inventory_target_set_evidence_missing", reasons)
        self.assertIn("gameplay_policy_inventory_action_target_set_not_excluded", reasons)

    def test_public_sdk_surface_release_readiness_target_sets_must_stay_pinned(self) -> None:
        fixtures = self.make_fixture()
        surface = fixtures["public_sdk_surfaces"]["surfaces"][0]
        surface["evidence"]["release_readiness_target_sets"] = ["inventory-action-compact-intake"]

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        reasons = set(payload["blockers"])
        self.assertIn("inventory_copied_release_readiness_target_sets_mismatch", reasons)

    def test_inventory_target_set_evidence_accounting_scope_and_reports_must_stay_pinned(self) -> None:
        fixtures = self.make_fixture()
        event = fixtures["public_gameplay_events"]["promoted_events"][0]
        evidence_by_target = {item["target_set"]: item for item in event["target_set_evidence"]}
        evidence_by_target[stability.EXPECTED_INVENTORY_TARGET_SET]["scope"] = "Inventory SDK ready"
        evidence_by_target[stability.EXPECTED_INVENTORY_TARGET_SET]["reports"] = []
        evidence_by_target[stability.EXPECTED_ITEM_RETURN_TARGET_SET]["scope"] = "ReturnValue-only item backing"
        evidence_by_target[stability.EXPECTED_ITEM_RETURN_TARGET_SET]["reports"] = ["/servidor/ark/live.log"]

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        reasons = set(payload["blockers"])
        self.assertIn("gameplay_policy_inventory_target_set_evidence_scope_guardrail_missing", reasons)
        self.assertIn("gameplay_policy_inventory_target_set_evidence_reports_missing", reasons)
        self.assertIn("gameplay_policy_inventory_target_set_evidence_report_live_path", reasons)

    def test_non_copied_payload_contract_wording_is_rejected(self) -> None:
        fixtures = self.make_fixture()
        fixtures["decisions"]["public_contract"]["payload_contract"] = "non-copied POD scalar observation only"
        fixtures["public_sdk_surfaces"]["surfaces"][0]["payload_contract"][0] = (
            "non-copied bool ReturnValue signals only where declared by docs/public_gameplay_events.json"
        )

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        reasons = set(payload["blockers"])
        self.assertIn("payload_contract_mismatch", reasons)
        self.assertIn("inventory_copied_payload_contract_mismatch", reasons)

    def test_public_inventory_items_sdk_and_authority_claims_are_rejected(self) -> None:
        fixtures = self.make_fixture()
        surface = fixtures["public_sdk_surfaces"]["surfaces"][0]
        surface["public_contract"].append(
            "Inventory SDK exposes lookup mutation ResourceHandle AdditionalData API"
        )
        fixtures["public_gameplay_events"]["promoted_events"][0]["resource_contract"] = (
            "kind metadata provides ResourceHandle lookup"
        )

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        reasons = set(payload["blockers"])
        self.assertIn("inventory_copied_surface_public_contract_mismatch", reasons)
        self.assertIn("public_claim_forbidden_term", reasons)
        self.assertIn("gameplay_policy_resource_contract_guardrail_missing", reasons)

    def test_mixed_negation_does_not_hide_public_inventory_sdk_claim(self) -> None:
        fixtures = self.make_fixture()
        surface = fixtures["public_sdk_surfaces"]["surfaces"][0]
        surface["public_contract"].append("Inventory SDK ready; not mutation")

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        reasons = set(payload["blockers"])
        self.assertIn("public_claim_forbidden_term", reasons)

    def test_mixed_negation_does_not_hide_public_items_sdk_claim(self) -> None:
        fixtures = self.make_fixture()
        surface = fixtures["public_sdk_surfaces"]["surfaces"][0]
        surface["public_contract"].append("without ResourceHandle, Items SDK ready")

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        reasons = set(payload["blockers"])
        self.assertIn("public_claim_forbidden_term", reasons)

    def test_top_level_public_sdk_surfaces_inventory_side_lane_claim_is_rejected(self) -> None:
        fixtures = self.make_fixture()
        fixtures["public_sdk_surfaces"]["release_note"] = (
            "Inventory SDK ready through inventory_item_copied_signals side lane."
        )

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        reasons = set(payload["blockers"])
        self.assertIn("public_sdk_surfaces_positive_inventory_side_lane_claim", reasons)
        detail = next(
            blocker
            for blocker in payload["blocker_details"]
            if blocker["reason"] == "public_sdk_surfaces_positive_inventory_side_lane_claim"
        )
        self.assertEqual("$.public_sdk_surfaces.release_note", detail["path"])
        self.assertEqual("Inventory SDK", detail["term"])

    def test_source_marker_inventory_sdk_side_lane_claim_is_rejected(self) -> None:
        fixtures = self.make_fixture()
        event = fixtures["public_gameplay_events"]["promoted_events"][0]
        event["source_marker"] = "Inventory-SDK ready from copied signal side lane"

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        reasons = set(payload["blockers"])
        self.assertIn("public_claim_forbidden_term", reasons)
        self.assertIn("readiness_claim_enabled", reasons)
        paths = {
            blocker["path"]
            for blocker in payload["blocker_details"]
            if blocker["reason"] in {"public_claim_forbidden_term", "readiness_claim_enabled"}
        }
        self.assertEqual({"$.public_gameplay_events.promoted_events[0].source_marker"}, paths)

    def test_source_marker_resource_handle_promotion_claim_is_rejected(self) -> None:
        fixtures = self.make_fixture()
        surface = fixtures["public_sdk_surfaces"]["surfaces"][0]
        surface["source_marker"] = (
            "ResourceHandle promotion ready through minimal-second-source-intake"
        )

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        reasons = set(payload["blockers"])
        self.assertIn("public_claim_forbidden_term", reasons)
        self.assertIn("readiness_claim_enabled", reasons)
        paths = {
            blocker["path"]
            for blocker in payload["blocker_details"]
            if blocker["reason"] in {"public_claim_forbidden_term", "readiness_claim_enabled"}
        }
        self.assertEqual(
            {
                "$.public_sdk_surfaces.obelisk.inventory_item_copied_signals.v1.source_marker",
                "$.public_sdk_surfaces.surfaces[0].source_marker",
            },
            paths,
        )

    def test_alias_runtime_and_v1_completion_claims_are_rejected(self) -> None:
        fixtures = self.make_fixture()
        event = fixtures["public_gameplay_events"]["promoted_events"][0]
        event["aliases"] = [
            "copied signal runtime readiness",
            "inventory side lane v1 completion",
        ]

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        paths = {
            blocker["path"]
            for blocker in payload["blocker_details"]
            if blocker["reason"] == "readiness_claim_enabled"
        }
        self.assertEqual(
            {
                "$.public_gameplay_events.promoted_events[0].aliases[0]",
                "$.public_gameplay_events.promoted_events[0].aliases[1]",
            },
            paths,
        )

    def test_report_section_return_override_public_readiness_claim_is_rejected(self) -> None:
        fixtures = self.make_fixture()
        event = fixtures["public_gameplay_events"]["promoted_events"][0]
        event["report_sections"] = [
            "inventory copied side lane has return override public readiness"
        ]

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        reasons = set(payload["blockers"])
        self.assertIn("public_claim_forbidden_term", reasons)
        self.assertIn("readiness_claim_enabled", reasons)
        paths = {
            blocker["path"]
            for blocker in payload["blocker_details"]
            if blocker["reason"] in {"public_claim_forbidden_term", "readiness_claim_enabled"}
        }
        self.assertEqual(
            {"$.public_gameplay_events.promoted_events[0].report_sections[0]"},
            paths,
        )

    def test_negated_public_sdk_surfaces_inventory_side_lane_text_is_allowed(self) -> None:
        fixtures = self.make_fixture()
        fixtures["public_sdk_surfaces"]["release_note"] = (
            "inventory_item_copied_signals remains a copied signal side lane only; "
            "no Inventory SDK or Items SDK readiness."
        )

        result = self.run_fixture(fixtures)
        payload = json.loads(result.stdout)

        self.assertTrue(payload["ready"])
        self.assertEqual(payload["blockers"], [])

    def test_positive_return_override_claim_is_rejected(self) -> None:
        fixtures = self.make_fixture()
        fixtures["decisions"]["public_contract"]["payload_contract"] = (
            "GameplayPolicyEvent includes copied scalars and return override support"
        )

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        reasons = set(payload["blockers"])
        self.assertIn("public_claim_forbidden_term", reasons)
        detail = next(
            blocker
            for blocker in payload["blocker_details"]
            if blocker["reason"] == "public_claim_forbidden_term"
        )
        self.assertEqual("return override", detail["term"])

    def test_positive_raw_inventory_identity_claims_are_rejected(self) -> None:
        fixtures = self.make_fixture()
        fixtures["public_gameplay_events"]["promoted_events"][0]["resource_contract"] = (
            "kind metadata provides ItemId identity and InventoryComp support"
        )

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        terms = {
            blocker["term"]
            for blocker in payload["blocker_details"]
            if blocker["reason"] == "public_claim_forbidden_term"
        }
        self.assertIn("ItemId", terms)
        self.assertIn("InventoryComp", terms)

    def test_nested_review_notes_cannot_leak_raw_param_identity_claims(self) -> None:
        fixtures = self.make_fixture()
        event = fixtures["public_gameplay_events"]["promoted_events"][0]
        event["target_set_evidence"][1]["review_notes"] = [
            "ItemID1 identity is ready for copied inventory signals",
            {
                "summary": (
                    "InventoryComp and raw params can be used for public inventory lookup"
                )
            },
        ]

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        terms = {
            blocker["term"]
            for blocker in payload["blocker_details"]
            if blocker["reason"] == "public_claim_forbidden_term"
        }
        self.assertIn("ItemID1", terms)
        self.assertIn("InventoryComp", terms)
        self.assertIn("raw params", terms)
        self.assertIn("lookup", terms)

    def test_negated_nested_review_notes_remain_allowed(self) -> None:
        fixtures = self.make_fixture()
        event = fixtures["public_gameplay_events"]["promoted_events"][0]
        event["target_set_evidence"][1]["review_notes"] = [
            (
                "No ItemID1 identity, no InventoryComp, no raw params, no lookup, "
                "no mutation, and no ResourceHandle are promoted."
            )
        ]

        result = self.run_fixture(fixtures)
        payload = json.loads(result.stdout)

        self.assertTrue(payload["ready"])
        self.assertEqual(payload["blockers"], [])

    def test_negative_guardrail_containers_cannot_hide_positive_readiness_claims(self) -> None:
        fixtures = self.make_fixture()
        event = fixtures["public_gameplay_events"]["promoted_events"][0]
        event["non_claims"] = [
            "Inventory SDK ready from copied signals",
            "ResourceHandle promotion ready through item return signals",
        ]

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        reasons = set(payload["blockers"])
        self.assertIn("public_claim_forbidden_term", reasons)
        self.assertIn("readiness_claim_enabled", reasons)
        paths = {
            blocker["path"]
            for blocker in payload["blocker_details"]
            if blocker["reason"] in {"public_claim_forbidden_term", "readiness_claim_enabled"}
        }
        self.assertEqual(
            {
                "$.public_gameplay_events.promoted_events[0].non_claims[0]",
                "$.public_gameplay_events.promoted_events[0].non_claims[1]",
            },
            paths,
        )

    def test_negative_guardrail_containers_still_allow_bare_excluded_terms(self) -> None:
        fixtures = self.make_fixture()
        event = fixtures["public_gameplay_events"]["promoted_events"][0]
        event["non_claims"] = [
            "Inventory SDK",
            "Items SDK",
            "ResourceHandle",
            "return override",
            "no Inventory SDK or Items SDK readiness",
        ]

        result = self.run_fixture(fixtures)
        payload = json.loads(result.stdout)

        self.assertTrue(payload["ready"])
        self.assertEqual(payload["blockers"], [])

    def test_public_sdk_and_v1_readiness_cannot_be_activated_by_this_surface(self) -> None:
        fixtures = self.make_fixture()
        surfaces = fixtures["public_sdk_surfaces"]
        surfaces["v1_completion_required"] = True
        surfaces["stable_release_contract"]["claim_allowed"] = True
        surfaces["promoted_surfaces"] = [stability.SURFACE]
        surface = surfaces["surfaces"][0]
        surface["status"] = "promoted"
        surface["public_sdk_ready"] = True
        fixtures["public_gameplay_events"]["promoted_events"][0]["v1_completion_evidence"] = True

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        reasons = set(payload["blockers"])
        self.assertIn("v1_completion_required_not_false", reasons)
        self.assertIn("claim_allowed_not_false", reasons)
        self.assertIn("inventory_copied_surface_in_promoted_surfaces", reasons)
        self.assertIn("status_mismatch", reasons)
        self.assertIn("readiness_claim_enabled", reasons)
        self.assertIn("v1_completion_evidence_not_false", reasons)

    def test_public_gameplay_events_runtime_or_v1_readiness_claims_are_rejected(self) -> None:
        fixtures = self.make_fixture()
        event = fixtures["public_gameplay_events"]["promoted_events"][0]
        event["runtime_ready"] = True
        event["v1_ready"] = True
        event["runtime_readiness"] = "inventory/item copied signals runtime ready; v1 completion ready"

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        reasons = set(payload["blockers"])
        self.assertIn("readiness_claim_enabled", reasons)
        paths = {
            blocker["path"]
            for blocker in payload["blocker_details"]
            if blocker["reason"] == "readiness_claim_enabled"
        }
        self.assertIn("$.public_gameplay_events.promoted_events[0].runtime_ready", paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].v1_ready", paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].runtime_readiness", paths)

    def test_public_gameplay_events_generic_readiness_aliases_are_rejected(self) -> None:
        fixtures = self.make_fixture()
        event = fixtures["public_gameplay_events"]["promoted_events"][0]
        event["v1_sdk_ready"] = True
        event["release_ready"] = True
        event["public_abi_ready"] = True

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        paths = {
            blocker["path"]
            for blocker in payload["blocker_details"]
            if blocker["reason"] == "readiness_claim_enabled"
        }
        self.assertIn("$.public_gameplay_events.promoted_events[0].v1_sdk_ready", paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].release_ready", paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].public_abi_ready", paths)


if __name__ == "__main__":
    unittest.main()
