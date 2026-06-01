#!/usr/bin/env python3
"""Tests for check_player_identity_first_evidence_readiness.py."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import check_player_identity_first_evidence_readiness as checker
from test_check_player_identity_lifecycle_anchor_candidates import accepted_lifecycle_anchor_manifest
from test_check_player_identity_principal_invalidation_policy import manifest as principal_policy_manifest
from test_check_player_identity_runtime_principal_lifecycle_approved_evidence import (
    manifest as approved_runtime_principal_lifecycle_manifest,
)
from test_check_player_identity_runtime_principal_lifecycle_evidence import manifest as runtime_principal_lifecycle_manifest
from test_validate_offline_artifact_gate import players_identity_first_evidence_manifest
from reflection_target_sets import schema_target_list  # noqa: E402


class CheckPlayerIdentityFirstEvidenceReadinessTests(unittest.TestCase):
    def run_checker(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.setdefault("OBELISK_COMMIT", "test-obelisk-commit")
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIR / "check_player_identity_first_evidence_readiness.py"),
                *args,
            ],
            check=check,
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )

    def accepted_inventory_payload(self) -> dict:
        targets = [
            "ShooterGameMode.PostLogin",
            "ShooterGameMode.Logout",
            "ShooterPlayerController.ServerSendChatMessage",
            "ShooterPlayerController.ServerRequestTribeLog",
            "ShooterPlayerController.AllowTribeGroupPermission",
            "ShooterPlayerController.IsInTribe",
            "ShooterPlayerController.ClientReceiveMyTribeOnlineList",
            "ShooterPlayerController.ClientReceiveActiveMissionTags",
            "ShooterPlayerState.ServerRequestSpawnPointsForDownloadedCharacters",
            "MissionType.AddPlayerToMission",
            "ShooterPlayerController.ServerKickPlayer",
            "ShooterPlayerController.ServerListPlayers",
        ]
        return {
            "ready": True,
            "accepted_pack": {
                "manifest": "/tmp/inventory/manifest.json",
                "schema": "obelisk.reflection-inventory-pack.v1",
                "status": "candidate-only",
                "promotion_status": "not_promoted_candidate_only",
                "inputs": {
                    "evidence_pack_manifest": "/tmp/core-evidence-pack/manifest.json",
                    "evidence_pack_schema": "obelisk.core-dump-evidence-pack.v1",
                    "evidence_pack_status": "complete",
                    "target_sets": ["players-identity-lifecycle-intake"],
                },
                "summary": {"fname_root_ready": True},
                "blockers": [],
                "matched_targets": targets,
                "target_set_coverage": {
                    "target_sets": [
                        {
                            "name": "players-identity-lifecycle-intake",
                            "expected_targets": targets,
                            "covered_targets": targets,
                            "missing_targets": [],
                            "complete": True,
                        }
                    ]
                },
            },
            "reasons": [],
        }

    def lower_level_accepted_inventory_payload(self) -> dict:
        targets = schema_target_list(
            checker.PLAYER_IDENTITY_TARGET_SET,
            "obelisk.ufunction-chain.snapshot.v1",
        )
        return {
            "ready": True,
            "accepted_pack": {
                "manifest": "/tmp/player-identity-artifacts/reflection-inventory-pack/manifest.json",
                "schema": "obelisk.reflection-inventory-pack.v1",
                "status": "candidate-only",
                "promotion_status": "not_promoted_candidate_only",
                "inputs": {
                    "evidence_pack_manifest": "/tmp/player-identity-artifacts/core-evidence-pack/manifest.json",
                    "target_sets": [checker.PLAYER_IDENTITY_TARGET_SET],
                },
                "target_set_coverage": {
                    "target_sets": [checker.PLAYER_IDENTITY_TARGET_SET],
                    "requested_targets": targets,
                },
                "summary": {"fname_root_ready": True},
                "blockers": [],
                "inventory": "/tmp/player-identity-artifacts/reflection-inventory-pack/ufunction-inventory.json",
                "ready": True,
                "reasons": [],
                "matched_targets": targets,
                "required_target_set": {
                    "target_set": checker.PLAYER_IDENTITY_TARGET_SET,
                    "expected_target_count": len(targets),
                    "expected_targets": targets,
                },
            },
            "reasons": [],
        }

    def test_current_fixture_gap_reports_exact_next_step_without_promoting_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_checker(["--artifact-root", temp_dir], check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["schema"], "obelisk.player-identity-first-evidence-readiness.v1")
        self.assertEqual(payload["status"], "blocked")
        self.assertFalse(payload["ready"])
        self.assertEqual(payload["primary_blocker"], "offline_binary_and_core_input_missing")
        self.assertFalse(payload["accepted_for_internal_planning"])
        self.assertTrue(payload["not_artifact_gate"])
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertEqual(payload["target_set"], "players-identity-lifecycle-intake")
        self.assertIn("missing_reflection_inventory_pack_or_core_evidence_pack", payload["blockers"])
        progress_signal = payload["progress_signal"]
        self.assertEqual(progress_signal["status"], "blocked")
        self.assertFalse(progress_signal["ready"])
        self.assertEqual(progress_signal["primary_blocker"], "offline_binary_and_core_input_missing")
        self.assertFalse(progress_signal["coverage"]["reflection_inventory_accepted"])
        self.assertEqual(progress_signal["coverage"]["fixture_targets"], "12/12")
        self.assertEqual(progress_signal["coverage"]["fixture_blocked_targets"], 0)
        self.assertEqual(progress_signal["coverage"]["second_source"]["missing"], 12)
        self.assertEqual(progress_signal["missing"]["required_targets"], [])
        self.assertEqual(
            progress_signal["missing"]["operator_inputs"],
            [
                "matching_non_protected_shooter_game_server",
                "non_protected_core_dump_input",
            ],
        )
        self.assertFalse(progress_signal["accepted_anchors"]["session_start"])
        self.assertFalse(progress_signal["accepted_anchors"]["session_end"])
        self.assertIn("does not promote reflection inventory", " ".join(progress_signal["non_claims"]))
        self.assertNotIn("fixture_coverage_incomplete", payload["blockers"])
        self.assertNotIn("second_source_evidence_missing", payload["blockers"])
        self.assertNotIn("players_identity_first_evidence_not_buildable", payload["blockers"])
        self.assertNotIn("accepted_lifecycle_anchors_missing", payload["blockers"])
        self.assertNotIn("fixture_coverage_incomplete", payload["deferred_until_reflection_inventory_ready"])
        self.assertIn("second_source_evidence_missing", payload["deferred_until_reflection_inventory_ready"])
        self.assertNotIn("players_identity_first_evidence_not_buildable", payload["deferred_until_reflection_inventory_ready"])
        self.assertIn("accepted_lifecycle_anchors_missing", payload["deferred_until_reflection_inventory_ready"])
        self.assertEqual(
            [artifact["schema"] for artifact in payload["next_required_artifacts"]],
            [
                "obelisk.core-dump-evidence-pack.v1",
                "obelisk.reflection-inventory-pack.v1",
            ],
        )
        recipe = payload["next_operator_recipe"]
        self.assertEqual(recipe["blocked_until"], "accepted_reflection_inventory_pack")
        self.assertNotIn("<reviewed-obelisk-id>", json.dumps(payload))
        self.assertEqual(
            recipe["obelisk_commit_source"],
            "OBELISK_COMMIT environment variable if set; otherwise current Git HEAD, or unknown when unavailable",
        )
        self.assertIn("build_core_dump_evidence_pack.py", recipe["build_core_evidence_pack"])
        self.assertIn("--binary", recipe["build_core_evidence_pack"])
        self.assertIn("--core", recipe["build_core_evidence_pack"])
        self.assertIn("--output-dir", recipe["build_core_evidence_pack"])
        self.assertIn("--fname-root-slot verified_fname_root_slot=0x5956f30", recipe["build_core_evidence_pack"])
        self.assertIn("--gobjects-candidate gobjects=0x595b7e0", recipe["build_core_evidence_pack"])
        self.assertIn("--gobjects-sample-index 25447", recipe["build_core_evidence_pack"])
        self.assertNotIn("--skip-core-sha256", recipe["build_core_evidence_pack"])
        self.assertNotIn("--allow-partial-gdb", recipe["build_core_evidence_pack"])
        self.assertIn("build_reflection_inventory_pack.py", recipe["build_reflection_inventory_pack"])
        self.assertIn(
            f"--ark-binary-sha256 {checker.EXPECTED_SHOOTERGAME_SHA256}",
            recipe["build_reflection_inventory_pack"],
        )
        self.assertIn("--target-set players-identity-lifecycle-intake", recipe["build_reflection_inventory_pack"])
        self.assertIn("check_reflection_inventory_pack_readiness.py", recipe["check_reflection_inventory_pack"])
        self.assertIn("plan_ufunction_focal_snapshots.py", recipe["plan_admin_focal_snapshots"])
        self.assertIn("--target ShooterPlayerController.ServerListPlayers", recipe["plan_admin_focal_snapshots"])
        self.assertIn("--target ShooterPlayerController.ServerKickPlayer", recipe["plan_admin_focal_snapshots"])
        self.assertNotIn("--target-set players-identity-lifecycle-intake", recipe["plan_admin_focal_snapshots"])
        self.assertIn("do not read from or write to /servidor/ark", " ".join(recipe["forbidden_next_commands"]))
        self.assertIn(
            "do not use --target-set players-identity-lifecycle-intake",
            " ".join(recipe["forbidden_next_commands"]),
        )
        self.assertIn("do not use direct --core mode", " ".join(recipe["forbidden_next_commands"]))
        self.assertIn("does not execute commands", " ".join(recipe["non_claims"]))
        self.assertEqual(
            payload["artifact_chain"]["required_admin_targets"],
            [
                "ShooterPlayerController.ServerKickPlayer",
                "ShooterPlayerController.ServerListPlayers",
            ],
        )
        self.assertEqual(
            payload["artifact_chain"]["offline_inputs"]["status"],
            "offline_binary_and_core_like_inputs_missing",
        )
        self.assertTrue(payload["artifact_chain"]["offline_inputs"]["artifact_root_only"])
        self.assertEqual(payload["artifact_chain"]["offline_inputs"]["server_root_excluded"], "/servidor/ark")
        self.assertFalse(payload["artifact_chain"]["offline_inputs"]["ready_to_build_core_evidence_pack"])
        self.assertTrue(payload["artifact_chain"]["blocked_before_focal_planning"])
        self.assertFalse(payload["artifact_chain"]["ready_to_plan_admin_snapshots"])
        self.assertTrue(payload["static_orientation"]["valid"])
        self.assertTrue(payload["static_orientation"]["accepted_for_orientation"])
        self.assertTrue(payload["static_orientation"]["not_artifact_gate"])
        self.assertFalse(payload["static_orientation"]["promotion_ready"])
        self.assertFalse(payload["static_orientation"]["public_sdk_ready"])
        self.assertFalse(payload["static_orientation"]["runtime_ready"])
        self.assertEqual(payload["static_orientation"]["blockers"], [])
        pre_core_boundary = payload["static_orientation"]["pre_core_evidence_boundary"]
        self.assertTrue(pre_core_boundary["useful"])
        self.assertTrue(pre_core_boundary["blocked"])
        self.assertEqual(pre_core_boundary["status"], "useful_orientation_blocked_before_core_evidence")
        self.assertIn("requires_non_protected_core_evidence_pack", pre_core_boundary["blockers"])
        self.assertIn(
            "requires_accepted_reflection_inventory_pack_before_admin_focal_planning",
            pre_core_boundary["blockers"],
        )
        self.assertIn("static_lifecycle_admin_orientation", pre_core_boundary["useful_for"])
        self.assertIn(
            "static orientation does not replace core evidence",
            " ".join(pre_core_boundary["non_claims"]),
        )
        self.assertIn(
            "candidate-only navigation evidence",
            " ".join(payload["static_orientation"]["non_claims"]),
        )
        self.assertEqual(
            payload["reflection_inventory"]["artifact_root_diagnosis"]["status"],
            "no_manifest_files_found",
        )
        self.assertEqual(payload["reflection_inventory"]["artifact_root_diagnosis"]["candidate_pack_count"], 0)
        self.assertEqual(payload["fixture_coverage"]["targets"], 12)
        self.assertEqual(payload["fixture_coverage"]["comparable"], 12)
        self.assertEqual(payload["fixture_coverage"]["blocked"], 0)
        self.assertEqual(payload["fixture_coverage"]["second_source_missing"], 12)
        self.assertEqual(payload["fixture_coverage"]["second_source_inconclusive"], 0)
        self.assertEqual(payload["fixture_coverage"]["second_source_rejected"], 0)
        self.assertIsNone(payload["candidate_root"])
        self.assertEqual(payload["first_evidence"]["missing_required_targets"], [])
        consume_gate = payload["first_evidence"]["consume_gate"]
        self.assertTrue(consume_gate["evaluated"])
        self.assertEqual(consume_gate["mode"], "consume")
        self.assertEqual(consume_gate["status"], "accepted")
        self.assertTrue(consume_gate["ready"])
        self.assertFalse(consume_gate["promotion_ready"])
        self.assertFalse(consume_gate["public_sdk_ready"])
        self.assertFalse(consume_gate["runtime_ready"])
        self.assertNotIn(
            "players_identity_first_evidence_artifact_identity_source_id_count_mismatch",
            consume_gate["blocker_reasons"],
        )
        self.assertNotIn(
            "players_identity_first_evidence_public_overclaim_public_api",
            consume_gate["blocker_reasons"],
        )
        self.assertNotIn(
            "players_identity_first_evidence_consume_gate_blocked",
            payload["deferred_until_reflection_inventory_ready"],
        )
        self.assertFalse(payload["first_evidence"]["lifecycle_anchors"]["session_start_accepted"])
        self.assertFalse(payload["first_evidence"]["lifecycle_anchors"]["session_end_accepted"])
        self.assertIn(
            "no accepted session-start/login/connect UFunction anchor in players-identity-lifecycle-intake",
            payload["first_evidence"]["lifecycle_anchors"]["blockers"],
        )
        self.assertIn(
            "no accepted session-end/logout/disconnect UFunction anchor in players-identity-lifecycle-intake",
            payload["first_evidence"]["lifecycle_anchors"]["blockers"],
        )
        self.assertEqual(
            payload["next_step"],
            "produce_or_approve_non_protected_core_evidence_pack_then_reflection_inventory_pack",
        )
        self.assertEqual(payload["next_actionable_blocker"]["code"], "offline_binary_and_core_input_missing")
        self.assertEqual(payload["primary_blocker"], payload["next_actionable_blocker"]["code"])
        self.assertEqual(
            payload["next_actionable_blocker"]["blocked_until"],
            "non_protected_offline_binary_and_core_inputs",
        )
        self.assertFalse(payload["next_actionable_blocker"]["promotion_ready"])
        self.assertFalse(payload["next_actionable_blocker"]["public_sdk_ready"])
        self.assertFalse(payload["next_actionable_blocker"]["runtime_ready"])
        self.assertEqual(
            payload["next_actionable_blocker"]["next_required_artifact"]["schema"],
            "obelisk.core-dump-evidence-pack.v1",
        )
        operator_commands = payload["operator_next_commands"]
        self.assertEqual(operator_commands["current_blocker"], "offline_binary_and_core_input_missing")
        self.assertEqual(operator_commands["blocked_until"], "non_protected_offline_binary_and_core_inputs")
        self.assertEqual(operator_commands["runnable_now"], [])
        self.assertEqual(
            operator_commands["missing_inputs"],
            [
                "matching_non_protected_shooter_game_server",
                "non_protected_core_dump_input",
            ],
        )
        self.assertFalse(operator_commands["inputs"]["matching_non_protected_shooter_game_server"]["present"])
        self.assertFalse(operator_commands["inputs"]["non_protected_core_dump_input"]["present"])
        input_layout = operator_commands["input_layout_requirements"]
        self.assertTrue(input_layout["accepted_raw_directory_pattern"].endswith("player-identity-offline-<run-id>/raw"))
        self.assertEqual(input_layout["binary_filename"], "ShooterGameServer")
        self.assertEqual(input_layout["core_filename"], "core")
        self.assertEqual(input_layout["run_directory_prefix"], "player-identity-offline-")
        self.assertIn("regular, non-symlink sibling files", input_layout["pairing_rule"])
        self.assertIn("copy or hardlink offline inputs", input_layout["staging_rule"])
        self.assertEqual(input_layout["protected_paths_rejected"], ["/servidor/ark"])
        self.assertEqual(
            input_layout["next_input_preparation_action"],
            "stage_matching_binary_and_core_under_same_player_identity_raw_dir",
        )
        self.assertIn("does not validate core contents", " ".join(input_layout["non_claims"]))
        blocked_resolution = operator_commands["blocked_input_resolution"]
        self.assertEqual(blocked_resolution["status"], "blocked")
        self.assertEqual(blocked_resolution["current_blocker"], "offline_binary_and_core_input_missing")
        self.assertEqual(
            blocked_resolution["missing_inputs"],
            [
                "matching_non_protected_shooter_game_server",
                "non_protected_core_dump_input",
            ],
        )
        self.assertIn("validate_player_identity_raw_inputs.py", blocked_resolution["validation_command_after_missing_inputs_exist"])
        self.assertIn(
            "player-identity-offline-<run-id-suffix>",
            blocked_resolution["validation_command_after_missing_inputs_exist"],
        )
        self.assertIn("does not make blocked commands runnable", " ".join(blocked_resolution["non_claims"]))
        input_staging = operator_commands["input_staging"]
        self.assertEqual(input_staging["id"], "stage_offline_raw_layout")
        self.assertEqual(input_staging["status"], "blocked")
        self.assertFalse(input_staging["ready"])
        self.assertEqual(
            input_staging["explicit_source_inputs_required"],
            [
                "matching_non_protected_shooter_game_server",
                "non_protected_core_dump_input",
            ],
        )
        self.assertIn("prepare_player_identity_offline_raw_layout.py", input_staging["command"])
        self.assertEqual(input_staging["command_argv"][5], "<non-protected-core-dump-input>")
        self.assertIn("does not create, validate, approve, or promote core dumps", " ".join(input_staging["non_claims"]))
        self.assertEqual(
            [step["id"] for step in operator_commands["sequence"]],
            [
                "build_core_evidence_pack",
                "build_reflection_inventory_pack",
                "check_reflection_inventory_pack",
                "plan_admin_focal_snapshots",
            ],
        )
        sequence_by_id = {step["id"]: step for step in operator_commands["sequence"]}
        self.assertFalse(operator_commands["sequence"][0]["ready"])
        self.assertEqual(operator_commands["sequence"][0]["status"], "blocked")
        self.assertEqual(
            operator_commands["sequence"][0]["blocked_until"],
            "non_protected_offline_binary_and_core_inputs",
        )
        self.assertIn("build_core_dump_evidence_pack.py", operator_commands["sequence"][0]["command"])
        self.assertFalse(sequence_by_id["build_reflection_inventory_pack"]["ready"])
        self.assertEqual(sequence_by_id["build_reflection_inventory_pack"]["status"], "blocked")
        self.assertEqual(
            sequence_by_id["build_reflection_inventory_pack"]["blocked_until"],
            "complete_core_evidence_pack",
        )
        self.assertEqual(
            sequence_by_id["build_reflection_inventory_pack"]["requires"],
            ["complete_core_evidence_pack"],
        )
        self.assertFalse(sequence_by_id["plan_admin_focal_snapshots"]["ready"])
        self.assertEqual(sequence_by_id["plan_admin_focal_snapshots"]["status"], "blocked")
        self.assertEqual(
            sequence_by_id["plan_admin_focal_snapshots"]["blocked_until"],
            "accepted_reflection_inventory_pack",
        )
        self.assertIn(
            "accepted_reflection_inventory_pack",
            sequence_by_id["plan_admin_focal_snapshots"]["requires"],
        )
        self.assertIn("does not execute commands", " ".join(operator_commands["non_claims"]))
        self.assertIn("does not touch servers", " ".join(payload["non_claims"]))
        self.assertIn("candidate-only planning evidence", " ".join(payload["non_claims"]))

    def test_json_flag_is_accepted_for_handoff_and_release_gate_callers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_checker(["--artifact-root", temp_dir, "--json"], check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["schema"], "obelisk.player-identity-first-evidence-readiness.v1")
        self.assertEqual(payload["status"], "blocked")
        self.assertIn("missing_reflection_inventory_pack_or_core_evidence_pack", payload["blockers"])
        self.assertTrue(payload["static_orientation"]["valid"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])

    def test_rejected_artifact_root_does_not_emit_copy_paste_protected_recipe_paths(self) -> None:
        result = self.run_checker(
            ["--artifact-root", "/servidor/ark/obelisk/player-identity-offline", "--json"],
            check=False,
        )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["artifact_chain"]["offline_inputs"]["status"], "artifact_root_rejected")
        recipe = payload["next_operator_recipe"]
        recipe_commands = "\n".join(
            [
                recipe["build_core_evidence_pack"],
                recipe["build_reflection_inventory_pack"],
                recipe["check_reflection_inventory_pack"],
                recipe["plan_admin_focal_snapshots"],
            ]
        )
        self.assertIn("<non-protected-artifact-root>", recipe_commands)
        self.assertNotIn("/servidor/ark/obelisk/player-identity-offline", recipe_commands)

    def test_workspace_offline_artifact_root_is_allowed_for_inventory_scan(self) -> None:
        ok = subprocess.CompletedProcess(["mock"], 0, "", "")
        saw_inventory_scan = False

        def fake_run_json_command(args: list[str], *, check: bool = False):
            nonlocal saw_inventory_scan
            command = " ".join(args)
            if "check_reflection_inventory_pack_readiness.py" in command:
                saw_inventory_scan = True
                return ok, {"ready": False, "accepted_pack": None, "reasons": []}
            if "compare_reflection_snapshots.py" in command:
                return ok, {
                    "totals": {
                        "targets": 12,
                        "comparable": 10,
                        "blocked": 2,
                        "second_source_missing": 10,
                        "second_source_inconclusive": 0,
                        "second_source_rejected": 0,
                    },
                    "promotion_gate": {"promotion_ready": False},
                    "second_source_status": "missing",
                }
            if "build_redacted_ufunction_signatures.py" in command:
                return subprocess.CompletedProcess(
                    ["mock"],
                    1,
                    "{}",
                    "missing_required_target:ShooterPlayerController.ServerKickPlayer",
                ), {}
            if "check_player_identity_static_orientation.py" in command:
                return ok, {
                    "valid": True,
                    "accepted_for_orientation": True,
                    "not_artifact_gate": True,
                    "blockers": [],
                    "non_claims": ["candidate-only navigation evidence"],
                }
            self.fail(f"unexpected command: {command}")

        args = SimpleNamespace(
            artifact_root=Path("/servidor/ark/workspace-offline/player-identity-offline"),
            snapshot_root=Path("/tmp/player-identity-snapshots"),
            candidate_root=None,
        )
        with (
            mock.patch.object(checker, "run_json_command", side_effect=fake_run_json_command),
            mock.patch.object(
                checker,
                "bounded_artifact_file_scan",
                return_value={
                    "status": "offline_binary_and_core_like_inputs_missing",
                    "artifact_root_only": True,
                    "resolved_root": "/servidor/ark/workspace-offline/player-identity-offline",
                    "server_root_excluded": "/servidor/ark",
                    "approved_offline_workspace_roots": ["/servidor/ark/workspace-offline"],
                    "shooter_game_server_candidates": [],
                    "core_like_candidates": [],
                    "ready_to_build_core_evidence_pack": False,
                },
            ),
        ):
            payload = checker.build_report(args)

        self.assertTrue(saw_inventory_scan)
        self.assertFalse(payload["ready"])
        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(
            payload["artifact_chain"]["offline_inputs"]["status"],
            "offline_binary_and_core_like_inputs_missing",
        )
        self.assertEqual(payload["reflection_inventory"]["returncode"], 0)
        self.assertIsNone(payload["reflection_inventory"]["manifests_scanned"])
        self.assertEqual(payload["reflection_inventory"]["reason_codes"], [])

    def test_candidate_root_reports_second_source_not_accepted_separately_from_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_checker(
                [
                    "--artifact-root",
                    temp_dir,
                    "--candidate-root",
                    str(REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"),
                ],
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["blockers"], ["missing_reflection_inventory_pack_or_core_evidence_pack"])
        self.assertEqual(
            payload["candidate_root"],
            str(REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"),
        )
        self.assertNotIn("second_source_evidence_missing", payload["deferred_until_reflection_inventory_ready"])
        self.assertIn("second_source_evidence_not_accepted", payload["deferred_until_reflection_inventory_ready"])
        self.assertEqual(payload["fixture_coverage"]["second_source_missing"], 0)
        self.assertEqual(payload["fixture_coverage"]["second_source_inconclusive"], 12)
        self.assertEqual(payload["fixture_coverage"]["second_source_rejected"], 0)
        self.assertEqual(payload["fixture_coverage"]["second_source_status"], "compared")

    def test_accepted_second_source_layout_reports_lifecycle_invalidation_remaining(self) -> None:
        ok = subprocess.CompletedProcess(["mock"], 0, "", "")
        vanilla_candidate_root = Path(
            "/servidor/ark/workspace-offline/"
            "player-identity-offline-identity-vanilla-gdb-20260529T012853Z/focal-snapshots"
        )

        def fake_run_json_command(args: list[str], *, check: bool = False):
            command = " ".join(args)
            if "check_reflection_inventory_pack_readiness.py" in command:
                return ok, self.accepted_inventory_payload()
            if "compare_reflection_snapshots.py" in command:
                self.assertIn(str(vanilla_candidate_root), command)
                return ok, {
                    "totals": {
                        "targets": 12,
                        "comparable": 12,
                        "blocked": 0,
                        "second_source_accepted": 12,
                        "second_source_missing": 0,
                        "second_source_inconclusive": 0,
                        "second_source_rejected": 0,
                    },
                    "promotion_gate": {
                        "ready": False,
                        "ready_scope": "planning_only",
                        "layout_ready": True,
                        "promotion_ready": False,
                        "blockers": [{"reason": "target_set_not_release_readiness", "count": 1}],
                    },
                    "second_source_status": "compared",
                }
            if "build_redacted_ufunction_signatures.py" in command:
                return ok, players_identity_first_evidence_manifest()
            if "check_player_identity_static_orientation.py" in command:
                return ok, {
                    "valid": True,
                    "accepted_for_orientation": True,
                    "not_artifact_gate": True,
                    "blockers": [],
                    "non_claims": ["candidate-only navigation evidence"],
                }
            self.fail(f"unexpected command: {command}")

        args = SimpleNamespace(
            artifact_root=Path("/tmp/player-identity-artifacts"),
            snapshot_root=Path("/tmp/player-identity-snapshots"),
            candidate_root=vanilla_candidate_root,
        )
        with (
            mock.patch.object(checker, "run_json_command", side_effect=fake_run_json_command),
            mock.patch.object(
                checker,
                "bounded_artifact_file_scan",
                return_value={"ready_to_build_core_evidence_pack": False},
            ),
        ):
            payload = checker.build_report(args)

        self.assertFalse(payload["ready"])
        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["candidate_root"], str(vanilla_candidate_root))
        self.assertEqual(payload["primary_blocker"], "accepted_lifecycle_anchor_evidence_missing")
        self.assertEqual(payload["next_actionable_blocker"]["code"], "accepted_lifecycle_anchor_evidence_missing")
        self.assertEqual(
            payload["readiness_statement"],
            "second-source layout accepted; lifecycle invalidation remains",
        )
        self.assertEqual(
            payload["layout_lifecycle_state"]["status"],
            "second_source_layout_accepted_lifecycle_invalidation_remains",
        )
        self.assertTrue(payload["layout_lifecycle_state"]["second_source_layout_accepted"])
        self.assertTrue(payload["layout_lifecycle_state"]["lifecycle_invalidation_remains"])
        self.assertIn("principal_invalidation_semantics", payload["layout_lifecycle_state"]["remaining_work"])
        self.assertFalse(payload["layout_lifecycle_state"]["promotion_ready"])
        self.assertFalse(payload["layout_lifecycle_state"]["public_sdk_ready"])
        self.assertFalse(payload["layout_lifecycle_state"]["runtime_ready"])
        self.assertEqual(
            payload["progress_signal"]["statement"],
            "second-source layout accepted; lifecycle invalidation remains",
        )
        self.assertTrue(payload["progress_signal"]["layout_lifecycle_state"]["second_source_layout_accepted"])
        self.assertTrue(payload["progress_signal"]["layout_lifecycle_state"]["lifecycle_invalidation_remains"])
        self.assertEqual(payload["fixture_coverage"]["second_source_accepted"], 12)
        self.assertTrue(payload["fixture_coverage"]["second_source_layout_accepted"])
        self.assertEqual(
            payload["next_step"],
            "produce_accepted_lifecycle_anchor_and_principal_invalidation_evidence",
        )
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])

    def test_consumes_lifecycle_anchor_candidate_but_keeps_principal_invalidation_blocked(self) -> None:
        ok = subprocess.CompletedProcess(["mock"], 0, "", "")
        vanilla_candidate_root = Path(
            "/servidor/ark/workspace-offline/"
            "player-identity-offline-identity-vanilla-gdb-20260529T012853Z/focal-snapshots"
        )

        def fake_run_json_command(args: list[str], *, check: bool = False):
            command = " ".join(args)
            if "check_reflection_inventory_pack_readiness.py" in command:
                return ok, self.accepted_inventory_payload()
            if "compare_reflection_snapshots.py" in command:
                return ok, {
                    "totals": {
                        "targets": 12,
                        "comparable": 12,
                        "blocked": 0,
                        "second_source_accepted": 12,
                        "second_source_missing": 0,
                        "second_source_inconclusive": 0,
                        "second_source_rejected": 0,
                    },
                    "promotion_gate": {
                        "layout_ready": True,
                        "promotion_ready": False,
                        "blockers": [{"reason": "target_set_not_release_readiness", "count": 1}],
                    },
                    "second_source_status": "compared",
                }
            if "build_redacted_ufunction_signatures.py" in command:
                return ok, players_identity_first_evidence_manifest()
            if "check_player_identity_static_orientation.py" in command:
                return ok, {
                    "valid": True,
                    "accepted_for_orientation": True,
                    "not_artifact_gate": True,
                    "blockers": [],
                    "non_claims": ["candidate-only navigation evidence"],
                }
            self.fail(f"unexpected command: {command}")

        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "lifecycle-candidates.json"
            manifest.write_text(json.dumps(accepted_lifecycle_anchor_manifest()), encoding="utf-8")
            args = SimpleNamespace(
                artifact_root=Path("/tmp/player-identity-artifacts"),
                snapshot_root=Path("/tmp/player-identity-snapshots"),
                candidate_root=vanilla_candidate_root,
                lifecycle_anchor_candidates_manifest=manifest,
            )
            with (
                mock.patch.object(checker, "run_json_command", side_effect=fake_run_json_command),
                mock.patch.object(
                    checker,
                    "bounded_artifact_file_scan",
                    return_value={"ready_to_build_core_evidence_pack": False},
                ),
            ):
                payload = checker.build_report(args)

        self.assertFalse(payload["ready"])
        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["primary_blocker"], "principal_invalidation_semantics_unresolved")
        self.assertIn("principal_invalidation_semantics_unresolved", payload["blockers"])
        self.assertEqual(
            payload["readiness_statement"],
            "lifecycle anchor layout accepted; principal invalidation remains",
        )
        anchors = payload["first_evidence"]["lifecycle_anchors"]
        self.assertEqual(anchors["source"], "players_identity_lifecycle_anchor_candidates")
        self.assertTrue(anchors["session_start_accepted"])
        self.assertTrue(anchors["session_end_accepted"])
        self.assertEqual(anchors["accepted_start_targets"], ["ShooterGameMode.HandleNewPlayer"])
        self.assertEqual(anchors["accepted_end_targets"], ["ShooterGameMode.OnLogout"])
        self.assertFalse(anchors["principal_invalidation_ready"])
        self.assertEqual(payload["next_step"], "produce_reviewed_principal_invalidation_semantics")
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])

    def test_consumes_principal_policy_but_keeps_runtime_evidence_blocked(self) -> None:
        ok = subprocess.CompletedProcess(["mock"], 0, "", "")

        def fake_run_json_command(args: list[str], *, check: bool = False):
            command = " ".join(args)
            if "check_reflection_inventory_pack_readiness.py" in command:
                return ok, self.accepted_inventory_payload()
            if "compare_reflection_snapshots.py" in command:
                return ok, {
                    "totals": {
                        "targets": 12,
                        "comparable": 12,
                        "blocked": 0,
                        "second_source_accepted": 12,
                        "second_source_missing": 0,
                        "second_source_inconclusive": 0,
                        "second_source_rejected": 0,
                    },
                    "promotion_gate": {"layout_ready": True, "promotion_ready": False},
                    "second_source_status": "compared",
                }
            if "build_redacted_ufunction_signatures.py" in command:
                return ok, players_identity_first_evidence_manifest()
            if "check_player_identity_static_orientation.py" in command:
                return ok, {
                    "valid": True,
                    "accepted_for_orientation": True,
                    "not_artifact_gate": True,
                    "blockers": [],
                    "non_claims": ["candidate-only navigation evidence"],
                }
            self.fail(f"unexpected command: {command}")

        with tempfile.TemporaryDirectory() as tmp:
            lifecycle_manifest = Path(tmp) / "lifecycle-candidates.json"
            principal_manifest = Path(tmp) / "principal-policy.json"
            runtime_manifest = Path(tmp) / "runtime-principal-lifecycle-shape.json"
            lifecycle_manifest.write_text(json.dumps(accepted_lifecycle_anchor_manifest()), encoding="utf-8")
            principal_manifest.write_text(json.dumps(principal_policy_manifest()), encoding="utf-8")
            runtime_manifest.write_text(
                json.dumps(runtime_principal_lifecycle_manifest()),
                encoding="utf-8",
            )
            args = SimpleNamespace(
                artifact_root=Path("/tmp/player-identity-artifacts"),
                snapshot_root=Path("/tmp/player-identity-snapshots"),
                candidate_root=Path("/tmp/player-identity-second-source"),
                lifecycle_anchor_candidates_manifest=lifecycle_manifest,
                principal_invalidation_policy_manifest=principal_manifest,
                runtime_principal_lifecycle_evidence_manifest=runtime_manifest,
            )
            with (
                mock.patch.object(checker, "run_json_command", side_effect=fake_run_json_command),
                mock.patch.object(
                    checker,
                    "bounded_artifact_file_scan",
                    return_value={"ready_to_build_core_evidence_pack": False},
                ),
            ):
                payload = checker.build_report(args)

        self.assertFalse(payload["ready"])
        self.assertEqual(payload["primary_blocker"], "approved_runtime_evidence_missing")
        self.assertIn("approved_runtime_evidence_missing", payload["blockers"])
        consume_gate = payload["first_evidence"]["consume_gate"]
        self.assertTrue(consume_gate["evaluated"])
        self.assertEqual(consume_gate["mode"], "consume")
        self.assertEqual(consume_gate["status"], "accepted")
        self.assertTrue(consume_gate["ready"])
        self.assertEqual(consume_gate["blocker_reasons"], [])
        self.assertFalse(consume_gate["promotion_ready"])
        self.assertFalse(consume_gate["public_sdk_ready"])
        self.assertFalse(consume_gate["runtime_ready"])
        self.assertNotIn("players_identity_first_evidence_consume_gate_blocked", payload["blockers"])
        anchors = payload["first_evidence"]["lifecycle_anchors"]
        self.assertEqual(anchors["source"], "players_identity_lifecycle_anchor_candidates")
        self.assertTrue(anchors["session_start_accepted"])
        self.assertTrue(anchors["session_end_accepted"])
        policy = payload["first_evidence"]["principal_invalidation_policy"]
        self.assertTrue(policy["policy_consume_ready"])
        self.assertFalse(policy["runtime_evidence_ready"])
        self.assertFalse(policy["promotion_ready"])
        self.assertFalse(policy["public_sdk_ready"])
        self.assertFalse(policy["runtime_ready"])
        runtime_requirements = payload["first_evidence"]["runtime_principal_lifecycle_evidence"]
        self.assertEqual(runtime_requirements["status"], "missing")
        self.assertFalse(runtime_requirements["accepted_by_this_preflight"])
        self.assertTrue(runtime_requirements["approval_required"])
        self.assertIn("promote", runtime_requirements["required_for"])
        self.assertIn("public_readiness", runtime_requirements["required_for"])
        self.assertIn("runtime_readiness", runtime_requirements["required_for"])
        self.assertIn(
            "offline layout comparison alone",
            runtime_requirements["insufficient_evidence"],
        )
        self.assertIn(
            "principal invalidation policy manifest alone",
            runtime_requirements["insufficient_evidence"],
        )
        observations = runtime_requirements["minimum_required_observations"]
        self.assertEqual(
            [observation["case"] for observation in observations],
            [
                "session_start_anchor",
                "session_start_rejected_anchor",
                "session_end_anchor",
                "stale_after_logout",
                "malformed_or_unsupported_evidence",
            ],
        )
        self.assertEqual([observation["required_order"] for observation in observations], [1, 2, 3, 4, 5])
        self.assertEqual(observations[0]["required_role"], "session_start")
        self.assertEqual(observations[0]["required_copied_fields"], ["bIsFromLogin", "ReturnValue"])
        self.assertEqual(observations[0]["required_copied_bool_fields"], ["bIsFromLogin", "ReturnValue"])
        self.assertEqual(observations[0]["required_copied_bool_values"], ["1", "1"])
        self.assertEqual(observations[1]["required_role"], "session_start_rejected")
        self.assertEqual(observations[1]["required_copied_fields"], ["bIsFromLogin", "ReturnValue"])
        self.assertEqual(observations[1]["required_copied_bool_fields"], ["bIsFromLogin", "ReturnValue"])
        self.assertEqual(observations[1]["required_copied_bool_values"], ["0", "1"])
        self.assertEqual(observations[2]["required_role"], "session_end")
        self.assertEqual(observations[2]["required_copied_fields"], [])
        self.assertEqual(observations[3]["required_role"], "none")
        self.assertEqual(observations[3]["required_copied_fields"], ["generation_state"])
        self.assertEqual(observations[4]["required_role"], "none")
        self.assertEqual(observations[4]["required_copied_fields"], [])
        approval_boundary = runtime_requirements["approval_boundary"]
        self.assertFalse(approval_boundary["approved_runtime_evidence_present"])
        self.assertFalse(approval_boundary["runtime_work_authorized_by_this_report"])
        self.assertFalse(approval_boundary["server_operations_authorized_by_this_report"])
        self.assertFalse(approval_boundary["publication_authorized_by_this_report"])
        self.assertIn(
            "debug attachment, ptrace, gcore, or runtime scanners",
            approval_boundary["separate_operator_approval_required_before"],
        )
        self.assertIn(
            "GitHub publication, tags, pushes, or release claims",
            approval_boundary["separate_operator_approval_required_before"],
        )
        self.assertEqual(
            payload["next_actionable_blocker"]["next_required_evidence"]["schema"],
            runtime_requirements["schema"],
        )
        runtime_manifest_diagnosis = payload["first_evidence"]["runtime_principal_lifecycle_evidence_manifest"]
        self.assertTrue(runtime_manifest_diagnosis["ready"])
        self.assertTrue(runtime_manifest_diagnosis["shape_accepted_by_this_checker"])
        self.assertFalse(runtime_manifest_diagnosis["approved_runtime_evidence_present"])
        self.assertFalse(runtime_manifest_diagnosis["runtime_evidence_ready"])
        self.assertEqual(runtime_manifest_diagnosis["remaining_blockers"], ["approved_runtime_evidence_missing"])
        self.assertEqual(payload["next_step"], "produce_approved_runtime_principal_lifecycle_evidence")
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])

    def test_artifact_root_diagnosis_summarizes_non_matching_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "scriptstruct-pack").mkdir()
            (root / "scriptstruct-pack" / "manifest.json").write_text(
                json.dumps({"schema": "obelisk.scriptstruct-inventory-pack.v1"}),
                encoding="utf-8",
            )
            (root / "container").mkdir()
            (root / "container" / "artifact-pack.manifest.json").write_text(
                json.dumps({"schema": "obelisk.offline-artifact-pack.v1"}),
                encoding="utf-8",
            )

            result = self.run_checker(["--artifact-root", str(root)], check=False)

        payload = json.loads(result.stdout)
        diagnosis = payload["reflection_inventory"]["artifact_root_diagnosis"]
        self.assertEqual(diagnosis["status"], "no_obelisk_reflection_inventory_pack_manifests_found")
        self.assertEqual(diagnosis["candidate_pack_count"], 0)
        self.assertEqual(diagnosis["reason_counts"]["missing_reflection_inventory_pack"], 1)
        self.assertEqual(diagnosis["reason_counts"]["scriptstruct_pack_not_reflection_inventory"], 1)
        self.assertEqual(diagnosis["reason_counts"]["artifact_pack_container_not_reflection_inventory"], 1)
        self.assertIn("scanned_paths", diagnosis["reason_examples"]["scriptstruct_pack_not_reflection_inventory"])
        self.assertIn("check_reflection_inventory_pack_readiness.py", diagnosis["next_useful_command"])

    def test_offline_input_diagnosis_reports_binary_and_core_like_files_without_accepting_pack(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary_dir = root / "offline-binaries" / "fake"
            binary_dir.mkdir(parents=True)
            (binary_dir / "ShooterGameServer").write_bytes(b"not the real server")
            (root / "core.1234").write_bytes(b"not a real core")

            result = self.run_checker(["--artifact-root", str(root)], check=False)

        payload = json.loads(result.stdout)
        offline_inputs = payload["artifact_chain"]["offline_inputs"]
        self.assertEqual(offline_inputs["status"], "offline_binary_present_hash_mismatch")
        self.assertEqual(len(offline_inputs["shooter_game_server_candidates"]), 1)
        self.assertFalse(offline_inputs["shooter_game_server_candidates"][0]["matches_current_binary"])
        self.assertEqual(len(offline_inputs["core_like_candidates"]), 1)
        self.assertFalse(offline_inputs["ready_to_build_core_evidence_pack"])
        self.assertIn("file presence only", " ".join(offline_inputs["non_claims"]))

    def test_offline_input_diagnosis_requires_paired_raw_binary_and_core(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw_dir = root / "player-identity-offline-test" / "raw"
            raw_dir.mkdir(parents=True)
            binary = raw_dir / "ShooterGameServer"
            binary.write_bytes(b"server")
            (root / "other" / "raw").mkdir(parents=True)
            (root / "other" / "raw" / "core").write_bytes(b"core")

            with mock.patch.object(checker, "sha256_file", return_value=checker.EXPECTED_SHOOTERGAME_SHA256):
                offline_inputs = checker.bounded_artifact_file_scan(root)

            self.assertEqual(offline_inputs["status"], "offline_binary_and_unpaired_core_like_inputs_present")
            self.assertFalse(offline_inputs["ready_to_build_core_evidence_pack"])
            self.assertEqual(offline_inputs["paired_raw_inputs"], [])

            (raw_dir / "core").write_bytes(b"paired-core")
            with mock.patch.object(checker, "sha256_file", return_value=checker.EXPECTED_SHOOTERGAME_SHA256):
                paired_inputs = checker.bounded_artifact_file_scan(root)

            self.assertEqual(paired_inputs["status"], "offline_binary_and_core_like_inputs_present")
            self.assertTrue(paired_inputs["ready_to_build_core_evidence_pack"])
            self.assertEqual(paired_inputs["paired_raw_inputs"][0]["binary"], str(binary))
            self.assertEqual(paired_inputs["paired_raw_inputs"][0]["core"], str(raw_dir / "core"))

    def test_offline_input_diagnosis_rejects_non_identity_raw_pair(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw_dir = root / "generic-offline-run" / "raw"
            raw_dir.mkdir(parents=True)
            binary = raw_dir / "ShooterGameServer"
            binary.write_bytes(b"server")
            (raw_dir / "core").write_bytes(b"core")

            with mock.patch.object(checker, "sha256_file", return_value=checker.EXPECTED_SHOOTERGAME_SHA256):
                offline_inputs = checker.bounded_artifact_file_scan(root)

        self.assertEqual(offline_inputs["status"], "offline_binary_and_unpaired_core_like_inputs_present")
        self.assertFalse(offline_inputs["ready_to_build_core_evidence_pack"])
        self.assertEqual(offline_inputs["paired_raw_inputs"], [])
        self.assertEqual(offline_inputs["rejected_raw_input_pairs"][0]["binary"], str(binary))
        self.assertEqual(
            offline_inputs["rejected_raw_input_pairs"][0]["reason"],
            "run_root_name_must_start_with_player_identity_offline",
        )

    def test_next_actionable_blocker_prioritizes_missing_core_input_when_binary_matches(self) -> None:
        blocker = checker.next_actionable_blocker(
            inventory_ready=False,
            inventory_payload_ready=False,
            inventory_chain={"ready": False, "blockers": [], "accepted_manifest": None},
            downstream_blockers=["fixture_coverage_incomplete"],
            offline_inputs={
                "status": "offline_binary_present_core_like_input_missing",
                "shooter_game_server_candidates": [
                    {
                        "path": "/tmp/artifacts/raw/ShooterGameServer",
                        "matches_current_binary": True,
                    }
                ],
            },
            raw_binary_pattern=Path("/tmp/artifacts/raw/ShooterGameServer"),
            raw_core_pattern=Path("/tmp/artifacts/raw/core"),
            core_manifest_pattern=Path("/tmp/artifacts/core-evidence-pack/manifest.json"),
            reflection_inventory_pattern=Path("/tmp/artifacts/reflection-inventory-pack/manifest.json"),
            next_operator_recipe={
                "build_core_evidence_pack": "python3 scripts/build_core_dump_evidence_pack.py ...",
                "build_reflection_inventory_pack": "python3 scripts/build_reflection_inventory_pack.py ...",
                "check_reflection_inventory_pack": "python3 scripts/check_reflection_inventory_pack_readiness.py ...",
                "plan_admin_focal_snapshots": "python3 scripts/plan_ufunction_focal_snapshots.py ...",
            },
        )

        self.assertEqual(blocker["code"], "non_protected_core_input_missing")
        self.assertEqual(blocker["blocked_until"], "non_protected_core_dump_input")
        self.assertEqual(blocker["available_binary"], "/tmp/artifacts/raw/ShooterGameServer")
        self.assertEqual(blocker["missing_input_path_pattern"], "/tmp/artifacts/raw/core")
        self.assertEqual(blocker["next_required_artifact"]["schema"], "obelisk.core-dump-evidence-pack.v1")
        self.assertIn("build_core_dump_evidence_pack.py", blocker["next_command_after_input"])
        self.assertFalse(blocker["promotion_ready"])
        self.assertFalse(blocker["public_sdk_ready"])
        self.assertFalse(blocker["runtime_ready"])

        operator_commands = checker.build_operator_next_commands(
            inventory_ready=False,
            offline_inputs={
                "status": "offline_binary_present_core_like_input_missing",
                "ready_to_build_core_evidence_pack": False,
                "shooter_game_server_candidates": [
                    {
                        "path": "/tmp/artifacts/raw/ShooterGameServer",
                        "matches_current_binary": True,
                    }
                ],
                "core_like_candidates": [],
            },
            next_blocker=blocker,
            raw_binary_pattern=Path("/tmp/artifacts/raw/ShooterGameServer"),
            raw_core_pattern=Path("/tmp/artifacts/raw/core"),
            core_manifest_pattern=Path("/tmp/artifacts/core-evidence-pack/manifest.json"),
            reflection_inventory_pattern=Path("/tmp/artifacts/reflection-inventory-pack/manifest.json"),
            next_operator_recipe={
                "build_core_evidence_pack": "python3 scripts/build_core_dump_evidence_pack.py ...",
                "build_reflection_inventory_pack": "python3 scripts/build_reflection_inventory_pack.py ...",
                "check_reflection_inventory_pack": "python3 scripts/check_reflection_inventory_pack_readiness.py ...",
                "plan_admin_focal_snapshots": "python3 scripts/plan_ufunction_focal_snapshots.py ...",
            },
        )
        self.assertEqual(operator_commands["current_blocker"], "non_protected_core_input_missing")
        self.assertEqual(operator_commands["missing_inputs"], ["non_protected_core_dump_input"])
        self.assertEqual(operator_commands["runnable_now"], [])
        self.assertTrue(operator_commands["inputs"]["matching_non_protected_shooter_game_server"]["present"])
        self.assertFalse(operator_commands["inputs"]["non_protected_core_dump_input"]["present"])
        self.assertFalse(operator_commands["ready_to_build_core_evidence_pack"])
        self.assertEqual(operator_commands["paired_raw_inputs"], [])
        input_staging = operator_commands["input_staging"]
        self.assertEqual(input_staging["status"], "blocked")
        self.assertFalse(input_staging["ready"])
        self.assertEqual(input_staging["blocked_until"], "non_protected_core_dump_input")
        self.assertEqual(
            input_staging["explicit_source_inputs_required"],
            [
                "matching_non_protected_shooter_game_server",
                "non_protected_core_dump_input",
            ],
        )
        self.assertIn("prepare_player_identity_offline_raw_layout.py", input_staging["command"])
        self.assertIn("--binary /tmp/artifacts/raw/ShooterGameServer", input_staging["command"])
        self.assertEqual(input_staging["command_argv"][5], "<non-protected-core-dump-input>")
        self.assertIn("--artifact-root /tmp", input_staging["command"])
        self.assertEqual(input_staging["command_argv"][9], "<run-id-suffix>")
        self.assertIn("does not create, validate, approve, or promote core dumps", " ".join(input_staging["non_claims"]))
        self.assertIn("does not build or approve core evidence packs", " ".join(input_staging["non_claims"]))
        blocked_resolution = operator_commands["blocked_input_resolution"]
        self.assertEqual(blocked_resolution["status"], "blocked")
        self.assertEqual(blocked_resolution["current_blocker"], "non_protected_core_input_missing")
        self.assertEqual(blocked_resolution["missing_inputs"], ["non_protected_core_dump_input"])
        self.assertEqual(blocked_resolution["available_matching_binary"], "/tmp/artifacts/raw/ShooterGameServer")
        self.assertEqual(blocked_resolution["expected_core_destination"], "/tmp/artifacts/raw/core")
        self.assertEqual(
            blocked_resolution["validation_command_argv"][3],
            "/tmp/player-identity-offline-<run-id-suffix>",
        )
        self.assertIn("validate_player_identity_raw_inputs.py", blocked_resolution["validation_command_after_missing_inputs_exist"])
        self.assertIn("/tmp/player-identity-offline-<run-id-suffix>", blocked_resolution["validation_command_argv"][3])
        self.assertIn("does not accept or promote core evidence", " ".join(blocked_resolution["non_claims"]))
        self.assertEqual(
            operator_commands["input_layout_requirements"]["next_input_preparation_action"],
            "stage_core_next_to_matching_binary_under_same_player_identity_raw_dir",
        )
        self.assertEqual(operator_commands["sequence"][0]["status"], "blocked")
        self.assertFalse(operator_commands["sequence"][0]["ready"])
        self.assertEqual(
            operator_commands["sequence"][0]["blocked_until"],
            "non_protected_core_dump_input",
        )

    def test_operator_recipe_uses_unambiguous_unpaired_core_for_staging(self) -> None:
        operator_commands = checker.build_operator_next_commands(
            inventory_ready=False,
            offline_inputs={
                "status": "offline_binary_and_unpaired_core_like_inputs_present",
                "ready_to_build_core_evidence_pack": False,
                "shooter_game_server_candidates": [
                    {
                        "path": "/tmp/artifacts/offline-binaries/current/ShooterGameServer",
                        "matches_current_binary": True,
                    }
                ],
                "core_like_candidates": [
                    {
                        "path": "/tmp/artifacts/unpaired/core.1234",
                        "size_bytes": 1234,
                    }
                ],
                "omitted_core_like_candidates": 0,
            },
            next_blocker={
                "code": "raw_inputs_unpaired",
                "blocked_until": "paired_non_protected_raw_binary_and_core",
            },
            raw_binary_pattern=Path("/tmp/artifacts/player-identity-offline-<run-id>/raw/ShooterGameServer"),
            raw_core_pattern=Path("/tmp/artifacts/player-identity-offline-<run-id>/raw/core"),
            core_manifest_pattern=Path("/tmp/artifacts/player-identity-offline-<run-id>/core-evidence-pack/manifest.json"),
            reflection_inventory_pattern=Path(
                "/tmp/artifacts/player-identity-offline-<run-id>/reflection-inventory-pack/manifest.json"
            ),
            next_operator_recipe={
                "build_core_evidence_pack": "python3 scripts/build_core_dump_evidence_pack.py ...",
                "build_reflection_inventory_pack": "python3 scripts/build_reflection_inventory_pack.py ...",
                "check_reflection_inventory_pack": "python3 scripts/check_reflection_inventory_pack_readiness.py ...",
                "plan_admin_focal_snapshots": "python3 scripts/plan_ufunction_focal_snapshots.py ...",
            },
        )

        input_staging = operator_commands["input_staging"]
        self.assertEqual(input_staging["status"], "ready")
        self.assertTrue(input_staging["ready"])
        self.assertIsNone(input_staging["blocked_until"])
        self.assertEqual(
            input_staging["command_argv"][3],
            "/tmp/artifacts/offline-binaries/current/ShooterGameServer",
        )
        self.assertEqual(input_staging["command_argv"][5], "/tmp/artifacts/unpaired/core.1234")
        self.assertIn("--core /tmp/artifacts/unpaired/core.1234", input_staging["command"])
        self.assertIn("--artifact-root /tmp/artifacts", input_staging["command"])
        self.assertEqual(operator_commands["ready_to_build_core_evidence_pack"], False)
        self.assertEqual(operator_commands["sequence"][0]["status"], "blocked")

    def test_detect_obelisk_commit_uses_env_then_git_head_then_unknown(self) -> None:
        completed = subprocess.CompletedProcess(
            ["git"],
            0,
            "abc123def456\n",
            "",
        )
        with (
            mock.patch.dict(os.environ, {"OBELISK_COMMIT": "envcommit123"}, clear=False),
            mock.patch.object(checker.subprocess, "run") as run,
        ):
            self.assertEqual(checker.detect_obelisk_commit(), "envcommit123")
            run.assert_not_called()

        with (
            mock.patch.dict(os.environ, {"OBELISK_COMMIT": ""}, clear=False),
            mock.patch.object(checker.subprocess, "run", return_value=completed) as run,
        ):
            self.assertEqual(checker.detect_obelisk_commit(), "abc123def456")
            run.assert_called_once()

        with (
            mock.patch.dict(os.environ, {"OBELISK_COMMIT": ""}, clear=False),
            mock.patch.object(
                checker.subprocess,
                "run",
                side_effect=subprocess.CalledProcessError(1, ["git"]),
            ),
        ):
            self.assertEqual(checker.detect_obelisk_commit(), "unknown")

    def test_report_stays_blocked_when_non_protected_core_input_is_missing(self) -> None:
        ok = subprocess.CompletedProcess(["mock"], 0, "", "")

        def fake_run_json_command(args: list[str], *, check: bool = False):
            command = " ".join(args)
            if "check_reflection_inventory_pack_readiness.py" in command:
                return ok, {"ready": False, "accepted_pack": None, "reasons": []}
            if "compare_reflection_snapshots.py" in command:
                return ok, {
                    "totals": {
                        "targets": 12,
                        "comparable": 10,
                        "blocked": 2,
                        "second_source_missing": 10,
                        "second_source_inconclusive": 0,
                        "second_source_rejected": 0,
                    },
                    "promotion_gate": {"promotion_ready": False},
                    "second_source_status": "missing",
                }
            if "build_redacted_ufunction_signatures.py" in command:
                return subprocess.CompletedProcess(
                    ["mock"],
                    1,
                    "{}",
                    "missing_required_target:ShooterPlayerController.ServerKickPlayer",
                ), {}
            if "check_player_identity_static_orientation.py" in command:
                return ok, {
                    "valid": True,
                    "accepted_for_orientation": True,
                    "not_artifact_gate": True,
                    "blockers": [],
                    "non_claims": ["candidate-only navigation evidence"],
                }
            self.fail(f"unexpected command: {command}")

        args = SimpleNamespace(
            artifact_root=Path("/tmp/player-identity-artifacts"),
            snapshot_root=Path("/tmp/player-identity-snapshots"),
            candidate_root=None,
        )
        with (
            mock.patch.object(checker, "run_json_command", side_effect=fake_run_json_command),
            mock.patch.object(
                checker,
                "bounded_artifact_file_scan",
                return_value={
                    "status": "offline_binary_present_core_like_input_missing",
                    "ready_to_build_core_evidence_pack": False,
                    "shooter_game_server_candidates": [
                        {
                            "path": "/tmp/player-identity-artifacts/player-identity-offline-a/raw/ShooterGameServer",
                            "matches_current_binary": True,
                        }
                    ],
                    "core_like_candidates": [],
                },
            ),
        ):
            payload = checker.build_report(args)

        self.assertFalse(payload["ready"])
        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["primary_blocker"], "non_protected_core_input_missing")
        self.assertEqual(payload["next_actionable_blocker"]["code"], "non_protected_core_input_missing")
        self.assertEqual(payload["progress_signal"]["status"], "blocked")
        self.assertFalse(payload["progress_signal"]["ready"])
        self.assertEqual(payload["progress_signal"]["primary_blocker"], "non_protected_core_input_missing")
        self.assertFalse(payload["progress_signal"]["coverage"]["reflection_inventory_accepted"])
        self.assertEqual(payload["progress_signal"]["missing"]["operator_inputs"], ["non_protected_core_dump_input"])
        operator_commands = payload["operator_next_commands"]
        self.assertEqual(operator_commands["runnable_now"], [])
        self.assertFalse(operator_commands["ready_to_build_core_evidence_pack"])
        self.assertTrue(operator_commands["inputs"]["matching_non_protected_shooter_game_server"]["present"])
        self.assertFalse(operator_commands["inputs"]["non_protected_core_dump_input"]["present"])
        input_staging = operator_commands["input_staging"]
        self.assertEqual(input_staging["status"], "blocked")
        self.assertFalse(input_staging["ready"])
        self.assertEqual(input_staging["blocked_until"], "non_protected_core_dump_input")
        self.assertEqual(
            input_staging["explicit_source_inputs_required"],
            [
                "matching_non_protected_shooter_game_server",
                "non_protected_core_dump_input",
            ],
        )
        self.assertIn(
            "--binary /tmp/player-identity-artifacts/player-identity-offline-a/raw/ShooterGameServer",
            input_staging["command"],
        )
        self.assertEqual(input_staging["command_argv"][5], "<non-protected-core-dump-input>")
        blocked_resolution = operator_commands["blocked_input_resolution"]
        self.assertEqual(blocked_resolution["status"], "blocked")
        self.assertEqual(blocked_resolution["current_blocker"], "non_protected_core_input_missing")
        self.assertEqual(blocked_resolution["missing_inputs"], ["non_protected_core_dump_input"])
        self.assertEqual(
            blocked_resolution["available_matching_binary"],
            "/tmp/player-identity-artifacts/player-identity-offline-a/raw/ShooterGameServer",
        )
        self.assertEqual(
            blocked_resolution["expected_core_destination"],
            "/tmp/player-identity-artifacts/player-identity-offline-<run-id>/raw/core",
        )
        self.assertEqual(
            blocked_resolution["validation_command_argv"][3],
            "/tmp/player-identity-artifacts/player-identity-offline-<run-id-suffix>",
        )
        self.assertEqual(operator_commands["sequence"][0]["status"], "blocked")
        self.assertFalse(operator_commands["sequence"][0]["ready"])
        self.assertEqual(operator_commands["sequence"][0]["blocked_until"], "non_protected_core_dump_input")

    def test_next_actionable_blocker_reports_unpaired_core_and_binary(self) -> None:
        blocker = checker.next_actionable_blocker(
            inventory_ready=False,
            inventory_payload_ready=False,
            inventory_chain={"ready": False, "blockers": [], "accepted_manifest": None},
            downstream_blockers=[],
            offline_inputs={
                "status": "offline_binary_and_unpaired_core_like_inputs_present",
                "ready_to_build_core_evidence_pack": False,
                "shooter_game_server_candidates": [
                    {
                        "path": "/tmp/artifacts/player-identity-offline-a/raw/ShooterGameServer",
                        "matches_current_binary": True,
                    }
                ],
                "core_like_candidates": [{"path": "/tmp/artifacts/other/raw/core"}],
            },
            raw_binary_pattern=Path("/tmp/artifacts/player-identity-offline-<run-id>/raw/ShooterGameServer"),
            raw_core_pattern=Path("/tmp/artifacts/player-identity-offline-<run-id>/raw/core"),
            core_manifest_pattern=Path("/tmp/artifacts/player-identity-offline-<run-id>/core-evidence-pack/manifest.json"),
            reflection_inventory_pattern=Path("/tmp/artifacts/player-identity-offline-<run-id>/reflection-inventory-pack/manifest.json"),
            next_operator_recipe={
                "build_core_evidence_pack": "python3 scripts/build_core_dump_evidence_pack.py ...",
                "build_reflection_inventory_pack": "python3 scripts/build_reflection_inventory_pack.py ...",
                "check_reflection_inventory_pack": "python3 scripts/check_reflection_inventory_pack_readiness.py ...",
                "plan_admin_focal_snapshots": "python3 scripts/plan_ufunction_focal_snapshots.py ...",
            },
        )
        self.assertEqual(blocker["code"], "paired_non_protected_raw_inputs_missing")
        self.assertEqual(blocker["blocked_until"], "paired_non_protected_shooter_game_server_and_core_dump_input")

        operator_commands = checker.build_operator_next_commands(
            inventory_ready=False,
            offline_inputs={
                "status": "offline_binary_and_unpaired_core_like_inputs_present",
                "ready_to_build_core_evidence_pack": False,
                "shooter_game_server_candidates": [
                    {
                        "path": "/tmp/artifacts/player-identity-offline-a/raw/ShooterGameServer",
                        "matches_current_binary": True,
                    }
                ],
                "core_like_candidates": [{"path": "/tmp/artifacts/other/raw/core"}],
            },
            next_blocker=blocker,
            raw_binary_pattern=Path("/tmp/artifacts/player-identity-offline-<run-id>/raw/ShooterGameServer"),
            raw_core_pattern=Path("/tmp/artifacts/player-identity-offline-<run-id>/raw/core"),
            core_manifest_pattern=Path("/tmp/artifacts/player-identity-offline-<run-id>/core-evidence-pack/manifest.json"),
            reflection_inventory_pattern=Path("/tmp/artifacts/player-identity-offline-<run-id>/reflection-inventory-pack/manifest.json"),
            next_operator_recipe={
                "build_core_evidence_pack": "python3 scripts/build_core_dump_evidence_pack.py ...",
                "build_reflection_inventory_pack": "python3 scripts/build_reflection_inventory_pack.py ...",
                "check_reflection_inventory_pack": "python3 scripts/check_reflection_inventory_pack_readiness.py ...",
                "plan_admin_focal_snapshots": "python3 scripts/plan_ufunction_focal_snapshots.py ...",
            },
        )
        self.assertEqual(operator_commands["missing_inputs"], ["paired_non_protected_raw_binary_and_core"])
        self.assertEqual(operator_commands["runnable_now"], [])
        self.assertEqual(
            operator_commands["input_layout_requirements"]["next_input_preparation_action"],
            "restage_binary_and_core_as_siblings_under_same_player_identity_raw_dir",
        )

    def test_accepted_inventory_still_fails_closed_on_malformed_coverage_payload(self) -> None:
        ok = subprocess.CompletedProcess(["mock"], 0, "", "")

        def fake_run_json_command(args: list[str], *, check: bool = False):
            command = " ".join(args)
            if "check_reflection_inventory_pack_readiness.py" in command:
                return ok, self.accepted_inventory_payload()
            if "compare_reflection_snapshots.py" in command:
                return ok, {"totals": {"targets": 12}}
            if "build_redacted_ufunction_signatures.py" in command:
                return ok, {
                    "schema": "obelisk.players-identity-first-evidence.v1",
                    "lifecycle_anchors": {
                        "session_start_accepted": True,
                        "session_end_accepted": True,
                        "accepted_start_targets": ["ShooterGameMode.PostLogin"],
                        "accepted_end_targets": ["ShooterGameMode.Logout"],
                        "blockers": [],
                    },
                }
            if "check_player_identity_static_orientation.py" in command:
                return ok, {
                    "valid": True,
                    "accepted_for_orientation": True,
                    "not_artifact_gate": True,
                    "blockers": [],
                    "non_claims": ["candidate-only navigation evidence"],
                }
            self.fail(f"unexpected command: {command}")

        args = SimpleNamespace(
            artifact_root=Path("/tmp/player-identity-artifacts"),
            snapshot_root=Path("/tmp/player-identity-snapshots"),
            candidate_root=None,
        )
        with (
            mock.patch.object(checker, "run_json_command", side_effect=fake_run_json_command),
            mock.patch.object(
                checker,
                "bounded_artifact_file_scan",
                return_value={"ready_to_build_core_evidence_pack": False},
            ),
        ):
            payload = checker.build_report(args)

        self.assertFalse(payload["ready"])
        self.assertEqual(payload["status"], "blocked")
        self.assertIn("fixture_coverage_incomplete", payload["blockers"])
        self.assertEqual(payload["deferred_until_reflection_inventory_ready"], [])
        self.assertEqual(
            payload["static_orientation"]["pre_core_evidence_boundary"]["status"],
            "orientation_only_not_downstream_promotion_gate",
        )
        self.assertFalse(payload["static_orientation"]["pre_core_evidence_boundary"]["blocked"])
        self.assertEqual(payload["static_orientation"]["pre_core_evidence_boundary"]["blockers"], [])
        self.assertIn(
            "static orientation does not replace core evidence, reflection inventory, focal snapshots",
            " ".join(payload["static_orientation"]["pre_core_evidence_boundary"]["non_claims"]),
        )

    def test_candidate_ready_remains_internal_planning_not_promotion(self) -> None:
        ok = subprocess.CompletedProcess(["mock"], 0, "", "")

        def fake_run_json_command(args: list[str], *, check: bool = False):
            command = " ".join(args)
            if "check_reflection_inventory_pack_readiness.py" in command:
                return ok, self.accepted_inventory_payload()
            if "compare_reflection_snapshots.py" in command:
                return ok, {
                    "totals": {
                        "targets": 12,
                        "comparable": 12,
                        "blocked": 0,
                        "second_source_missing": 0,
                        "second_source_inconclusive": 0,
                        "second_source_rejected": 0,
                    },
                    "promotion_gate": {"promotion_ready": False},
                    "second_source_status": "compared",
                }
            if "build_redacted_ufunction_signatures.py" in command:
                return ok, {
                    "schema": "obelisk.players-identity-first-evidence.v1",
                    "lifecycle_anchors": {
                        "session_start_accepted": True,
                        "session_end_accepted": True,
                        "accepted_start_targets": ["ShooterGameMode.PostLogin"],
                        "accepted_end_targets": ["ShooterGameMode.Logout"],
                        "blockers": [],
                    },
                }
            if "check_player_identity_static_orientation.py" in command:
                return ok, {
                    "valid": True,
                    "accepted_for_orientation": True,
                    "not_artifact_gate": True,
                    "blockers": [],
                    "non_claims": ["candidate-only navigation evidence"],
                }
            self.fail(f"unexpected command: {command}")

        args = SimpleNamespace(
            artifact_root=Path("/tmp/player-identity-artifacts"),
            snapshot_root=Path("/tmp/player-identity-snapshots"),
            candidate_root=None,
        )
        with (
            mock.patch.object(checker, "run_json_command", side_effect=fake_run_json_command),
            mock.patch.object(
                checker,
                "bounded_artifact_file_scan",
                return_value={"ready_to_build_core_evidence_pack": False},
            ),
        ):
            payload = checker.build_report(args)

        self.assertFalse(payload["ready"])
        self.assertEqual(payload["status"], "blocked")
        self.assertFalse(payload["accepted_for_internal_planning"])
        self.assertEqual(payload["primary_blocker"], "principal_invalidation_semantics_unresolved")
        self.assertTrue(payload["not_artifact_gate"])
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertEqual(payload["progress_signal"]["status"], "blocked")
        self.assertFalse(payload["progress_signal"]["ready"])
        self.assertTrue(payload["progress_signal"]["coverage"]["reflection_inventory_accepted"])
        self.assertEqual(payload["progress_signal"]["coverage"]["fixture_targets"], "12/12")
        self.assertTrue(payload["progress_signal"]["accepted_anchors"]["session_start"])
        self.assertTrue(payload["progress_signal"]["accepted_anchors"]["session_end"])
        self.assertIn("candidate-only planning evidence", " ".join(payload["non_claims"]))

    def test_lower_level_accepted_pack_shape_passes_chain_validation_without_promotion(self) -> None:
        ok = subprocess.CompletedProcess(["mock"], 0, "", "")

        def fake_run_json_command(args: list[str], *, check: bool = False):
            command = " ".join(args)
            if "check_reflection_inventory_pack_readiness.py" in command:
                return ok, self.lower_level_accepted_inventory_payload()
            if "compare_reflection_snapshots.py" in command:
                return ok, {
                    "totals": {
                        "targets": 12,
                        "comparable": 12,
                        "blocked": 0,
                        "second_source_missing": 0,
                        "second_source_inconclusive": 0,
                        "second_source_rejected": 0,
                    },
                    "promotion_gate": {"promotion_ready": False},
                    "second_source_status": "compared",
                }
            if "build_redacted_ufunction_signatures.py" in command:
                return ok, {
                    "schema": "obelisk.players-identity-first-evidence.v1",
                    "lifecycle_anchors": {
                        "session_start_accepted": True,
                        "session_end_accepted": True,
                        "accepted_start_targets": ["ShooterGameMode.PostLogin"],
                        "accepted_end_targets": ["ShooterGameMode.Logout"],
                        "blockers": [],
                    },
                }
            if "check_player_identity_static_orientation.py" in command:
                return ok, {
                    "valid": True,
                    "accepted_for_orientation": True,
                    "not_artifact_gate": True,
                    "blockers": [],
                    "non_claims": ["candidate-only navigation evidence"],
                }
            self.fail(f"unexpected command: {command}")

        args = SimpleNamespace(
            artifact_root=Path("/tmp/player-identity-artifacts"),
            snapshot_root=Path("/tmp/player-identity-snapshots"),
            candidate_root=None,
        )
        with (
            mock.patch.object(checker, "run_json_command", side_effect=fake_run_json_command),
            mock.patch.object(
                checker,
                "bounded_artifact_file_scan",
                return_value={"ready_to_build_core_evidence_pack": False},
            ),
        ):
            payload = checker.build_report(args)

        self.assertTrue(payload["reflection_inventory"]["chain_validation"]["ready"])
        self.assertEqual(payload["reflection_inventory"]["chain_validation"]["blockers"], [])
        self.assertFalse(payload["ready"])
        self.assertEqual(payload["status"], "blocked")
        self.assertFalse(payload["accepted_for_internal_planning"])
        self.assertEqual(payload["primary_blocker"], "principal_invalidation_semantics_unresolved")
        self.assertTrue(payload["not_artifact_gate"])
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertNotIn("accepted_reflection_inventory_chain_incomplete", payload["blockers"])
        self.assertTrue(payload["progress_signal"]["coverage"]["reflection_inventory_accepted"])
        self.assertIn("candidate-only planning evidence", " ".join(payload["non_claims"]))

    def test_ready_inventory_payload_without_core_evidence_chain_still_blocks(self) -> None:
        ok = subprocess.CompletedProcess(["mock"], 0, "", "")

        def fake_run_json_command(args: list[str], *, check: bool = False):
            command = " ".join(args)
            if "check_reflection_inventory_pack_readiness.py" in command:
                return ok, {
                    "ready": True,
                    "accepted_pack": {"manifest": "/tmp/inventory/manifest.json"},
                    "reasons": [],
                }
            if "compare_reflection_snapshots.py" in command:
                return ok, {
                    "totals": {
                        "targets": 12,
                        "comparable": 12,
                        "blocked": 0,
                        "second_source_missing": 0,
                        "second_source_inconclusive": 0,
                        "second_source_rejected": 0,
                    },
                    "promotion_gate": {"promotion_ready": False},
                    "second_source_status": "compared",
                }
            if "build_redacted_ufunction_signatures.py" in command:
                return ok, {
                    "schema": "obelisk.players-identity-first-evidence.v1",
                    "lifecycle_anchors": {
                        "session_start_accepted": True,
                        "session_end_accepted": True,
                        "accepted_start_targets": ["ShooterGameMode.PostLogin"],
                        "accepted_end_targets": ["ShooterGameMode.Logout"],
                        "blockers": [],
                    },
                }
            if "check_player_identity_static_orientation.py" in command:
                return ok, {
                    "valid": True,
                    "accepted_for_orientation": True,
                    "not_artifact_gate": True,
                    "blockers": [],
                    "non_claims": ["candidate-only navigation evidence"],
                }
            self.fail(f"unexpected command: {command}")

        args = SimpleNamespace(
            artifact_root=Path("/tmp/player-identity-artifacts"),
            snapshot_root=Path("/tmp/player-identity-snapshots"),
            candidate_root=None,
        )
        with (
            mock.patch.object(checker, "run_json_command", side_effect=fake_run_json_command),
            mock.patch.object(
                checker,
                "bounded_artifact_file_scan",
                return_value={"ready_to_build_core_evidence_pack": False},
            ),
        ):
            payload = checker.build_report(args)

        self.assertFalse(payload["ready"])
        self.assertEqual(payload["status"], "blocked")
        self.assertIn("missing_reflection_inventory_pack_or_core_evidence_pack", payload["blockers"])
        self.assertIn("accepted_reflection_inventory_chain_incomplete", payload["blockers"])
        self.assertFalse(payload["reflection_inventory"]["chain_validation"]["ready"])
        self.assertIn(
            "accepted_reflection_inventory_core_evidence_pack_manifest_missing",
            payload["reflection_inventory"]["chain_validation"]["blockers"],
        )

    def test_ready_inventory_substitutes_are_rejected_before_identity_planning(self) -> None:
        ok = subprocess.CompletedProcess(["mock"], 0, "", "")
        base_pack = self.accepted_inventory_payload()["accepted_pack"]
        two_targets = [
            "ShooterPlayerController.ServerKickPlayer",
            "ShooterPlayerController.ServerListPlayers",
        ]
        cases = [
            (
                "scriptstruct_inventory",
                {
                    **base_pack,
                    "schema": "obelisk.scriptstruct-inventory-pack.v1",
                },
                "accepted_pack_schema_not_reflection_inventory",
            ),
            (
                "direct_core_manual_mode",
                {
                    **base_pack,
                    "inputs": {
                        "core": "/tmp/core",
                        "ark_binary": "/tmp/ShooterGameServer",
                        "target_sets": ["players-identity-lifecycle-intake"],
                    },
                },
                "accepted_reflection_inventory_core_evidence_pack_manifest_missing",
            ),
            (
                "standalone_snapshots",
                {
                    **base_pack,
                    "inputs": {
                        "snapshot_root": "/tmp/snapshots",
                        "target_sets": ["players-identity-lifecycle-intake"],
                    },
                },
                "accepted_reflection_inventory_core_evidence_pack_manifest_missing",
            ),
            (
                "radare2_static_orientation_manifest",
                {
                    **base_pack,
                    "inputs": {
                        "evidence_pack_manifest": "/tmp/radare2-static-orientation/manifest.json",
                        "evidence_pack_schema": "obelisk.radare2-static-orientation-windows.v1",
                        "evidence_pack_status": "candidate_only_orientation_captured",
                        "target_sets": ["players-identity-lifecycle-intake"],
                    },
                },
                "accepted_reflection_inventory_static_orientation_manifest_not_core_evidence",
            ),
            (
                "two_function_only_inventory",
                {
                    **base_pack,
                    "matched_targets": two_targets,
                    "target_set_coverage": {
                        "target_sets": [
                            {
                                "name": "players-identity-lifecycle-intake",
                                "expected_targets": two_targets,
                                "covered_targets": two_targets,
                                "missing_targets": [],
                                "complete": True,
                            }
                        ]
                    },
                },
                "accepted_reflection_inventory_not_full_player_identity_target_set",
            ),
        ]

        def fake_run_json_command(args: list[str], *, check: bool = False):
            command = " ".join(args)
            if "compare_reflection_snapshots.py" in command:
                return ok, {
                    "totals": {
                        "targets": 12,
                        "comparable": 12,
                        "blocked": 0,
                        "second_source_missing": 0,
                        "second_source_inconclusive": 0,
                        "second_source_rejected": 0,
                    },
                    "promotion_gate": {"promotion_ready": False},
                    "second_source_status": "compared",
                }
            if "build_redacted_ufunction_signatures.py" in command:
                return ok, {
                    "schema": "obelisk.players-identity-first-evidence.v1",
                    "lifecycle_anchors": {
                        "session_start_accepted": True,
                        "session_end_accepted": True,
                        "accepted_start_targets": ["ShooterGameMode.PostLogin"],
                        "accepted_end_targets": ["ShooterGameMode.Logout"],
                        "blockers": [],
                    },
                }
            if "check_player_identity_static_orientation.py" in command:
                return ok, {
                    "valid": True,
                    "accepted_for_orientation": True,
                    "not_artifact_gate": True,
                    "blockers": [],
                    "non_claims": ["candidate-only navigation evidence"],
                }
            self.fail(f"unexpected command: {command}")

        args = SimpleNamespace(
            artifact_root=Path("/tmp/player-identity-artifacts"),
            snapshot_root=Path("/tmp/player-identity-snapshots"),
            candidate_root=None,
        )
        for label, accepted_pack, expected_blocker in cases:
            with self.subTest(label=label):
                def fake_with_inventory(args: list[str], *, check: bool = False):
                    command = " ".join(args)
                    if "check_reflection_inventory_pack_readiness.py" in command:
                        return ok, {"ready": True, "accepted_pack": accepted_pack, "reasons": []}
                    return fake_run_json_command(args, check=check)

                with (
                    mock.patch.object(checker, "run_json_command", side_effect=fake_with_inventory),
                    mock.patch.object(
                        checker,
                        "bounded_artifact_file_scan",
                        return_value={"ready_to_build_core_evidence_pack": False},
                    ),
                ):
                    payload = checker.build_report(args)

                self.assertFalse(payload["ready"])
                self.assertIn("accepted_reflection_inventory_chain_incomplete", payload["blockers"])
                self.assertIn(expected_blocker, payload["reflection_inventory"]["chain_validation"]["blockers"])

    def test_accepted_inventory_still_fails_closed_on_wrong_first_evidence_schema(self) -> None:
        ok = subprocess.CompletedProcess(["mock"], 0, "", "")

        def fake_run_json_command(args: list[str], *, check: bool = False):
            command = " ".join(args)
            if "check_reflection_inventory_pack_readiness.py" in command:
                return ok, self.accepted_inventory_payload()
            if "compare_reflection_snapshots.py" in command:
                return ok, {
                    "totals": {
                        "targets": 12,
                        "comparable": 12,
                        "blocked": 0,
                        "second_source_missing": 0,
                        "second_source_inconclusive": 0,
                        "second_source_rejected": 0,
                    },
                    "promotion_gate": {"promotion_ready": False},
                    "second_source_status": "compared",
                }
            if "build_redacted_ufunction_signatures.py" in command:
                return ok, {
                    "schema": "unexpected.schema.v1",
                    "lifecycle_anchors": {
                        "session_start_accepted": True,
                        "session_end_accepted": True,
                        "accepted_start_targets": ["ShooterGameMode.PostLogin"],
                        "accepted_end_targets": ["ShooterGameMode.Logout"],
                        "blockers": [],
                    },
                }
            if "check_player_identity_static_orientation.py" in command:
                return ok, {
                    "valid": True,
                    "accepted_for_orientation": True,
                    "not_artifact_gate": True,
                    "blockers": [],
                    "non_claims": ["candidate-only navigation evidence"],
                }
            self.fail(f"unexpected command: {command}")

        args = SimpleNamespace(
            artifact_root=Path("/tmp/player-identity-artifacts"),
            snapshot_root=Path("/tmp/player-identity-snapshots"),
            candidate_root=None,
        )
        with (
            mock.patch.object(checker, "run_json_command", side_effect=fake_run_json_command),
            mock.patch.object(
                checker,
                "bounded_artifact_file_scan",
                return_value={"ready_to_build_core_evidence_pack": False},
            ),
        ):
            payload = checker.build_report(args)

        self.assertFalse(payload["ready"])
        self.assertEqual(payload["status"], "blocked")
        self.assertIn("players_identity_first_evidence_not_buildable", payload["blockers"])
        self.assertNotIn("accepted_lifecycle_anchors_missing", payload["blockers"])

    def test_approved_runtime_principal_lifecycle_manifest_clears_runtime_blocker_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            approved_manifest = Path(tmp) / "approved-runtime-principal-lifecycle.json"
            approved_manifest.write_text(
                json.dumps(approved_runtime_principal_lifecycle_manifest()),
                encoding="utf-8",
            )

            diagnosis = checker.approved_runtime_principal_lifecycle_evidence_manifest_diagnosis(
                approved_manifest
            )

        self.assertTrue(diagnosis["ready"])
        self.assertTrue(diagnosis["approved_runtime_evidence_present"])
        self.assertTrue(diagnosis["runtime_evidence_ready"])
        self.assertFalse(diagnosis["promotion_ready"])
        self.assertFalse(diagnosis["public_sdk_ready"])
        self.assertFalse(diagnosis["runtime_ready"])
        self.assertEqual(diagnosis["remaining_blockers"], [])
        self.assertEqual(
            diagnosis["observed_runtime_cases"],
            ["session_start_anchor", "session_start_rejected_anchor", "session_end_anchor"],
        )
        self.assertEqual(
            diagnosis["consumer_cases"],
            ["malformed_or_unsupported_evidence", "stale_after_logout"],
        )


if __name__ == "__main__":
    unittest.main()
