#!/usr/bin/env python3
"""Tests for check_mission_copied_bool_readiness.py."""

from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_mission_copied_bool_readiness.py"
sys.path.insert(0, str(SCRIPT_DIR))
import check_mission_copied_bool_readiness as checker  # noqa: E402


class CheckMissionCopiedBoolReadinessTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def make_policy(self) -> dict:
        snapshots = [
            {
                "id": "snapshot-0001",
                "sha256": "1" * 64,
                "target": "MissionType.AddPlayerToMission",
            },
            {
                "id": "snapshot-0002",
                "sha256": "2" * 64,
                "target": "MissionType.BPAllowPlayerToLeaveMission",
            },
            {
                "id": "snapshot-0003",
                "sha256": "3" * 64,
                "target": "MissionType.BPOnPlayerRemovedFromMission",
            },
            {
                "id": "snapshot-0004",
                "sha256": "4" * 64,
                "target": "MissionType.GetPlayerUsableItems",
            },
        ]
        snapshot_by_target = {snapshot["target"]: snapshot for snapshot in snapshots}
        copied_shapes = {
            "MissionType.AddPlayerToMission.bForceAdd": {
                "field": "bForceAdd",
                "direction": "in",
                "offset": "0x8",
                "offset_internal": 8,
                "property_flags": "0x1040000280",
                "return_value_offset": "0x9",
            },
            "MissionType.AddPlayerToMission.ReturnValue": {
                "field": "ReturnValue",
                "direction": "return",
                "offset": "0x9",
                "offset_internal": 9,
                "property_flags": "0x1040000780",
                "return_value_offset": "0x9",
            },
            "MissionType.BPAllowPlayerToLeaveMission.ReturnValue": {
                "field": "ReturnValue",
                "direction": "return",
                "offset": "0x8",
                "offset_internal": 8,
                "property_flags": "0x1040000780",
                "return_value_offset": "0x8",
            },
            "MissionType.BPOnPlayerRemovedFromMission.bFromMissionCompleteEvent": {
                "field": "bFromMissionCompleteEvent",
                "direction": "in",
                "offset": "0x10",
                "offset_internal": 16,
                "property_flags": "0x1040000280",
                "return_value_offset": "0xffff",
            },
            "MissionType.BPOnPlayerRemovedFromMission.bLastPhaseSuccess": {
                "field": "bLastPhaseSuccess",
                "direction": "in",
                "offset": "0x11",
                "offset_internal": 17,
                "property_flags": "0x1040000280",
                "return_value_offset": "0xffff",
            },
        }
        redacted_shapes = {
            "MissionType.AddPlayerToMission.PlayerCharacter": {
                "field": "PlayerCharacter",
                "property_class": "ObjectProperty",
                "offset": "0x0",
                "offset_internal": 0,
                "element_size": 8,
                "array_dim": 1,
                "property_flags": "0x1040000280",
            },
            "MissionType.BPAllowPlayerToLeaveMission.PlayerPawn": {
                "field": "PlayerPawn",
                "property_class": "ObjectProperty",
                "offset": "0x0",
                "offset_internal": 0,
                "element_size": 8,
                "array_dim": 1,
                "property_flags": "0x1040000280",
            },
            "MissionType.BPOnPlayerRemovedFromMission.Player": {
                "field": "Player",
                "property_class": "ObjectProperty",
                "offset": "0x0",
                "offset_internal": 0,
                "element_size": 8,
                "array_dim": 1,
                "property_flags": "0x1040000280",
            },
            "MissionType.BPOnPlayerRemovedFromMission.Controller": {
                "field": "Controller",
                "property_class": "ObjectProperty",
                "offset": "0x8",
                "offset_internal": 8,
                "element_size": 8,
                "array_dim": 1,
                "property_flags": "0x1040000280",
            },
            "MissionType.GetPlayerUsableItems.Character": {
                "field": "Character",
                "property_class": "ObjectProperty",
                "offset": "0x0",
                "offset_internal": 0,
                "element_size": 8,
                "array_dim": 1,
                "property_flags": "0x1040000280",
            },
            "MissionType.GetPlayerUsableItems.OutItemIDs": {
                "field": "OutItemIDs",
                "property_class": "ArrayProperty",
                "offset": "0x8",
                "offset_internal": 8,
                "element_size": 16,
                "array_dim": 1,
                "property_flags": "0x380",
            },
        }
        copied_fields = [
            "MissionType.AddPlayerToMission.bForceAdd",
            "MissionType.AddPlayerToMission.ReturnValue",
            "MissionType.BPAllowPlayerToLeaveMission.ReturnValue",
            "MissionType.BPOnPlayerRemovedFromMission.bFromMissionCompleteEvent",
            "MissionType.BPOnPlayerRemovedFromMission.bLastPhaseSuccess",
        ]
        redacted_fields = [
            "MissionType.AddPlayerToMission.PlayerCharacter",
            "MissionType.BPAllowPlayerToLeaveMission.PlayerPawn",
            "MissionType.BPOnPlayerRemovedFromMission.Player",
            "MissionType.BPOnPlayerRemovedFromMission.Controller",
            "MissionType.GetPlayerUsableItems.Character",
            "MissionType.GetPlayerUsableItems.OutItemIDs",
        ]

        def copied(copied_field: str) -> dict:
            target = copied_field.rsplit(".", 1)[0]
            snapshot = snapshot_by_target[target]
            return {
                "array_dim": 1,
                "bool_byte_offset": 0,
                "bool_field_size": 1,
                "byte_mask": "0x01",
                "copied_field": copied_field,
                "element_size": 1,
                "evidence_status": "copied-mission-bool-only",
                "field_mask": "0xff",
                "native_bool": False,
                "property_class": "BoolProperty",
                "source_snapshot": snapshot["id"],
                "source_snapshot_sha256": snapshot["sha256"],
                "target": target,
                "type": "bool",
                **copied_shapes[copied_field],
            }

        def redacted(redacted_field: str) -> dict:
            target = redacted_field.rsplit(".", 1)[0]
            snapshot = snapshot_by_target[target]
            return {
                "evidence_status": "recognition-only-redacted",
                "reason": "unit_test_redacted",
                "redacted_field": redacted_field,
                "source_snapshot": snapshot["id"],
                "source_snapshot_sha256": snapshot["sha256"],
                "target": target,
                **redacted_shapes[redacted_field],
            }

        return {
            "schema": "obelisk.mission-copied-bool-policy-slice.v1",
            "snapshot_root": "redacted",
            "input_target_set": "mission-compact-intake",
            "output_target_set": "mission-copied-bool-policy-slice",
            "policy_status": "evidence-only",
            "missing_targets": [],
            "coverage": {
                "status": "complete",
                "input_targets": [
                    "MissionType.AddPlayerToMission",
                    "MissionType.BPAllowPlayerToLeaveMission",
                    "MissionType.BPOnPlayerRemovedFromMission",
                    "MissionType.GetPlayerUsableItems",
                ],
                "copied_targets": [
                    "MissionType.AddPlayerToMission",
                    "MissionType.BPAllowPlayerToLeaveMission",
                    "MissionType.BPOnPlayerRemovedFromMission",
                ],
                "copied_fields": copied_fields,
                "redacted_fields": redacted_fields,
            },
            "copied_bools": [copied(field) for field in copied_fields],
            "redacted_mission_fields": [redacted(field) for field in redacted_fields],
            "generated_from": {
                "snapshot_schema": "obelisk.ufunction-chain.snapshot.v1",
                "input_snapshots": snapshots,
            },
            "safety_summary": {
                "artifact_status": "evidence_only",
                "intended_use": "offline_review_only",
                "promotion_ready": False,
                "copied_bool_count": 5,
                "redacted_field_count": 6,
                "explicitly_excluded": [
                    "GetPlayerUsableItems.OutItemIDs",
                    "Mission SDK",
                    "arrays",
                    "dispatcher_wiring",
                    "hook_wiring",
                    "mission_identity",
                    "mutation",
                    "object_refs",
                    "player_identity",
                    "public_sdk",
                    "raw_params",
                    "resource_handle",
                    "return_override",
                    "runtime_markers",
                ],
            },
            "non_claims": [
                "does not expose UE pointers, object identity, class identity, raw params, mutation, or return overrides",
                "does not promote public SDK callbacks or public metadata helpers",
                "does not promote runtime hook wiring, dispatcher wiring, mission payload decoding, or public Mission SDK",
                "does not copy player/controller/character object refs, OutItemIDs arrays, mission identity, player identity, or ResourceHandle",
            ],
        }

    def write_pack(self, root: Path, payload: dict | None = None) -> tuple[Path, str]:
        root.mkdir(parents=True, exist_ok=True)
        manifest = root / "mission-copied-bool-policy-slice.json"
        content = json.dumps(payload if payload is not None else self.make_policy(), sort_keys=True).encode("utf-8")
        manifest.write_bytes(content)
        return manifest, hashlib.sha256(content).hexdigest()

    def checker_args(self, root: Path, manifest: Path, sha256: str) -> list[str]:
        return [
            "--root",
            str(root),
            "--manifest",
            str(manifest),
            "--expected-manifest-sha256",
            sha256,
            "--skip-artifact-gates",
        ]

    def write_minimal_public_frontier_repo(
        self,
        root: Path,
        *,
        cmake: str | None = None,
        api_header: str | None = None,
        public_gameplay_events: dict | None = None,
        plugin_manager: str | None = None,
        plugin_manager_guardrails: str | None = None,
    ) -> None:
        (root / "include" / "obelisk").mkdir(parents=True, exist_ok=True)
        (root / "core").mkdir(parents=True, exist_ok=True)
        (root / "docs").mkdir(parents=True, exist_ok=True)
        (root / "scripts").mkdir(parents=True, exist_ok=True)
        (root / "CMakeLists.txt").write_text(
            cmake
            if cmake is not None
            else """
add_library(obelisk SHARED
    hooks/ProcessEventStructureReflection.cpp
)
add_executable(process_event_mission_reflection_tests
    tests/core/ProcessEventMissionReflectionTests.cpp
    hooks/ProcessEventMissionReflection.cpp
)
""",
            encoding="utf-8",
        )
        (root / "include" / "obelisk" / "ObeliskApi.h").write_text(
            api_header
            if api_header is not None
            else """
#pragma once
#define OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS (1ull << 6)
typedef struct ObeliskGameplayPolicyEvent ObeliskGameplayPolicyEvent;
""",
            encoding="utf-8",
        )
        (root / "docs" / "public_gameplay_events.json").write_text(
            json.dumps(
                public_gameplay_events
                if public_gameplay_events is not None
                else {
                    "schema": "obelisk.public-gameplay-events.v1",
                    "metadata_surfaces": [],
                    "promoted_events": [],
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        (root / "core" / "PluginManager.cpp").write_text(
            plugin_manager
            if plugin_manager is not None
            else """
namespace Obelisk {
bool PluginManager::UnregisterPluginCallbacks(const std::string& pluginName, void* owner, const char* reason)
{
    return EventManager::Get().UnregisterCallbacksForOwner(owner) == 0 || true;
}
}
""",
            encoding="utf-8",
        )
        (root / "scripts" / "test_plugin_manager_guardrails.py").write_text(
            plugin_manager_guardrails
            if plugin_manager_guardrails is not None
            else """
COPIED_DISPATCHER_CLEANUP_EXCEPTIONS = {
    "MissionCopiedBoolEventDispatcher": (
        "internal/test-only copied lifecycle dispatcher; not plugin-facing until owner cleanup"
    ),
}
COPIED_DISPATCHER_PUBLIC_ABI_TOKENS = {
    "MissionCopiedBoolEventDispatcher": ("RegisterMission", "UnregisterMission"),
}
""",
            encoding="utf-8",
        )

    def test_default_pack_is_candidate_ready_but_not_public_or_runtime_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            manifest, sha256 = self.write_pack(root)
            result = self.run_checker(*self.checker_args(root, manifest, sha256), "--json")
            payload = json.loads(result.stdout)

        self.assertEqual(payload["schema"], "obelisk.mission-copied-bool-readiness-check.v1")
        self.assertEqual(payload["status"], "candidate_ready")
        self.assertTrue(payload["ready"])
        self.assertEqual(checker.NON_AUTHORIZING_READY_SCOPE, payload["ready_scope"])
        self.assertTrue(
            set(checker.NON_AUTHORIZING_READY_DOES_NOT_SATISFY)
            <= set(payload["does_not_satisfy_readiness"])
        )
        self.assertTrue(payload["accepted_for_internal_planning"])
        self.assertTrue(payload["consume_only"])
        self.assertTrue(payload["internal_reusable_evidence_only"])
        self.assertTrue(payload["not_artifact_gate"])
        self.assertEqual("approved_runtime_evidence_missing", payload["current_sdk_blocker"])
        self.assertEqual(["approved_runtime_evidence_missing"], payload["remaining_blockers"])
        self.assertFalse(payload["approved_runtime_evidence_ready"])
        self.assertFalse(payload["runtime_evidence_ready"])
        self.assertFalse(payload["player_principal_runtime_evidence_ready"])
        self.assertFalse(payload["clears_approved_runtime_evidence_missing"])
        self.assertFalse(payload["counts_as_approved_runtime_evidence"])
        self.assertFalse(payload["replaces_player_principal_evidence"])
        self.assertEqual(0, payload["sdk_progress"])
        self.assertEqual(0, payload["sdk_progress_contribution"])
        self.assertFalse(payload["p0_dependency_chain_ready"])
        self.assertFalse(payload["counts_toward_p0_dependency_chain_claim"])
        self.assertEqual(0, payload["p0_dependency_chain_claim_progress_contribution"])
        beta_capture = payload["beta_capture_prep"]
        self.assertEqual("future_capture_targets_only", beta_capture["status"])
        self.assertEqual("mission_copied_bool", beta_capture["surface"])
        self.assertEqual("dedicated_beta_capture_check_required", beta_capture["capture_gate"])
        self.assertFalse(beta_capture["approved_runtime_evidence_ready"])
        self.assertFalse(beta_capture["runtime_evidence_ready"])
        self.assertFalse(beta_capture["clears_approved_runtime_evidence_missing"])
        self.assertFalse(beta_capture["player_principal_runtime_evidence_ready"])
        self.assertFalse(beta_capture["replaces_player_principal_evidence"])
        self.assertFalse(beta_capture["public_sdk_ready"])
        self.assertFalse(beta_capture["runtime_ready"])
        self.assertFalse(beta_capture["p0_dependency_chain_ready"])
        self.assertFalse(beta_capture["counts_toward_p0_dependency_chain_claim"])
        self.assertEqual(0, beta_capture["sdk_progress"])
        self.assertEqual(4, len(beta_capture["targets"]))
        self.assertFalse(payload["mission_sdk_ready"])
        self.assertFalse(payload["public_abi_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_observer_approved"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["identity_ready"])
        self.assertFalse(payload["lookup_ready"])
        self.assertFalse(payload["mutation_ready"])
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["resource_handle_ready"])
        self.assertFalse(payload["return_override_ready"])
        self.assertFalse(payload["runtime_capture_ready"])
        self.assertFalse(payload["candidate_capture_evidence_ready"])
        self.assertFalse(payload["debug_capture_evidence_ready"])
        self.assertEqual(0, payload["candidate_capture_progress_contribution"])
        self.assertFalse(payload["complete_sdk_ready"])
        self.assertFalse(payload["counts_toward_complete_sdk_claim"])
        self.assertEqual(0, payload["complete_sdk_claim_progress_contribution"])
        self.assertFalse(payload["v1_completion"])
        self.assertEqual(payload["consume_gate"]["status"], "skipped")
        self.assertEqual(payload["promote_gate"]["status"], "skipped")
        self.assertEqual(payload["fixture_policy_regeneration"]["status"], "accepted")
        self.assertTrue(payload["fixture_policy_regeneration"]["summary"]["get_player_usable_items_recognition_only"])
        self.assertEqual(payload["repo_public_runtime_frontier"]["status"], "accepted")
        self.assertTrue(payload["repo_public_runtime_frontier"]["mission_internal_test_only"])
        self.assertEqual(payload["attestation"]["schema"], "obelisk.mission-copied-bool-offline-attestation.v1")
        self.assertEqual(payload["attestation"]["status"], "not_attested")
        self.assertFalse(payload["attestation"]["attestation_ready"])
        self.assertFalse(payload["attestation"]["consume_gate_proven"])
        self.assertFalse(payload["attestation"]["promote_block_proven"])
        self.assertTrue(payload["attestation"]["fixture_policy_regeneration_proven"])
        self.assertTrue(payload["attestation"]["repo_public_runtime_frontier_proven"])
        self.assertTrue(payload["attestation"]["frontier_proven"])
        self.assertFalse(payload["attestation"]["mission_sdk_ready"])
        self.assertFalse(payload["attestation"]["public_abi_ready"])
        self.assertFalse(payload["attestation"]["public_sdk_ready"])
        self.assertFalse(payload["attestation"]["runtime_ready"])
        self.assertFalse(payload["attestation"]["resource_handle_ready"])
        self.assertFalse(payload["attestation"]["return_override_ready"])
        self.assertFalse(payload["attestation"]["approved_runtime_evidence_ready"])
        self.assertFalse(payload["attestation"]["clears_approved_runtime_evidence_missing"])
        self.assertFalse(payload["attestation"]["replaces_player_principal_evidence"])
        self.assertEqual(["approved_runtime_evidence_missing"], payload["attestation"]["remaining_blockers"])
        self.assertFalse(payload["attestation"]["runtime_capture_ready"])
        self.assertFalse(payload["attestation"]["candidate_capture_evidence_ready"])
        self.assertFalse(payload["attestation"]["debug_capture_evidence_ready"])
        self.assertEqual(0, payload["attestation"]["candidate_capture_progress_contribution"])
        self.assertFalse(payload["attestation"]["v1_completion"])
        self.assertEqual(len(payload["summary"]["input_targets"]), 4)
        self.assertEqual(len(payload["summary"]["copied_targets"]), 3)
        self.assertEqual(len(payload["summary"]["copied_fields"]), 5)
        self.assertEqual(len(payload["summary"]["redacted_fields"]), 6)
        self.assertEqual(payload["summary"]["copied_bool_count"], 5)
        self.assertEqual(payload["summary"]["redacted_field_count"], 6)
        self.assertTrue(payload["summary"]["get_player_usable_items_recognition_only"])
        self.assertIn("candidate readiness is exactly consume-only internal reusable evidence", " ".join(payload["non_claims"]))
        self.assertIn("candidate readiness is internal planning evidence only", " ".join(payload["non_claims"]))
        self.assertIn(
            "candidate/debug captures before checker acceptance are non-evidence and non-progress",
            " ".join(payload["non_claims"]),
        )
        self.assertIn("beta capture prep is future target planning only", " ".join(payload["non_claims"]))
        self.assertIn("does not clear approved_runtime_evidence_missing", " ".join(payload["non_claims"]))
        self.assertIn("Mission copied-bool recognizer remains SHA-gated", " ".join(payload["non_claims"]))

    def test_fixture_boundary_only_validates_regenerated_policy_without_artifact_claims(self) -> None:
        result = self.run_checker("--fixture-boundary-only", "--json")
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertEqual(payload["schema"], "obelisk.mission-copied-bool-readiness-check.v1")
        self.assertEqual(payload["mode"], "fixture_boundary_only")
        self.assertEqual(payload["status"], "fixture_boundary_ready")
        self.assertTrue(payload["ready"])
        self.assertEqual(checker.NON_AUTHORIZING_READY_SCOPE, payload["ready_scope"])
        self.assertTrue(
            set(checker.NON_AUTHORIZING_READY_DOES_NOT_SATISFY)
            <= set(payload["does_not_satisfy_readiness"])
        )
        self.assertTrue(payload["fixture_boundary_only"])
        self.assertTrue(payload["fixture_boundary_ready"])
        self.assertFalse(payload["root_inspected"])
        self.assertFalse(payload["manifest_inspected"])
        self.assertFalse(payload["artifact_gates_run"])
        self.assertEqual(["approved_runtime_evidence_missing"], payload["remaining_blockers"])
        self.assertFalse(payload["approved_runtime_evidence_ready"])
        self.assertFalse(payload["clears_approved_runtime_evidence_missing"])
        self.assertFalse(payload["replaces_player_principal_evidence"])
        self.assertEqual("future_capture_targets_only", payload["beta_capture_prep"]["status"])
        self.assertEqual(payload["consume_gate"]["status"], "not_run_fixture_boundary_only")
        self.assertEqual(payload["promote_gate"]["status"], "not_run_fixture_boundary_only")
        self.assertEqual(payload["repo_public_runtime_frontier"]["status"], "not_run_fixture_boundary_only")
        self.assertEqual(payload["fixture_policy_regeneration"]["status"], "accepted")
        self.assertFalse(payload["attestation"]["attestation_ready"])
        self.assertFalse(payload["attestation"]["consume_gate_proven"])
        self.assertFalse(payload["attestation"]["promote_block_proven"])
        self.assertFalse(payload["attestation"]["repo_public_runtime_frontier_proven"])
        self.assertFalse(payload["mission_sdk_ready"])
        self.assertFalse(payload["public_abi_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["resource_handle_ready"])
        self.assertFalse(payload["runtime_capture_ready"])
        self.assertFalse(payload["candidate_capture_evidence_ready"])
        self.assertFalse(payload["debug_capture_evidence_ready"])
        self.assertEqual(0, payload["candidate_capture_progress_contribution"])
        self.assertFalse(payload["p0_dependency_chain_ready"])
        self.assertFalse(payload["counts_toward_p0_dependency_chain_claim"])
        self.assertFalse(payload["v1_completion"])
        self.assertEqual(payload["summary"]["copied_bool_count"], 5)
        self.assertTrue(payload["summary"]["get_player_usable_items_recognition_only"])
        self.assertIn(
            "fixture-boundary mode does not inspect copied artifact roots or manifests",
            " ".join(payload["non_claims"]),
        )
        self.assertIn("Mission copied-bool recognizer remains SHA-gated", " ".join(payload["non_claims"]))

    def test_fixture_boundary_only_does_not_inspect_protected_root_or_manifest_arguments(self) -> None:
        result = self.run_checker(
            "--fixture-boundary-only",
            "--root",
            "/servidor/ark/obelisk/artifacts/mission",
            "--manifest",
            "/servidor/ark/obelisk/artifacts/mission/manifest.json",
            "--json",
        )
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertEqual(payload["status"], "fixture_boundary_ready")
        self.assertFalse(payload["root_inspected"])
        self.assertFalse(payload["manifest_inspected"])
        self.assertNotIn("path_rejected", {blocker["reason"] for blocker in payload["blockers"]})
        self.assertFalse(payload["attestation"]["attestation_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["v1_completion"])

    def test_attestation_proves_consume_promote_and_fixture_frontier_when_hash_pin_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            manifest, sha256 = self.write_pack(root)
            with mock.patch.object(checker, "EXPECTED_MANIFEST_SHA256", sha256):
                payload = checker.build_report(root, manifest, sha256)

        self.assertTrue(payload["ready"])
        self.assertEqual(payload["consume_gate"]["status"], "accepted")
        self.assertEqual(payload["promote_gate"]["status"], "blocked")
        self.assertIn(
            "promote_mode_mission_copied_bool_policy_slice_evidence_only",
            payload["promote_gate"]["blocker_reasons"],
        )
        self.assertIn("promote_mode_manifest_has_non_claims", payload["promote_gate"]["blocker_reasons"])

        attestation = payload["attestation"]
        self.assertEqual(attestation["status"], "attested")
        self.assertTrue(attestation["attestation_ready"])
        self.assertTrue(attestation["reviewed_hash_pinned"])
        self.assertTrue(attestation["consume_gate_proven"])
        self.assertTrue(attestation["promote_block_proven"])
        self.assertTrue(attestation["fixture_policy_regeneration_proven"])
        self.assertTrue(attestation["repo_public_runtime_frontier_proven"])
        self.assertTrue(attestation["frontier_proven"])
        self.assertEqual(attestation["actual_manifest_sha256"], sha256)
        self.assertEqual(attestation["reviewed_direct_policy_manifest_sha256"], sha256)
        self.assertEqual(attestation["frontier"]["copied_target_count"], 3)
        self.assertEqual(attestation["frontier"]["copied_bool_count"], 5)
        self.assertEqual(attestation["frontier"]["redacted_field_count"], 6)
        self.assertTrue(attestation["frontier"]["get_player_usable_items_recognition_only"])
        self.assertEqual(
            attestation["frontier"]["copied_targets"],
            [
                "MissionType.AddPlayerToMission",
                "MissionType.BPAllowPlayerToLeaveMission",
                "MissionType.BPOnPlayerRemovedFromMission",
            ],
        )
        self.assertNotIn(
            "MissionType.GetPlayerUsableItems",
            attestation["frontier"]["copied_targets"],
        )
        self.assertTrue(attestation["consume_only"])
        self.assertTrue(attestation["internal_reusable_evidence_only"])
        self.assertFalse(attestation["mission_sdk_ready"])
        self.assertFalse(attestation["public_abi_ready"])
        self.assertFalse(attestation["public_sdk_ready"])
        self.assertFalse(attestation["runtime_observer_approved"])
        self.assertFalse(attestation["runtime_ready"])
        self.assertFalse(attestation["identity_ready"])
        self.assertFalse(attestation["lookup_ready"])
        self.assertFalse(attestation["mutation_ready"])
        self.assertFalse(attestation["promotion_ready"])
        self.assertFalse(attestation["resource_handle_ready"])
        self.assertFalse(attestation["return_override_ready"])
        self.assertFalse(attestation["approved_runtime_evidence_ready"])
        self.assertFalse(attestation["clears_approved_runtime_evidence_missing"])
        self.assertFalse(attestation["replaces_player_principal_evidence"])
        self.assertEqual(["approved_runtime_evidence_missing"], attestation["remaining_blockers"])
        self.assertFalse(attestation["runtime_capture_ready"])
        self.assertFalse(attestation["candidate_capture_evidence_ready"])
        self.assertFalse(attestation["debug_capture_evidence_ready"])
        self.assertEqual(0, attestation["candidate_capture_progress_contribution"])
        self.assertFalse(attestation["v1_completion"])

    def test_get_player_usable_items_copied_field_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["coverage"]["copied_targets"].append("MissionType.GetPlayerUsableItems")
            payload["coverage"]["copied_fields"].append("MissionType.GetPlayerUsableItems.OutItemIDs")
            payload["copied_bools"].append(
                {
                    **payload["copied_bools"][0],
                    "target": "MissionType.GetPlayerUsableItems",
                    "copied_field": "MissionType.GetPlayerUsableItems.OutItemIDs",
                    "field": "OutItemIDs",
                }
            )
            manifest, sha256 = self.write_pack(root, payload)

            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("copied_target_coverage_mismatch", reasons)
        self.assertIn("copied_field_coverage_mismatch", reasons)
        self.assertIn("forbidden_copied_field", reasons)
        self.assertIn("get_player_usable_items_copied_target_not_allowed", reasons)
        self.assertIn("get_player_usable_items_copied_field_not_allowed", reasons)

    def test_noncanonical_bool_tail_metadata_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["copied_bools"][0]["native_bool"] = True
            payload["copied_bools"][0]["byte_mask"] = "0xff"
            manifest, sha256 = self.write_pack(root, payload)

            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("copied_bool_entry_metadata_mismatch", reasons)
        self.assertIn("mission_copied_bool_policy_copied_bool_shape_mismatch", reasons)

    def test_stale_manifest_without_bool_tail_metadata_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            for entry in payload["copied_bools"]:
                del entry["bool_field_size"]
                del entry["bool_byte_offset"]
            manifest, sha256 = self.write_pack(root, payload)

            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("copied_bool_entry_metadata_mismatch", reasons)
        self.assertIn("mission_copied_bool_policy_copied_bool_shape_mismatch", reasons)

    def test_copied_bool_source_snapshot_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["copied_bools"][0]["source_snapshot_sha256"] = "f" * 64
            payload["copied_bools"][1]["source_snapshot"] = "snapshot-0004"
            manifest, sha256 = self.write_pack(root, payload)

            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("copied_bool_entry_source_snapshot_sha256_mismatch", reasons)
        self.assertIn("copied_bool_entry_source_snapshot_target_mismatch", reasons)

    def test_redacted_source_snapshot_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["redacted_mission_fields"][0]["source_snapshot"] = "unknown-snapshot"
            payload["redacted_mission_fields"][1]["target"] = "MissionType.GetPlayerUsableItems"
            manifest, sha256 = self.write_pack(root, payload)

            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("redacted_mission_field_source_snapshot_unknown", reasons)
        self.assertIn("redacted_mission_field_source_snapshot_target_mismatch", reasons)

    def test_generated_from_snapshot_target_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["generated_from"]["input_snapshots"][0]["target"] = "PrimalItem.CanUse"
            manifest, sha256 = self.write_pack(root, payload)

            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("input_snapshot_target_invalid", reasons)
        self.assertIn("input_snapshot_targets_mismatch", reasons)

    def test_manifest_hash_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            manifest, _ = self.write_pack(root)
            result = self.run_checker(
                *self.checker_args(root, manifest, "0" * 64),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("manifest_sha256_mismatch", {blocker["reason"] for blocker in report["blockers"]})

    def test_promote_gate_must_stay_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["non_claims"] = []
            manifest, sha256 = self.write_pack(root, payload)

            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("required_non_claim_missing", reasons)
        self.assertIn("required_non_claim_missing", reasons)
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_public_runtime_and_artifact_gate_claims_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["not_artifact_gate"] = False
            payload["consume_only"] = False
            payload["public_mission_sdk_ready"] = True
            payload["runtime_ready"] = True
            payload["mission_identity_ready"] = True
            payload["player_authority_ready"] = True
            payload["runtime_claim"] = "runtime ready with public Mission SDK"
            payload["identity_claim"] = "mission identity established"
            payload["authority_claim"] = "player authority promoted"
            payload["safety_summary"]["public_sdk_ready"] = True
            payload["safety_summary"]["runtime_hook_ready"] = True
            manifest, sha256 = self.write_pack(root, payload)

            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("not_artifact_gate_contradiction", reasons)
        self.assertIn("consume_only_not_true", reasons)
        self.assertIn("readiness_overclaim", reasons)
        self.assertIn("runtime_public_readiness_overclaim", reasons)
        self.assertIn("runtime_public_claim_overclaim", reasons)
        self.assertIn("mission_copied_bool_policy_public_overclaim_public_sdk", reasons)
        self.assertIn("mission_copied_bool_policy_public_overclaim_runtime_ready", reasons)
        self.assertIn("mission_copied_bool_policy_public_overclaim_mission_identity", reasons)
        self.assertIn("mission_copied_bool_policy_public_overclaim_player_authority", reasons)

    def test_candidate_surface_overclaims_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["public_abi_ready"] = True
            payload["v1_completion"] = True
            payload["surface_claims"] = {
                "mutation": "mutation supported",
                "return_override": "return override enabled",
                "runtime_hooks": "runtime hooks enabled",
                "public_abi": "public ABI ready",
                "v1": "v1 complete",
            }
            manifest, sha256 = self.write_pack(root, payload)

            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        claims = {blocker.get("claim") for blocker in report["blockers"]}
        self.assertIn("runtime_public_readiness_overclaim", reasons)
        self.assertIn("mission_candidate_claim_overclaim", reasons)
        self.assertTrue({"mutation", "return_override", "runtime_hooks", "public_abi", "v1_completion"} <= claims)

    def test_candidate_debug_capture_overclaims_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["candidate_capture_ready"] = True
            payload["candidate_capture_evidence_ready"] = True
            payload["candidate_capture_progress_contribution"] = 1
            payload["runtime_capture_ready"] = True
            payload["resource_handle_ready"] = True
            payload["capture_plan"] = (
                "Candidate capture is ready evidence. Debug capture counts toward runtime support. "
                "Candidate capture enables ResourceHandle. Candidate capture enables mutation. "
                "Candidate capture enables return override. Candidate capture enables runtime support."
            )
            payload["non_claims"].append("candidate capture enables ResourceHandle")
            manifest, sha256 = self.write_pack(root, payload)

            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("runtime_public_readiness_overclaim", reasons)
        self.assertIn("mission_candidate_capture_overclaim", reasons)
        self.assertIn("mission_candidate_claim_overclaim", reasons)
        self.assertIn("mission_allowed_prefix_affirmative_overclaim", reasons)
        readiness_fields = {
            blocker.get("field")
            for blocker in report["blockers"]
            if blocker["reason"] == "runtime_public_readiness_overclaim"
        }
        self.assertTrue(
            {
                "$.candidate_capture_ready",
                "$.candidate_capture_evidence_ready",
                "$.runtime_capture_ready",
                "$.resource_handle_ready",
            }
            <= readiness_fields
        )
        claims = {
            blocker.get("claim")
            for blocker in report["blockers"]
            if blocker["reason"] == "mission_candidate_claim_overclaim"
        }
        self.assertTrue(
            {
                "candidate_capture_progress_contribution",
                "resource_handle",
                "mutation",
                "return_override",
                "runtime_ready",
            }
            <= claims
        )
        self.assertFalse(report["resource_handle_ready"])
        self.assertFalse(report["runtime_capture_ready"])
        self.assertFalse(report["candidate_capture_evidence_ready"])
        self.assertEqual(0, report["candidate_capture_progress_contribution"])

    def test_candidate_only_beta_capture_prep_is_allowed_without_artifact_claims(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["beta_capture_prep"] = checker.build_beta_capture_prep()
            manifest, sha256 = self.write_pack(root, payload)

            result = self.run_checker(*self.checker_args(root, manifest, sha256))

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["ready"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertFalse(report["clears_approved_runtime_evidence_missing"])
        self.assertFalse(report["replaces_player_principal_evidence"])
        self.assertFalse(report["p0_dependency_chain_ready"])
        self.assertEqual(0, report["sdk_progress"])
        self.assertEqual("future_capture_targets_only", report["beta_capture_prep"]["status"])

    def test_multi_surface_beta_capture_pack_overclaims_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["multi_surface_beta_capture_pack"] = {
                "status": "future_capture_targets_only",
                "surface": "mission_copied_bool",
                "capture_gate": "dedicated_beta_capture_check_required",
                "approved_runtime_evidence_ready": True,
                "clears_approved_runtime_evidence_missing": True,
                "player_principal_runtime_evidence_ready": True,
                "replaces_player_principal_evidence": True,
                "resource_handle_ready": True,
                "mutation_authority_ready": True,
                "return_value_override_ready": True,
                "counts_toward_p0_dependency_chain_claim": True,
                "sdk_progress": 1,
                "targets": [
                    {
                        "target": "MissionType.AddPlayerToMission",
                        "status": "future_capture_target",
                        "approved_runtime_evidence_ready": True,
                        "replaces_player_principal_evidence": True,
                        "sdk_progress": 1,
                    }
                ],
            }
            payload["capture_plan"] = (
                "Multi-surface beta capture pack is approved runtime evidence. "
                "Mission beta capture clears approved_runtime_evidence_missing and replaces player-principal lifecycle evidence. "
                "Beta capture counts toward P0 dependency chain and enables return value override."
            )
            payload["non_claims"].append("beta capture enables return override")
            manifest, sha256 = self.write_pack(root, payload)

            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("beta_capture_readiness_overclaim", reasons)
        self.assertIn("runtime_public_readiness_overclaim", reasons)
        self.assertIn("mission_candidate_capture_overclaim", reasons)
        self.assertIn("mission_candidate_claim_overclaim", reasons)
        self.assertIn("mission_allowed_prefix_affirmative_overclaim", reasons)
        paths = {
            blocker.get("path") or blocker.get("field")
            for blocker in report["blockers"]
            if blocker["reason"] in {"beta_capture_readiness_overclaim", "runtime_public_readiness_overclaim"}
        }
        self.assertIn("$.multi_surface_beta_capture_pack.approved_runtime_evidence_ready", paths)
        self.assertIn("$.multi_surface_beta_capture_pack.clears_approved_runtime_evidence_missing", paths)
        self.assertIn("$.multi_surface_beta_capture_pack.sdk_progress", paths)
        claims = {
            blocker.get("claim")
            for blocker in report["blockers"]
            if blocker["reason"] == "mission_candidate_claim_overclaim"
        }
        self.assertTrue(
            {
                "approved_runtime_evidence",
                "player_principal_evidence",
                "p0_dependency_chain",
                "return_override",
                "sdk_progress",
            }
            <= claims
        )
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertFalse(report["clears_approved_runtime_evidence_missing"])
        self.assertFalse(report["replaces_player_principal_evidence"])
        self.assertFalse(report["resource_handle_ready"])
        self.assertFalse(report["return_override_ready"])
        self.assertFalse(report["p0_dependency_chain_ready"])

    def test_allowed_non_claim_and_exclusion_fields_reject_affirmative_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["safety_summary"]["explicitly_excluded"].extend(
                [
                    "Mission SDK unlocked",
                    "ResourceHandle lookup available",
                ]
            )
            payload["non_claims"].append("return override supported")
            manifest, sha256 = self.write_pack(root, payload)

            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        blockers = [
            blocker
            for blocker in report["blockers"]
            if blocker["reason"] == "mission_allowed_prefix_affirmative_overclaim"
        ]
        self.assertEqual(len(blockers), 3)
        claims = {blocker["claim"] for blocker in blockers}
        self.assertEqual(claims, {"Mission SDK", "ResourceHandle", "return override"})

    def test_support_and_umbrella_leaf_claim_aliases_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["support_tier"] = "active"
            payload["runtime_support"] = "unlocked"
            payload["v1_support"] = "unblocked"
            payload["surface_claims"] = {
                "umbrella": "umbrella leaf promotion is ready",
            }
            manifest, sha256 = self.write_pack(root, payload)

            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        blockers = [
            blocker
            for blocker in report["blockers"]
            if blocker["reason"] == "mission_candidate_claim_overclaim"
        ]
        claims = {blocker["claim"] for blocker in blockers}
        self.assertTrue(
            {"support_tier", "runtime_support", "v1_support", "umbrella_leaf_promotion"} <= claims
        )
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["v1_completion"])

    def test_source_label_and_source_labels_positive_aliases_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["sourceLabel"] = "ready"
            payload["sourceLabels"] = ["candidate-only", "supported"]
            manifest, sha256 = self.write_pack(root, payload)

            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        blockers = [
            blocker
            for blocker in report["blockers"]
            if blocker["reason"] == "mission_candidate_claim_overclaim"
        ]
        fields = {blocker["field"] for blocker in blockers}
        self.assertIn("$.sourceLabel", fields)
        self.assertIn("$.sourceLabels[1]", fields)
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["v1_completion"])

    def test_nested_public_runtime_status_result_outcome_aliases_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["public_module"] = {
                "status": "accepted",
                "result": "validated",
                "outcome": "ready",
                "progress": 1,
                "credits": 1,
                "unlocked": True,
            }
            payload["runtime_capture"] = {"outcome": "enabled", "unblocked": True}
            payload["v1_readiness"] = {"result": "v1-ready"}
            payload["p0_dependency_chain"] = {"status": "supported"}
            payload["readiness"] = {"approved": True}
            payload["v1"] = {"complete": True}
            payload["public_sdk"] = {"enabled": True}
            payload["runtime"] = {"validated": True}
            payload["candidate"] = {"accepted": True}
            payload["package_shape"] = {"passed": True}
            payload["support_tier"] = {"active": True}
            payload["plugin_hub"] = {"ready": True}
            payload["target_set"] = {"promoted": True}
            manifest, sha256 = self.write_pack(root, payload)

            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        blockers = [
            blocker
            for blocker in report["blockers"]
            if blocker["reason"] == "mission_candidate_claim_overclaim"
        ]
        fields = {blocker["field"] for blocker in blockers}
        self.assertTrue(
            {
                "$.public_module.status",
                "$.public_module.result",
                "$.public_module.outcome",
                "$.public_module.progress",
                "$.public_module.credits",
                "$.public_module.unlocked",
                "$.runtime_capture.outcome",
                "$.runtime_capture.unblocked",
                "$.v1_readiness.result",
                "$.p0_dependency_chain.status",
                "$.readiness.approved",
                "$.v1.complete",
                "$.public_sdk.enabled",
                "$.runtime.validated",
                "$.candidate.accepted",
                "$.package_shape.passed",
                "$.support_tier.active",
                "$.plugin_hub.ready",
                "$.target_set.promoted",
            }
            <= fields
        )
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["v1_completion"])

    def test_numeric_count_and_ratio_progress_aliases_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload.update(
                {
                    "publicSdkCount": 1,
                    "sdkCount": 1,
                    "stableSdkCount": 1,
                    "runtimeCount": 1,
                    "publicSdkSurfaceCount": 1,
                    "completeSdkCount": 1,
                    "completeSdkClaimCount": 1,
                    "p0DependencyChainCount": 1,
                    "completeSdkClaimProgressRatio": "1/12",
                    "p0DependencyChainClaimProgressRatio": "1/4",
                    "publicSdkProgress": "1/12",
                    "v1CompletionProgress": "1/8",
                }
            )
            manifest, sha256 = self.write_pack(root, payload)

            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        blockers = [
            blocker
            for blocker in report["blockers"]
            if blocker["reason"] == "mission_candidate_claim_overclaim"
        ]
        fields = {blocker["field"] for blocker in blockers}
        self.assertTrue(
            {
                "$.publicSdkCount",
                "$.sdkCount",
                "$.stableSdkCount",
                "$.runtimeCount",
                "$.publicSdkSurfaceCount",
                "$.completeSdkCount",
                "$.completeSdkClaimCount",
                "$.p0DependencyChainCount",
                "$.completeSdkClaimProgressRatio",
                "$.p0DependencyChainClaimProgressRatio",
                "$.publicSdkProgress",
                "$.v1CompletionProgress",
            }
            <= fields
        )
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["v1_completion"])

    def test_priority_lane_stays_internal_reuse_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["priority"] = {
                "lane": "mission",
                "recommended_scope": "public Mission SDK",
                "runtime": "runtime hook ready",
            }
            manifest, sha256 = self.write_pack(root, payload)

            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        claims = {blocker.get("claim") for blocker in report["blockers"]}
        self.assertIn("runtime_public_claim_overclaim", reasons)
        self.assertIn("mission_candidate_claim_overclaim", reasons)
        self.assertTrue({"public_sdk", "runtime_hooks"} <= claims)
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_repo_frontier_blocks_mission_hook_in_runtime_or_shared_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "repo"
            self.write_minimal_public_frontier_repo(
                repo_root,
                cmake="""
add_library(obelisk SHARED
    loader/Bootstrap.cpp
    hooks/ProcessEventMissionReflection.cpp
)
target_sources(obelisk_runtime PRIVATE hooks/ProcessEventMissionReflection.cpp)
""",
            )
            blockers: list[dict] = []
            frontier = checker.validate_offline_repo_frontier(repo_root, blockers)

        self.assertEqual(frontier["status"], "blocked")
        self.assertFalse(frontier["mission_internal_test_only"])
        self.assertIn("mission_hook_in_runtime_or_shared_target", {blocker["reason"] for blocker in blockers})
        self.assertIn("obelisk", {blocker.get("target") for blocker in blockers})
        self.assertIn("obelisk_runtime", {blocker.get("target") for blocker in blockers})

    def test_repo_frontier_blocks_nested_cmake_mission_hook_runtime_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "repo"
            self.write_minimal_public_frontier_repo(
                repo_root,
                cmake="add_subdirectory(runtime)\n",
            )
            runtime_dir = repo_root / "runtime"
            runtime_dir.mkdir()
            (runtime_dir / "CMakeLists.txt").write_text(
                "add_library(obelisk SHARED ../hooks/ProcessEventMissionReflection.cpp)\n",
                encoding="utf-8",
            )
            blockers: list[dict] = []
            frontier = checker.validate_offline_repo_frontier(repo_root, blockers)

        self.assertEqual(frontier["status"], "blocked")
        self.assertFalse(frontier["mission_internal_test_only"])
        self.assertIn("mission_hook_in_runtime_or_shared_target", {blocker["reason"] for blocker in blockers})
        self.assertIn(str(repo_root / "runtime" / "CMakeLists.txt"), frontier["cmake"]["paths"])

    def test_repo_frontier_blocks_public_mission_api_and_docs_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "repo"
            self.write_minimal_public_frontier_repo(
                repo_root,
                api_header="""
#pragma once
#define OBELISK_API_CAPABILITY_MISSION_EVENTS (1ull << 12)
typedef struct ObeliskMissionEvent ObeliskMissionEvent;
""",
                public_gameplay_events={
                    "schema": "obelisk.public-gameplay-events.v1",
                    "metadata_surfaces": [
                        {
                            "surface_id": "obelisk.mission_event_descriptors.v1",
                            "public_name": "DescribeMissionEventKind",
                        }
                    ],
                    "promoted_events": [
                        {
                            "event_id": "obelisk.mission.v1",
                            "event_kinds": ["OBELISK_GAMEPLAY_POLICY_EVENT_KIND_MISSION_ADD_PLAYER"],
                        }
                    ],
                },
            )
            blockers: list[dict] = []
            frontier = checker.validate_offline_repo_frontier(repo_root, blockers)

        reasons = {blocker["reason"] for blocker in blockers}
        self.assertEqual(frontier["status"], "blocked")
        self.assertIn("public_mission_sdk_symbol_in_api_header", reasons)
        self.assertIn("public_mission_gameplay_event_or_descriptor", reasons)
        self.assertIn("mission_public_frontier_missing_plugin_manager_owner_cleanup", reasons)
        self.assertIn("mission_public_frontier_missing_owner_cleanup_guardrail", reasons)

    def test_repo_frontier_blocks_register_mission_api_without_owner_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "repo"
            self.write_minimal_public_frontier_repo(
                repo_root,
                api_header="""
#pragma once
typedef unsigned long long uint64_t;
typedef struct ObeliskApi {
    uint64_t (*RegisterMissionCopiedBoolEventWithOwnerTokenHandle)(void* token);
    bool (*UnregisterMissionCopiedBoolEventWithOwnerToken)(void* token, uint64_t handle);
} ObeliskApi;
""",
            )
            blockers: list[dict] = []
            frontier = checker.validate_offline_repo_frontier(repo_root, blockers)

        reasons = {blocker["reason"] for blocker in blockers}
        api_symbols = {blocker.get("symbol") for blocker in blockers}
        self.assertEqual(frontier["status"], "blocked")
        self.assertFalse(frontier["mission_internal_test_only"])
        self.assertIn("public_mission_sdk_symbol_in_api_header", reasons)
        self.assertIn("mission_public_frontier_missing_plugin_manager_owner_cleanup", reasons)
        self.assertIn("mission_public_frontier_missing_owner_cleanup_guardrail", reasons)
        self.assertIn(
            "mission_public_frontier_still_internal_test_only_cleanup_exception",
            reasons,
        )
        self.assertIn("RegisterMissionCopiedBoolEventWithOwnerTokenHandle", api_symbols)
        self.assertTrue(frontier["mission_public_frontier_owner_cleanup"]["public_frontier_detected"])
        self.assertFalse(frontier["mission_public_frontier_owner_cleanup"]["owner_cleanup_present"])

    def test_repo_frontier_allows_mission_terms_in_not_promoted_doc_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "repo"
            self.write_minimal_public_frontier_repo(
                repo_root,
                public_gameplay_events={
                    "schema": "obelisk.public-gameplay-events.v1",
                    "metadata_surfaces": [
                        {
                            "surface_id": "obelisk.gameplay_policy_event_descriptors.v1",
                            "not_promoted": ["Mission SDK", "Mission callbacks"],
                            "non_claims": ["does not promote public Mission SDK"],
                        }
                    ],
                    "promoted_events": [],
                },
            )
            blockers: list[dict] = []
            frontier = checker.validate_offline_repo_frontier(repo_root, blockers)

        self.assertEqual(frontier["status"], "accepted")
        self.assertTrue(frontier["mission_internal_test_only"])
        self.assertNotIn("public_mission_gameplay_event_or_descriptor", {blocker["reason"] for blocker in blockers})

    def test_repo_frontier_blocks_plugin_manager_mission_wiring_without_owner_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "repo"
            self.write_minimal_public_frontier_repo(
                repo_root,
                plugin_manager="""
namespace Obelisk {
uint64_t PluginRegisterMissionCopiedBoolEventWithOwnerTokenHandle(void* token) { return 0; }
bool PluginUnregisterMissionCopiedBoolEventWithOwnerToken(void* token, uint64_t handle) { return false; }
bool PluginManager::UnregisterPluginCallbacks(const std::string& pluginName, void* owner, const char* reason)
{
    return EventManager::Get().UnregisterCallbacksForOwner(owner) == 0 || true;
}
PluginManager::PluginManager()
{
    m_Api.RegisterMissionCopiedBoolEventWithOwnerTokenHandle =
        &PluginRegisterMissionCopiedBoolEventWithOwnerTokenHandle;
}
}
""",
            )
            blockers: list[dict] = []
            frontier = checker.validate_offline_repo_frontier(repo_root, blockers)

        reasons = {blocker["reason"] for blocker in blockers}
        symbols = {blocker.get("symbol") for blocker in blockers}
        self.assertEqual(frontier["status"], "blocked")
        self.assertIn("mission_plugin_facing_wiring_in_plugin_manager", reasons)
        self.assertIn("mission_public_frontier_missing_plugin_manager_owner_cleanup", reasons)
        self.assertIn("mission_public_frontier_missing_owner_cleanup_guardrail", reasons)
        self.assertIn("PluginRegisterMissionCopiedBoolEventWithOwnerTokenHandle", symbols)
        self.assertTrue(frontier["mission_public_frontier_owner_cleanup"]["public_frontier_detected"])

    def test_repo_frontier_requires_matching_guardrail_when_owner_cleanup_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "repo"
            self.write_minimal_public_frontier_repo(
                repo_root,
                api_header="""
#pragma once
typedef unsigned long long uint64_t;
typedef struct ObeliskApi {
    uint64_t (*RegisterMissionCopiedBoolEventWithOwnerTokenHandle)(void* token);
} ObeliskApi;
""",
                plugin_manager="""
namespace Obelisk {
bool PluginManager::UnregisterPluginCallbacks(const std::string& pluginName, void* owner, const char* reason)
{
    MissionCopiedBoolEventDispatcher::Get().UnregisterCallbacksForOwner(owner);
    return true;
}
}
""",
            )
            blockers: list[dict] = []
            frontier = checker.validate_offline_repo_frontier(repo_root, blockers)

        reasons = {blocker["reason"] for blocker in blockers}
        self.assertEqual(frontier["status"], "blocked")
        self.assertIn("public_mission_sdk_symbol_in_api_header", reasons)
        self.assertNotIn("mission_public_frontier_missing_plugin_manager_owner_cleanup", reasons)
        self.assertIn("mission_public_frontier_missing_owner_cleanup_guardrail", reasons)
        self.assertIn(
            "mission_public_frontier_still_internal_test_only_cleanup_exception",
            reasons,
        )
        self.assertTrue(frontier["mission_public_frontier_owner_cleanup"]["owner_cleanup_present"])

    def test_report_readiness_frontier_blocks_public_runtime_identity_mutation_and_return_override(self) -> None:
        report = {
            "ready": True,
            "public_sdk_ready": True,
            "runtime_ready": True,
            "identity_ready": True,
            "mutation_ready": True,
            "return_override_ready": True,
            "attestation": {
                "public_abi_ready": True,
                "runtime_observer_approved": True,
            },
        }
        blockers: list[dict] = []

        checker.validate_report_readiness_frontier(report, blockers)

        fields = {blocker.get("field") for blocker in blockers}
        self.assertIn("$.public_sdk_ready", fields)
        self.assertIn("$.runtime_ready", fields)
        self.assertIn("$.identity_ready", fields)
        self.assertIn("$.mutation_ready", fields)
        self.assertIn("$.return_override_ready", fields)
        self.assertIn("$.attestation.public_abi_ready", fields)
        self.assertIn("$.attestation.runtime_observer_approved", fields)

    def test_protected_and_symlink_inputs_are_rejected(self) -> None:
        result = self.run_checker(
            "--root",
            "/servidor/ark/obelisk/artifacts/mission",
            "--manifest",
            "/servidor/ark/obelisk/artifacts/mission/manifest.json",
            check=False,
        )
        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("path_rejected", {blocker["reason"] for blocker in report["blockers"]})

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            manifest, sha256 = self.write_pack(root)
            link = Path(temp_dir) / "manifest-link.json"
            link.symlink_to(manifest)
            result = self.run_checker(*self.checker_args(root, link, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("path_rejected", {blocker["reason"] for blocker in report["blockers"]})


if __name__ == "__main__":
    unittest.main()
