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
            "promoted_experimental_outcome": stability.expected_promoted_experimental_outcome(
                stability.SURFACE
            ),
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
            "promoted_experimental_surface_outcomes": [
                stability.expected_promoted_experimental_outcome(surface_id)
                for surface_id in stability.PROMOTED_EXPERIMENTAL_SURFACE_IDS
            ],
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
                    ],
                    "target_set_evidence": [
                        {"target_set": "structure-observer-intake"},
                        {
                            "target_set": stability.EXPECTED_INVENTORY_TARGET_SET,
                            "reports": ["docs/research/2026-05-29-minimal-second-source-readiness.md"],
                            "scope": "layout-only compact inventory/structure backing; no standalone module-specific inventory or structure surface",
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

    def run_checker_with_paths(
        self,
        *,
        decisions: Path,
        public_sdk_surfaces: Path,
        public_gameplay_events: Path,
        public_header: Path,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--decisions",
                str(decisions),
                "--public-sdk-surfaces",
                str(public_sdk_surfaces),
                "--public-gameplay-events",
                str(public_gameplay_events),
                "--public-header",
                str(public_header),
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

    def test_valid_fixture_passes_as_experimental_copied_signal_only(self) -> None:
        result = self.run_fixture(self.make_fixture())
        payload = json.loads(result.stdout)

        self.assertTrue(payload["ready"])
        self.assertEqual("approved_runtime_evidence_missing", payload["current_route_blocker"])
        self.assertEqual(["approved_runtime_evidence_missing"], payload["remaining_route_blockers"])
        self.assertEqual(
            stability.REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
            payload["required_runtime_evidence"],
        )
        self.assertFalse(
            payload["multi_surface_beta_capture_guardrail"][
                "counts_as_approved_runtime_evidence"
            ]
        )
        self.assertFalse(
            payload["multi_surface_beta_capture_guardrail"][
                "clears_approved_runtime_evidence_missing"
            ]
        )
        self.assertFalse(
            payload["multi_surface_beta_capture_guardrail"][
                "replaces_player_principal_evidence"
            ]
        )
        self.assertFalse(payload["multi_surface_beta_capture_guardrail"]["sdk_p0_unlock_allowed"])
        self.assertFalse(payload["multi_surface_beta_capture_guardrail"]["side_lane_counts_toward_sdk"])
        self.assertFalse(payload["multi_surface_beta_capture_guardrail"]["side_lane_counts_toward_p0"])
        self.assertFalse(payload["sdk_p0_unlock_allowed"])
        self.assertFalse(payload["side_lane_counts_toward_sdk"])
        self.assertFalse(payload["side_lane_counts_toward_p0"])
        self.assertEqual(stability.NON_AUTHORIZING_READY_SCOPE, payload["ready_scope"])
        self.assertTrue(
            set(stability.NON_AUTHORIZING_READY_DOES_NOT_SATISFY)
            <= set(payload["does_not_satisfy_readiness"])
        )
        self.assertEqual(payload["surface"], stability.SURFACE)
        self.assertEqual(payload["summary"]["allowed_signal_count"], 5)
        self.assertEqual(stability.NON_AUTHORIZING_READY_SCOPE, payload["summary"]["ready_scope"])
        self.assertTrue(
            set(stability.NON_AUTHORIZING_READY_DOES_NOT_SATISFY)
            <= set(payload["summary"]["does_not_satisfy_readiness"])
        )
        self.assertFalse(payload["summary"]["public_sdk_ready"])
        self.assertFalse(payload["summary"]["v1_completion_ready"])
        self.assertEqual(payload["blockers"], [])
        self.assertEqual(
            "non_authorizing_guardrail_passed_only",
            payload["readiness_report"]["ready_field_semantics"],
        )
        self.assertTrue(payload["readiness_report"]["input_guardrails_passed"])
        self.assertFalse(payload["readiness_report"]["public_inventory_sdk_claim_allowed"])
        self.assertFalse(payload["readiness_report"]["v1_completion_claim_allowed"])
        self.assertEqual(0, payload["readiness_report"]["v1_progress_contribution"])
        self.assertEqual(
            "public_inventory_items_mutation_contract_not_in_scope",
            payload["next_blockers"]["offline"]["id"],
        )
        self.assertFalse(
            payload["next_blockers"]["offline"]["blocked_for_current_copied_signal_guardrail"]
        )
        self.assertTrue(payload["next_blockers"]["offline"]["blocked_for_public_inventory_sdk"])
        self.assertEqual(
            "object_identity_resource_handle_runtime_evidence_missing",
            payload["next_blockers"]["runtime"]["id"],
        )
        self.assertEqual(
            "approved_runtime_evidence_missing",
            payload["next_blockers"]["player_principal_runtime"]["id"],
        )
        self.assertEqual(
            stability.REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
            payload["next_blockers"]["player_principal_runtime"]["required_artifact"],
        )
        self.assertFalse(
            payload["next_blockers"]["player_principal_runtime"][
                "candidate_beta_capture_plan_counts_as_runtime_evidence"
            ]
        )
        self.assertIn("runtime object negative samples", payload["next_blockers"]["runtime"]["required_future_evidence"])
        self.assertIn("Inventory SDK", payload["next_blockers"]["runtime"]["blocked_claims"])
        self.assertEqual(
            payload["readiness_report"],
            payload["summary"]["readiness_report"],
        )
        self.assertEqual(
            payload["next_blockers"],
            payload["summary"]["next_blockers"],
        )
        outcome_gate = payload["promoted_experimental_outcome_gate"]
        self.assertEqual(
            list(stability.PROMOTED_EXPERIMENTAL_SURFACE_IDS),
            outcome_gate["unresolved_surfaces"],
        )
        self.assertEqual(
            stability.PROMOTED_EXPERIMENTAL_COMPLETE_SDK_ACCOUNTING,
            outcome_gate["complete_sdk_accounting"],
        )
        self.assertFalse(outcome_gate["counts_toward_complete_sdk_claim"])
        self.assertFalse(outcome_gate["counts_toward_p0_dependency_chain_claim"])
        self.assertEqual(0, outcome_gate["complete_sdk_claim_progress_contribution"])
        self.assertEqual(0, outcome_gate["p0_dependency_chain_claim_progress_contribution"])
        self.assertFalse(outcome_gate["public_sdk_ready"])
        self.assertFalse(outcome_gate["runtime_ready"])
        self.assertFalse(outcome_gate["stable_claim_allowed"])
        self.assertFalse(outcome_gate["v1_completion_ready"])
        self.assertEqual(
            outcome_gate,
            payload["summary"]["promoted_experimental_outcome_gate"],
        )
        self.assertEqual(
            list(stability.PROMOTED_EXPERIMENTAL_SURFACE_IDS),
            payload["checks"]["public_gameplay_events"]["promoted_experimental_outcomes"],
        )

    def test_accepted_report_emits_non_counting_latch_for_sdk_runtime_v1_and_p0(self) -> None:
        result = self.run_fixture(self.make_fixture())
        payload = json.loads(result.stdout)

        expected_non_counting = {
            "counts_toward_complete_sdk_claim": False,
            "counts_toward_p0_dependency_chain_claim": False,
            "complete_sdk_claim_progress_contribution": 0,
            "p0_dependency_chain_claim_progress_contribution": 0,
            "promotion_ready": False,
            "runtime_ready": False,
            "runtime_capture_ready": False,
            "live_ops_ready": False,
            "public_sdk_ready": False,
            "public_module_ready": False,
            "stable_claim_allowed": False,
            "v1_completion_ready": False,
        }
        self.assertTrue(payload["ready"])
        self.assertTrue(payload["accepted_for_internal_planning"])
        self.assertTrue(payload["offline_only"])
        self.assertTrue(payload["candidate_only"])
        self.assertTrue(payload["not_artifact_gate"])
        self.assertTrue(payload["summary"]["accepted_for_internal_planning"])
        self.assertTrue(payload["summary"]["offline_only"])
        self.assertTrue(payload["summary"]["candidate_only"])
        self.assertTrue(payload["summary"]["not_artifact_gate"])
        for key, expected in expected_non_counting.items():
            self.assertEqual(payload[key], expected, key)
            self.assertEqual(payload["summary"][key], expected, key)

    def test_promoted_experimental_outcome_records_are_required(self) -> None:
        fixtures = self.make_fixture()
        del fixtures["decisions"]["promoted_experimental_outcome"]
        fixtures["public_gameplay_events"]["promoted_experimental_surface_outcomes"] = [
            record
            for record in fixtures["public_gameplay_events"]["promoted_experimental_surface_outcomes"]
            if record["surface_id"] != "obelisk.chat.local_routing.v1"
        ]

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(1, result.returncode)
        reasons = set(payload["blockers"])
        self.assertIn("decisions_promoted_experimental_outcome_missing", reasons)
        self.assertIn("public_gameplay_promoted_experimental_outcome_missing", reasons)
        self.assertFalse(payload["promoted_experimental_outcome_gate"]["public_sdk_ready"])
        self.assertFalse(payload["promoted_experimental_outcome_gate"]["v1_completion_ready"])

    def test_promoted_experimental_outcome_latches_fail_closed(self) -> None:
        fixtures = self.make_fixture()
        decisions_outcome = fixtures["decisions"]["promoted_experimental_outcome"]
        decisions_outcome["counts_toward_complete_sdk_claim"] = True
        decisions_outcome["complete_sdk_claim_progress_contribution"] = 1
        gameplay_outcome = next(
            record
            for record in fixtures["public_gameplay_events"]["promoted_experimental_surface_outcomes"]
            if record["surface_id"] == "obelisk.chat_message.v1"
        )
        gameplay_outcome["v1_completion_ready"] = True
        gameplay_outcome["allowed_resolutions"] = ["promote_with_surface_specific_evidence"]
        gameplay_outcome["must_not_unlock"] = ["lookup", "mutation", "return override", "ResourceHandle"]

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(1, result.returncode)
        reasons = set(payload["blockers"])
        self.assertIn("counts_toward_complete_sdk_claim_not_false", reasons)
        self.assertIn("complete_sdk_claim_progress_contribution_not_zero", reasons)
        self.assertIn("v1_completion_ready_not_false", reasons)
        self.assertIn("public_gameplay_promoted_experimental_outcome_allowed_resolutions_mismatch", reasons)
        self.assertIn("public_gameplay_promoted_experimental_outcome_must_not_unlock_missing", reasons)
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["stable_claim_allowed"])
        self.assertEqual(0, payload["complete_sdk_claim_progress_contribution"])

    def test_clean_candidate_only_ready_preserves_experimental_status_without_source_overclaim(self) -> None:
        fixtures = self.make_fixture()
        event = fixtures["public_gameplay_events"]["promoted_events"][0]
        event["candidate_metadata"] = {
            "artifact_status": "candidate-only",
            "source_label": "candidate-only",
            "source_marker": "candidate-only",
            "source_snapshot_sha256": "0" * 64,
            "accepted_for_internal_planning": True,
        }

        result = self.run_fixture(fixtures)
        payload = json.loads(result.stdout)

        self.assertTrue(payload["ready"])
        self.assertTrue(payload["candidate_only"])
        self.assertEqual("promoted-experimental-only", payload["checks"]["decisions"]["status"])
        self.assertEqual(
            "promoted-experimental-only",
            payload["checks"]["public_sdk_surfaces"]["inventory_copied_status"],
        )
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["v1_completion_ready"])
        self.assertEqual([], payload["blockers"])

    def test_candidate_debug_capture_bundle_is_allowed_when_candidate_only_and_non_counting(self) -> None:
        fixtures = self.make_fixture()
        event = fixtures["public_gameplay_events"]["promoted_events"][0]
        event["beta_capture_bundle"] = {
            "schema": "obelisk.beta-capture-bundle.v1",
            "status": "candidate-only",
            "candidate_only": True,
            "candidateOnly": True,
            "debug_capture_candidate_only": True,
            "offline_only": True,
            "consume_only": True,
            "not_artifact_gate": True,
            "non_counting": True,
            "debug_capture_non_counting": True,
            "counts_toward_complete_sdk_claim": False,
            "counts_toward_p0_dependency_chain_claim": False,
            "complete_sdk_claim_progress_contribution": 0,
            "p0_dependency_chain_claim_progress_contribution": 0,
            "runtime_capture_ready": False,
            "public_sdk_ready": False,
            "public_module_ready": False,
            "mutation_ready": False,
            "return_override_ready": False,
            "resource_handle_ready": False,
            "surfaces": [
                stability.SURFACE,
                "obelisk.transfer_scriptstruct_candidates.v1",
            ],
            "review_notes": [
                "candidate-only non-counting debug capture bundle for offline beta evidence review"
            ],
        }

        result = self.run_fixture(fixtures)
        payload = json.loads(result.stdout)

        self.assertTrue(payload["ready"])
        self.assertTrue(payload["candidate_only"])
        self.assertFalse(payload["runtime_capture_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertEqual(0, payload["complete_sdk_claim_progress_contribution"])
        self.assertEqual(0, payload["p0_dependency_chain_claim_progress_contribution"])
        self.assertEqual([], payload["blockers"])

    def test_multi_surface_beta_capture_plan_is_candidate_prep_only(self) -> None:
        fixtures = self.make_fixture()
        event = fixtures["public_gameplay_events"]["promoted_events"][0]
        non_claim_flags = {
            "candidate_only": True,
            "touches_live_servers": False,
            "authorizes_server_restart": False,
            "authorizes_marker_or_env_changes": False,
            "authorizes_discord_send": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_progress": False,
            "counts_as_p0_progress": False,
            "clears_approved_runtime_evidence_missing": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "stable_sdk_ready": False,
            "plugin_hub_ready": False,
            "publication_ready": False,
        }
        event["multi_surface_beta_capture_plan"] = {
            "schema": "obelisk.multi-surface-beta-capture-plan.v1",
            "status": "candidate_capture_plan",
            "target": {"instance": "arkserver", "map": "TheIsland"},
            "server_policy": {
                "keep_servers_running_when_practical": True,
                "max_ark_servers_running": 2,
                "restart_only_for_obelisk_update_or_gate_change": True,
                "broadcast_before_restart_if_players_connected": True,
                "keep_transfer_server_when_practical": True,
            },
            "required_primary_evidence": {
                "surface": "player_principal_lifecycle",
                "strict_triplet": "HandleNewPlayer(1,1) -> CheckJoinInProgress(1,0) -> matched OnLogout",
                "must_be_checker_accepted": True,
            },
            "capture_surfaces": [
                {
                    "id": "inventory_item_copied_signals",
                    "checker": "scripts/check_inventory_item_copied_signals_stability.py",
                    "objective": "inventory/item copied-signal candidates only",
                    "operator_action": "open inventory and move benign test items without mutation API claims",
                    "priority": 8,
                    "candidate_capture_only": True,
                    "requires_checker_acceptance": True,
                    "replaces_player_principal_triplet": False,
                    "non_claim_flags": dict(non_claim_flags),
                }
            ],
            "non_claim_flags": non_claim_flags,
        }

        result = self.run_fixture(fixtures)
        payload = json.loads(result.stdout)

        self.assertTrue(payload["ready"])
        self.assertEqual([], payload["blockers"])
        self.assertEqual("approved_runtime_evidence_missing", payload["current_route_blocker"])
        self.assertFalse(payload["multi_surface_beta_capture_guardrail"]["public_sdk_ready"])
        self.assertFalse(
            payload["multi_surface_beta_capture_guardrail"][
                "counts_as_approved_runtime_evidence"
            ]
        )

    def test_multi_surface_beta_capture_pack_overclaims_fail_closed(self) -> None:
        fixtures = self.make_fixture()
        event = fixtures["public_gameplay_events"]["promoted_events"][0]
        event["multi_surface_beta_capture_plan_queue"] = {
            "schema": "obelisk.multi-surface-beta-capture-plan-queue.v1",
            "ready_scope": "multi_surface_beta_capture_plan_queue",
            "status": "ready",
            "queueStatus": "ready",
            "approvedRuntimeEvidenceMissingCleared": True,
            "approvedRuntimeEvidenceReady": True,
            "clearsApprovedRuntimeEvidenceMissing": True,
            "evidenceBundleAccepted": True,
            "publicSdkReady": True,
            "runtimeReady": True,
            "sdkAccountingCountsAsCompletedSurface": True,
            "p0AccountingCountsAsPromotedSurface": True,
            "completeSdkClaimProgressContribution": "1/12",
            "p0DependencyChainClaimProgressRatio": "1/4",
            "replacement_claim": "multi-surface beta capture replaces player-principal lifecycle evidence",
            "candidate_surfaces": [
                {
                    "surface": "inventory_item_copied_signals",
                    "captureReady": True,
                    "countsTowardSdk": True,
                }
            ],
        }

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        self.assertIn("readiness_claim_enabled", set(payload["blockers"]))
        paths = {
            blocker["path"]
            for blocker in payload["blocker_details"]
            if blocker["reason"] == "readiness_claim_enabled"
        }
        prefix = "$.public_gameplay_events.promoted_events[0].multi_surface_beta_capture_plan_queue"
        self.assertIn(f"{prefix}.status", paths)
        self.assertIn(f"{prefix}.queueStatus", paths)
        self.assertIn(f"{prefix}.approvedRuntimeEvidenceMissingCleared", paths)
        self.assertIn(f"{prefix}.approvedRuntimeEvidenceReady", paths)
        self.assertIn(f"{prefix}.clearsApprovedRuntimeEvidenceMissing", paths)
        self.assertIn(f"{prefix}.evidenceBundleAccepted", paths)
        self.assertIn(f"{prefix}.publicSdkReady", paths)
        self.assertIn(f"{prefix}.runtimeReady", paths)
        self.assertIn(f"{prefix}.sdkAccountingCountsAsCompletedSurface", paths)
        self.assertIn(f"{prefix}.p0AccountingCountsAsPromotedSurface", paths)
        self.assertIn(f"{prefix}.completeSdkClaimProgressContribution", paths)
        self.assertIn(f"{prefix}.p0DependencyChainClaimProgressRatio", paths)
        self.assertIn(f"{prefix}.candidate_surfaces[0].captureReady", paths)
        self.assertIn(f"{prefix}.candidate_surfaces[0].countsTowardSdk", paths)
        public_terms = {
            blocker.get("term")
            for blocker in payload["blocker_details"]
            if blocker["reason"] == "public_claim_forbidden_term"
        }
        self.assertIn("player-principal lifecycle evidence", public_terms)
        self.assertFalse(payload["counts_as_approved_runtime_evidence"])
        self.assertEqual("approved_runtime_evidence_missing", payload["current_route_blocker"])

    def test_candidate_debug_capture_bundle_overclaims_fail_closed(self) -> None:
        fixtures = self.make_fixture()
        event = fixtures["public_gameplay_events"]["promoted_events"][0]
        event["beta_capture_bundle"] = {
            "status": "candidate-only",
            "candidate_only": True,
            "offline_only": True,
            "consume_only": True,
            "non_counting": True,
            "runtime_capture_ready": True,
            "publicSdkReady": True,
            "mutation_ready": True,
            "return_override_ready": True,
            "resource_handle_ready": True,
            "counts_toward_complete_sdk_claim": True,
            "counts_toward_p0_dependency_chain_claim": True,
            "complete_sdk_claim_progress_contribution": 1,
            "p0_dependency_chain_claim_progress_contribution": 1,
            "review_notes": [
                "ResourceHandle ready for public SDK callbacks",
                "return override support is ready for copied inventory signals",
            ],
        }

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(1, result.returncode)
        reasons = set(payload["blockers"])
        self.assertIn("readiness_claim_enabled", reasons)
        self.assertIn("public_claim_forbidden_term", reasons)
        readiness_paths = {
            blocker["path"]
            for blocker in payload["blocker_details"]
            if blocker["reason"] == "readiness_claim_enabled"
        }
        prefix = "$.public_gameplay_events.promoted_events[0].beta_capture_bundle"
        self.assertIn(f"{prefix}.runtime_capture_ready", readiness_paths)
        self.assertIn(f"{prefix}.publicSdkReady", readiness_paths)
        self.assertIn(f"{prefix}.mutation_ready", readiness_paths)
        self.assertIn(f"{prefix}.return_override_ready", readiness_paths)
        self.assertIn(f"{prefix}.resource_handle_ready", readiness_paths)
        self.assertIn(f"{prefix}.counts_toward_complete_sdk_claim", readiness_paths)
        self.assertIn(f"{prefix}.counts_toward_p0_dependency_chain_claim", readiness_paths)
        self.assertIn(f"{prefix}.complete_sdk_claim_progress_contribution", readiness_paths)
        self.assertIn(f"{prefix}.p0_dependency_chain_claim_progress_contribution", readiness_paths)
        public_terms = {
            blocker.get("term")
            for blocker in payload["blocker_details"]
            if blocker["reason"] == "public_claim_forbidden_term"
        }
        self.assertIn("ResourceHandle", public_terms)
        self.assertIn("public SDK", public_terms)
        self.assertIn("return override", public_terms)
        self.assertFalse(payload["runtime_capture_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertEqual(0, payload["complete_sdk_claim_progress_contribution"])

    def test_p0_and_complete_sdk_progress_accounting_claims_are_rejected(self) -> None:
        fixtures = self.make_fixture()
        event = fixtures["public_gameplay_events"]["promoted_events"][0]
        event["aliases"] = [
            "counts toward P0 dependency chain claim",
            "complete SDK claim progress contribution",
        ]
        event["counts_toward_p0_dependency_chain_claim"] = True
        event["p0DependencyChainClaimProgressContribution"] = 1
        event["completeSdkClaimProgressContribution"] = 1

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        reasons = set(payload["blockers"])
        self.assertIn("public_claim_forbidden_term", reasons)
        self.assertIn("readiness_claim_enabled", reasons)
        public_terms = {
            blocker.get("term")
            for blocker in payload["blocker_details"]
            if blocker["reason"] == "public_claim_forbidden_term"
        }
        self.assertIn("counts toward P0 dependency chain claim", public_terms)
        self.assertIn("complete SDK claim progress contribution", public_terms)
        readiness_paths = {
            blocker["path"]
            for blocker in payload["blocker_details"]
            if blocker["reason"] == "readiness_claim_enabled"
        }
        self.assertIn(
            "$.public_gameplay_events.promoted_events[0].counts_toward_p0_dependency_chain_claim",
            readiness_paths,
        )
        self.assertIn(
            "$.public_gameplay_events.promoted_events[0].p0DependencyChainClaimProgressContribution",
            readiness_paths,
        )
        self.assertIn(
            "$.public_gameplay_events.promoted_events[0].completeSdkClaimProgressContribution",
            readiness_paths,
        )

    def test_rejects_symlinked_decisions_before_reading(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_fixture(root, self.make_fixture())
            decisions = root / "inventory_item_copied_signals_public_contract_decisions.json"
            decisions_link = root / "decisions.link.json"
            decisions_link.symlink_to(decisions)
            result = self.run_checker_with_paths(
                decisions=decisions_link,
                public_sdk_surfaces=root / "public_sdk_surfaces.json",
                public_gameplay_events=root / "public_gameplay_events.json",
                public_header=root / "ObeliskApi.h",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        self.assertIn("decisions_path_rejected", set(payload["blockers"]))
        self.assertFalse(payload["summary"]["public_sdk_ready"])
        self.assertFalse(payload["summary"]["v1_completion_ready"])

    def test_rejects_symlinked_public_header_before_scanning(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_fixture(root, self.make_fixture())
            header = root / "ObeliskApi.h"
            header_link = root / "ObeliskApi.link.h"
            header_link.symlink_to(header)
            result = self.run_checker_with_paths(
                decisions=root / "inventory_item_copied_signals_public_contract_decisions.json",
                public_sdk_surfaces=root / "public_sdk_surfaces.json",
                public_gameplay_events=root / "public_gameplay_events.json",
                public_header=header_link,
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        self.assertIn("public_header_path_rejected", set(payload["blockers"]))
        self.assertFalse(payload["summary"]["public_sdk_ready"])
        self.assertFalse(payload["summary"]["v1_completion_ready"])

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

    def test_public_header_inventory_numeric_values_are_pinned(self) -> None:
        fixtures = self.make_fixture()
        fixtures["header"] = (
            fixtures["header"]
            .replace(
                "#define OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_REMOTE_ADD_CHECK (1ull << 6)",
                "#define OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_REMOTE_ADD_CHECK (1ull << 12)",
            )
            .replace(
                "#define OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE (1ull << 0)",
                "#define OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE (1ull << 12)",
            )
            .replace(
                "    OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM = 2,",
                "    OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM = 12,",
            )
            .replace(
                "    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK = 7,",
                "    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK = 12,",
            )
        )

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        reasons = set(payload["blockers"])
        self.assertIn("public_header_inventory_event_kind_value_mismatch", reasons)
        self.assertIn("public_header_inventory_event_mask_value_mismatch", reasons)
        self.assertIn("public_header_inventory_field_mask_value_mismatch", reasons)
        self.assertIn("public_header_inventory_resource_kind_value_mismatch", reasons)

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

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        reasons = set(payload["blockers"])
        self.assertIn("gameplay_policy_inventory_target_set_evidence_scope_guardrail_missing", reasons)
        self.assertIn("gameplay_policy_inventory_target_set_evidence_reports_missing", reasons)

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
        event["public_module"] = {
            "status": "accepted",
            "result": "validated",
            "outcome": "ready",
            "progress": 1,
            "target_count": 1,
        }
        event["runtime_capture"] = {"outcome": "enabled", "progress": 1}
        event["live_ops"] = {"stable": True}
        event["v1_readiness"] = {"result": "v1-ready"}
        event["p0_dependency_chain"] = {"status": "supported"}

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
        self.assertIn("$.public_gameplay_events.promoted_events[0].public_module.status", paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].public_module.result", paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].public_module.outcome", paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].public_module.progress", paths)
        self.assertNotIn("$.public_gameplay_events.promoted_events[0].public_module.target_count", paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].runtime_capture.outcome", paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].runtime_capture.progress", paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].live_ops.stable", paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].v1_readiness.result", paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].p0_dependency_chain.status", paths)

    def test_candidate_consume_promotion_alias_paths_are_rejected(self) -> None:
        fixtures = self.make_fixture()
        event = fixtures["public_gameplay_events"]["promoted_events"][0]
        event["target_set"] = {"promoted": True}
        event["artifact_identity"] = {"approved": True}
        event["consume_gate"] = {"ready": True}
        event["static_evidence"] = {"validated": True}
        event["side_lane"] = {"counts_toward_v1": True}
        event["inventory"] = {"public_contract": True}
        event["transfer"] = {"runtime_ready": True}
        event["readiness"] = {"approved": True}
        event["v1"] = {"complete": True}
        event["public_sdk"] = {"enabled": True}
        event["runtime"] = {"validated": True}
        event["candidate"] = {"accepted": True}
        event["package_shape"] = {"passed": True}
        event["support_tier"] = {"active": True}
        event["plugin_hub"] = {"ready": True}

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        paths = {
            blocker["path"]
            for blocker in payload["blocker_details"]
            if blocker["reason"] == "readiness_claim_enabled"
        }
        prefix = "$.public_gameplay_events.promoted_events[0]"
        self.assertIn(f"{prefix}.target_set.promoted", paths)
        self.assertIn(f"{prefix}.artifact_identity.approved", paths)
        self.assertIn(f"{prefix}.consume_gate.ready", paths)
        self.assertIn(f"{prefix}.static_evidence.validated", paths)
        self.assertIn(f"{prefix}.side_lane.counts_toward_v1", paths)
        self.assertIn(f"{prefix}.inventory.public_contract", paths)
        self.assertIn(f"{prefix}.transfer.runtime_ready", paths)
        self.assertIn(f"{prefix}.readiness.approved", paths)
        self.assertIn(f"{prefix}.v1.complete", paths)
        self.assertIn(f"{prefix}.public_sdk.enabled", paths)
        self.assertIn(f"{prefix}.runtime.validated", paths)
        self.assertIn(f"{prefix}.candidate.accepted", paths)
        self.assertIn(f"{prefix}.package_shape.passed", paths)
        self.assertIn(f"{prefix}.support_tier.active", paths)
        self.assertIn(f"{prefix}.plugin_hub.ready", paths)

    def test_source_ready_split_claims_are_rejected(self) -> None:
        fixtures = self.make_fixture()
        event = fixtures["public_gameplay_events"]["promoted_events"][0]
        event["sourceReady"] = True
        event["sourceStatus"] = "accepted"
        event["source"] = {
            "ready": True,
            "status": "accepted",
            "progress": 1,
        }

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        paths = {
            blocker["path"]
            for blocker in payload["blocker_details"]
            if blocker["reason"] == "readiness_claim_enabled"
        }
        self.assertIn("$.public_gameplay_events.promoted_events[0].sourceReady", paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].sourceStatus", paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].source.ready", paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].source.status", paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].source.progress", paths)

    def test_status_shortcut_aliases_are_rejected(self) -> None:
        fixtures = self.make_fixture()
        event = fixtures["public_gameplay_events"]["promoted_events"][0]
        event["runtime"] = {"status": "ok"}
        event["public_sdk"] = {"state": "green"}
        event["v1"] = {"result": "go"}
        event["aliases"] = [
            "public SDK green from copied signals",
            "runtime ok for copied signals",
            "v1 completion go",
        ]

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("readiness_claim_enabled", set(payload["blockers"]))
        paths = {
            blocker["path"]
            for blocker in payload["blocker_details"]
            if blocker["reason"] == "readiness_claim_enabled"
        }
        prefix = "$.public_gameplay_events.promoted_events[0]"
        self.assertIn(f"{prefix}.runtime.status", paths)
        self.assertIn(f"{prefix}.public_sdk.state", paths)
        self.assertIn(f"{prefix}.v1.result", paths)
        self.assertIn(f"{prefix}.aliases[1]", paths)
        self.assertIn(f"{prefix}.aliases[2]", paths)
        public_claim_paths = {
            blocker["path"]
            for blocker in payload["blocker_details"]
            if blocker["reason"] == "public_claim_forbidden_term"
        }
        self.assertIn(f"{prefix}.aliases[0]", public_claim_paths)
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["v1_completion_ready"])
        self.assertEqual(0, payload["complete_sdk_claim_progress_contribution"])

    def test_source_label_and_source_labels_positive_aliases_are_rejected(self) -> None:
        fixtures = self.make_fixture()
        event = fixtures["public_gameplay_events"]["promoted_events"][0]
        event["sourceLabel"] = "ready"
        event["sourceLabels"] = ["candidate-only", "supported"]

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        paths = {
            blocker["path"]
            for blocker in payload["blocker_details"]
            if blocker["reason"] == "readiness_claim_enabled"
        }
        self.assertIn("$.public_gameplay_events.promoted_events[0].sourceLabel", paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].sourceLabels[1]", paths)
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["v1_completion_ready"])
        self.assertEqual(0, payload["complete_sdk_claim_progress_contribution"])

    def test_approved_runtime_source_marker_aliases_are_rejected(self) -> None:
        fixtures = self.make_fixture()
        fixtures["decisions"]["source_marker"] = "source approved"
        event = fixtures["public_gameplay_events"]["promoted_events"][0]
        event["sourceMarkers"] = ["candidate-only", "approved runtime bundle"]
        surface = fixtures["public_sdk_surfaces"]["surfaces"][0]
        surface["source_markers"] = ["approved runtime evidence"]

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("readiness_claim_enabled", set(payload["blockers"]))
        paths = {
            blocker["path"]
            for blocker in payload["blocker_details"]
            if blocker["reason"] == "readiness_claim_enabled"
        }
        self.assertIn("$.decisions.source_marker", paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].sourceMarkers[1]", paths)
        self.assertIn("$.public_sdk_surfaces.surfaces[0].source_markers[0]", paths)
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["v1_completion_ready"])

    def test_stale_readiness_satisfied_aliases_are_rejected(self) -> None:
        fixtures = self.make_fixture()
        event = fixtures["public_gameplay_events"]["promoted_events"][0]
        evidence = event["target_set_evidence"][1]
        evidence["readiness_satisfied"] = True
        evidence["second_source_readiness_satisfied"] = True
        surface = fixtures["public_sdk_surfaces"]["surfaces"][0]
        surface["evidence"]["artifact_readiness_satisfied"] = "ready"

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("readiness_claim_enabled", set(payload["blockers"]))
        paths = {
            blocker["path"]
            for blocker in payload["blocker_details"]
            if blocker["reason"] == "readiness_claim_enabled"
        }
        self.assertIn(
            "$.public_gameplay_events.promoted_events[0].target_set_evidence[1].readiness_satisfied",
            paths,
        )
        self.assertIn(
            "$.public_gameplay_events.promoted_events[0].target_set_evidence[1].second_source_readiness_satisfied",
            paths,
        )
        self.assertIn(
            "$.public_sdk_surfaces.surfaces[0].evidence.artifact_readiness_satisfied",
            paths,
        )
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["v1_completion_ready"])

    def test_inventory_action_identity_authority_and_release_aliases_are_rejected(self) -> None:
        fixtures = self.make_fixture()
        event = fixtures["public_gameplay_events"]["promoted_events"][0]
        event["aliases"] = [
            "Inventory SDK public alias",
            "inventory action aliases are release-supported",
            "item mutation ready",
            "item stack identity is stable",
            "ownership lookup ready",
            "return override ready",
            "equip authority and repair authority are public",
            "craft authority for copied item actions",
            "countsTowardCompleteSdkClaim",
            "countsForPublicSdkV1",
            "contributes to v1 completion",
        ]
        event["counts_toward_complete_sdk"] = True
        event["countsTowardCompleteSdkClaim"] = True
        event["countsForPublicSdkV1"] = True
        event["v1CompletionContribution"] = True

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        reasons = set(payload["blockers"])
        self.assertIn("public_claim_forbidden_term", reasons)
        self.assertIn("readiness_claim_enabled", reasons)
        terms = {
            blocker.get("term")
            for blocker in payload["blocker_details"]
            if blocker["reason"] == "public_claim_forbidden_term"
        }
        self.assertIn("Inventory SDK", terms)
        self.assertIn("action aliases", terms)
        self.assertIn("mutation", terms)
        self.assertIn("item stack identity", terms)
        self.assertIn("ownership lookup", terms)
        self.assertIn("return override", terms)
        self.assertIn("equip authority", terms)
        self.assertIn("repair authority", terms)
        self.assertIn("craft authority", terms)
        self.assertIn("countsForPublicSdkV1", terms)
        self.assertIn("contributes to v1 completion", terms)
        public_claim_paths = {
            blocker["path"]
            for blocker in payload["blocker_details"]
            if blocker["reason"] == "public_claim_forbidden_term"
        }
        self.assertIn("$.public_gameplay_events.promoted_events[0].aliases[0]", public_claim_paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].aliases[2]", public_claim_paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].aliases[5]", public_claim_paths)
        paths = {
            blocker["path"]
            for blocker in payload["blocker_details"]
            if blocker["reason"] == "readiness_claim_enabled"
        }
        self.assertIn("$.public_gameplay_events.promoted_events[0].counts_toward_complete_sdk", paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].countsTowardCompleteSdkClaim", paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].countsForPublicSdkV1", paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].v1CompletionContribution", paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].aliases[1]", paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].aliases[3]", paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].aliases[8]", paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].aliases[9]", paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].aliases[10]", paths)

    def test_support_and_umbrella_leaf_claim_aliases_are_rejected(self) -> None:
        fixtures = self.make_fixture()
        event = fixtures["public_gameplay_events"]["promoted_events"][0]
        event["aliases"] = [
            "public SDK support is active",
            "runtime/v1 support is enabled",
            "gameplay policy umbrella leaf promotion is ready",
        ]
        fixtures["public_sdk_surfaces"]["release_note"] = "support tier active for inventory side lane"

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        reasons = set(payload["blockers"])
        self.assertIn("public_claim_forbidden_term", reasons)
        self.assertIn("readiness_claim_enabled", reasons)
        readiness_paths = {
            blocker["path"]
            for blocker in payload["blocker_details"]
            if blocker["reason"] == "readiness_claim_enabled"
        }
        self.assertIn("$.public_gameplay_events.promoted_events[0].aliases[0]", readiness_paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].aliases[1]", readiness_paths)
        self.assertIn("$.public_gameplay_events.promoted_events[0].aliases[2]", readiness_paths)
        self.assertIn("$.public_sdk_surfaces.release_note", readiness_paths)

    def test_nested_runtime_support_boolean_alias_is_rejected_but_candidate_metadata_is_allowed(self) -> None:
        fixtures = self.make_fixture()
        event = fixtures["public_gameplay_events"]["promoted_events"][0]
        event["candidate_metadata"] = {
            "artifact_status": "candidate-only",
            "accepted_for_internal_planning": True,
            "source_snapshot_sha256": "0" * 64,
        }

        result = self.run_fixture(fixtures)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ready"])
        self.assertEqual(payload["blockers"], [])

        event["candidate_metadata"]["runtimeSupport"] = True

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        reasons = set(payload["blockers"])
        self.assertIn("readiness_claim_enabled", reasons)
        paths = {
            blocker["path"]
            for blocker in payload["blocker_details"]
            if blocker["reason"] == "readiness_claim_enabled"
        }
        self.assertIn(
            "$.public_gameplay_events.promoted_events[0].candidate_metadata.runtimeSupport",
            paths,
        )
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["v1_completion_ready"])

    def test_nested_positive_package_plugin_mutation_and_resource_aliases_are_rejected(self) -> None:
        fixtures = self.make_fixture()
        event = fixtures["public_gameplay_events"]["promoted_events"][0]
        event["candidate_metadata"] = {
            "review": {
                "aliases": [
                    "public SDK ready from copied inventory signals",
                    "runtime/v1 support is active for copied inventory signals",
                    "package-shape ready for copied inventory signals",
                    "support tier ready for copied inventory signals",
                    "Plugin Hub ready for copied inventory signals",
                    "item mutation ready for copied inventory signals",
                    "return override ready for copied inventory signals",
                    "resource handle support for copied inventory signals",
                ],
            },
            "packageShapeReady": True,
            "supportTierStatus": "approved",
            "pluginHubStatus": "ready",
        }

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(1, result.returncode)
        reasons = set(payload["blockers"])
        self.assertIn("public_claim_forbidden_term", reasons)
        self.assertIn("readiness_claim_enabled", reasons)
        public_terms = {
            blocker.get("term")
            for blocker in payload["blocker_details"]
            if blocker["reason"] == "public_claim_forbidden_term"
        }
        for term in (
            "public SDK",
            "runtime/v1 support",
            "package shape",
            "support tier",
            "Plugin Hub",
            "mutation",
            "return override",
            "resource handle",
        ):
            self.assertIn(term, public_terms)
        readiness_paths = {
            blocker["path"]
            for blocker in payload["blocker_details"]
            if blocker["reason"] == "readiness_claim_enabled"
        }
        prefix = "$.public_gameplay_events.promoted_events[0].candidate_metadata"
        self.assertIn(f"{prefix}.review.aliases[2]", readiness_paths)
        self.assertIn(f"{prefix}.review.aliases[4]", readiness_paths)
        self.assertIn(f"{prefix}.review.aliases[7]", readiness_paths)
        self.assertIn(f"{prefix}.packageShapeReady", readiness_paths)
        self.assertIn(f"{prefix}.supportTierStatus", readiness_paths)
        self.assertIn(f"{prefix}.pluginHubStatus", readiness_paths)
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["v1_completion_ready"])

    def test_custom_filter_array_range_claims_are_rejected_by_copied_signal_accounting(self) -> None:
        fixtures = self.make_fixture()
        event = fixtures["public_gameplay_events"]["promoted_events"][0]
        event["review_notes"] = [
            "InventoryCustomFilter public API is available from copied signals",
            "custom filter array range ready for public callbacks",
            "TArray copied list exposes range for item payloads",
            "raw array and raw range support",
        ]

        result = self.run_fixture(fixtures, check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        reasons = set(payload["blockers"])
        self.assertIn("public_claim_forbidden_term", reasons)
        terms = {
            blocker.get("term")
            for blocker in payload["blocker_details"]
            if blocker["reason"] == "public_claim_forbidden_term"
        }
        for term in (
            "InventoryCustomFilter",
            "custom filter",
            "array range",
            "TArray",
            "copied list",
            "exposes range",
            "raw array",
            "raw range",
        ):
            self.assertIn(term, terms)


if __name__ == "__main__":
    unittest.main()
