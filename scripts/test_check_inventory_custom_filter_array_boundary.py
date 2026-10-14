#!/usr/bin/env python3
"""Tests for check_inventory_custom_filter_array_boundary.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_inventory_custom_filter_array_boundary.py"
sys.path.insert(0, str(SCRIPT_DIR))

import check_inventory_custom_filter_array_boundary as checker  # noqa: E402
from reflection_target_sets import (  # noqa: E402
    PLANNING_ONLY_TARGET_SETS,
    RELEASE_READINESS_TARGET_SETS,
    schema_target_list,
    target_set_module_lane,
    target_set_readiness_classification,
)


class CheckInventoryCustomFilterArrayBoundaryTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if check and result.returncode != 0:
            self.fail(f"checker failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def load_snapshot(self) -> dict[str, Any]:
        return json.loads(checker.DEFAULT_SNAPSHOT.read_text(encoding="utf-8"))

    def write_snapshot(self, root: Path, payload: dict[str, Any]) -> Path:
        snapshot = root / "PrimalInventoryComponent.InventoryCustomFilter.snapshot.json"
        snapshot.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        return snapshot

    def write_public_inputs(
        self,
        root: Path,
        *,
        surfaces: dict[str, Any] | None = None,
        events: dict[str, Any] | None = None,
        header: str = "#pragma once\n",
    ) -> tuple[Path, Path, Path]:
        surfaces_path = root / "public_sdk_surfaces.json"
        events_path = root / "public_gameplay_events.json"
        header_path = root / "ObeliskApi.h"
        surfaces_payload = dict(surfaces) if surfaces is not None else {"surfaces": []}
        events_payload = dict(events) if events is not None else {"promoted_events": []}
        surfaces_payload.setdefault("schema", checker.PUBLIC_SDK_SURFACES_SCHEMA)
        events_payload.setdefault("schema", checker.PUBLIC_GAMEPLAY_EVENTS_SCHEMA)
        surfaces_path.write_text(json.dumps(surfaces_payload), encoding="utf-8")
        events_path.write_text(json.dumps(events_payload), encoding="utf-8")
        header_path.write_text(header, encoding="utf-8")
        return surfaces_path, events_path, header_path

    def test_target_set_is_planning_only_inventory_side_lane(self) -> None:
        self.assertEqual(
            [checker.TARGET],
            schema_target_list(checker.TARGET_SET, checker.SNAPSHOT_SCHEMA),
        )
        self.assertIn(checker.TARGET_SET, PLANNING_ONLY_TARGET_SETS)
        self.assertNotIn(checker.TARGET_SET, RELEASE_READINESS_TARGET_SETS)
        self.assertEqual("inventory", target_set_module_lane(checker.TARGET_SET))
        self.assertEqual("planning_only", target_set_readiness_classification(checker.TARGET_SET))

    def test_snapshot_readme_documents_custom_filter_as_planning_only_target_set(self) -> None:
        readme = (REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots" / "README.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("inventory-custom-filter-array-boundary", readme)
        self.assertIn("planning-only", readme)
        self.assertIn("not", readme)
        self.assertIn("release-readiness scope", readme)
        self.assertNotIn("does not currently belong to any named target set", readme)

    def test_missing_target_set_coverage_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            surfaces, events, header = self.write_public_inputs(Path(temp_dir))
            with mock.patch.object(checker, "TARGET_SET", "inventory-custom-filter-missing-target-set"):
                payload = checker.build_check(
                    public_sdk_surfaces=surfaces,
                    public_gameplay_events=events,
                    public_header=header,
                )

        self.assertFalse(payload["ready"])
        self.assertIn("target_set_missing", {blocker["reason"] for blocker in payload["blockers"]})
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])

    def test_unknown_snapshot_schema_fails_closed(self) -> None:
        snapshot_payload = self.load_snapshot()
        snapshot_payload["schema"] = "obelisk.unknown-ufunction-snapshot.v1"

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            snapshot = self.write_snapshot(root, snapshot_payload)
            surfaces, events, header = self.write_public_inputs(root)
            result = self.run_checker(
                "--snapshot",
                str(snapshot),
                "--public-sdk-surfaces",
                str(surfaces),
                "--public-gameplay-events",
                str(events),
                "--public-header",
                str(header),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        self.assertIn("snapshot_schema_mismatch", {blocker["reason"] for blocker in payload["blockers"]})
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])

    def test_unknown_public_manifest_schemas_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            surfaces, events, header = self.write_public_inputs(
                root,
                surfaces={"schema": "obelisk.unknown-public-sdk-surfaces.v1", "surfaces": []},
                events={"schema": "obelisk.unknown-public-gameplay-events.v1", "promoted_events": []},
            )
            result = self.run_checker(
                "--public-sdk-surfaces",
                str(surfaces),
                "--public-gameplay-events",
                str(events),
                "--public-header",
                str(header),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("public_sdk_surfaces_schema_mismatch", reasons)
        self.assertIn("public_gameplay_events_schema_mismatch", reasons)
        self.assertEqual(
            "obelisk.unknown-public-sdk-surfaces.v1",
            payload["public_contract_scan"]["public_sdk_surfaces"]["schema"],
        )
        self.assertEqual(
            "obelisk.unknown-public-gameplay-events.v1",
            payload["public_contract_scan"]["public_gameplay_events"]["schema"],
        )
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])

    def test_committed_snapshot_passes_as_candidate_only_non_promoting_boundary(self) -> None:
        result = self.run_checker("--json")
        payload = json.loads(result.stdout)

        self.assertEqual(checker.REPORT_SCHEMA, payload["schema"])
        self.assertTrue(payload["ready"])
        self.assertEqual(checker.NON_AUTHORIZING_READY_SCOPE, payload["ready_scope"])
        self.assertTrue(
            set(checker.NON_AUTHORIZING_READY_DOES_NOT_SATISFY)
            <= set(payload["does_not_satisfy_readiness"])
        )
        self.assertTrue(payload["fixture_only"])
        self.assertTrue(payload["candidate_only"])
        self.assertTrue(payload["accepted_for_internal_planning"])
        self.assertTrue(payload["offline_only"])
        self.assertTrue(payload["not_artifact_gate"])
        self.assertEqual("non_p0_side_lane", payload["priority_class"])
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["v1_completion_ready"])
        self.assertFalse(payload["counts_for_p0_dependency_chain"])
        self.assertFalse(payload["counts_for_public_sdk_v1"])
        self.assertFalse(payload["counts_toward_complete_sdk_claim"])
        self.assertFalse(payload["counts_toward_p0_dependency_chain_claim"])
        self.assertFalse(payload["counts_toward_v1_completion"])
        self.assertEqual(0, payload["complete_sdk_claim_progress_contribution"])
        self.assertEqual(0, payload["p0_dependency_chain_claim_progress_contribution"])
        self.assertEqual(0, payload["v1_completion_progress_contribution"])
        self.assertFalse(payload["inventory_sdk_ready"])
        self.assertFalse(payload["items_sdk_ready"])
        self.assertFalse(payload["lookup_ready"])
        self.assertFalse(payload["resource_handle_ready"])
        self.assertFalse(payload["mutation_ready"])
        self.assertFalse(payload["return_override_ready"])
        for flag in checker.FALSE_READINESS_FLAGS:
            self.assertIn(flag, payload)
            self.assertFalse(payload[flag], flag)
        self.assertEqual([], payload["blockers"])

        self.assertEqual(0, payload["copied_scalar_count"])
        self.assertEqual(0, payload["copied_array_count"])
        self.assertEqual(0, payload["copied_list_count"])
        self.assertEqual(2, payload["array_boundary_count"])
        self.assertEqual(0, payload["unsafe_array_boundary_count"])
        self.assertEqual(0, payload["forged_array_payload_boundary_count"])
        self.assertEqual(0, payload["public_api_count"])
        self.assertEqual(0, payload["public_contract_offender_count"])
        self.assertEqual(0, payload["public_positive_claim_offender_count"])
        self.assertEqual(0, payload["public_readiness_offender_count"])
        self.assertEqual(
            {
                "approved_runtime_evidence_present": False,
                "approved_runtime_evidence_ready": False,
                "approved_runtime_evidence_substitution_allowed": False,
                "authorizes_discord_send": False,
                "authorizes_live_log_reads": False,
                "authorizes_marker_or_env_changes": False,
                "authorizes_player_backed_window": False,
                "authorizes_runtime_capture": False,
                "authorizes_runtime_observer": False,
                "authorizes_server_restart": False,
                "clears_approved_runtime_evidence_missing": False,
                "counts_as_approved_runtime_evidence": False,
                "counts_as_runtime_evidence": False,
                "counts_for_p0_dependency_chain": False,
                "counts_for_public_sdk_v1": False,
                "side_lane_counts_toward_sdk": False,
                "side_lane_counts_toward_p0": False,
                "sdk_p0_unlock_allowed": False,
                "counts_toward_complete_sdk_claim": False,
                "counts_toward_p0_dependency_chain_claim": False,
                "counts_toward_v1_completion": False,
                "primary_evidence_substitution_allowed": False,
                "complete_sdk_claim_progress_contribution": 0,
                "p0_dependency_chain_claim_progress_contribution": 0,
                "v1_completion_progress_contribution": 0,
                "evidence_use": "offline_fixture_boundary_only",
                "accepted_for_internal_planning": True,
                "offline_only": True,
                "not_artifact_gate": True,
                "ready_scope": checker.NON_AUTHORIZING_READY_SCOPE,
                "does_not_satisfy_readiness": list(checker.NON_AUTHORIZING_READY_DOES_NOT_SATISFY),
                "current_route_blocker": checker.CURRENT_ROUTE_BLOCKER,
                "remaining_route_blockers": [checker.CURRENT_ROUTE_BLOCKER],
                "required_runtime_evidence": checker.REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
                "replaces_player_principal_evidence": False,
                "replaces_player_principal_triplet": False,
                "player_principal_lifecycle_evidence_substitution_allowed": False,
                "side_lane_collection_can_replace_player_principal_evidence": False,
                "side_lane_collection_counts_before_checker_acceptance": False,
                "side_lane_substitutes_for_player_principal_lifecycle_evidence": False,
                "substitutes_for_player_principal_lifecycle_evidence": False,
                "substitutes_for_player_principal_lifecycle_triplet": False,
                "blocked_promotion_claims": [
                    "Inventory SDK",
                    "Items SDK",
                    "identity",
                    "mutation",
                    "return override",
                    "ResourceHandle",
                    "v1 completion",
                ],
            },
            payload["side_lane_accounting"],
        )

        summary = payload["summary"]
        self.assertEqual(checker.TARGET, summary["target"])
        self.assertEqual(2, summary["param_count"])
        self.assertEqual(
            [
                {
                    "field": f"{checker.TARGET}.UnfilteredItemsList",
                    "boundary_kind": "reflected_param_tarray_shell_only",
                    "offset_internal": 0,
                    "element_size": 16,
                    "array_dim": 1,
                    "end_offset": 16,
                    "parms_size": 32,
                    "safe": True,
                    "redaction": (
                        "TArray parameter shell recognized; data pointer/count/capacity "
                        "and element identity redacted"
                    ),
                },
                {
                    "field": f"{checker.TARGET}.FilteredItemsList",
                    "boundary_kind": "reflected_param_tarray_shell_only",
                    "offset_internal": 16,
                    "element_size": 16,
                    "array_dim": 1,
                    "end_offset": 32,
                    "parms_size": 32,
                    "safe": True,
                    "redaction": (
                        "TArray parameter shell recognized; data pointer/count/capacity "
                        "and element identity redacted"
                    ),
                },
            ],
            summary["param_byte_boundaries"],
        )
        self.assertEqual(2, summary["redacted_array_count"])
        self.assertEqual({"ObjectProperty": 2}, summary["array_inner_classes"])
        self.assertEqual(
            [
                f"{checker.TARGET}.UnfilteredItemsList",
                f"{checker.TARGET}.FilteredItemsList",
            ],
            [field["field"] for field in summary["redacted_array_fields"]],
        )
        self.assertEqual(
            ["ArrayProperty payload redacted; no TArray copy"] * 2,
            [field["redaction"] for field in summary["redacted_array_fields"]],
        )
        self.assertEqual(
            ["ObjectProperty", "ObjectProperty"],
            [field["array_inner"]["source_property_class"] for field in summary["redacted_array_fields"]],
        )
        non_claims = "\n".join(payload["non_claims"])
        self.assertEqual(
            [
                "non-P0 candidate-only inventory array side-lane audit; no v1 completion or priority promotion",
                "not an Inventory SDK or Items SDK; no public Inventory/Items SDK, no public API, public callback, public ABI, or public payload contract",
                "no AdditionalData exposure, no raw arrays/ranges, no copied array/list payload, and no copied scalars",
                "no item identity, no ResourceHandle, no identity, no lookup, no mutation, no return override, and no runtime readiness",
            ],
            payload["non_claims"],
        )
        for token in (
            "non-P0",
            "not an Inventory SDK",
            "no public Inventory/Items SDK",
            "no AdditionalData",
            "no raw arrays",
            "no item identity",
            "no public API",
            "no ResourceHandle",
            "no mutation",
            "no return override",
            "no runtime readiness",
        ):
            self.assertIn(token, non_claims)

    def test_clean_candidate_only_ready_preserves_candidate_source_without_overclaim(self) -> None:
        result = self.run_checker("--json")
        payload = json.loads(result.stdout)

        self.assertTrue(payload["ready"])
        self.assertEqual("accepted_candidate_only_boundary", payload["status"])
        self.assertTrue(payload["candidate_only"])
        self.assertEqual("candidate-only", payload["summary"]["status"])
        self.assertEqual("offline_core", payload["summary"]["evidence_identity"]["source"])
        self.assertEqual("candidate-only", payload["summary"]["evidence_identity"]["status"])
        self.assertTrue(payload["target_set_summary"]["planning_only"])
        self.assertFalse(payload["target_set_summary"]["release_readiness"])
        self.assertEqual(0, payload["public_positive_claim_offender_count"])
        self.assertEqual(0, payload["public_readiness_offender_count"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["v1_completion_ready"])
        self.assertEqual([], payload["blockers"])
        self.assertEqual(
            "non_authorizing_candidate_boundary_passed_only",
            payload["readiness_report"]["ready_field_semantics"],
        )
        self.assertTrue(payload["readiness_report"]["input_guardrails_passed"])
        self.assertFalse(payload["readiness_report"]["public_inventory_sdk_claim_allowed"])
        self.assertFalse(payload["readiness_report"]["array_payload_claim_allowed"])
        self.assertFalse(payload["readiness_report"]["v1_completion_claim_allowed"])
        self.assertEqual(0, payload["readiness_report"]["v1_progress_contribution"])
        self.assertEqual(
            "array_payload_intentionally_redacted_boundary_only",
            payload["next_blockers"]["offline"]["id"],
        )
        self.assertTrue(payload["next_blockers"]["offline"]["blocked_for_public_inventory_sdk"])
        self.assertIn(
            "separate reflected copied-payload contract if an array surface is ever proposed",
            payload["next_blockers"]["offline"]["required_future_evidence"],
        )
        self.assertEqual(
            "runtime_array_lifetime_and_identity_evidence_missing",
            payload["next_blockers"]["runtime"]["id"],
        )
        self.assertIn("ResourceHandle", payload["next_blockers"]["runtime"]["blocked_claims"])

    def test_copied_array_or_list_leakage_fails_closed(self) -> None:
        snapshot_payload = self.load_snapshot()
        array_param = snapshot_payload["targets"][0]["property_chain"]["properties"][0]
        array_param["copied_array_range"] = {"offset": 0, "element_size": 8}
        array_param["payload_contract"] = "copied list of inventory item object refs"

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            snapshot = self.write_snapshot(root, snapshot_payload)
            surfaces, events, header = self.write_public_inputs(root)
            result = self.run_checker(
                "--snapshot",
                str(snapshot),
                "--public-sdk-surfaces",
                str(surfaces),
                "--public-gameplay-events",
                str(events),
                "--public-header",
                str(header),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        self.assertIn("copied_array_or_list_leak", reasons)
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["v1_completion_ready"])

    def test_forged_array_payload_boundary_metadata_fails_closed(self) -> None:
        snapshot_payload = self.load_snapshot()
        array_param = snapshot_payload["targets"][0]["property_chain"]["properties"][0]
        array_param["array_payload_boundary"] = {
            "data_ptr": "0x4141414141414141",
            "array_num": 2,
            "array_max": 2,
            "element_range": {"offset": 0, "size": 16},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            snapshot = self.write_snapshot(root, snapshot_payload)
            surfaces, events, header = self.write_public_inputs(root)
            result = self.run_checker(
                "--snapshot",
                str(snapshot),
                "--public-sdk-surfaces",
                str(surfaces),
                "--public-gameplay-events",
                str(events),
                "--public-header",
                str(header),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        self.assertIn("forged_array_payload_boundary", reasons)
        self.assertIn("forbidden_snapshot_exposure", reasons)
        self.assertGreaterEqual(payload["forged_array_payload_boundary_count"], 4)
        forged_terms = {
            blocker["term"]
            for blocker in payload["blockers"]
            if blocker["reason"] == "forged_array_payload_boundary"
        }
        for term in ("array_payload_boundary", "data_ptr", "array_num", "array_max", "element_range"):
            self.assertIn(term, forged_terms)
        self.assertEqual(2, payload["array_boundary_count"])
        self.assertEqual(0, payload["unsafe_array_boundary_count"])
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["v1_completion_ready"])

    def test_array_value_payload_aliases_fail_closed(self) -> None:
        snapshot_payload = self.load_snapshot()
        array_param = snapshot_payload["targets"][0]["property_chain"]["properties"][0]
        array_param["observedArrayValues"] = ["PrimalItem_1"]
        array_param["elementValues"] = [1, 2]
        array_param["tarrayValues"] = [{"item": "ItemNetID"}]

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            snapshot = self.write_snapshot(root, snapshot_payload)
            surfaces, events, header = self.write_public_inputs(root)
            result = self.run_checker(
                "--snapshot",
                str(snapshot),
                "--public-sdk-surfaces",
                str(surfaces),
                "--public-gameplay-events",
                str(events),
                "--public-header",
                str(header),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        self.assertIn("forged_array_payload_boundary", {blocker["reason"] for blocker in payload["blockers"]})
        forged_terms = {
            blocker["term"]
            for blocker in payload["blockers"]
            if blocker["reason"] == "forged_array_payload_boundary"
        }
        self.assertIn("observedarrayvalue", forged_terms)
        self.assertIn("elementvalue", forged_terms)
        self.assertIn("tarrayvalue", forged_terms)
        self.assertFalse(payload["readiness_report"]["array_payload_claim_allowed"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])

    def test_unsafe_array_param_byte_boundary_fails_closed(self) -> None:
        snapshot_payload = self.load_snapshot()
        array_param = snapshot_payload["targets"][0]["property_chain"]["properties"][0]
        array_param["offset_internal"] = 20
        array_param["element_size"] = 16

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            snapshot = self.write_snapshot(root, snapshot_payload)
            surfaces, events, header = self.write_public_inputs(root)
            result = self.run_checker(
                "--snapshot",
                str(snapshot),
                "--public-sdk-surfaces",
                str(surfaces),
                "--public-gameplay-events",
                str(events),
                "--public-header",
                str(header),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        self.assertIn("array_param_shape_mismatch", reasons)
        self.assertIn("array_param_boundary_mismatch", reasons)
        self.assertIn("array_param_boundary_unsafe", reasons)
        self.assertIn("array_param_boundary_overlap", reasons)
        self.assertIn("array_param_boundary_coverage_mismatch", reasons)
        self.assertEqual(2, payload["array_boundary_count"])
        self.assertEqual(1, payload["unsafe_array_boundary_count"])
        unsafe_boundary = payload["summary"]["param_byte_boundaries"][0]
        self.assertEqual(f"{checker.TARGET}.UnfilteredItemsList", unsafe_boundary["field"])
        self.assertEqual(20, unsafe_boundary["offset_internal"])
        self.assertEqual(36, unsafe_boundary["end_offset"])
        self.assertFalse(unsafe_boundary["safe"])
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["v1_completion_ready"])

    def test_extra_reflected_param_payload_fails_closed(self) -> None:
        snapshot_payload = self.load_snapshot()
        target = snapshot_payload["targets"][0]
        chain = target["property_chain"]
        extra_param = dict(chain["properties"][1])
        extra_param["name"] = "UnexpectedItemPayload"
        extra_param["offset_internal"] = 32
        chain["properties"].append(extra_param)
        chain["observed_count"] = 3
        target["num_parms"] = 3
        target["parms_size"] = 48

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            snapshot = self.write_snapshot(root, snapshot_payload)
            surfaces, events, header = self.write_public_inputs(root)
            result = self.run_checker(
                "--snapshot",
                str(snapshot),
                "--public-sdk-surfaces",
                str(surfaces),
                "--public-gameplay-events",
                str(events),
                "--public-header",
                str(header),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        self.assertIn("param_count_mismatch", reasons)
        self.assertIn("unexpected_extra_param_payload", reasons)
        extra_blockers = [
            blocker for blocker in payload["blockers"] if blocker["reason"] == "unexpected_extra_param_payload"
        ]
        self.assertEqual(
            [
                {
                    "reason": "unexpected_extra_param_payload",
                    "index": 2,
                    "name": "UnexpectedItemPayload",
                    "class_name": "ArrayProperty",
                    "offset_internal": 32,
                }
            ],
            extra_blockers,
        )
        self.assertEqual(2, payload["array_boundary_count"])
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["v1_completion_ready"])

    def test_raw_range_additional_data_identity_and_readiness_claims_fail_closed(self) -> None:
        snapshot_payload = self.load_snapshot()
        target = snapshot_payload["targets"][0]
        array_param = target["property_chain"]["properties"][0]
        inner = array_param["array_inner_candidate"]["inner_property"]
        array_param["raw_array_range"] = {"offset": 0, "count": 2}
        array_param["AdditionalData"] = {"exposes_range": True}
        inner["item_identity"] = "ItemNetID identity ready"
        target["runtime_ready"] = True
        target["mutation_ready"] = True
        target["return_override_ready"] = True

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            snapshot = self.write_snapshot(root, snapshot_payload)
            surfaces, events, header = self.write_public_inputs(root)
            result = self.run_checker(
                "--snapshot",
                str(snapshot),
                "--public-sdk-surfaces",
                str(surfaces),
                "--public-gameplay-events",
                str(events),
                "--public-header",
                str(header),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        self.assertIn("forbidden_snapshot_exposure", reasons)
        self.assertIn("snapshot_readiness_flag_enabled", reasons)
        exposure_terms = {
            blocker["term"]
            for blocker in payload["blockers"]
            if blocker["reason"] == "forbidden_snapshot_exposure"
        }
        self.assertIn("raw_array", exposure_terms)
        self.assertIn("additionaldata", exposure_terms)
        self.assertIn("item_identity", exposure_terms)
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["mutation_ready"])
        self.assertFalse(payload["return_override_ready"])

    def test_positive_snapshot_status_and_string_readiness_aliases_fail_closed(self) -> None:
        snapshot_payload = self.load_snapshot()
        target = snapshot_payload["targets"][0]
        target["runtime_ready"] = "runtime-ready"
        target["runtimeValidation"] = "passed"
        target["resource_handle_ready"] = "enabled"
        target["resourceHandleStatus"] = "approved"
        target["review"] = {"status": "sdk-ready"}
        target["sourceStatus"] = "complete"
        target["sourceTier"] = "approved"
        target["publicSdkStatus"] = "complete"
        target["public_module"] = {
            "status": "accepted",
            "result": "validated",
            "outcome": "ready",
            "progress": 1,
            "target_count": 1,
        }
        target["mutationOutcome"] = "complete"
        target["returnOverrideResult"] = "approved"
        target["runtime_capture"] = {"outcome": "enabled", "progress": 1}
        target["live_ops"] = {"stable": True}
        target["v1_readiness"] = {"result": "v1-ready"}
        target["v1CompletionStatus"] = "complete"
        target["p0_dependency_chain"] = {"status": "supported"}
        target["readiness"] = {"approved": True}
        target["v1"] = {"complete": True}
        target["public_sdk"] = {"enabled": True}
        target["runtime"] = {"validated": True}
        target["candidate"] = {"accepted": True}
        target["package_shape"] = {"passed": True}
        target["support_tier"] = {"active": True}
        target["plugin_hub"] = {"ready": True}
        target["target_set"] = {"promoted": True}

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            snapshot = self.write_snapshot(root, snapshot_payload)
            surfaces, events, header = self.write_public_inputs(root)
            result = self.run_checker(
                "--snapshot",
                str(snapshot),
                "--public-sdk-surfaces",
                str(surfaces),
                "--public-gameplay-events",
                str(events),
                "--public-header",
                str(header),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("snapshot_readiness_flag_enabled", reasons)
        readiness_paths = {
            blocker["path"]
            for blocker in payload["blockers"]
            if blocker["reason"] == "snapshot_readiness_flag_enabled"
        }
        self.assertIn("targets.0.runtime_ready", readiness_paths)
        self.assertIn("targets.0.runtimeValidation", readiness_paths)
        self.assertIn("targets.0.resource_handle_ready", readiness_paths)
        self.assertIn("targets.0.resourceHandleStatus", readiness_paths)
        self.assertIn("targets.0.review.status", readiness_paths)
        self.assertIn("targets.0.sourceStatus", readiness_paths)
        self.assertIn("targets.0.sourceTier", readiness_paths)
        self.assertIn("targets.0.publicSdkStatus", readiness_paths)
        self.assertIn("targets.0.public_module.status", readiness_paths)
        self.assertIn("targets.0.public_module.result", readiness_paths)
        self.assertIn("targets.0.public_module.outcome", readiness_paths)
        self.assertIn("targets.0.public_module.progress", readiness_paths)
        self.assertNotIn("targets.0.public_module.target_count", readiness_paths)
        self.assertIn("targets.0.mutationOutcome", readiness_paths)
        self.assertIn("targets.0.returnOverrideResult", readiness_paths)
        self.assertIn("targets.0.runtime_capture.outcome", readiness_paths)
        self.assertIn("targets.0.runtime_capture.progress", readiness_paths)
        self.assertIn("targets.0.live_ops.stable", readiness_paths)
        self.assertIn("targets.0.v1_readiness.result", readiness_paths)
        self.assertIn("targets.0.v1CompletionStatus", readiness_paths)
        self.assertIn("targets.0.p0_dependency_chain.status", readiness_paths)
        self.assertIn("targets.0.readiness.approved", readiness_paths)
        self.assertIn("targets.0.v1.complete", readiness_paths)
        self.assertIn("targets.0.public_sdk.enabled", readiness_paths)
        self.assertIn("targets.0.runtime.validated", readiness_paths)
        self.assertIn("targets.0.candidate.accepted", readiness_paths)
        self.assertIn("targets.0.package_shape.passed", readiness_paths)
        self.assertIn("targets.0.support_tier.active", readiness_paths)
        self.assertIn("targets.0.plugin_hub.ready", readiness_paths)
        self.assertIn("targets.0.target_set.promoted", readiness_paths)
        self.assertFalse(payload["resource_handle_ready"])
        self.assertFalse(payload["runtime_ready"])

    def test_authorization_and_substitution_aliases_fail_closed(self) -> None:
        snapshot_payload = self.load_snapshot()
        target = snapshot_payload["targets"][0]
        target["authorizesRuntimeCapture"] = True
        target["authorizesServerRestart"] = True
        target["primaryEvidenceSubstitutionAllowed"] = True
        target["sideLaneSubstitutesForPlayerPrincipalLifecycleEvidence"] = True
        target["sideLaneCollectionCanReplacePlayerPrincipalEvidence"] = True

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            snapshot = self.write_snapshot(root, snapshot_payload)
            surfaces, events, header = self.write_public_inputs(root)
            result = self.run_checker(
                "--snapshot",
                str(snapshot),
                "--public-sdk-surfaces",
                str(surfaces),
                "--public-gameplay-events",
                str(events),
                "--public-header",
                str(header),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        self.assertIn("snapshot_readiness_flag_enabled", {blocker["reason"] for blocker in payload["blockers"]})
        readiness_paths = {
            blocker["path"]
            for blocker in payload["blockers"]
            if blocker["reason"] == "snapshot_readiness_flag_enabled"
        }
        self.assertIn("targets.0.authorizesRuntimeCapture", readiness_paths)
        self.assertIn("targets.0.authorizesServerRestart", readiness_paths)
        self.assertIn("targets.0.primaryEvidenceSubstitutionAllowed", readiness_paths)
        self.assertIn("targets.0.sideLaneSubstitutesForPlayerPrincipalLifecycleEvidence", readiness_paths)
        self.assertIn("targets.0.sideLaneCollectionCanReplacePlayerPrincipalEvidence", readiness_paths)
        self.assertFalse(payload["authorizes_runtime_capture"])
        self.assertFalse(payload["primary_evidence_substitution_allowed"])

    def test_side_lane_source_artifacts_and_target_aliases_fail_closed(self) -> None:
        snapshot_payload = self.load_snapshot()
        snapshot_payload["source_overclaim_total_flag_count"] = 0
        snapshot_payload["principal_start_end_runtime_evidence"] = {
            "ready_scope": "principal_start_end_runtime_evidence_only",
            "principal_start_end_runtime_evidence_ready": False,
            "resolved_inputs": ["runtime.lifecycle_start_end_evidence"],
        }
        snapshot_payload["passive_snapshot"] = {
            "status": "passive_snapshot_non_evidence",
            "passive_snapshot_evidence_allowed": False,
        }
        snapshot_payload["target_sets"] = ["inventory-public-sdk-ready"]
        snapshot_payload["target_set_alias"] = "inventory-runtime-ready"

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            snapshot = self.write_snapshot(root, snapshot_payload)
            surfaces, events, header = self.write_public_inputs(root)
            result = self.run_checker(
                "--snapshot",
                str(snapshot),
                "--public-sdk-surfaces",
                str(surfaces),
                "--public-gameplay-events",
                str(events),
                "--public-header",
                str(header),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("source_overclaim_zero_not_allowed", reasons)
        self.assertIn("copied_start_end_player_evidence_not_allowed", reasons)
        self.assertIn("passive_snapshot_source_not_allowed", reasons)
        self.assertIn("non_current_target_alias", reasons)
        self.assertFalse(payload["ready"])

    def test_status_shortcut_aliases_fail_closed(self) -> None:
        snapshot_payload = self.load_snapshot()
        target = snapshot_payload["targets"][0]
        target["runtime"] = {"status": "ok"}
        target["public_sdk"] = {"state": "green"}
        target["v1"] = {"result": "go"}
        surfaces_payload = {
            "surfaces": [
                {
                    "id": "obelisk.inventory_custom_filter.v1",
                    "runtime": {"status": "ok"},
                    "public_sdk": {"state": "green"},
                    "v1": {"result": "go"},
                }
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            snapshot = self.write_snapshot(root, snapshot_payload)
            surfaces, events, public_header = self.write_public_inputs(root, surfaces=surfaces_payload)
            result = self.run_checker(
                "--snapshot",
                str(snapshot),
                "--public-sdk-surfaces",
                str(surfaces),
                "--public-gameplay-events",
                str(events),
                "--public-header",
                str(public_header),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        self.assertIn("snapshot_readiness_flag_enabled", {blocker["reason"] for blocker in payload["blockers"]})
        snapshot_paths = {
            blocker["path"]
            for blocker in payload["blockers"]
            if blocker["reason"] == "snapshot_readiness_flag_enabled"
        }
        self.assertIn("targets.0.runtime.status", snapshot_paths)
        self.assertIn("targets.0.public_sdk.state", snapshot_paths)
        self.assertIn("targets.0.v1.result", snapshot_paths)
        readiness_paths = {
            offender["path"]
            for blocker in payload["blockers"]
            if blocker["reason"] == "public_readiness_leak"
            for offender in blocker["offenders"]
        }
        self.assertIn("surfaces.0.runtime.status", readiness_paths)
        self.assertIn("surfaces.0.public_sdk.state", readiness_paths)
        self.assertIn("surfaces.0.v1.result", readiness_paths)
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["v1_completion_ready"])
        self.assertEqual(0, payload["complete_sdk_claim_progress_contribution"])

    def test_additional_data_resource_handle_exposes_range_and_completion_claims_fail_closed(self) -> None:
        snapshot_payload = self.load_snapshot()
        target = snapshot_payload["targets"][0]
        array_param = target["property_chain"]["properties"][0]
        inner = array_param["array_inner_candidate"]["inner_property"]
        array_param["AdditionalData"] = {
            "ExposesRange": True,
            "ResourceHandle": "ResourceHandle ready for item lookup",
        }
        array_param["copiedRange"] = {"offset": 0, "size": 16}
        array_param["arrayPayloadBoundary"] = {
            "dataPtr": "0x4141414141414141",
            "arrayNum": 1,
        }
        inner["resource_handle"] = "ResourceHandle ready"
        target["v1_completion_evidence"] = True
        target["complete_sdk_counting_allowed"] = True
        target["counts_for_public_sdk_v1"] = True

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            snapshot = self.write_snapshot(root, snapshot_payload)
            surfaces, events, header = self.write_public_inputs(root)
            result = self.run_checker(
                "--snapshot",
                str(snapshot),
                "--public-sdk-surfaces",
                str(surfaces),
                "--public-gameplay-events",
                str(events),
                "--public-header",
                str(header),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        self.assertIn("copied_array_or_list_leak", reasons)
        self.assertIn("forbidden_snapshot_exposure", reasons)
        self.assertIn("forged_array_payload_boundary", reasons)
        self.assertIn("snapshot_readiness_flag_enabled", reasons)
        exposure_terms = {
            blocker["term"]
            for blocker in payload["blockers"]
            if blocker["reason"] == "forbidden_snapshot_exposure"
        }
        for term in ("additionaldata", "exposesrange", "resourcehandle", "resource_handle", "ResourceHandle"):
            self.assertIn(term, exposure_terms)
        readiness_paths = {
            blocker["path"]
            for blocker in payload["blockers"]
            if blocker["reason"] == "snapshot_readiness_flag_enabled"
        }
        self.assertIn("targets.0.v1_completion_evidence", readiness_paths)
        self.assertIn("targets.0.complete_sdk_counting_allowed", readiness_paths)
        self.assertIn("targets.0.counts_for_public_sdk_v1", readiness_paths)
        forged_terms = {
            blocker["term"]
            for blocker in payload["blockers"]
            if blocker["reason"] == "forged_array_payload_boundary"
        }
        self.assertIn("arraypayloadboundary", forged_terms)
        self.assertIn("dataptr", forged_terms)
        self.assertIn("arraynum", forged_terms)
        self.assertFalse(payload["resource_handle_ready"])
        self.assertFalse(payload["v1_completion_ready"])
        self.assertFalse(payload["counts_toward_complete_sdk"])

    def test_missing_array_inner_metadata_fails_closed(self) -> None:
        snapshot_payload = self.load_snapshot()
        array_param = snapshot_payload["targets"][0]["property_chain"]["properties"][1]
        del array_param["array_inner_candidate"]

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            snapshot = self.write_snapshot(root, snapshot_payload)
            surfaces, events, header = self.write_public_inputs(root)
            result = self.run_checker(
                "--snapshot",
                str(snapshot),
                "--public-sdk-surfaces",
                str(surfaces),
                "--public-gameplay-events",
                str(events),
                "--public-header",
                str(header),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        self.assertIn("array_inner_candidate_missing", reasons)
        self.assertIn("redacted_array_count_mismatch", reasons)
        self.assertIn("array_inner_classes_mismatch", reasons)

    def test_public_contract_readiness_and_header_leaks_fail_closed(self) -> None:
        surfaces_payload = {
            "surfaces": [
                {
                    "id": "obelisk.inventory_custom_filter.v1",
                    "status": "promoted",
                    "public_contract": ["InventoryCustomFilter callback"],
                    "payload_contract": ["copied InventoryCustomFilter array payload"],
                    "promotion_ready": True,
                    "public_sdk_ready": True,
                    "runtime_ready": True,
                    "v1_completion_ready": True,
                }
            ]
        }
        events_payload = {
            "promoted_events": [
                {
                    "event_id": "obelisk.inventory_custom_filter.v1",
                    "status": "supported",
                    "target_sets": [checker.TARGET_SET],
                    "public_contract": ["PrimalInventoryComponent.InventoryCustomFilter"],
                    "public_sdk_ready": True,
                }
            ]
        }
        header = "#define OBELISK_INVENTORY_CUSTOM_FILTER_READY 1\nvoid InventoryCustomFilter(void);\n"

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            surfaces, events, public_header = self.write_public_inputs(
                root,
                surfaces=surfaces_payload,
                events=events_payload,
                header=header,
            )
            result = self.run_checker(
                "--public-sdk-surfaces",
                str(surfaces),
                "--public-gameplay-events",
                str(events),
                "--public-header",
                str(public_header),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        self.assertIn("public_contract_leak", reasons)
        self.assertIn("public_readiness_leak", reasons)
        self.assertIn("public_header_token_leak", reasons)
        self.assertGreater(payload["public_contract_offender_count"], 0)
        self.assertGreater(payload["public_readiness_offender_count"], 0)
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["v1_completion_ready"])

    def test_public_manifest_positive_status_and_string_aliases_fail_closed(self) -> None:
        surfaces_payload = {
            "surfaces": [
                {
                    "id": "obelisk.inventory_custom_filter.v1",
                    "status": "promoted",
                    "public_sdk_ready": "supported",
                    "runtime_ready": "runtime-ready",
                    "runtimeValidation": "passed",
                    "resourceHandleStatus": "approved",
                    "sourceStatus": "complete",
                    "sourceTier": "approved",
                    "publicSdkStatus": "complete",
                    "mutationOutcome": "complete",
                    "returnOverrideResult": "approved",
                    "v1CompletionStatus": "complete",
                    "target_set": {"promoted": True},
                    "artifact_identity": {"approved": True},
                    "consume_gate": {"ready": True},
                    "static_evidence": {"validated": True},
                    "side_lane": {"counts_toward_v1": True},
                    "inventory": {"public_contract": True},
                    "transfer": {"runtime_ready": True},
                    "public_module": {
                        "status": "accepted",
                        "result": "validated",
                        "outcome": "ready",
                        "progress": 1,
                        "target_count": 1,
                    },
                    "sourceReady": True,
                    "sourceStatus": "accepted",
                    "source": {"ready": True, "status": "accepted", "progress": 1},
                    "v1_readiness": {"result": "v1-ready"},
                    "p0_dependency_chain": {"status": "supported"},
                    "readiness": {"approved": True},
                    "v1": {"complete": True},
                    "public_sdk": {"enabled": True},
                    "runtime": {"validated": True},
                    "candidate": {"accepted": True},
                    "package_shape": {"passed": True},
                    "support_tier": {"active": True},
                    "plugin_hub": {"ready": True},
                }
            ]
        }
        events_payload = {
            "promoted_events": [
                {
                    "event_id": "obelisk.inventory_custom_filter.v1",
                    "status": "sdk-ready",
                    "resource_handle_ready": "enabled",
                    "runtime_capture": {"outcome": "enabled", "progress": 1},
                }
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            surfaces, events, public_header = self.write_public_inputs(
                root,
                surfaces=surfaces_payload,
                events=events_payload,
            )
            result = self.run_checker(
                "--public-sdk-surfaces",
                str(surfaces),
                "--public-gameplay-events",
                str(events),
                "--public-header",
                str(public_header),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        self.assertIn("public_readiness_leak", {blocker["reason"] for blocker in payload["blockers"]})
        readiness_paths = {
            offender["path"]
            for blocker in payload["blockers"]
            if blocker["reason"] == "public_readiness_leak"
            for offender in blocker["offenders"]
        }
        self.assertIn("surfaces.0.status", readiness_paths)
        self.assertIn("surfaces.0.public_sdk_ready", readiness_paths)
        self.assertIn("surfaces.0.runtime_ready", readiness_paths)
        self.assertIn("surfaces.0.runtimeValidation", readiness_paths)
        self.assertIn("surfaces.0.resourceHandleStatus", readiness_paths)
        self.assertIn("surfaces.0.sourceStatus", readiness_paths)
        self.assertIn("surfaces.0.sourceTier", readiness_paths)
        self.assertIn("surfaces.0.publicSdkStatus", readiness_paths)
        self.assertIn("surfaces.0.mutationOutcome", readiness_paths)
        self.assertIn("surfaces.0.returnOverrideResult", readiness_paths)
        self.assertIn("surfaces.0.v1CompletionStatus", readiness_paths)
        self.assertIn("surfaces.0.target_set.promoted", readiness_paths)
        self.assertIn("surfaces.0.artifact_identity.approved", readiness_paths)
        self.assertIn("surfaces.0.consume_gate.ready", readiness_paths)
        self.assertIn("surfaces.0.static_evidence.validated", readiness_paths)
        self.assertIn("surfaces.0.side_lane.counts_toward_v1", readiness_paths)
        self.assertIn("surfaces.0.inventory.public_contract", readiness_paths)
        self.assertIn("surfaces.0.transfer.runtime_ready", readiness_paths)
        self.assertIn("surfaces.0.public_module.status", readiness_paths)
        self.assertIn("surfaces.0.public_module.result", readiness_paths)
        self.assertIn("surfaces.0.public_module.outcome", readiness_paths)
        self.assertIn("surfaces.0.public_module.progress", readiness_paths)
        self.assertNotIn("surfaces.0.public_module.target_count", readiness_paths)
        self.assertIn("surfaces.0.sourceReady", readiness_paths)
        self.assertIn("surfaces.0.sourceStatus", readiness_paths)
        self.assertIn("surfaces.0.source.ready", readiness_paths)
        self.assertIn("surfaces.0.source.status", readiness_paths)
        self.assertIn("surfaces.0.source.progress", readiness_paths)
        self.assertIn("surfaces.0.v1_readiness.result", readiness_paths)
        self.assertIn("surfaces.0.p0_dependency_chain.status", readiness_paths)
        self.assertIn("surfaces.0.readiness.approved", readiness_paths)
        self.assertIn("surfaces.0.v1.complete", readiness_paths)
        self.assertIn("surfaces.0.public_sdk.enabled", readiness_paths)
        self.assertIn("surfaces.0.runtime.validated", readiness_paths)
        self.assertIn("surfaces.0.candidate.accepted", readiness_paths)
        self.assertIn("surfaces.0.package_shape.passed", readiness_paths)
        self.assertIn("surfaces.0.support_tier.active", readiness_paths)
        self.assertIn("surfaces.0.plugin_hub.ready", readiness_paths)
        self.assertIn("promoted_events.0.status", readiness_paths)
        self.assertIn("promoted_events.0.resource_handle_ready", readiness_paths)
        self.assertIn("promoted_events.0.runtime_capture.outcome", readiness_paths)
        self.assertIn("promoted_events.0.runtime_capture.progress", readiness_paths)
        self.assertGreater(payload["public_readiness_offender_count"], 0)
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])

    def test_nested_positive_package_plugin_support_and_resource_aliases_fail_closed(self) -> None:
        surfaces_payload = {
            "surfaces": [
                {
                    "id": "obelisk.inventory_custom_filter.v1",
                    "candidate_metadata": {
                        "review_notes": [
                            "public SDK ready for custom filter array side lane",
                            "runtime/v1 support is active for custom filter array side lane",
                            "package-shape ready for custom filter array side lane",
                            "support tier ready for custom filter array side lane",
                            "Plugin Hub ready for custom filter array side lane",
                            "item mutation ready for custom filter array side lane",
                            "return override ready for custom filter array side lane",
                            "resource handle support for custom filter array side lane",
                        ],
                        "packageShapeReady": True,
                        "supportTierStatus": "approved",
                        "pluginHubStatus": "ready",
                    },
                }
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            surfaces, events, public_header = self.write_public_inputs(root, surfaces=surfaces_payload)
            result = self.run_checker(
                "--public-sdk-surfaces",
                str(surfaces),
                "--public-gameplay-events",
                str(events),
                "--public-header",
                str(public_header),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("public_positive_claim_leak", reasons)
        self.assertIn("public_readiness_leak", reasons)
        terms = {
            offender["term"]
            for blocker in payload["blockers"]
            if blocker["reason"] == "public_positive_claim_leak"
            for offender in blocker["offenders"]
        }
        for term in (
            "public SDK",
            "runtime/v1 support",
            "package shape",
            "support tier",
            "Plugin Hub",
            "item mutation",
            "return override",
            "resource handle",
        ):
            self.assertIn(term, terms)
        readiness_paths = {
            offender["path"]
            for blocker in payload["blockers"]
            if blocker["reason"] == "public_readiness_leak"
            for offender in blocker["offenders"]
        }
        self.assertIn("surfaces.0.candidate_metadata.packageShapeReady", readiness_paths)
        self.assertIn("surfaces.0.candidate_metadata.supportTierStatus", readiness_paths)
        self.assertIn("surfaces.0.candidate_metadata.pluginHubStatus", readiness_paths)
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["v1_completion_ready"])

    def test_source_label_and_source_labels_positive_aliases_fail_closed(self) -> None:
        snapshot_payload = self.load_snapshot()
        target = snapshot_payload["targets"][0]
        target["sourceLabel"] = "ready"
        target["sourceLabels"] = ["candidate-only", "supported"]
        surfaces_payload = {
            "surfaces": [
                {
                    "id": "obelisk.inventory_custom_filter.v1",
                    "sourceLabel": "ready",
                    "sourceLabels": ["candidate-only", "supported"],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            snapshot = self.write_snapshot(root, snapshot_payload)
            surfaces, events, public_header = self.write_public_inputs(root, surfaces=surfaces_payload)
            result = self.run_checker(
                "--snapshot",
                str(snapshot),
                "--public-sdk-surfaces",
                str(surfaces),
                "--public-gameplay-events",
                str(events),
                "--public-header",
                str(public_header),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("snapshot_readiness_flag_enabled", {blocker["reason"] for blocker in payload["blockers"]})
        snapshot_paths = {
            blocker["path"]
            for blocker in payload["blockers"]
            if blocker["reason"] == "snapshot_readiness_flag_enabled"
        }
        self.assertIn("targets.0.sourceLabel", snapshot_paths)
        self.assertIn("targets.0.sourceLabels.1", snapshot_paths)
        readiness_paths = {
            offender["path"]
            for blocker in payload["blockers"]
            if blocker["reason"] == "public_readiness_leak"
            for offender in blocker["offenders"]
        }
        self.assertIn("surfaces.0.sourceLabel", readiness_paths)
        self.assertIn("surfaces.0.sourceLabels.1", readiness_paths)
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertEqual(0, payload["complete_sdk_claim_progress_contribution"])

    def test_source_marker_and_source_markers_positive_aliases_fail_closed(self) -> None:
        snapshot_payload = self.load_snapshot()
        target = snapshot_payload["targets"][0]
        target["sourceMarker"] = "ready"
        target["sourceMarkers"] = ["candidate-only", "supported"]
        surfaces_payload = {
            "surfaces": [
                {
                    "id": "obelisk.inventory_custom_filter.v1",
                    "sourceMarker": "ready",
                    "sourceMarkers": ["candidate-only", "supported"],
                }
            ]
        }
        events_payload = {
            "promoted_events": [
                {
                    "event_id": "obelisk.inventory_custom_filter.v1",
                    "sourceMarker": "ready",
                    "sourceMarkers": ["candidate-only", "supported"],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            snapshot = self.write_snapshot(root, snapshot_payload)
            surfaces, events, public_header = self.write_public_inputs(
                root,
                surfaces=surfaces_payload,
                events=events_payload,
            )
            result = self.run_checker(
                "--snapshot",
                str(snapshot),
                "--public-sdk-surfaces",
                str(surfaces),
                "--public-gameplay-events",
                str(events),
                "--public-header",
                str(public_header),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("snapshot_readiness_flag_enabled", {blocker["reason"] for blocker in payload["blockers"]})
        snapshot_paths = {
            blocker["path"]
            for blocker in payload["blockers"]
            if blocker["reason"] == "snapshot_readiness_flag_enabled"
        }
        self.assertIn("targets.0.sourceMarker", snapshot_paths)
        self.assertIn("targets.0.sourceMarkers.1", snapshot_paths)
        readiness_paths = {
            offender["path"]
            for blocker in payload["blockers"]
            if blocker["reason"] == "public_readiness_leak"
            for offender in blocker["offenders"]
        }
        self.assertIn("surfaces.0.sourceMarker", readiness_paths)
        self.assertIn("surfaces.0.sourceMarkers.1", readiness_paths)
        self.assertIn("promoted_events.0.sourceMarker", readiness_paths)
        self.assertIn("promoted_events.0.sourceMarkers.1", readiness_paths)
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertEqual(0, payload["complete_sdk_claim_progress_contribution"])

    def test_rejects_symlinked_snapshot_input_before_reading(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            snapshot_payload = self.load_snapshot()
            snapshot = self.write_snapshot(root, snapshot_payload)
            snapshot_link = root / "InventoryCustomFilter.snapshot.link.json"
            snapshot_link.symlink_to(snapshot)
            surfaces, events, header = self.write_public_inputs(root)
            result = self.run_checker(
                "--snapshot",
                str(snapshot_link),
                "--public-sdk-surfaces",
                str(surfaces),
                "--public-gameplay-events",
                str(events),
                "--public-header",
                str(header),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        self.assertIn("snapshot_path_rejected", {blocker["reason"] for blocker in payload["blockers"]})
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["v1_completion_ready"])

    def test_rejects_symlinked_public_header_before_scanning(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            surfaces, events, header = self.write_public_inputs(root)
            header_link = root / "ObeliskApi.link.h"
            header_link.symlink_to(header)
            result = self.run_checker(
                "--public-sdk-surfaces",
                str(surfaces),
                "--public-gameplay-events",
                str(events),
                "--public-header",
                str(header_link),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        self.assertIn("public_header_path_rejected", {blocker["reason"] for blocker in payload["blockers"]})
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["v1_completion_ready"])

    def test_rejects_symlinked_public_json_inputs_before_scanning(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            surfaces, events, header = self.write_public_inputs(root)
            surfaces_link = root / "public_sdk_surfaces.link.json"
            events_link = root / "public_gameplay_events.link.json"
            surfaces_link.symlink_to(surfaces)
            events_link.symlink_to(events)
            result = self.run_checker(
                "--public-sdk-surfaces",
                str(surfaces_link),
                "--public-gameplay-events",
                str(events_link),
                "--public-header",
                str(header),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("public_sdk_surfaces_path_rejected", reasons)
        self.assertIn("public_gameplay_events_path_rejected", reasons)
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["v1_completion_ready"])

    def test_positive_public_inventory_sdk_and_raw_claims_fail_closed(self) -> None:
        surfaces_payload = {
            "surfaces": [
                {
                    "id": "obelisk.inventory_review",
                    "status": "candidate-only",
                    "public_contract": ["Inventory SDK ready for raw array range callbacks"],
                    "payload_contract": ["AdditionalData exposes item identity and raw params"],
                    "scope": "mutation and return override ready",
                    "exclusions": ["Items SDK", "ResourceHandle"],
                }
            ]
        }
        events_payload = {
            "promoted_events": [
                {
                    "event_id": "obelisk.inventory_review",
                    "resource_contract": "runtime readiness with ItemNetID lookup",
                    "non_claims": ["No Inventory SDK, no Items SDK, no AdditionalData exposure."],
                }
            ]
        }
        header = "#define OBELISK_INVENTORY_SDK_READY 1\n"

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            surfaces, events, public_header = self.write_public_inputs(
                root,
                surfaces=surfaces_payload,
                events=events_payload,
                header=header,
            )
            result = self.run_checker(
                "--public-sdk-surfaces",
                str(surfaces),
                "--public-gameplay-events",
                str(events),
                "--public-header",
                str(public_header),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        self.assertIn("public_positive_claim_leak", reasons)
        self.assertGreater(payload["public_positive_claim_offender_count"], 0)
        offender_terms = {
            offender["term"]
            for blocker in payload["blockers"]
            if blocker["reason"] == "public_positive_claim_leak"
            for offender in blocker["offenders"]
        }
        for term in (
            "Inventory SDK",
            "AdditionalData",
            "item identity",
            "raw params",
            "mutation",
            "return override",
            "ItemNetID",
            "lookup",
        ):
            self.assertIn(term, offender_terms)
        self.assertFalse(payload["inventory_sdk_ready"])
        self.assertFalse(payload["items_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["v1_completion_ready"])

    def test_copied_signal_planning_alias_claims_and_completion_count_fail_closed(self) -> None:
        surfaces_payload = {
            "surfaces": [
                {
                    "id": "obelisk.inventory_item_copied_signals.v1",
                    "status": "promoted-experimental-only",
                    "support_tier": "promoted-experimental-only copied-data seed",
                    "aliases": [
                        "Inventory SDK public alias",
                        "item mutation ready",
                        "return override ready",
                        "item identity lookup ready",
                        "countsTowardCompleteSdkClaim",
                        "countsForPublicSdkV1",
                        "contributes to v1 completion",
                    ],
                    "countsTowardCompleteSdkClaim": True,
                    "countsForPublicSdkV1": True,
                    "v1CompletionContribution": True,
                }
            ]
        }
        events_payload = {
            "promoted_events": [
                {
                    "event_id": "obelisk.inventory_item_copied_signals.v1",
                    "source_marker": "accepted copied-signal planning only",
                    "aliases": ["Inventory SDK readiness through copied signals"],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            surfaces, events, public_header = self.write_public_inputs(
                root,
                surfaces=surfaces_payload,
                events=events_payload,
            )
            result = self.run_checker(
                "--public-sdk-surfaces",
                str(surfaces),
                "--public-gameplay-events",
                str(events),
                "--public-header",
                str(public_header),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        self.assertIn("public_positive_claim_leak", reasons)
        self.assertIn("public_readiness_leak", reasons)
        offender_terms = {
            offender["term"]
            for blocker in payload["blockers"]
            if blocker["reason"] == "public_positive_claim_leak"
            for offender in blocker["offenders"]
        }
        for term in (
            "Inventory SDK",
            "item mutation",
            "return override",
            "item identity",
            "lookup",
            "countsTowardCompleteSdkClaim",
            "countsForPublicSdkV1",
            "contributes to v1 completion",
        ):
            self.assertIn(term, offender_terms)
        readiness_paths = {
            offender["path"]
            for blocker in payload["blockers"]
            if blocker["reason"] == "public_readiness_leak"
            for offender in blocker["offenders"]
        }
        self.assertIn("surfaces.0.countsTowardCompleteSdkClaim", readiness_paths)
        self.assertIn("surfaces.0.countsForPublicSdkV1", readiness_paths)
        self.assertIn("surfaces.0.v1CompletionContribution", readiness_paths)
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["v1_completion_ready"])
        self.assertFalse(payload["counts_toward_complete_sdk"])
        self.assertFalse(payload["counts_toward_complete_sdk_claim"])

    def test_negated_copied_signal_side_lane_alias_text_is_allowed(self) -> None:
        surfaces_payload = {
            "surfaces": [
                {
                    "id": "obelisk.inventory_item_copied_signals.v1",
                    "status": "promoted-experimental-only",
                    "support_tier": "promoted-experimental-only copied-data seed",
                    "aliases": [
                        (
                            "inventory_item_copied_signals remains non-public copied-signal planning only; "
                            "no Inventory SDK, no item mutation, no return override, no item identity, "
                            "no lookup, no countsTowardCompleteSdkClaim, no countsForPublicSdkV1, "
                            "and no v1 completion contribution"
                        )
                    ],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            surfaces, events, public_header = self.write_public_inputs(root, surfaces=surfaces_payload)
            result = self.run_checker(
                "--public-sdk-surfaces",
                str(surfaces),
                "--public-gameplay-events",
                str(events),
                "--public-header",
                str(public_header),
                "--json",
            )

        payload = json.loads(result.stdout)
        self.assertTrue(payload["ready"])
        self.assertEqual([], payload["blockers"])

if __name__ == "__main__":
    unittest.main()
