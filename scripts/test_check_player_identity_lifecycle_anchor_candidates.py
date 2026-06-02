#!/usr/bin/env python3
"""Tests for check_player_identity_lifecycle_anchor_candidates.py."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_player_identity_lifecycle_anchor_candidates.py"
SHA = "a" * 64


def base_anchor(role: str, target: str) -> dict:
    outer, _, function = target.rpartition(".")
    return {
        "role": role,
        "target": target,
        "outer": outer,
        "function": function,
        "acceptance_status": "candidate_recorded",
        "accepted": False,
        "function_flags": "0x00000000",
        "num_parms": 1,
        "parms_size": 4,
        "return_value_offset": "0xffffffff",
        "property_order": ["bWasSuccessful"],
        "fields": [
            {
                "name": "bWasSuccessful",
                "source_property_class": "BoolProperty",
                "direction": "out",
                "offset": "0x0",
                "element_size": 1,
                "array_dim": 1,
                "classification": "copied_candidate",
                "copied_scalar_eligibility": "candidate_non_identity_scalar",
                "bool_masks": {"byte_mask": "0x01", "field_mask": "0xff"},
            }
        ],
        "evidence": {
            "source_snapshot": "snapshot-0001",
            "source_snapshot_sha256": SHA,
            "snapshot_schema": "obelisk.ufunction-chain.snapshot.v1",
            "source_kind": "sanitized_snapshot",
            "binary_sha256": SHA,
        },
        "corroboration": {
            "status": "missing",
            "second_source_report_sha256": None,
            "static_report_sha256": None,
        },
        "blockers": ["layout_not_accepted"],
    }


def lifecycle_layout_anchor(role: str, target: str) -> dict:
    anchor = base_anchor(role, target)
    anchor["accepted"] = True
    anchor["acceptance_status"] = "layout_accepted_candidate_only"
    anchor["corroboration"]["status"] = "second_source_accepted"
    anchor["blockers"] = []
    if target == "ShooterGameMode.HandleNewPlayer":
        anchor["num_parms"] = 5
        anchor["parms_size"] = 26
        anchor["property_order"] = ["NewPlayer", "PlayerData", "PlayerCharacter", "bIsFromLogin", "ReturnValue"]
        anchor["fields"] = [
            {
                "name": "NewPlayer",
                "source_property_class": "ObjectProperty",
                "direction": "in",
                "offset": "0x0",
                "element_size": 8,
                "array_dim": 1,
                "classification": "recognition_only",
                "copied_scalar_eligibility": "recognition_only_object",
            },
            {
                "name": "PlayerData",
                "source_property_class": "ObjectProperty",
                "direction": "in",
                "offset": "0x8",
                "element_size": 8,
                "array_dim": 1,
                "classification": "recognition_only",
                "copied_scalar_eligibility": "recognition_only_object",
            },
            {
                "name": "PlayerCharacter",
                "source_property_class": "ObjectProperty",
                "direction": "in",
                "offset": "0x10",
                "element_size": 8,
                "array_dim": 1,
                "classification": "recognition_only",
                "copied_scalar_eligibility": "recognition_only_object",
            },
            {
                "name": "bIsFromLogin",
                "source_property_class": "BoolProperty",
                "direction": "in",
                "offset": "0x18",
                "element_size": 1,
                "array_dim": 1,
                "classification": "copied_candidate",
                "copied_scalar_eligibility": "candidate_non_identity_scalar",
                "bool_masks": {"byte_mask": "0x01", "field_mask": "0xff"},
            },
            {
                "name": "ReturnValue",
                "source_property_class": "BoolProperty",
                "direction": "out",
                "offset": "0x19",
                "element_size": 1,
                "array_dim": 1,
                "classification": "copied_candidate",
                "copied_scalar_eligibility": "candidate_non_identity_scalar",
                "bool_masks": {"byte_mask": "0x01", "field_mask": "0xff"},
            },
        ]
    elif target == "ShooterGameMode.OnLogout":
        anchor["num_parms"] = 1
        anchor["parms_size"] = 8
        anchor["property_order"] = ["Exiting"]
        anchor["fields"] = [
            {
                "name": "Exiting",
                "source_property_class": "ObjectProperty",
                "direction": "in",
                "offset": "0x0",
                "element_size": 8,
                "array_dim": 1,
                "classification": "recognition_only",
                "copied_scalar_eligibility": "recognition_only_object",
            }
        ]
    else:
        raise AssertionError(f"unknown lifecycle target {target}")
    return anchor


def manifest() -> dict:
    return {
        "schema": "obelisk.players-identity-lifecycle-anchor-candidates.v1",
        "artifact_status": "candidate_only",
        "readiness_classification": "planning_only",
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "input_target_set": "players-identity-lifecycle-intake",
        "snapshot_root": "redacted",
        "artifact_identity": {
            "ark_binary_sha256": SHA,
            "obelisk_commit": "reviewed-commit",
            "build_type": "sanitized_snapshot",
            "target_set_revision": "reflection_target_sets.py:players-identity-lifecycle-intake",
            "source_artifact_ids": [
                f"artifact_sha256:{SHA}",
                "capture_id:player-lifecycle-candidates",
                "evidence_pack_id:player-lifecycle-pack",
            ],
            "path_redacted": True,
        },
        "candidate_anchors": [
            base_anchor("session_start", "MissionType.AddPlayerToMission"),
            base_anchor("session_end", "MissionType.BPAllowPlayerToLeaveMission"),
        ],
        "lifecycle_acceptance": {
            "session_start_accepted": False,
            "session_end_accepted": False,
            "accepted_start_targets": [],
            "accepted_end_targets": [],
            "blockers": ["layout_not_accepted"],
        },
        "principal_policy": {
            "public_principal_ready": False,
            "copied_public_identifier": None,
            "principal_copy_policy": "unresolved",
            "privacy_policy": "unresolved",
            "invalidation_semantics": "unresolved",
            "logging_policy": "identity_values_not_logged",
        },
        "promotion_gate": {
            "ready": False,
            "ready_scope": "planning_only",
            "promotion_ready": False,
            "blockers": ["public_principal_policy_unresolved"],
        },
        "safety_summary": {
            "candidate_anchor_count": 2,
            "accepted_anchor_count": 0,
            "field_count": 2,
            "identity_redacted_field_count": 0,
            "copied_candidate_count": 2,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "explicitly_excluded": [
                "public_player_identity",
                "permissions",
                "commands",
                "economy",
                "lookup",
                "ResourceHandle",
                "mutation",
                "return_override",
                "runtime_hook_wiring",
                "ue_pointers",
                "raw_params",
                "fname_indices",
                "gobjects_indices",
                "identity_value_logging",
            ],
        },
        "non_claims": [
            "candidate-only lifecycle anchor planning evidence",
            "does not expose public player identity, permissions, commands, economy, lookup, or moderation APIs",
            "does not expose UE pointers, raw params, FName/GObjects indices, ResourceHandle, mutation, or return overrides",
            "accepted layout anchors are non-public and do not prove principal invalidation semantics",
        ],
    }


def accepted_lifecycle_anchor_manifest() -> dict:
    payload = manifest()
    payload["candidate_anchors"][0] = lifecycle_layout_anchor("session_start", "ShooterGameMode.HandleNewPlayer")
    payload["candidate_anchors"][1] = lifecycle_layout_anchor("session_end", "ShooterGameMode.OnLogout")
    payload["lifecycle_acceptance"]["session_start_accepted"] = True
    payload["lifecycle_acceptance"]["session_end_accepted"] = True
    payload["lifecycle_acceptance"]["accepted_start_targets"] = ["ShooterGameMode.HandleNewPlayer"]
    payload["lifecycle_acceptance"]["accepted_end_targets"] = ["ShooterGameMode.OnLogout"]
    payload["lifecycle_acceptance"]["blockers"] = ["principal_invalidation_semantics_unresolved"]
    payload["safety_summary"]["accepted_anchor_count"] = 2
    payload["safety_summary"]["field_count"] = 6
    payload["safety_summary"]["copied_candidate_count"] = 2
    return payload


class PlayerIdentityLifecycleAnchorCandidateTests(unittest.TestCase):
    def run_checker(self, payload: dict, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(path), "--json", *args],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
        if check and result.returncode != 0:
            self.fail(f"checker failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def test_consume_accepts_unaccepted_candidates_without_public_claims(self) -> None:
        result = self.run_checker(manifest())
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertTrue(payload["ready"])
        self.assertEqual(payload["accepted_start_targets"], [])
        self.assertEqual(payload["accepted_end_targets"], [])
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])

    def test_rejects_unexpected_top_level_runtime_authorization_claim(self) -> None:
        payload = manifest()
        payload["server_operations_authorized"] = True

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("top_level_fields_unexpected", report["blockers"])
        self.assertIn("forbidden_runtime_or_public_claim", report["blockers"])

    def test_rejects_positive_runtime_and_command_text_claim(self) -> None:
        payload = manifest()
        payload["principal_policy"]["note"] = "runtime ready and commands enabled"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("forbidden_runtime_or_public_claim", report["blockers"])

    def test_accepts_multiple_complete_source_artifact_id_triples(self) -> None:
        payload = manifest()
        payload["artifact_identity"]["source_artifact_ids"] = [
            f"artifact_sha256:{SHA}",
            "capture_id:player-lifecycle-candidates",
            "evidence_pack_id:player-lifecycle-pack",
            f"artifact_sha256:{'1' * 64}",
            "capture_id:second-capture",
            "evidence_pack_id:second-pack",
        ]

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["ready"])
        self.assertEqual([], report["blockers"])

    def test_promote_blocks_candidate_only(self) -> None:
        result = self.run_checker(manifest(), "--promote", check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("promote_mode_players_identity_lifecycle_anchor_candidates_candidate_only", payload["blockers"])

    def test_rejects_accepted_anchor_without_exact_layout(self) -> None:
        payload = manifest()
        payload["candidate_anchors"][0]["accepted"] = True
        payload["candidate_anchors"][0]["acceptance_status"] = "layout_accepted_non_public"
        payload["candidate_anchors"][0].pop("parms_size")
        payload["candidate_anchors"][0]["corroboration"]["status"] = "second_source_accepted"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("accepted_anchor_layout_evidence_missing", report["blockers"])

    def test_rejects_accepted_anchor_without_corroboration(self) -> None:
        payload = manifest()
        payload["candidate_anchors"][0]["accepted"] = True
        payload["candidate_anchors"][0]["acceptance_status"] = "layout_accepted_non_public"
        payload["lifecycle_acceptance"]["session_start_accepted"] = True
        payload["lifecycle_acceptance"]["accepted_start_targets"] = ["ShooterPlayerController.ClientNotifyPlayerJoined"]
        payload["safety_summary"]["accepted_anchor_count"] = 1

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("accepted_anchor_corroboration_missing", report["blockers"])

    def test_rejects_acceptance_summary_mismatch(self) -> None:
        payload = manifest()
        payload["lifecycle_acceptance"]["session_start_accepted"] = True

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("lifecycle_acceptance_summary_mismatch", report["blockers"])

    def test_rejects_public_principal_overclaim(self) -> None:
        payload = manifest()
        payload["principal_policy"]["public_principal_ready"] = True
        payload["principal_policy"]["copied_public_identifier"] = "SteamID"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("public_principal_overclaim", report["blockers"])

    def test_rejects_lifecycle_anchor_target_outside_closed_target_set(self) -> None:
        payload = manifest()
        payload["candidate_anchors"][0] = base_anchor("session_start", "ShooterPlayerController.ClientNotifyPlayerJoined")

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("candidate_anchor_target_outside_closed_target_set", report["blockers"])

    def test_consumes_corroborated_gamemode_layout_anchors_candidate_only(self) -> None:
        payload = accepted_lifecycle_anchor_manifest()

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["ready"])
        self.assertNotIn("candidate_anchor_target_outside_closed_target_set", report["blockers"])
        self.assertEqual(report["accepted_start_targets"], ["ShooterGameMode.HandleNewPlayer"])
        self.assertEqual(report["accepted_end_targets"], ["ShooterGameMode.OnLogout"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_promote_blocks_layout_anchors_on_invalidation_semantics(self) -> None:
        payload = accepted_lifecycle_anchor_manifest()

        result = self.run_checker(payload, "--promote", check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("promote_mode_principal_invalidation_semantics_unresolved", report["blockers"])
        self.assertIn("promote_mode_players_identity_lifecycle_anchor_candidates_candidate_only", report["blockers"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_lifecycle_layout_anchor_shape_drift(self) -> None:
        payload = manifest()
        payload["candidate_anchors"][0] = lifecycle_layout_anchor("session_start", "ShooterGameMode.HandleNewPlayer")
        payload["candidate_anchors"][1] = lifecycle_layout_anchor("session_end", "ShooterGameMode.OnLogout")
        payload["candidate_anchors"][0]["parms_size"] = 24
        payload["lifecycle_acceptance"]["session_start_accepted"] = True
        payload["lifecycle_acceptance"]["session_end_accepted"] = True
        payload["lifecycle_acceptance"]["accepted_start_targets"] = ["ShooterGameMode.HandleNewPlayer"]
        payload["lifecycle_acceptance"]["accepted_end_targets"] = ["ShooterGameMode.OnLogout"]
        payload["safety_summary"]["accepted_anchor_count"] = 2

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("candidate_layout_anchor_shape_mismatch", report["blockers"])

    def test_rejects_accepted_anchor_that_is_not_lifecycle_layout_candidate(self) -> None:
        payload = manifest()
        payload["candidate_anchors"][0]["accepted"] = True
        payload["candidate_anchors"][0]["acceptance_status"] = "layout_accepted_non_public"
        payload["candidate_anchors"][0]["corroboration"]["status"] = "static_accepted"
        payload["candidate_anchors"][0]["blockers"] = []
        payload["lifecycle_acceptance"]["session_start_accepted"] = True
        payload["lifecycle_acceptance"]["accepted_start_targets"] = ["MissionType.AddPlayerToMission"]
        payload["safety_summary"]["accepted_anchor_count"] = 1

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("accepted_anchor_not_lifecycle_layout_candidate", report["blockers"])
        self.assertEqual(report["accepted_start_targets"], [])

    def test_rejects_lifecycle_object_field_public_copy_overclaim(self) -> None:
        payload = manifest()
        payload["candidate_anchors"][0] = lifecycle_layout_anchor("session_start", "ShooterGameMode.HandleNewPlayer")
        payload["candidate_anchors"][1] = lifecycle_layout_anchor("session_end", "ShooterGameMode.OnLogout")
        payload["candidate_anchors"][0]["fields"][0]["classification"] = "copied_candidate"
        payload["candidate_anchors"][0]["fields"][0]["copied_scalar_eligibility"] = "candidate_copied_public_identifier"
        payload["lifecycle_acceptance"]["session_start_accepted"] = True
        payload["lifecycle_acceptance"]["session_end_accepted"] = True
        payload["lifecycle_acceptance"]["accepted_start_targets"] = ["ShooterGameMode.HandleNewPlayer"]
        payload["lifecycle_acceptance"]["accepted_end_targets"] = ["ShooterGameMode.OnLogout"]
        payload["safety_summary"]["accepted_anchor_count"] = 2

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("candidate_layout_object_field_not_redacted", report["blockers"])
        self.assertIn("candidate_layout_object_field_public_overclaim", report["blockers"])

    def test_rejects_lifecycle_object_field_forbidden_classification(self) -> None:
        payload = manifest()
        payload["candidate_anchors"][0] = lifecycle_layout_anchor("session_start", "ShooterGameMode.HandleNewPlayer")
        payload["candidate_anchors"][1] = lifecycle_layout_anchor("session_end", "ShooterGameMode.OnLogout")
        payload["candidate_anchors"][0]["fields"][0]["classification"] = "forbidden"
        payload["candidate_anchors"][0]["fields"][0]["copied_scalar_eligibility"] = "not_copied"
        payload["lifecycle_acceptance"]["session_start_accepted"] = True
        payload["lifecycle_acceptance"]["session_end_accepted"] = True
        payload["lifecycle_acceptance"]["accepted_start_targets"] = ["ShooterGameMode.HandleNewPlayer"]
        payload["lifecycle_acceptance"]["accepted_end_targets"] = ["ShooterGameMode.OnLogout"]
        payload["safety_summary"]["accepted_anchor_count"] = 2

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("candidate_layout_object_field_not_redacted", report["blockers"])

    def test_rejects_missing_public_surface_exclusions(self) -> None:
        payload = manifest()
        payload["safety_summary"]["explicitly_excluded"] = [
            item
            for item in payload["safety_summary"]["explicitly_excluded"]
            if item not in {"commands", "lookup", "ResourceHandle", "mutation", "return_override"}
        ]

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("explicit_exclusions_missing_required_boundaries", report["blockers"])

    def test_rejects_admin_snapshots_as_accepted_lifecycle_anchors(self) -> None:
        payload = manifest()
        payload["candidate_anchors"][0] = base_anchor("session_start", "ShooterPlayerController.ServerListPlayers")
        payload["candidate_anchors"][1] = base_anchor("session_end", "ShooterPlayerController.ServerKickPlayer")
        for anchor in payload["candidate_anchors"]:
            anchor["accepted"] = True
            anchor["acceptance_status"] = "layout_accepted_non_public"
            anchor["corroboration"]["status"] = "static_accepted"
            anchor["blockers"] = []
        payload["lifecycle_acceptance"]["session_start_accepted"] = True
        payload["lifecycle_acceptance"]["session_end_accepted"] = True
        payload["lifecycle_acceptance"]["accepted_start_targets"] = ["ShooterPlayerController.ServerListPlayers"]
        payload["lifecycle_acceptance"]["accepted_end_targets"] = ["ShooterPlayerController.ServerKickPlayer"]
        payload["safety_summary"]["accepted_anchor_count"] = 2

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("candidate_anchor_admin_snapshot_not_lifecycle_proof", report["blockers"])
        self.assertIn("lifecycle_acceptance_summary_mismatch", report["blockers"])
        self.assertIn("lifecycle_acceptance_targets_mismatch", report["blockers"])
        self.assertIn("safety_accepted_anchor_count_mismatch", report["blockers"])
        self.assertEqual(report["accepted_start_targets"], [])
        self.assertEqual(report["accepted_end_targets"], [])

    def test_rejects_principal_invalidation_semantics_overclaim(self) -> None:
        payload = manifest()
        payload["principal_policy"]["invalidation_semantics"] = "stable_cross_instance_principal"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("principal_invalidation_semantics_overclaim", report["blockers"])

    def test_rejects_identity_field_copied_public(self) -> None:
        payload = manifest()
        field = copy.deepcopy(payload["candidate_anchors"][0]["fields"][0])
        field["name"] = "SteamID"
        field["classification"] = "copied_candidate"
        field["copied_scalar_eligibility"] = "candidate_copied_public_identifier"
        payload["candidate_anchors"][0]["fields"].append(field)
        payload["candidate_anchors"][0]["property_order"].append("SteamID")

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("identity_field_not_redacted", report["blockers"])
        self.assertIn("identity_field_copied_public_overclaim", report["blockers"])

    def test_rejects_path_or_coordinate_leakage(self) -> None:
        payload = manifest()
        payload["snapshot_root"] = "/home/flowcommunity-ark/obelisk-artifacts/snapshots"
        payload["candidate_anchors"][0]["evidence"]["raw_param_address"] = "0x1234"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("snapshot_root_not_redacted", report["blockers"])
        self.assertIn("path_or_coordinate_leakage", report["blockers"])

    def test_rejects_manifest_under_protected_server_root_before_reading(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "/servidor/ark/obelisk/player-identity-lifecycle-anchor-candidates.json",
                "--json",
            ],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("manifest must not read from protected server root /servidor/ark", result.stderr)

    def test_rejects_symlinked_manifest_before_reading(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest()), encoding="utf-8")
            link = root / "manifest-link.json"
            link.symlink_to(manifest_path)

            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(link), "--json"],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("manifest must not be a symlink", result.stderr)


if __name__ == "__main__":
    unittest.main()
