#!/usr/bin/env python3
"""Tests for check_player_identity_first_evidence_readiness.py."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from test_check_player_identity_runtime_principal_lifecycle_approved_evidence import (
    SAFE_OFFLINE_WORKSPACE,
    manifest as approved_runtime_principal_lifecycle_manifest,
    safe_test_env as approved_runtime_safe_test_env,
)

import check_player_identity_first_evidence_readiness as checker
from test_check_player_identity_lifecycle_anchor_candidates import accepted_lifecycle_anchor_manifest
from test_check_player_identity_principal_invalidation_policy import manifest as principal_policy_manifest
from test_check_player_identity_runtime_principal_lifecycle_evidence import manifest as runtime_principal_lifecycle_manifest
from test_validate_offline_artifact_gate import players_identity_first_evidence_manifest
import prepare_player_principal_lifecycle_window_request as prepare_window_request
from reflection_target_sets import schema_target_list  # noqa: E402


def current_obelisk_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
    ).strip()


def lifecycle_manifest_bound_to_first_evidence(first_evidence: dict | None = None) -> dict:
    first_evidence = first_evidence or players_identity_first_evidence_manifest()
    payload = accepted_lifecycle_anchor_manifest()
    source_ids = first_evidence["artifact_identity"]["source_artifact_ids"]
    payload["artifact_identity"]["source_artifact_ids"] = list(source_ids)
    snapshots_by_target = {
        snapshot["target"]: snapshot
        for snapshot in first_evidence["generated_from"]["input_snapshots"]
    }
    for anchor in payload["candidate_anchors"]:
        target = anchor.get("target")
        snapshot = snapshots_by_target.get(target)
        if snapshot is not None:
            anchor["evidence"]["source_snapshot"] = snapshot["id"]
            anchor["evidence"]["source_snapshot_sha256"] = snapshot["sha256"]
    return payload


def principal_policy_bound_to_lifecycle(lifecycle_manifest: dict | None = None) -> dict:
    lifecycle_manifest = lifecycle_manifest or lifecycle_manifest_bound_to_first_evidence()
    payload = principal_policy_manifest()
    payload["lifecycle_layout_source"]["source_binding"] = {
        "lifecycle_manifest_schema": lifecycle_manifest["schema"],
        "artifact_identity_source_artifact_ids": list(
            lifecycle_manifest["artifact_identity"]["source_artifact_ids"]
        ),
        "accepted_start_targets": list(lifecycle_manifest["lifecycle_acceptance"]["accepted_start_targets"]),
        "accepted_end_targets": list(lifecycle_manifest["lifecycle_acceptance"]["accepted_end_targets"]),
    }
    return payload


class CheckPlayerIdentityFirstEvidenceReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self._old_approved_roots = (
            checker.approved_runtime_principal_lifecycle_evidence.APPROVED_OFFLINE_WORKSPACE_ROOTS
        )
        self._old_window_roots = (
            checker.approved_runtime_principal_lifecycle_evidence.window_manifest_checker.APPROVED_OFFLINE_WORKSPACE_ROOTS
        )
        checker.approved_runtime_principal_lifecycle_evidence.APPROVED_OFFLINE_WORKSPACE_ROOTS = (
            SAFE_OFFLINE_WORKSPACE,
        )
        checker.approved_runtime_principal_lifecycle_evidence.window_manifest_checker.APPROVED_OFFLINE_WORKSPACE_ROOTS = (
            SAFE_OFFLINE_WORKSPACE,
        )

    def tearDown(self) -> None:
        checker.approved_runtime_principal_lifecycle_evidence.APPROVED_OFFLINE_WORKSPACE_ROOTS = (
            self._old_approved_roots
        )
        checker.approved_runtime_principal_lifecycle_evidence.window_manifest_checker.APPROVED_OFFLINE_WORKSPACE_ROOTS = (
            self._old_window_roots
        )

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
            "OBELISK_COMMIT environment variable if set; otherwise unknown; this checker does not invoke Git",
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
        public_contract_gap = payload["first_evidence"]["public_contract_gap_report"]
        self.assertTrue(public_contract_gap["ready"])
        self.assertEqual(public_contract_gap["primary_offline_gap"], "lifetime.generation_scope_invalidation")
        self.assertEqual(
            public_contract_gap["contract_review_inputs_resolved"],
            [
                "privacy.identifier_redaction",
                "planning.source_bound_committed_manifests",
                "lifetime.generation_scope_invalidation.candidate_policy",
            ],
        )
        planning_source = public_contract_gap["source_bound_planning_manifest_verification"]
        self.assertTrue(planning_source["accepted_for_contract_review"])
        self.assertIsNone(planning_source["current_route_blocker"])
        self.assertEqual([], planning_source["blockers"])
        self.assertTrue(public_contract_gap["identifier_redaction_evidence"]["accepted_for_contract_review"])
        self.assertTrue(public_contract_gap["principal_invalidation_policy"]["accepted_for_policy_review"])
        self.assertFalse(public_contract_gap["promotion_ready"])
        self.assertFalse(public_contract_gap["public_sdk_ready"])
        self.assertFalse(public_contract_gap["runtime_ready"])
        self.assertFalse(public_contract_gap["public_header_allowed"])

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

    def test_default_artifact_root_can_fallback_to_approved_workspace_when_no_identity_pack_exists(self) -> None:
        ok = subprocess.CompletedProcess(["mock"], 0, "", "")
        scanned_roots: list[str] = []
        offline_scan_roots: list[Path] = []

        def fake_run_json_command(args: list[str], *, check: bool = False):
            command = " ".join(args)
            if "check_reflection_inventory_pack_readiness.py" in command:
                root = args[args.index("--root") + 1]
                scanned_roots.append(root)
                if root == str(checker.DEFAULT_ARTIFACT_ROOT):
                    return ok, {
                        "ready": False,
                        "accepted_pack": None,
                        "manifests_scanned": 0,
                        "candidate_packs": [],
                        "reasons": [],
                    }
                if root == str(checker.APPROVED_WORKSPACE_FALLBACK_ROOT):
                    return ok, self.lower_level_accepted_inventory_payload()
            if "compare_reflection_snapshots.py" in command:
                return ok, {
                    "totals": {
                        "targets": 12,
                        "comparable": 12,
                        "blocked": 0,
                        "second_source_accepted": 0,
                        "second_source_missing": 12,
                        "second_source_inconclusive": 0,
                        "second_source_rejected": 0,
                    },
                    "promotion_gate": {"promotion_ready": False},
                    "second_source_status": "missing_candidate_root",
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

        def fake_bounded_artifact_file_scan(root: Path, *, max_depth: int = 6):
            offline_scan_roots.append(root)
            return {
                "status": "offline_binary_and_core_like_inputs_missing",
                "artifact_root_only": True,
                "resolved_root": str(root),
                "server_root_excluded": "/servidor/ark",
                "shooter_game_server_candidates": [],
                "core_like_candidates": [],
                "ready_to_build_core_evidence_pack": False,
            }

        args = SimpleNamespace(
            artifact_root=checker.DEFAULT_ARTIFACT_ROOT,
            snapshot_root=Path("/tmp/player-identity-snapshots"),
            candidate_root=None,
        )
        with (
            mock.patch.object(checker, "run_json_command", side_effect=fake_run_json_command),
            mock.patch.object(checker, "bounded_artifact_file_scan", side_effect=fake_bounded_artifact_file_scan),
        ):
            payload = checker.build_report(args)

        self.assertEqual(
            scanned_roots,
            [
                str(checker.DEFAULT_ARTIFACT_ROOT),
                str(checker.APPROVED_WORKSPACE_FALLBACK_ROOT),
            ],
        )
        self.assertEqual(offline_scan_roots, [checker.APPROVED_WORKSPACE_FALLBACK_ROOT])
        self.assertEqual(payload["artifact_root"], str(checker.DEFAULT_ARTIFACT_ROOT))
        self.assertEqual(payload["effective_artifact_root"], str(checker.APPROVED_WORKSPACE_FALLBACK_ROOT))
        self.assertTrue(payload["artifact_root_fallback"]["used"])
        self.assertEqual(
            payload["artifact_root_fallback"]["reason"],
            "default_root_had_no_reflection_inventory_pack",
        )
        self.assertTrue(payload["reflection_inventory"]["ready"])
        self.assertTrue(payload["artifact_chain"]["ready_to_plan_admin_snapshots"])

    def test_default_preflight_uses_approved_workspace_identity_inputs_when_available(self) -> None:
        ok = subprocess.CompletedProcess(["mock"], 0, "", "")
        scanned_roots: list[str] = []
        compared_with_candidate: list[str] = []

        def fake_run_json_command(args: list[str], *, check: bool = False):
            command = " ".join(args)
            if "check_reflection_inventory_pack_readiness.py" in command:
                root = args[args.index("--root") + 1]
                scanned_roots.append(root)
                if root == str(checker.DEFAULT_ARTIFACT_ROOT):
                    return ok, {
                        "ready": False,
                        "accepted_pack": None,
                        "manifests_scanned": 0,
                        "candidate_packs": [],
                        "reasons": [],
                    }
                return ok, self.lower_level_accepted_inventory_payload()
            if "compare_reflection_snapshots.py" in command:
                self.assertIn("--candidate-root", args)
                compared_with_candidate.append(args[args.index("--candidate-root") + 1])
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
                    "promotion_gate": {"promotion_ready": False},
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

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate_root = root / "focal-snapshots"
            candidate_root.mkdir()
            lifecycle_manifest = root / "players-identity-lifecycle-anchor-candidates.json"
            principal_manifest = root / "players-identity-principal-invalidation-policy.json"
            lifecycle_payload = lifecycle_manifest_bound_to_first_evidence()
            lifecycle_manifest.write_text(json.dumps(lifecycle_payload), encoding="utf-8")
            principal_manifest.write_text(
                json.dumps(principal_policy_bound_to_lifecycle(lifecycle_payload)),
                encoding="utf-8",
            )
            args = SimpleNamespace(
                artifact_root=checker.DEFAULT_ARTIFACT_ROOT,
                snapshot_root=Path("/tmp/player-identity-snapshots"),
                candidate_root=None,
                lifecycle_anchor_candidates_manifest=None,
                principal_invalidation_policy_manifest=None,
                runtime_principal_lifecycle_evidence_manifest=None,
                approved_runtime_principal_lifecycle_evidence_manifest=None,
            )
            with (
                mock.patch.object(checker, "APPROVED_WORKSPACE_FALLBACK_ROOT", root),
                mock.patch.object(checker, "APPROVED_CANDIDATE_ROOT_FALLBACK", candidate_root),
                mock.patch.object(checker, "APPROVED_LIFECYCLE_ANCHOR_CANDIDATES_FALLBACK", lifecycle_manifest),
                mock.patch.object(checker, "APPROVED_PRINCIPAL_INVALIDATION_POLICY_FALLBACK", principal_manifest),
                mock.patch.object(checker, "run_json_command", side_effect=fake_run_json_command),
                mock.patch.object(
                    checker,
                    "bounded_artifact_file_scan",
                    return_value={"ready_to_build_core_evidence_pack": False, "resolved_root": str(root)},
                ),
            ):
                payload = checker.build_report(args)

        self.assertEqual(scanned_roots, [str(checker.DEFAULT_ARTIFACT_ROOT), str(root)])
        self.assertEqual(compared_with_candidate, [str(candidate_root)])
        self.assertEqual(payload["candidate_root"], str(candidate_root))
        self.assertEqual(payload["lifecycle_anchor_candidates_manifest"], str(lifecycle_manifest))
        self.assertEqual(payload["principal_invalidation_policy_manifest"], str(principal_manifest))
        self.assertEqual(
            set(payload["input_fallbacks"]["used"]),
            {
                "candidate_root",
                "lifecycle_anchor_candidates_manifest",
                "principal_invalidation_policy_manifest",
            },
        )
        self.assertEqual(payload["primary_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(payload["blockers"], ["approved_runtime_evidence_missing"])
        self.assertEqual(payload["next_step"], "produce_approved_runtime_principal_lifecycle_evidence")

    def test_explicit_artifact_root_does_not_use_workspace_fallback(self) -> None:
        ok = subprocess.CompletedProcess(["mock"], 0, "", "")
        scanned_roots: list[str] = []

        def fake_run_json_command(args: list[str], *, check: bool = False):
            command = " ".join(args)
            if "check_reflection_inventory_pack_readiness.py" in command:
                root = args[args.index("--root") + 1]
                scanned_roots.append(root)
                return ok, {
                    "ready": False,
                    "accepted_pack": None,
                    "manifests_scanned": 0,
                    "candidate_packs": [],
                    "reasons": [],
                }
            if "compare_reflection_snapshots.py" in command:
                return ok, {
                    "totals": {
                        "targets": 12,
                        "comparable": 12,
                        "blocked": 0,
                        "second_source_missing": 12,
                        "second_source_inconclusive": 0,
                        "second_source_rejected": 0,
                    },
                    "promotion_gate": {"promotion_ready": False},
                    "second_source_status": "missing_candidate_root",
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

        with tempfile.TemporaryDirectory() as temp_dir:
            explicit_root = Path(temp_dir)
            args = SimpleNamespace(
                artifact_root=explicit_root,
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

        self.assertEqual(scanned_roots, [str(explicit_root)])
        self.assertEqual(payload["artifact_root"], str(explicit_root))
        self.assertEqual(payload["effective_artifact_root"], str(explicit_root))
        self.assertFalse(payload["artifact_root_fallback"]["used"])

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
            manifest.write_text(json.dumps(lifecycle_manifest_bound_to_first_evidence()), encoding="utf-8")
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
            lifecycle_payload = lifecycle_manifest_bound_to_first_evidence()
            lifecycle_manifest.write_text(json.dumps(lifecycle_payload), encoding="utf-8")
            principal_manifest.write_text(
                json.dumps(principal_policy_bound_to_lifecycle(lifecycle_payload)),
                encoding="utf-8",
            )
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

    def test_blocks_stale_lifecycle_and_principal_policy_provenance_before_runtime_blocker(self) -> None:
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
            root = Path(tmp)
            lifecycle_manifest = root / "stale-lifecycle-candidates.json"
            principal_manifest = root / "unbound-principal-policy.json"
            stale_lifecycle = accepted_lifecycle_anchor_manifest()
            stale_lifecycle["artifact_identity"]["source_artifact_ids"] = [
                f"artifact_sha256:{'f' * 64}",
                "capture_id:stale-capture",
                "evidence_pack_id:stale-pack",
            ]
            for anchor in stale_lifecycle["candidate_anchors"]:
                if anchor.get("accepted") is True:
                    anchor["evidence"]["source_snapshot_sha256"] = "e" * 64
            lifecycle_manifest.write_text(json.dumps(stale_lifecycle), encoding="utf-8")
            principal_manifest.write_text(json.dumps(principal_policy_manifest()), encoding="utf-8")
            args = SimpleNamespace(
                artifact_root=Path("/tmp/player-identity-artifacts"),
                snapshot_root=Path("/tmp/player-identity-snapshots"),
                candidate_root=Path("/tmp/player-identity-second-source"),
                lifecycle_anchor_candidates_manifest=lifecycle_manifest,
                principal_invalidation_policy_manifest=principal_manifest,
                runtime_principal_lifecycle_evidence_manifest=None,
                approved_runtime_principal_lifecycle_evidence_manifest=None,
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
        self.assertEqual(payload["primary_blocker"], "lifecycle_anchor_first_evidence_provenance_unbound")
        self.assertIn("lifecycle_anchor_first_evidence_provenance_unbound", payload["blockers"])
        self.assertNotIn("approved_runtime_evidence_missing", payload["blockers"])
        provenance = payload["first_evidence"]["planning_provenance"]
        self.assertFalse(provenance["ready"])
        self.assertIn("lifecycle_anchor_source_artifact_identity_mismatch", provenance["blockers"])
        self.assertIn("principal_policy_lifecycle_source_binding_missing", provenance["blockers"])
        next_action = provenance["next_action"]
        self.assertTrue(next_action["active"])
        self.assertTrue(next_action["safe_offline_only"])
        self.assertEqual(
            next_action["recommended_next_step"],
            "regenerate_or_select_lifecycle_and_principal_planning_manifests_bound_to_current_first_evidence",
        )
        self.assertEqual(next_action["expected_next_blocker_after_alignment"], "approved_runtime_evidence_missing")
        self.assertIn("check_command_permission_route_gate_bound_identity_sources.py", next_action["verification_command"])
        required_artifacts = {item["artifact"]: item for item in next_action["required_artifacts"]}
        self.assertEqual(
            required_artifacts["lifecycle_anchor_candidates"]["current_path"],
            str(lifecycle_manifest),
        )
        self.assertEqual(
            required_artifacts["principal_invalidation_policy"]["current_path"],
            str(principal_manifest),
        )
        self.assertIn("do not request or run runtime/server capture", "\n".join(next_action["forbidden_shortcuts"]))

    def test_blocks_self_consistent_stale_lifecycle_source_before_runtime_blocker(self) -> None:
        first_evidence = players_identity_first_evidence_manifest()
        lifecycle = lifecycle_manifest_bound_to_first_evidence(first_evidence)
        lifecycle["artifact_identity"]["source_artifact_ids"] = [
            f"artifact_sha256:{'f' * 64}",
            "capture_id:stale-capture",
            "evidence_pack_id:stale-pack",
        ]
        principal = principal_policy_bound_to_lifecycle(lifecycle)
        lifecycle_validation = checker.lifecycle_anchor_candidates.validate_manifest_details(lifecycle)
        lifecycle_diagnosis = checker.lifecycle_anchor_candidates.build_report(
            lifecycle,
            lifecycle_validation,
            promote=False,
        )
        lifecycle_diagnosis["artifact_identity_source_artifact_ids"] = lifecycle["artifact_identity"]["source_artifact_ids"]
        principal_diagnosis = {
            "policy_consume_ready": True,
            "lifecycle_source_binding": principal["lifecycle_layout_source"]["source_binding"],
        }

        blockers = checker.planning_provenance_blockers(
            first_evidence_payload=first_evidence,
            lifecycle_candidate_diagnosis=lifecycle_diagnosis,
            principal_policy_diagnosis=principal_diagnosis,
        )

        self.assertIn("lifecycle_anchor_first_evidence_provenance_unbound", blockers)
        self.assertIn("lifecycle_anchor_source_artifact_identity_mismatch", blockers)
        self.assertNotIn("principal_policy_lifecycle_source_artifact_identity_mismatch", blockers)
        self.assertNotIn("approved_runtime_evidence_missing", blockers)

    def test_blocks_principal_lifecycle_source_binding_mismatch_before_runtime_blocker(self) -> None:
        first_evidence = players_identity_first_evidence_manifest()
        lifecycle = lifecycle_manifest_bound_to_first_evidence(first_evidence)
        principal = principal_policy_bound_to_lifecycle(lifecycle)
        principal["lifecycle_layout_source"]["source_binding"]["artifact_identity_source_artifact_ids"] = [
            f"artifact_sha256:{'e' * 64}",
            "capture_id:wrong-capture",
            "evidence_pack_id:wrong-pack",
        ]
        lifecycle_validation = checker.lifecycle_anchor_candidates.validate_manifest_details(lifecycle)
        lifecycle_diagnosis = checker.lifecycle_anchor_candidates.build_report(
            lifecycle,
            lifecycle_validation,
            promote=False,
        )
        lifecycle_diagnosis["artifact_identity_source_artifact_ids"] = lifecycle["artifact_identity"]["source_artifact_ids"]
        principal_diagnosis = {
            "policy_consume_ready": True,
            "lifecycle_source_binding": principal["lifecycle_layout_source"]["source_binding"],
        }

        blockers = checker.planning_provenance_blockers(
            first_evidence_payload=first_evidence,
            lifecycle_candidate_diagnosis=lifecycle_diagnosis,
            principal_policy_diagnosis=principal_diagnosis,
        )

        self.assertIn("lifecycle_anchor_first_evidence_provenance_unbound", blockers)
        self.assertIn("principal_policy_lifecycle_source_artifact_identity_mismatch", blockers)
        self.assertNotIn("approved_runtime_evidence_missing", blockers)

    def test_approved_runtime_evidence_routes_to_identity_public_contract_gate(self) -> None:
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
            approved_runtime_manifest = Path(tmp) / "approved-runtime-principal-lifecycle.json"
            lifecycle_payload = lifecycle_manifest_bound_to_first_evidence()
            lifecycle_manifest.write_text(json.dumps(lifecycle_payload), encoding="utf-8")
            principal_manifest.write_text(
                json.dumps(principal_policy_bound_to_lifecycle(lifecycle_payload)),
                encoding="utf-8",
            )
            approved_runtime_manifest.write_text(
                json.dumps(approved_runtime_principal_lifecycle_manifest()),
                encoding="utf-8",
            )
            args = SimpleNamespace(
                artifact_root=Path("/tmp/player-identity-artifacts"),
                snapshot_root=Path("/tmp/player-identity-snapshots"),
                candidate_root=Path("/tmp/player-identity-second-source"),
                lifecycle_anchor_candidates_manifest=lifecycle_manifest,
                principal_invalidation_policy_manifest=principal_manifest,
                runtime_principal_lifecycle_evidence_manifest=None,
                approved_runtime_principal_lifecycle_evidence_manifest=approved_runtime_manifest,
            )
            with (
                mock.patch.object(checker, "run_json_command", side_effect=fake_run_json_command),
                mock.patch.object(
                    checker,
                    "bounded_artifact_file_scan",
                    return_value={"ready_to_build_core_evidence_pack": False},
                ),
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
            ):
                payload = checker.build_report(args)

        self.assertNotIn("approved_runtime_evidence_missing", payload["blockers"])
        self.assertIn("identity_public_contract_gate_missing", payload["blockers"])
        self.assertFalse(payload["ready"])
        self.assertFalse(payload["accepted_for_internal_planning"])
        self.assertEqual(payload["next_step"], "prepare_identity_public_contract_review")
        self.assertEqual(payload["primary_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(payload["next_actionable_blocker"]["code"], "identity_public_contract_gate_missing")
        self.assertEqual(
            payload["next_actionable_blocker"]["decision_manifest"],
            "docs/player_identity_public_contract_decisions.json",
        )
        self.assertEqual(
            payload["next_actionable_blocker"]["required_public_contract_gates"],
            [
                "approved runtime evidence remains necessary but not sufficient",
                "copied opaque principal POD ABI reviewed",
                "named player identity capability reviewed",
                "owner-token registration and unregister lifecycle reviewed",
                "process-local non-persistent handle scope reviewed",
                "ABI layout tests passing",
                "installed SDK consumer tests passing",
                "public docs preserve lookup, persistence, permissions/admin, commands, mutation, return override, and cross-process non-claims",
            ],
        )
        public_contract_gap = payload["first_evidence"]["public_contract_gap_report"]
        self.assertTrue(public_contract_gap["ready"])
        self.assertFalse(public_contract_gap["runtime_evidence_missing"])
        self.assertEqual(public_contract_gap["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(public_contract_gap["next_blocker"], "identity_public_contract_gate_missing")
        self.assertIn("runtime.lifecycle_evidence", public_contract_gap["contract_review_inputs_resolved"])
        self.assertTrue(public_contract_gap["approved_runtime_evidence"]["accepted_for_contract_review"])
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])

    def test_window_request_pack_is_reported_without_clearing_runtime_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request_path = Path(tmp) / "window-request.json"
            env_path = Path(tmp) / "observer-window.env"
            start = datetime.now(timezone.utc) + timedelta(hours=1)
            end = start + timedelta(minutes=10)
            run_id = start.strftime("%Y%m%dT%H%M%SZ") + "-player-principal-lifecycle"
            request_args = SimpleNamespace(
                instance="arkserver2",
                map_name="TheIsland",
                run_id=run_id,
                obelisk_commit=current_obelisk_commit(),
                approved_window_start_utc=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                approved_window_end_utc=end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                binary_sha256=prepare_window_request.EXPECTED_BINARY_SHA256,
                server_binary_path=prepare_window_request.EXPECTED_SERVER_BINARY_PATH,
                restart_expectation="restart",
                final_posture="stable",
                user_policy="no_regular_users",
                notice_path="not_applicable",
                rollback_owner="operator",
                output_dir=Path(tmp),
                json=True,
            )
            request_payload = prepare_window_request.request_payload(request_args)
            env_lines = prepare_window_request.env_lines(request_args)
            request_path.write_text(json.dumps(request_payload), encoding="utf-8")
            env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
            (Path(tmp) / "operator-approval-request.md").write_text(
                prepare_window_request.markdown_request(request_payload, env_lines),
                encoding="utf-8",
            )

            diagnosis = checker.player_principal_lifecycle_window_request_diagnosis(request_path, env_path)

        self.assertTrue(diagnosis["ready"])
        self.assertTrue(diagnosis["request_pack_ready"])
        self.assertTrue(diagnosis["operator_request_verified"])
        self.assertFalse(diagnosis["bundle_inputs_ready"])
        self.assertFalse(diagnosis["request_pack_is_runtime_evidence"])
        self.assertTrue(diagnosis["operator_current_turn_runtime_window_approval_required"])
        self.assertFalse(diagnosis["approved_runtime_evidence_present"])
        self.assertFalse(diagnosis["runtime_evidence_ready"])
        self.assertEqual(diagnosis["remaining_blockers"], ["approved_runtime_evidence_missing"])
        self.assertEqual(diagnosis["next_blocker"], "operator_current_turn_runtime_window_approval_required")
        self.assertEqual(
            [artifact["artifact"] for artifact in diagnosis["next_required_runtime_artifacts"]],
            [
                "copied_obelisk_log",
                "checked_window_manifest_env",
                "approved_runtime_principal_lifecycle_evidence_manifest",
            ],
        )

    def test_build_report_keeps_request_pack_from_satisfying_runtime_evidence(self) -> None:
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
                        "second_source_accepted": 12,
                        "second_source_missing": 0,
                        "second_source_inconclusive": 0,
                        "second_source_rejected": 0,
                    },
                    "promotion_gate": {"promotion_ready": False},
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
            root = Path(tmp)
            lifecycle_manifest = root / "lifecycle-candidates.json"
            principal_manifest = root / "principal-policy.json"
            request_path = root / "window-request.json"
            env_path = root / "observer-window.env"
            lifecycle_payload = lifecycle_manifest_bound_to_first_evidence()
            lifecycle_manifest.write_text(json.dumps(lifecycle_payload), encoding="utf-8")
            principal_manifest.write_text(
                json.dumps(principal_policy_bound_to_lifecycle(lifecycle_payload)),
                encoding="utf-8",
            )
            start = datetime.now(timezone.utc) + timedelta(hours=1)
            end = start + timedelta(minutes=10)
            run_id = start.strftime("%Y%m%dT%H%M%SZ") + "-player-principal-lifecycle"
            request_args = SimpleNamespace(
                instance="arkserver2",
                map_name="TheIsland",
                run_id=run_id,
                obelisk_commit=current_obelisk_commit(),
                approved_window_start_utc=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                approved_window_end_utc=end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                binary_sha256=prepare_window_request.EXPECTED_BINARY_SHA256,
                server_binary_path=prepare_window_request.EXPECTED_SERVER_BINARY_PATH,
                restart_expectation="restart",
                final_posture="stable",
                user_policy="no_regular_users",
                notice_path="not_applicable",
                rollback_owner="operator",
                output_dir=root,
                json=True,
            )
            request_payload = prepare_window_request.request_payload(request_args)
            env_lines = prepare_window_request.env_lines(request_args)
            request_path.write_text(json.dumps(request_payload), encoding="utf-8")
            env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
            (root / "operator-approval-request.md").write_text(
                prepare_window_request.markdown_request(request_payload, env_lines),
                encoding="utf-8",
            )
            args = SimpleNamespace(
                artifact_root=Path("/tmp/player-identity-artifacts"),
                snapshot_root=Path("/tmp/player-identity-snapshots"),
                candidate_root=Path("/tmp/player-identity-second-source"),
                lifecycle_anchor_candidates_manifest=lifecycle_manifest,
                principal_invalidation_policy_manifest=principal_manifest,
                runtime_principal_lifecycle_evidence_manifest=None,
                approved_runtime_principal_lifecycle_evidence_manifest=None,
                player_principal_lifecycle_window_request=request_path,
                player_principal_lifecycle_window_env=env_path,
            )
            with (
                mock.patch.object(checker, "run_json_command", side_effect=fake_run_json_command),
                mock.patch.object(
                    checker,
                    "bounded_artifact_file_scan",
                    return_value={"ready_to_build_core_evidence_pack": False},
                ),
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
            ):
                payload = checker.build_report(args)

        window_request = payload["first_evidence"]["player_principal_lifecycle_window_request"]
        self.assertFalse(payload["ready"])
        self.assertFalse(payload["accepted_for_internal_planning"])
        self.assertEqual(payload["primary_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(payload["blockers"], ["approved_runtime_evidence_missing"])
        self.assertEqual(payload["next_step"], "produce_approved_runtime_principal_lifecycle_evidence")
        self.assertTrue(window_request["request_pack_ready"])
        self.assertTrue(window_request["operator_request_verified"])
        self.assertFalse(window_request["bundle_inputs_ready"])
        self.assertFalse(window_request["request_pack_is_runtime_evidence"])
        self.assertTrue(window_request["operator_current_turn_runtime_window_approval_required"])
        self.assertFalse(window_request["approved_runtime_evidence_present"])
        self.assertFalse(window_request["runtime_evidence_ready"])
        self.assertFalse(window_request["promotion_ready"])
        self.assertFalse(window_request["public_sdk_ready"])
        self.assertFalse(window_request["runtime_ready"])
        self.assertEqual(window_request["remaining_blockers"], ["approved_runtime_evidence_missing"])
        self.assertEqual(window_request["next_blocker"], "operator_current_turn_runtime_window_approval_required")

    def test_window_request_pack_diagnosis_preserves_env_parse_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request_path = Path(tmp) / "window-request.json"
            env_path = Path(tmp) / "observer-window.env"
            start = datetime.now(timezone.utc) + timedelta(hours=1)
            end = start + timedelta(minutes=10)
            run_id = start.strftime("%Y%m%dT%H%M%SZ") + "-player-principal-lifecycle"
            request_args = SimpleNamespace(
                instance="arkserver2",
                map_name="TheIsland",
                run_id=run_id,
                obelisk_commit=current_obelisk_commit(),
                approved_window_start_utc=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                approved_window_end_utc=end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                binary_sha256=prepare_window_request.EXPECTED_BINARY_SHA256,
                server_binary_path=prepare_window_request.EXPECTED_SERVER_BINARY_PATH,
                restart_expectation="restart",
                final_posture="stable",
                user_policy="no_regular_users",
                notice_path="not_applicable",
                rollback_owner="operator",
                output_dir=Path(tmp),
                json=True,
            )
            request_path.write_text(
                json.dumps(prepare_window_request.request_payload(request_args)),
                encoding="utf-8",
            )
            env_path.write_text(
                "\n".join(prepare_window_request.env_lines(request_args)) + "\nnot-a-key-value-line\n",
                encoding="utf-8",
            )

            diagnosis = checker.player_principal_lifecycle_window_request_diagnosis(request_path, env_path)

        self.assertFalse(diagnosis["ready"])
        self.assertFalse(diagnosis["request_pack_ready"])
        self.assertIn("env_line_not_key_value", diagnosis["blockers"])

    def test_window_request_pack_diagnosis_rejects_env_from_other_request_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request_dir = root / "request"
            other_dir = root / "other-request"
            request_dir.mkdir()
            other_dir.mkdir()
            request_path = request_dir / "window-request.json"
            env_path = other_dir / "observer-window.env"
            start = datetime.now(timezone.utc) + timedelta(hours=1)
            end = start + timedelta(minutes=10)
            run_id = start.strftime("%Y%m%dT%H%M%SZ") + "-player-principal-lifecycle"
            request_args = SimpleNamespace(
                instance="arkserver2",
                map_name="TheIsland",
                run_id=run_id,
                obelisk_commit=current_obelisk_commit(),
                approved_window_start_utc=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                approved_window_end_utc=end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                binary_sha256=prepare_window_request.EXPECTED_BINARY_SHA256,
                server_binary_path=prepare_window_request.EXPECTED_SERVER_BINARY_PATH,
                restart_expectation="restart",
                final_posture="stable",
                user_policy="no_regular_users",
                notice_path="not_applicable",
                rollback_owner="operator",
                output_dir=request_dir,
                json=True,
            )
            request_payload = prepare_window_request.request_payload(request_args)
            env_lines = prepare_window_request.env_lines(request_args)
            request_path.write_text(json.dumps(request_payload), encoding="utf-8")
            env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
            (request_dir / "operator-approval-request.md").write_text(
                prepare_window_request.markdown_request(request_payload, env_lines),
                encoding="utf-8",
            )

            diagnosis = checker.player_principal_lifecycle_window_request_diagnosis(request_path, env_path)

        self.assertFalse(diagnosis["ready"])
        self.assertFalse(diagnosis["request_pack_ready"])
        self.assertIn("env_file_not_sibling_of_request_json", diagnosis["blockers"])
        self.assertFalse(diagnosis["operator_current_turn_runtime_window_approval_required"])
        self.assertEqual(diagnosis["remaining_blockers"], ["approved_runtime_evidence_missing"])

    def test_window_request_pack_diagnosis_requires_operator_request_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request_path = Path(tmp) / "window-request.json"
            env_path = Path(tmp) / "observer-window.env"
            start = datetime.now(timezone.utc) + timedelta(hours=1)
            end = start + timedelta(minutes=10)
            run_id = start.strftime("%Y%m%dT%H%M%SZ") + "-player-principal-lifecycle"
            request_args = SimpleNamespace(
                instance="arkserver2",
                map_name="TheIsland",
                run_id=run_id,
                obelisk_commit=current_obelisk_commit(),
                approved_window_start_utc=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                approved_window_end_utc=end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                binary_sha256=prepare_window_request.EXPECTED_BINARY_SHA256,
                server_binary_path=prepare_window_request.EXPECTED_SERVER_BINARY_PATH,
                restart_expectation="restart",
                final_posture="stable",
                user_policy="no_regular_users",
                notice_path="not_applicable",
                rollback_owner="operator",
                output_dir=Path(tmp),
                json=True,
            )
            request_path.write_text(
                json.dumps(prepare_window_request.request_payload(request_args)),
                encoding="utf-8",
            )
            env_path.write_text(
                "\n".join(prepare_window_request.env_lines(request_args)) + "\n",
                encoding="utf-8",
            )

            diagnosis = checker.player_principal_lifecycle_window_request_diagnosis(request_path, env_path)

        self.assertFalse(diagnosis["ready"])
        self.assertFalse(diagnosis["request_pack_ready"])
        self.assertFalse(diagnosis["operator_request_verified"])
        self.assertIn("operator_request_unreadable", diagnosis["blockers"])

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

    def test_next_actionable_blocker_fallback_uses_current_public_contract_blocker_name(self) -> None:
        blocker = checker.next_actionable_blocker(
            inventory_ready=True,
            inventory_payload_ready=True,
            inventory_chain={"ready": True, "blockers": [], "accepted_manifest": {}},
            downstream_blockers=[],
            offline_inputs={"status": "ready", "shooter_game_server_candidates": []},
            raw_binary_pattern=Path("/tmp/artifacts/raw/ShooterGameServer"),
            raw_core_pattern=Path("/tmp/artifacts/raw/core"),
            core_manifest_pattern=Path("/tmp/artifacts/core-evidence-pack/manifest.json"),
            reflection_inventory_pattern=Path("/tmp/artifacts/reflection-inventory-pack/manifest.json"),
            next_operator_recipe={},
        )

        self.assertEqual(blocker["code"], "identity_public_contract_gate_missing")
        self.assertEqual(blocker["blocked_until"], "reviewed_identity_public_contract")
        self.assertFalse(blocker["promotion_ready"])
        self.assertFalse(blocker["public_sdk_ready"])
        self.assertFalse(blocker["runtime_ready"])

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

    def test_detect_obelisk_commit_uses_env_then_unknown_without_git(self) -> None:
        with (
            mock.patch.dict(os.environ, {"OBELISK_COMMIT": "envcommit123"}, clear=False),
            mock.patch.object(checker.subprocess, "run") as run,
        ):
            self.assertEqual(checker.detect_obelisk_commit(), "envcommit123")
            run.assert_not_called()

        with (
            mock.patch.dict(os.environ, {"OBELISK_COMMIT": ""}, clear=False),
            mock.patch.object(checker.subprocess, "run") as run,
        ):
            self.assertEqual(checker.detect_obelisk_commit(), "unknown")
            run.assert_not_called()

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

            with mock.patch.dict(os.environ, approved_runtime_safe_test_env()):
                diagnosis = checker.approved_runtime_principal_lifecycle_evidence_manifest_diagnosis(
                    approved_manifest
                )

        self.assertTrue(diagnosis["ready"])
        self.assertEqual(
            diagnosis["report_schema"],
            "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
        )
        self.assertEqual(diagnosis["mode"], "consume")
        self.assertEqual(diagnosis["ready_scope"], "runtime_evidence_only")
        self.assertEqual(diagnosis["next_blocker"], "identity_public_contract_gate_missing")
        self.assertTrue(diagnosis["approved_runtime_evidence_present"])
        self.assertTrue(diagnosis["runtime_evidence_ready"])
        self.assertFalse(diagnosis["promotion_ready"])
        self.assertFalse(diagnosis["public_sdk_ready"])
        self.assertFalse(diagnosis["runtime_ready"])
        self.assertEqual(diagnosis["remaining_blockers"], [])
        self.assertEqual(
            diagnosis["observed_runtime_cases"],
            ["observer_enable", "session_start_anchor", "session_start_rejected_anchor", "session_end_anchor"],
        )
        self.assertEqual(
            diagnosis["consumer_cases"],
            ["malformed_or_unsupported_evidence", "stale_after_logout"],
        )

    def test_approved_runtime_manifest_diagnosis_rejects_checker_report_overclaim(self) -> None:
        original_build_report = checker.approved_runtime_principal_lifecycle_evidence.build_report

        def overclaiming_report(payload, validation, *, check_mode: str):
            report = original_build_report(payload, validation, check_mode=check_mode)
            report["public_header_allowed"] = True
            report["public_sdk_ready"] = True
            report["public_abi_ready"] = True
            report["v1_completion_ready"] = True
            report["public_capability_bits_now"] = ["OBELISK_PUBLIC_IDENTITY"]
            report["public_callback_abi_now"] = ["ObeliskRegisterPlayerIdentityCallback"]
            return report

        with tempfile.TemporaryDirectory() as tmp:
            approved_manifest = Path(tmp) / "approved-runtime-principal-lifecycle.json"
            approved_manifest.write_text(
                json.dumps(approved_runtime_principal_lifecycle_manifest()),
                encoding="utf-8",
            )
            with mock.patch.object(
                checker.approved_runtime_principal_lifecycle_evidence,
                "build_report",
                side_effect=overclaiming_report,
            ), mock.patch.dict(os.environ, approved_runtime_safe_test_env()):
                diagnosis = checker.approved_runtime_principal_lifecycle_evidence_manifest_diagnosis(
                    approved_manifest
                )

        self.assertFalse(diagnosis["ready"])
        self.assertFalse(diagnosis["approved_runtime_evidence_present"])
        self.assertFalse(diagnosis["runtime_evidence_ready"])
        self.assertFalse(diagnosis["promotion_ready"])
        self.assertFalse(diagnosis["public_header_allowed"])
        self.assertFalse(diagnosis["public_sdk_ready"])
        self.assertFalse(diagnosis["public_abi_ready"])
        self.assertFalse(diagnosis["v1_completion_ready"])
        self.assertFalse(diagnosis["runtime_ready"])
        self.assertEqual(diagnosis["public_capability_bits_now"], [])
        self.assertEqual(diagnosis["public_callback_abi_now"], [])
        self.assertEqual(diagnosis["remaining_blockers"], ["approved_runtime_evidence_missing"])
        self.assertIn("approved_runtime_report_public_header_allowed_not_false", diagnosis["blockers"])
        self.assertIn("approved_runtime_report_public_sdk_ready_not_false", diagnosis["blockers"])
        self.assertIn("approved_runtime_report_public_abi_ready_not_false", diagnosis["blockers"])
        self.assertIn("approved_runtime_report_v1_completion_ready_not_false", diagnosis["blockers"])
        self.assertIn("approved_runtime_report_public_capability_bits_now_not_empty", diagnosis["blockers"])
        self.assertIn("approved_runtime_report_public_callback_abi_now_not_empty", diagnosis["blockers"])

    def test_approved_runtime_manifest_diagnosis_rejects_accounting_alias_overclaim(self) -> None:
        original_build_report = checker.approved_runtime_principal_lifecycle_evidence.build_report

        def accounting_overclaim_report(payload, validation, *, check_mode: str):
            report = original_build_report(payload, validation, check_mode=check_mode)
            report["counts_toward_public_sdk"] = True
            report["counts_toward_runtime"] = True
            report["counts_toward_v1_completion"] = True
            report["counts_toward_complete_sdk_claim"] = True
            report["public_or_runtime_accounting_allowed"] = True
            return report

        with tempfile.TemporaryDirectory() as tmp:
            approved_manifest = Path(tmp) / "approved-runtime-principal-lifecycle.json"
            approved_manifest.write_text(
                json.dumps(approved_runtime_principal_lifecycle_manifest()),
                encoding="utf-8",
            )
            with mock.patch.object(
                checker.approved_runtime_principal_lifecycle_evidence,
                "build_report",
                side_effect=accounting_overclaim_report,
            ), mock.patch.dict(os.environ, approved_runtime_safe_test_env()):
                diagnosis = checker.approved_runtime_principal_lifecycle_evidence_manifest_diagnosis(
                    approved_manifest
                )

        self.assertFalse(diagnosis["ready"])
        self.assertFalse(diagnosis["approved_runtime_evidence_present"])
        self.assertEqual(diagnosis["remaining_blockers"], ["approved_runtime_evidence_missing"])
        self.assertIn("approved_runtime_report_counts_toward_public_sdk_not_false", diagnosis["blockers"])
        self.assertIn("approved_runtime_report_counts_toward_runtime_not_false", diagnosis["blockers"])
        self.assertIn("approved_runtime_report_counts_toward_v1_completion_not_false", diagnosis["blockers"])
        self.assertIn("approved_runtime_report_counts_toward_complete_sdk_claim_not_false", diagnosis["blockers"])
        self.assertIn("approved_runtime_report_public_or_runtime_accounting_allowed_not_false", diagnosis["blockers"])

    def test_approved_runtime_manifest_diagnosis_rejects_report_not_ready(self) -> None:
        original_build_report = checker.approved_runtime_principal_lifecycle_evidence.build_report

        def not_ready_report(payload, validation, *, check_mode: str):
            report = original_build_report(payload, validation, check_mode=check_mode)
            report["ready"] = False
            return report

        with tempfile.TemporaryDirectory() as tmp:
            approved_manifest = Path(tmp) / "approved-runtime-principal-lifecycle.json"
            approved_manifest.write_text(
                json.dumps(approved_runtime_principal_lifecycle_manifest()),
                encoding="utf-8",
            )
            with mock.patch.object(
                checker.approved_runtime_principal_lifecycle_evidence,
                "build_report",
                side_effect=not_ready_report,
            ), mock.patch.dict(os.environ, approved_runtime_safe_test_env()):
                diagnosis = checker.approved_runtime_principal_lifecycle_evidence_manifest_diagnosis(
                    approved_manifest
                )

        self.assertFalse(diagnosis["ready"])
        self.assertFalse(diagnosis["approved_runtime_evidence_present"])
        self.assertFalse(diagnosis["runtime_evidence_ready"])
        self.assertEqual(diagnosis["remaining_blockers"], ["approved_runtime_evidence_missing"])
        self.assertIn("approved_runtime_report_ready_not_true", diagnosis["blockers"])

    def test_approved_runtime_manifest_diagnosis_rejects_legacy_public_contract_gate_alias(self) -> None:
        original_build_report = checker.approved_runtime_principal_lifecycle_evidence.build_report

        def stale_alias_report(payload, validation, *, check_mode: str):
            report = original_build_report(payload, validation, check_mode=check_mode)
            report["next_blocker"] = "identity_public_contract_gate"
            return report

        with tempfile.TemporaryDirectory() as tmp:
            approved_manifest = Path(tmp) / "approved-runtime-principal-lifecycle.json"
            approved_manifest.write_text(
                json.dumps(approved_runtime_principal_lifecycle_manifest()),
                encoding="utf-8",
            )
            with mock.patch.object(
                checker.approved_runtime_principal_lifecycle_evidence,
                "build_report",
                side_effect=stale_alias_report,
            ), mock.patch.dict(os.environ, approved_runtime_safe_test_env()):
                diagnosis = checker.approved_runtime_principal_lifecycle_evidence_manifest_diagnosis(
                    approved_manifest
                )

        self.assertFalse(diagnosis["ready"])
        self.assertIn(
            "approved_runtime_report_next_blocker_not_identity_public_contract_gate_missing",
            diagnosis["blockers"],
        )

    def test_unaccepted_approved_runtime_manifest_keeps_runtime_evidence_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            approved_manifest = Path(tmp) / "approved-runtime-principal-lifecycle.json"
            approved_manifest.write_text(json.dumps({"not": "approved-runtime-evidence"}), encoding="utf-8")

            result = self.run_checker(
                [
                    "--approved-runtime-principal-lifecycle-evidence-manifest",
                    str(approved_manifest),
                    "--json",
                ],
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["primary_blocker"], "approved_runtime_evidence_missing")
        self.assertIn("approved_runtime_evidence_missing", payload["blockers"])
        self.assertNotIn("identity_public_contract_gap_report_invalid", payload["blockers"])
        self.assertEqual(
            payload["first_evidence"]["approved_runtime_principal_lifecycle_evidence_manifest"]["remaining_blockers"],
            ["approved_runtime_evidence_missing"],
        )


if __name__ == "__main__":
    unittest.main()
