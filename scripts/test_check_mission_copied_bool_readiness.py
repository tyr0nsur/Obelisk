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
    ) -> None:
        (root / "include" / "obelisk").mkdir(parents=True, exist_ok=True)
        (root / "docs").mkdir(parents=True, exist_ok=True)
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

    def test_default_pack_is_candidate_ready_but_not_public_or_runtime_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            manifest, sha256 = self.write_pack(root)
            result = self.run_checker(*self.checker_args(root, manifest, sha256), "--json")
            payload = json.loads(result.stdout)

        self.assertEqual(payload["schema"], "obelisk.mission-copied-bool-readiness-check.v1")
        self.assertEqual(payload["status"], "candidate_ready")
        self.assertTrue(payload["ready"])
        self.assertTrue(payload["accepted_for_internal_planning"])
        self.assertTrue(payload["consume_only"])
        self.assertTrue(payload["internal_reusable_evidence_only"])
        self.assertTrue(payload["not_artifact_gate"])
        self.assertFalse(payload["mission_sdk_ready"])
        self.assertFalse(payload["public_abi_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_observer_approved"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["identity_ready"])
        self.assertFalse(payload["lookup_ready"])
        self.assertFalse(payload["mutation_ready"])
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["return_override_ready"])
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
        self.assertFalse(attestation["return_override_ready"])
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
