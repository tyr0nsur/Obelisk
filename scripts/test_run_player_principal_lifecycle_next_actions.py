#!/usr/bin/env python3
"""Tests for run_player_principal_lifecycle_next_actions.py."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "run_player_principal_lifecycle_next_actions.py"
PLAN_SCHEMA = "obelisk.player-principal-lifecycle-next-action-plan.v1"
RUNNER_SCHEMA = "obelisk.player-principal-lifecycle-next-action-runner.v1"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bound_artifact(
    path: Path,
    *,
    role: str,
    relative_path: str,
    argv_flags: list[str] | None = None,
    argv_position: int | None = None,
    must_exist: bool | None = None,
) -> dict:
    artifact = {
        "role": role,
        "path": str(path),
        "relative_path": relative_path,
        "required": True,
        "must_exist": role == "input" if must_exist is None else must_exist,
    }
    if argv_flags is not None:
        artifact["argv_flags"] = argv_flags
    if argv_position is not None:
        artifact["argv_position"] = argv_position
    if path.is_file():
        artifact["sha256"] = sha256(path)
        artifact["size_bytes"] = path.stat().st_size
    return artifact


def command_path_binding(
    evidence_dir: Path,
    *,
    inputs: list[dict] | None = None,
    outputs: list[dict] | None = None,
) -> dict:
    return {
        "schema": "obelisk.player-principal-lifecycle-command-path-binding.v1",
        "evidence_dir": str(evidence_dir),
        "inputs": inputs or [],
        "outputs": outputs or [],
        "path_hash_bound": True,
        "counts_as_approved_runtime_evidence": False,
    }


def operator_context() -> dict:
    return {
        "post_reboot_monitor_context_present": True,
        "post_reboot_monitor_path": "/tmp/obelisk-test-passive-monitor-post-reboot.log",
        "confirmed_beta_notice_context_present": True,
        "confirmed_beta_notice_path": "/tmp/obelisk-test-beta-notice.confirmed.json",
        "confirmed_beta_notice_completed": True,
        "context_inputs_are_non_evidence": True,
        "context_inputs_authorize_runner": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
    }


def plan_payload(*, command: str | None = None, extra_action: dict | None = None) -> dict:
    action = {
        "order": 1,
        "id": "closure_missing_window_manifest_env",
        "action": "provide_completed_window_manifest_env_sibling",
        "artifact": "window-manifest.env",
        "items": ["window-manifest.env"],
        "authorized_by_this_report": False,
        "counts_as_approved_runtime_evidence": False,
        "writes_under_evidence_dir": True,
    }
    if command is not None:
        action["command_text_not_executed"] = command
    if extra_action:
        action.update(extra_action)
    return {
        "schema": PLAN_SCHEMA,
        "status": "next_actions_planned",
        "ready": False,
        "approved_runtime_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "next_action_sequence": [action],
    }


def evidence_split_context(*, include_overclaim_alias: bool = False) -> dict:
    payload = {
        "schema": "obelisk.player-principal-lifecycle-evidence-split-status.v1",
        "present": True,
        "classification": "start_end_contract_input_present_rejected_start_missing_non_evidence",
        "source_schema": "obelisk.players-identity-runtime-principal-start-end-evidence-check.v1",
        "source_status": "accepted_for_contract_review",
        "start_end_contract_input_present": True,
        "start_end_contract_input_accepted": True,
        "session_start_rejected_required": True,
        "session_start_rejected_missing": True,
        "strict_approved_runtime_evidence_bundle_required": True,
        "strict_approved_runtime_evidence_bundle_missing": True,
        "blockers": [
            "runtime.lifecycle_rejected_start_evidence_missing",
            "approved_runtime_principal_lifecycle_evidence_bundle_missing_or_unaccepted",
        ],
        "next_actions": [
            {
                "action": "supply_exact_checkjoininprogress_session_start_rejected_for_strict_triplet",
                "action_kind": "player_principal_evidence_split_missing_rejected_start",
                "artifact": "lifecycle-role/session_start_rejected",
                "role": "session_start_rejected",
                "items": ["lifecycle-role/session_start_rejected"],
            }
        ],
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
    }
    if include_overclaim_alias:
        payload["audit_alias"] = {"claim": "public_sdk_ready", "status": "ready"}
    return payload


def exact_triplet_bundle_route_payload() -> dict:
    return {
        "schema": "obelisk.player-principal-lifecycle-exact-triplet-bundle-route.v1",
        "status": "blocked_approved_runtime_evidence_missing",
        "route_name": "same_run_exact_copied_lifecycle_triplet_bundle",
        "current_route_blocker": "approved_runtime_evidence_missing",
        "next_action_target": "exact_copied_lifecycle_triplet_bundle",
        "first_missing_kind": "copied_lifecycle_triplet_role",
        "first_missing_role": "session_start",
        "first_missing_copied_lifecycle_event_label": "HandleNewPlayer(1,1)",
        "first_missing_runtime_evidence_path": "copied-lifecycle-triplet/HandleNewPlayer(1,1)",
        "accepted_lifecycle_event_roles": ["session_start_rejected"],
        "missing_lifecycle_event_roles": ["session_start", "session_end"],
        "missing_copied_lifecycle_event_triplet_labels": [
            "HandleNewPlayer(1,1)",
            "OnLogout matched",
        ],
        "missing_required_artifacts": [
            "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
        ],
        "fastest_missing_role_artifact_path": [
            {
                "stage": "copied_lifecycle_triplet_role",
                "role": "session_start",
                "label": "HandleNewPlayer(1,1)",
                "status": "missing",
                "counts_as_approved_runtime_evidence": False,
            },
            {
                "stage": "copied_lifecycle_triplet_role",
                "role": "session_start_rejected",
                "label": "CheckJoinInProgress(1,0)",
                "status": "accepted",
                "counts_as_approved_runtime_evidence": False,
            },
            {
                "stage": "copied_lifecycle_triplet_role",
                "role": "session_end",
                "label": "OnLogout matched",
                "status": "missing",
                "counts_as_approved_runtime_evidence": False,
            },
        ],
        "partial_lifecycle_material_counts_as_approved_runtime_evidence": False,
        "copied_log_presence_counts_as_approved_runtime_evidence": False,
        "stale_passive_tail_counts_as_approved_runtime_evidence": False,
        "direct_discord_send_counts_as_approved_runtime_evidence": False,
        "active_notice_state_counts_as_approved_runtime_evidence": False,
        "diagnostic_samples_count_as_approved_runtime_evidence": False,
        "helper_command_authorized_by_route": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "sdk_progress": 0,
        "p0_progress": 0,
    }


def runtime_window_lifecycle_action(*, expired: bool) -> dict:
    return {
        "id": (
            "close_expired_player_principal_lifecycle_window_as_non_evidence"
            if expired
            else "wait_for_active_player_principal_lifecycle_window_exact_triplet_or_end"
        ),
        "action": (
            "close_expired_player_principal_lifecycle_window_as_non_evidence"
            if expired
            else "wait_for_active_player_principal_lifecycle_window_exact_triplet_or_end"
        ),
        "action_kind": (
            "expired_runtime_window_non_evidence_closure"
            if expired
            else "active_runtime_window_waiting_for_exact_triplet"
        ),
        "runtime_window_lifecycle": {
            "schema": "obelisk.player-principal-lifecycle-runtime-window-lifecycle.v1",
            "classification": (
                "expired_runtime_window_non_evidence_prepare_fresh_player_backed_window"
                if expired
                else "active_runtime_window_waiting_for_exact_copied_triplet_or_window_end"
            ),
            "window_state": "post_window" if expired else "in_progress",
            "close_or_classify_as_non_evidence": expired,
            "active_waiting_not_closure_ready": not expired,
            "fresh_player_backed_window_required": expired,
            "copy_bundle_commands_suppressed_until_exact_triplet": True,
            "approved_runtime_evidence": False,
            "counts_as_approved_runtime_evidence": False,
        },
        "fresh_player_backed_window": {
            "schema": "obelisk.player-principal-lifecycle-fresh-player-backed-window-prep.v1",
            "diagnostic_candidates": "disabled",
            "runner_command_available": False,
            "approved_runtime_evidence": False,
            "counts_as_approved_runtime_evidence": False,
        },
        "offline_parallel_evidence_lanes": {
            "schema": "obelisk.player-principal-lifecycle-offline-parallel-evidence-lanes.v1",
            "present": True,
            "classification": (
                "post_window_non_evidence_fanout_prepare_fresh_player_backed_window"
                if expired
                else "active_window_parallel_offline_preparation_waiting_for_exact_triplet"
            ),
            "runtime_window_state": "expired_non_evidence" if expired else "active_waiting",
            "primary_route_blocker": "approved_runtime_evidence_missing",
            "required_primary_artifact": "approved_runtime_principal_lifecycle_evidence_bundle",
            "parallel_lane_count": 4,
            "lanes": [
                {
                    "id": "runtime_evidence_closure_status",
                    "status": "prepared_offline_after_copied_log_only",
                    "counts_as_approved_runtime_evidence": False,
                    "counts_as_runtime_evidence": False,
                    "counts_as_sdk_evidence": False,
                    "counts_toward_sdk": False,
                    "counts_toward_p0_dependency_chain": False,
                    "runtime_ready": False,
                    "public_sdk_ready": False,
                    "stable_claim_allowed": False,
                    "runner_command_available": False,
                    "runner_must_not_execute_lane": True,
                },
                {
                    "id": "single_player_multi_surface_candidate_pack",
                    "status": "prepared_candidate_only_same_window",
                    "counts_as_approved_runtime_evidence": False,
                    "counts_as_runtime_evidence": False,
                    "counts_as_sdk_evidence": False,
                    "counts_toward_sdk": False,
                    "counts_toward_p0_dependency_chain": False,
                    "runtime_ready": False,
                    "public_sdk_ready": False,
                    "stable_claim_allowed": False,
                    "runner_command_available": False,
                    "runner_must_not_execute_lane": True,
                },
                {
                    "id": "post_runtime_identity_public_contract_gate",
                    "status": "pre_hardened_waiting_for_approved_runtime_evidence",
                    "counts_as_approved_runtime_evidence": False,
                    "counts_as_runtime_evidence": False,
                    "counts_as_sdk_evidence": False,
                    "counts_toward_sdk": False,
                    "counts_toward_p0_dependency_chain": False,
                    "runtime_ready": False,
                    "public_sdk_ready": False,
                    "stable_claim_allowed": False,
                    "runner_command_available": False,
                    "runner_must_not_execute_lane": True,
                },
                {
                    "id": "post_identity_p0_chain_certificates",
                    "status": "pre_hardened_waiting_for_identity_public_contract",
                    "counts_as_approved_runtime_evidence": False,
                    "counts_as_runtime_evidence": False,
                    "counts_as_sdk_evidence": False,
                    "counts_toward_sdk": False,
                    "counts_toward_p0_dependency_chain": False,
                    "runtime_ready": False,
                    "public_sdk_ready": False,
                    "stable_claim_allowed": False,
                    "runner_command_available": False,
                    "runner_must_not_execute_lane": True,
                },
            ],
            "runner_command_available": False,
            "runner_must_not_execute_lanes": True,
            "approved_runtime_evidence": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_evidence": False,
            "counts_toward_sdk": False,
            "counts_toward_p0_dependency_chain": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "stable_claim_allowed": False,
            "sdk_progress": 0,
            "p0_progress": 0,
        },
        "expired_runtime_window_non_evidence": expired,
        "active_runtime_window_waiting_for_exact_triplet": not expired,
        "active_window_not_closure_ready": not expired,
        "prepare_fresh_player_backed_window_required": expired,
        "copy_bundle_commands_suppressed_until_exact_triplet": True,
        "copy_bundle_commands_allowed_before_exact_triplet": False,
        "runner_command_available": False,
        "writes_under_evidence_dir": False,
        "authorized_by_this_report": False,
        "counts_as_approved_runtime_evidence": False,
    }


def run_script(*args: str, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class RunPlayerPrincipalLifecycleNextActionsTests(unittest.TestCase):
    def test_dry_run_blocks_missing_copied_log_without_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            command = (
                "scripts/check_player_identity_runtime_principal_lifecycle_window_manifest.py "
                f"--emit-template {root / 'window-manifest.env'} "
                f"--copied-log {root / 'Obelisk.log'}"
            )
            write_json(plan, plan_payload(command=command))

            result = run_script("--plan-json", str(plan), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["schema"], RUNNER_SCHEMA)
        self.assertEqual(report["status"], "dry_run")
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["executed_count"], 0)
        self.assertEqual(report["blocked_count"], 1)
        self.assertTrue(
            any(blocker.startswith("--copied-log") for blocker in report["results"][0]["blockers"])
        )
        self.assertFalse(report["results"][0]["executed"])
        self.assertFalse(report["results"][0]["counts_as_approved_runtime_evidence"])
        choreography = report["results"][0]["beta_runtime_choreography"]
        self.assertTrue(choreography["single_tester_only"])
        self.assertTrue(choreography["direct_target_join_required"])
        self.assertTrue(
            choreography["observer_gate"]["wait_until_observer_sees_exact_checkjoin_or_window_closes"]
        )
        self.assertFalse(choreography["logout_before_exact_checkjoin_allowed"])
        self.assertFalse(choreography["mixed_transfer_reconnect_same_approved_window_allowed"])
        self.assertFalse(choreography["choreography_authorizes_runner"])
        self.assertTrue(choreography["source_bound_blockers_must_be_clear_before_choreography"])
        self.assertFalse(choreography["blind_wait_instruction"])
        self.assertFalse(choreography["logout_instruction_allowed_now"])
        self.assertFalse(choreography["counts_as_approved_runtime_evidence"])
        self.assertFalse(
            report["runtime_choreography_boundary"][
                "wait_for_exact_checkjoin_before_logout_required"
            ]
        )
        self.assertTrue(
            report["runtime_choreography_boundary"][
                "wait_for_exact_checkjoin_before_logout_candidate_only_after_blocker_clear"
            ]
        )
        self.assertTrue(
            report["runtime_choreography_boundary"][
                "source_bound_blockers_must_be_clear_before_choreography"
            ]
        )
        self.assertFalse(report["runtime_choreography_boundary"]["blind_wait_instruction"])
        self.assertFalse(report["runtime_choreography_boundary"]["logout_instruction_allowed_now"])
        self.assertTrue(
            report["runtime_choreography_boundary"][
                "stale_or_diagnostic_exact_checkjoin_lines_are_stimulus_clues_only"
            ]
        )
        self.assertFalse(report["runtime_choreography_boundary"]["choreography_authorizes_runner"])
        current_boundary = report["current_live_diagnostic_blocker_boundaries"]
        self.assertEqual(
            current_boundary["classification"],
            "current_live_source_bound_drift_context_not_runner_authority",
        )
        self.assertEqual(current_boundary["source_freshness"], "stale_operator_supplied")
        self.assertTrue(current_boundary["stale_operator_supplied_context"])
        self.assertTrue(current_boundary["stale_operator_supplied_blockers_suppressed"])
        self.assertEqual(
            current_boundary["stale_operator_supplied_next_blocker_ids"],
            current_boundary["next_blocker_ids"],
        )
        self.assertTrue(current_boundary["source_bound_blocker"])
        self.assertFalse(current_boundary["runner_starts_blind_wait"])
        self.assertFalse(current_boundary["runner_starts_restart"])
        self.assertFalse(current_boundary["runner_issues_logout_instruction"])
        self.assertFalse(current_boundary["counts_as_approved_runtime_evidence"])

    def test_player_principal_evidence_split_context_is_preserved_but_not_executable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            split = evidence_split_context()
            payload = plan_payload(
                extra_action={
                    "id": "status_split_missing_rejected_start",
                    "action": "supply_exact_checkjoininprogress_session_start_rejected_for_strict_triplet",
                    "action_kind": "player_principal_evidence_split_missing_rejected_start",
                    "artifact": "lifecycle-role/session_start_rejected",
                    "role": "session_start_rejected",
                    "items": ["lifecycle-role/session_start_rejected"],
                    "player_principal_evidence_split": split,
                    "runner_command_available": False,
                    "authorized_by_this_report": False,
                    "counts_as_approved_runtime_evidence": False,
                    "writes_under_evidence_dir": False,
                },
            )
            payload["player_principal_evidence_split"] = split
            write_json(plan, payload)

            result = run_script("--plan-json", str(plan), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["eligible_count"], 0)
        action = report["results"][0]
        self.assertTrue(action["player_principal_evidence_split_present"])
        self.assertEqual(
            action["player_principal_evidence_split"]["classification"],
            "start_end_contract_input_present_rejected_start_missing_non_evidence",
        )
        self.assertIn(
            "player_principal_evidence_split_requires_manual_offline_resolution",
            action["blockers"],
        )
        self.assertFalse(action["player_principal_evidence_split_authorizes_runner"])
        self.assertFalse(action["player_principal_evidence_split_counts_as_approved_runtime_evidence"])
        self.assertFalse(action["counts_as_approved_runtime_evidence"])
        split_summary = report["player_principal_evidence_split_runner_summary"]
        self.assertTrue(split_summary["present"])
        self.assertIn("status_split_missing_rejected_start", split_summary["action_ids"])
        self.assertFalse(split_summary["split_authorizes_runner"])
        self.assertFalse(split_summary["split_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["approved_runtime_evidence"])

    def test_player_principal_evidence_split_positive_alias_blocks_runner_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            split = evidence_split_context(include_overclaim_alias=True)
            payload = plan_payload(
                command="scripts/report_obelisk_sdk_status.py --compact",
                extra_action={
                    "id": "offline_status_with_split_context",
                    "action": "run_offline_status_summary",
                    "player_principal_evidence_split": split,
                    "writes_under_evidence_dir": False,
                    "authorized_by_this_report": False,
                    "counts_as_approved_runtime_evidence": False,
                },
            )
            payload["player_principal_evidence_split"] = split
            write_json(plan, payload)

            result = run_script("--plan-json", str(plan), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        action = report["results"][0]
        self.assertIn(
            "player_principal_evidence_split_positive_alias_claim_not_runner_authority",
            action["blockers"],
        )
        self.assertEqual(
            action["player_principal_evidence_split"]["positive_alias_claim_paths"],
            ["$.audit_alias"],
        )
        self.assertEqual(report["eligible_count"], 0)
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["public_sdk_ready"])

    def test_preserves_runtime_artifact_blocker_and_explains_missing_copied_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            command = (
                "scripts/check_player_identity_runtime_principal_lifecycle_window_manifest.py "
                f"--emit-template {root / 'window-manifest.env'} "
                f"--copied-log {root / 'Obelisk.log'}"
            )
            write_json(
                plan,
                plan_payload(
                    command=command,
                    extra_action={
                        "missing_artifact_blocker": {
                            "artifact": "window-manifest.env",
                            "reason": "window_manifest_env_missing",
                            "required_script": "scripts/check_player_identity_runtime_principal_lifecycle_window_manifest.py",
                            "counts_as_approved_runtime_evidence": False,
                        },
                        "missing_artifact_blocker_reason": "window_manifest_env_missing",
                        "missing_artifact_reasons": ["window_manifest_env_missing"],
                        "required_script": "scripts/check_player_identity_runtime_principal_lifecycle_window_manifest.py",
                    },
                ),
            )

            result = run_script("--plan-json", str(plan), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        action = report["results"][0]
        self.assertEqual(action["missing_artifact_blocker_reason"], "window_manifest_env_missing")
        self.assertEqual(action["missing_artifact_blocker"]["artifact"], "window-manifest.env")
        self.assertTrue(
            any(
                "copied Obelisk.log is missing" in explanation
                for explanation in action["blocker_explanations"]
            )
        )
        summary = report["runtime_evidence_artifact_runner_summary"]
        self.assertEqual(summary["first_missing_artifact"], "window-manifest.env")
        self.assertEqual(summary["first_blocker_reason"], "window_manifest_env_missing")
        self.assertFalse(summary["runner_accepts_approved_bundle_as_evidence"])
        self.assertFalse(action["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["approved_runtime_evidence"])

    def test_execute_returns_nonzero_when_only_action_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            write_json(
                plan,
                plan_payload(
                    command=(
                        "scripts/check_player_identity_runtime_principal_lifecycle_window_manifest.py "
                        f"--emit-template {root / 'window-manifest.env'} "
                        f"--copied-log {root / 'missing.log'}"
                    )
                ),
            )

            result = run_script("--plan-json", str(plan), "--execute", "--json")
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "execute_blocked")
        self.assertEqual(report["executed_count"], 0)

    def test_stale_active_window_action_is_blocked_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            write_json(
                plan,
                plan_payload(
                    extra_action={
                        "id": "active_observation_window",
                        "action": "Run the exact player-principal lifecycle observer window.",
                        "run_id": "20260606T100000Z-player-principal-lifecycle",
                        "approved_window": {
                            "start_utc": "2026-06-06T10:00:00Z",
                            "end_utc": "2026-06-06T10:15:00Z",
                        },
                        "writes_under_evidence_dir": False,
                    },
                ),
            )

            result = run_script("--plan-json", str(plan), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        action = report["results"][0]
        self.assertEqual(report["stale_or_too_late_action_count"], 1)
        self.assertEqual(report["stale_or_too_late_action_ids"], ["active_observation_window"])
        self.assertTrue(action["runtime_window_stale_or_too_late"])
        self.assertIn(
            "runtime_window_start_already_passed_prepare_fresh_window",
            action["blockers"],
        )
        self.assertIn(
            "runtime_window_end_already_passed_prepare_fresh_window",
            action["blockers"],
        )
        self.assertEqual(action["eligibility"], "blocked_live_or_server_action")
        self.assertFalse(action["activation_or_restart_from_stale_request_allowed"])
        self.assertFalse(
            report["runtime_window_stale_prevention"][
                "activation_or_restart_from_stale_request_allowed"
            ]
        )

    def test_run_id_without_explicit_approved_window_blocks_as_missing_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            write_json(
                plan,
                plan_payload(
                    extra_action={
                        "id": "active_observation_window",
                        "action": "Run the exact player-principal lifecycle observer window.",
                        "run_id": "20260606T100000Z-player-principal-lifecycle",
                        "writes_under_evidence_dir": False,
                    },
                ),
            )

            result = run_script("--plan-json", str(plan), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["stale_or_too_late_action_count"], 1)
        self.assertEqual(report["stale_or_too_late_action_ids"], ["active_observation_window"])
        self.assertTrue(report["results"][0]["runtime_window_stale_or_too_late"])
        self.assertIn(
            "runtime_window_approved_window_missing_for_action",
            report["results"][0]["blockers"],
        )
        self.assertNotIn(
            "runtime_window_start_already_passed_prepare_fresh_window",
            report["results"][0]["blockers"],
        )

    def test_rejects_positive_evidence_alias_in_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "overclaim.json"
            payload = plan_payload()
            payload["next_action_sequence"][0]["approved_runtime_evidence"] = True
            payload["next_action_sequence"][0]["approved_in_game_evidence"] = True
            payload["next_action_sequence"][0]["runtime_evidence_ready"] = "ready"
            write_json(plan, payload)

            result = run_script("--plan-json", str(plan), "--json")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("positive runtime/readiness shortcut aliases", result.stderr)
        self.assertIn("$.next_action_sequence[0].approved_in_game_evidence", result.stderr)
        self.assertIn("$.next_action_sequence[0].runtime_evidence_ready", result.stderr)

    def test_rejects_positive_post_window_sidecar_authority_alias_in_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "overclaim.json"
            payload = plan_payload()
            payload["next_action_sequence"][0]["post_window_sidecar_generation_authorized_by_this_report"] = True
            write_json(plan, payload)

            result = run_script("--plan-json", str(plan), "--json")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("positive runtime/readiness shortcut aliases", result.stderr)

    def test_rejects_positive_standing_authority_evidence_alias_in_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "overclaim.json"
            payload = plan_payload()
            payload["action_plan"] = {
                "standing_launch_authority_counts_as_approved_runtime_evidence": True,
            }
            write_json(plan, payload)

            result = run_script("--plan-json", str(plan), "--json")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("positive runtime/readiness shortcut aliases", result.stderr)

    def test_json_output_dash_does_not_create_dash_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            write_json(plan, plan_payload())

            result = run_script("--plan-json", str(plan), "--json-output", "-", cwd=root)
            report = json.loads(result.stdout)

            self.assertFalse((root / "-").exists())

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["schema"], RUNNER_SCHEMA)

    def test_safe_stdout_redirection_is_parsed_without_shell(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            output = root / "status.txt"
            write_json(
                plan,
                plan_payload(
                    command=f"scripts/report_obelisk_sdk_status.py --compact > {output}",
                    extra_action={"writes_under_evidence_dir": False},
                ),
            )

            result = run_script("--plan-json", str(plan), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["eligible_count"], 1)
        self.assertEqual(report["first_eligible_action_id"], "closure_missing_window_manifest_env")
        self.assertEqual(report["results"][0]["argv"], ["scripts/report_obelisk_sdk_status.py", "--compact"])
        self.assertEqual(report["results"][0]["execution_argv"][1:], ["scripts/report_obelisk_sdk_status.py", "--compact"])
        self.assertEqual(report["results"][0]["redirect_stdout"], str(output))

    def test_execute_uses_interpreter_for_repo_python_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            output = root / "status.txt"
            write_json(
                plan,
                plan_payload(
                    command=f"scripts/report_obelisk_sdk_status.py --compact > {output}",
                    extra_action={"writes_under_evidence_dir": False},
                ),
            )

            result = run_script("--plan-json", str(plan), "--execute", "--json")
            report = json.loads(result.stdout)

            self.assertTrue(output.read_text(encoding="utf-8").startswith("Obelisk SDK status:"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "executed")
        self.assertEqual(report["executed_count"], 1)
        self.assertEqual(report["results"][0]["returncode"], 0)

    def test_unsafe_compound_redirection_remains_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            write_json(
                plan,
                plan_payload(command=f"scripts/report_obelisk_sdk_status.py --compact 2> {root / 'err.txt'}"),
            )

            result = run_script("--plan-json", str(plan), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["blocked_count"], 1)
        self.assertIn("unsafe_or_compound_redirection_command_blocked", report["results"][0]["blockers"])

    def test_blocked_until_relative_artifact_unblocks_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            artifact = root / "window-manifest.env"
            write_json(
                plan,
                plan_payload(
                    command="scripts/report_obelisk_sdk_status.py --compact",
                    extra_action={
                        "evidence_dir": str(root),
                        "blocked_until": ["window-manifest.env"],
                    },
                ),
            )

            blocked = run_script("--plan-json", str(plan), "--json")
            blocked_report = json.loads(blocked.stdout)
            artifact.write_text("OBELISK_INSTANCE_ID=arkserver3\n", encoding="utf-8")
            eligible = run_script(
                "--plan-json",
                str(plan),
                "--allow-evidence-dir-writes",
                "--json",
            )
            eligible_report = json.loads(eligible.stdout)

        self.assertEqual(blocked.returncode, 0, blocked.stderr)
        self.assertIn("blocked_until_missing:window-manifest.env", blocked_report["results"][0]["blockers"])
        self.assertEqual(blocked_report["missing_input_or_artifact_blocker_count"], 1)
        self.assertEqual(eligible.returncode, 0, eligible.stderr)
        self.assertEqual(eligible_report["eligible_count"], 1)
        self.assertEqual(eligible_report["results"][0]["blocked_until_missing"], [])

    def test_live_role_action_preserves_context_but_is_not_runner_eligible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            write_json(
                plan,
                plan_payload(
                    command=(
                        "scripts/monitor_ark_player_presence_passive.sh --interval 10 "
                        "--linger-after-detect 900 --no-details arkserver3:Genesis2:27017"
                    ),
                    extra_action={
                        "id": "closure_missing_lifecycle_role_session_end",
                        "action": "continue_or_request_passive_wait_for_missing_lifecycle_role",
                        "action_kind": "lifecycle_event_role",
                        "artifact": "lifecycle-role/session_end",
                        "role": "session_end",
                        "items": ["lifecycle-role/session_end"],
                        "writes_under_evidence_dir": False,
                        "operator_context": operator_context(),
                    },
                ),
            )

            result = run_script("--plan-json", str(plan), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["eligible_count"], 0)
        self.assertEqual(report["eligibility_counts"], {"blocked_live_or_server_action": 1})
        blockers = report["results"][0]["blockers"]
        self.assertIn("live_monitor_action_not_started_by_runner", blockers)
        self.assertIn("live_wait_action_not_started_by_runner", blockers)
        self.assertIn("post_reboot_monitor_context_is_non_evidence_operator_context", blockers)
        self.assertIn("confirmed_beta_notice_context_does_not_authorize_runner", blockers)
        self.assertTrue(report["results"][0]["operator_context"]["confirmed_beta_notice_completed"])
        self.assertFalse(report["results"][0]["operator_context"]["context_inputs_authorize_runner"])
        self.assertFalse(report["results"][0]["counts_as_approved_runtime_evidence"])

    def test_player_presence_context_does_not_authorize_live_wait_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            write_json(
                plan,
                plan_payload(
                    command=(
                        "scripts/monitor_ark_player_presence_passive.sh --interval 10 "
                        "--linger-after-detect 900 --no-details arkserver3:Genesis2:27017"
                    ),
                    extra_action={
                        "id": "closure_missing_lifecycle_role_session_end",
                        "action": "continue_or_request_passive_wait_for_missing_lifecycle_role",
                        "action_kind": "lifecycle_event_role",
                        "artifact": "lifecycle-role/session_end",
                        "role": "session_end",
                        "items": ["lifecycle-role/session_end"],
                        "writes_under_evidence_dir": False,
                        "player_presence_context": {
                            "classification": "players_detected_operator_context_non_evidence",
                            "known_player_counts_by_target": {"arkserver3:Genesis2:27017": 2},
                            "targets_with_players_detected": ["arkserver3:Genesis2:27017"],
                            "players_detected": True,
                            "approved_runtime_evidence": False,
                            "counts_as_approved_runtime_evidence": False,
                        },
                    },
                ),
            )

            result = run_script("--plan-json", str(plan), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        blockers = report["results"][0]["blockers"]
        self.assertIn("live_wait_action_not_started_by_runner", blockers)
        self.assertIn("player_presence_context_is_non_evidence_operator_context", blockers)
        self.assertTrue(report["results"][0]["operator_context"]["player_presence_context_present"])
        self.assertTrue(report["results"][0]["operator_context"]["player_presence_players_detected"])
        self.assertFalse(
            report["results"][0]["operator_context"][
                "player_presence_context_counts_as_approved_runtime_evidence"
            ]
        )
        self.assertFalse(report["results"][0]["counts_as_approved_runtime_evidence"])
        self.assertEqual(report["eligible_count"], 0)

    def test_monitor_log_path_and_standing_context_do_not_authorize_live_wait_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            monitor_log = root / "post-reboot-passive-monitor.log"
            write_json(
                plan,
                plan_payload(
                    command=(
                        "scripts/monitor_ark_player_presence_passive.sh --interval 10 "
                        "--linger-after-detect 900 --no-details arkserver3:Genesis2:27017"
                    ),
                    extra_action={
                        "id": "closure_missing_lifecycle_role_session_start_rejected",
                        "action": "continue_or_request_passive_wait_for_missing_lifecycle_role",
                        "artifact": "lifecycle-role/session_start_rejected",
                        "role": "session_start_rejected",
                        "items": ["lifecycle-role/session_start_rejected"],
                        "writes_under_evidence_dir": False,
                        "recorded_standing_authority_observed": True,
                        "allowed_under_recorded_standing_authority": True,
                        "operator_context": {
                            "post_reboot_passive_monitor_log_supplied": True,
                            "post_reboot_passive_monitor_log_path": str(monitor_log),
                            "confirmed_beta_notice_context_present": True,
                            "confirmed_beta_notice_path": str(root / "beta-notice.confirmed.json"),
                            "confirmed_beta_notice_completed": True,
                            "confirmed_beta_notice_standing_launch_authority_recorded": True,
                            "context_inputs_authorize_runner": False,
                            "approved_runtime_evidence": False,
                            "counts_as_approved_runtime_evidence": False,
                        },
                    },
                ),
            )

            result = run_script("--plan-json", str(plan), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        blockers = report["results"][0]["blockers"]
        self.assertIn("live_monitor_action_not_started_by_runner", blockers)
        self.assertIn("live_wait_action_not_started_by_runner", blockers)
        self.assertIn("post_reboot_monitor_context_is_non_evidence_operator_context", blockers)
        self.assertIn("confirmed_beta_notice_context_does_not_authorize_runner", blockers)
        context = report["results"][0]["operator_context"]
        self.assertTrue(context["post_reboot_monitor_context_present"])
        self.assertEqual(context["post_reboot_monitor_path"], str(monitor_log))
        self.assertEqual(context["post_reboot_passive_monitor_log_path"], str(monitor_log))
        self.assertTrue(context["confirmed_beta_notice_standing_launch_authority_recorded"])
        self.assertTrue(report["results"][0]["recorded_standing_authority_observed"])
        self.assertTrue(report["results"][0]["allowed_operator_context_under_recorded_standing_authority"])
        self.assertTrue(report["results"][0]["allowed_under_recorded_standing_authority"])
        self.assertTrue(report["results"][0]["standing_authority_is_operator_context_only"])
        self.assertFalse(report["results"][0]["runner_execution_authorized_by_recorded_standing_authority"])
        self.assertFalse(context["standing_authority_authorizes_runner"])
        self.assertFalse(context["standing_authority_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["results"][0]["authorized_by_this_report"])
        self.assertFalse(report["results"][0]["counts_as_approved_runtime_evidence"])
        self.assertEqual(report["eligible_count"], 0)

    def test_fresh_authority_requirement_blocks_runner_even_with_standing_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            write_json(
                plan,
                plan_payload(
                    command="scripts/report_obelisk_sdk_status.py --compact",
                    extra_action={
                        "id": "stage_closure_compatible_root",
                        "action": "stage_closure_compatible_player_principal_lifecycle_evidence_root",
                        "action_kind": "invalid_evidence_source",
                        "writes_under_evidence_dir": False,
                        "recorded_standing_authority_observed": True,
                        "allowed_operator_context_under_recorded_standing_authority": False,
                        "allowed_under_recorded_standing_authority": False,
                        "requires_operator_authority_before_execution": True,
                        "operator_authority_source_required": "fresh_current_turn_operator_message",
                        "requires_current_turn_operator_approval": True,
                        "requires_fresh_current_turn_operator_approval": True,
                        "counts_as_approved_runtime_evidence": False,
                    },
                ),
            )

            result = run_script("--plan-json", str(plan), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["eligible_count"], 0)
        self.assertEqual(report["results"][0]["eligibility"], "blocked_requires_operator_authority")
        self.assertIn(
            "operator_authority_required_before_runner_execution:fresh_current_turn_operator_message",
            report["results"][0]["blockers"],
        )
        self.assertTrue(report["results"][0]["recorded_standing_authority_observed"])
        self.assertFalse(report["results"][0]["allowed_under_recorded_standing_authority"])
        self.assertFalse(report["results"][0]["runner_execution_authorized_by_recorded_standing_authority"])
        self.assertFalse(report["results"][0]["counts_as_approved_runtime_evidence"])

    def test_invalid_passive_root_manual_staging_is_not_runner_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            source_dir = "/tmp/live-validation-logs/20260607T071833Z-postpatch-ragnarok-theisland-monitor"
            closure_dir = "/tmp/live-validation-logs/20260607T071833Z-player-principal-lifecycle"
            write_json(
                plan,
                plan_payload(
                    extra_action={
                        "id": "stage_closure_compatible_root",
                        "action": "stage_closure_compatible_player_principal_lifecycle_evidence_root",
                        "action_kind": "invalid_evidence_source",
                        "missing_kind": "invalid_evidence_source",
                        "artifact": source_dir,
                        "items": [source_dir],
                        "source_evidence_dir": source_dir,
                        "invalid_source_evidence_dir": source_dir,
                        "suggested_valid_closure_evidence_dir": closure_dir,
                        "closure_compatible_evidence_dir": closure_dir,
                        "source_looks_like_passive_monitor_root": True,
                        "machine_action_suggested_for_invalid_passive_root": False,
                        "runner_command_available": False,
                        "manual_staging_required_before_machine_actions": True,
                        "writes_under_evidence_dir": False,
                        "requires_operator_authority_before_execution": False,
                        "authorized_by_this_report": False,
                        "counts_as_approved_runtime_evidence": False,
                    },
                ),
            )

            result = run_script("--plan-json", str(plan), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["eligible_count"], 0)
        action = report["results"][0]
        self.assertEqual(action["eligibility"], "blocked_unsafe_or_unavailable_command")
        self.assertIn("command_metadata_missing", action["blockers"])
        self.assertIn(
            "invalid_passive_root_requires_manual_offline_staging_not_runner",
            action["blockers"],
        )
        self.assertEqual(action["source_evidence_dir"], source_dir)
        self.assertEqual(action["suggested_valid_closure_evidence_dir"], closure_dir)
        self.assertFalse(action["machine_action_suggested_for_invalid_passive_root"])
        self.assertFalse(action["runner_command_available"])
        self.assertTrue(action["manual_staging_required_before_machine_actions"])
        self.assertFalse(action["runner_execution_authorized_by_recorded_standing_authority"])
        self.assertFalse(action["counts_as_approved_runtime_evidence"])

    def test_exact_standing_scope_is_metadata_only_not_runner_execution_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            write_json(
                plan,
                plan_payload(
                    command="scripts/report_obelisk_sdk_status.py --compact",
                    extra_action={
                        "id": "offline_status_summary",
                        "action": "run_offline_status_summary",
                        "writes_under_evidence_dir": False,
                        "recorded_standing_authority_observed": True,
                        "allowed_operator_context_under_recorded_standing_authority": True,
                        "allowed_under_recorded_standing_authority": True,
                        "requires_operator_authority_before_execution": True,
                        "operator_authority_source_required": "standing_launch_authority",
                        "standing_launch_authority_covers_target_run": True,
                        "standing_launch_authority_satisfies_operator_approval": True,
                        "counts_as_approved_runtime_evidence": False,
                    },
                ),
            )

            result = run_script("--plan-json", str(plan), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["eligible_count"], 0)
        self.assertEqual(report["results"][0]["status"], "blocked")
        self.assertEqual(report["results"][0]["eligibility"], "blocked_requires_operator_authority")
        self.assertIn(
            "standing_authority_metadata_only_not_runner_execution_authority:standing_launch_authority",
            report["results"][0]["blockers"],
        )
        self.assertTrue(report["results"][0]["allowed_under_recorded_standing_authority"])
        self.assertFalse(report["results"][0]["standing_authority_authorizes_runner"])
        self.assertFalse(report["results"][0]["runner_execution_authorized_by_recorded_standing_authority"])
        self.assertFalse(report["results"][0]["authorized_by_this_report"])
        self.assertFalse(report["results"][0]["counts_as_approved_runtime_evidence"])
        self.assertIn(
            "offline_status_summary",
            report["execution_boundaries"]["standing_authority_metadata"]["action_ids"],
        )
        self.assertFalse(
            report["execution_boundaries"]["standing_authority_metadata"][
                "standing_authority_converted_to_machine_action"
            ]
        )
        self.assertFalse(
            report["execution_boundaries"]["standing_authority_metadata"][
                "standing_authority_authorizes_runner_execution"
            ]
        )

    def test_stale_passive_monitor_root_is_source_only_even_with_allowlisted_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            source_dir = "/tmp/live-validation-logs/20260607T071833Z-postpatch-ragnarok-theisland-monitor"
            write_json(
                plan,
                plan_payload(
                    command="scripts/report_obelisk_sdk_status.py --compact",
                    extra_action={
                        "id": "stage_stale_passive_monitor_source",
                        "action": "stage_closure_compatible_player_principal_lifecycle_evidence_root",
                        "source_evidence_dir": source_dir,
                        "source_root_role": "post_reboot_passive_monitor_root",
                        "writes_under_evidence_dir": False,
                        "authorized_by_this_report": False,
                        "counts_as_approved_runtime_evidence": False,
                    },
                ),
            )

            result = run_script("--plan-json", str(plan), "--json")
            report = json.loads(result.stdout)
            action = report["results"][0]
            source_boundary = action["source_root_boundary"]

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["eligible_count"], 0)
        self.assertEqual(action["eligibility"], "blocked_unsafe_or_unavailable_command")
        self.assertIn("invalid_passive_root_requires_manual_offline_staging_not_runner", action["blockers"])
        self.assertIn("source_root_source_only_non_evidence_not_runner_action", action["blockers"])
        self.assertEqual(
            source_boundary["classification"],
            "stale_passive_monitor_root_source_only_non_evidence",
        )
        self.assertTrue(source_boundary["source_looks_like_passive_monitor_root"])
        self.assertTrue(source_boundary["source_is_stale"])
        self.assertTrue(source_boundary["source_only_non_evidence"])
        self.assertFalse(source_boundary["source_authorizes_runner"])
        self.assertFalse(source_boundary["source_counts_as_approved_runtime_evidence"])
        self.assertIn(
            "stage_stale_passive_monitor_source",
            report["source_only_monitor_roots"]["action_ids"],
        )
        self.assertFalse(report["source_only_monitor_roots"]["source_roots_authorize_runner"])
        self.assertFalse(
            report["source_only_monitor_roots"][
                "source_roots_count_as_approved_runtime_evidence"
            ]
        )

    def test_live_log_copy_command_is_blocked_even_with_evidence_write_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            write_json(
                plan,
                plan_payload(
                    command=(
                        "scripts/copy_player_principal_lifecycle_ready_log.py "
                        "--instance arkserver3 "
                        f"--evidence-dir {root} "
                        "--expected-binary-sha256 "
                        "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                        "--allow-live-log-read --allow-evidence-dir-write --execute"
                    ),
                    extra_action={
                        "id": "closure_missing_obelisk_log",
                        "action": "copy_ready_player_principal_lifecycle_obelisk_log",
                        "artifact": "Obelisk.log",
                        "blocked_until": [
                            "lifecycle-role/session_start",
                            "lifecycle-role/session_start_rejected",
                            "lifecycle-role/session_end",
                        ],
                    },
                ),
            )

            result = run_script(
                "--plan-json",
                str(plan),
                "--allow-evidence-dir-writes",
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        blockers = report["results"][0]["blockers"]
        self.assertIn("live_log_copy_not_started_by_runner", blockers)
        self.assertIn("live_log_read_flag_not_allowed_by_runner", blockers)
        self.assertEqual(report["results"][0]["eligibility"], "blocked_live_or_server_action")

    def test_live_log_copy_command_is_blocked_with_post_window_sidecar_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            write_json(
                plan,
                plan_payload(
                    command=(
                        "scripts/copy_player_principal_lifecycle_ready_log.py "
                        "--instance arkserver3 "
                        f"--evidence-dir {root} "
                        "--expected-binary-sha256 "
                        "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                        "--allow-post-window-sidecar-generation "
                        "--allow-post-window-preflight-live-read "
                        "--allow-live-log-read --allow-evidence-dir-write --execute"
                    ),
                    extra_action={
                        "id": "closure_missing_obelisk_log",
                        "action": "copy_ready_player_principal_lifecycle_obelisk_log",
                        "artifact": "Obelisk.log",
                    },
                ),
            )

            result = run_script(
                "--plan-json",
                str(plan),
                "--allow-evidence-dir-writes",
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        blockers = report["results"][0]["blockers"]
        self.assertIn("live_log_copy_not_started_by_runner", blockers)
        self.assertIn("post_window_sidecar_generation_flag_not_allowed_by_runner", blockers)
        self.assertIn("post_window_preflight_live_read_flag_not_allowed_by_runner", blockers)
        self.assertFalse(report["post_window_sidecar_generation_authorized_by_this_report"])
        self.assertFalse(report["post_window_preflight_live_read_authorized_by_this_report"])
        self.assertFalse(report["post_window_sidecar_generation_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["post_window_preflight_live_read_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["results"][0]["eligible_for_execution"])
        self.assertFalse(report["results"][0]["post_window_sidecar_generation_authorized_by_this_report"])
        self.assertFalse(report["results"][0]["post_window_preflight_live_read_authorized_by_this_report"])
        self.assertEqual(report["results"][0]["eligibility"], "blocked_live_or_server_action")

    def test_post_window_sidecar_flags_do_not_make_offline_helper_eligible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            write_json(
                plan,
                plan_payload(
                    command=(
                        "scripts/report_obelisk_sdk_status.py --compact "
                        "--allow-post-window-sidecar-generation "
                        "--allow-post-window-preflight-live-read"
                    ),
                    extra_action={"writes_under_evidence_dir": False},
                ),
            )

            result = run_script("--plan-json", str(plan), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        blockers = report["results"][0]["blockers"]
        self.assertIn("post_window_sidecar_generation_flag_not_allowed_by_runner", blockers)
        self.assertIn("post_window_preflight_live_read_flag_not_allowed_by_runner", blockers)
        self.assertEqual(report["eligible_count"], 0)
        self.assertEqual(report["results"][0]["eligibility"], "blocked_live_or_server_action")

    def test_structured_runner_command_cannot_bypass_no_shell_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            write_json(
                plan,
                plan_payload(
                    extra_action={
                        "runner_command": {
                            "argv": ["/bin/sh", "-c", "scripts/report_obelisk_sdk_status.py --compact"],
                        },
                        "writes_under_evidence_dir": False,
                    },
                ),
            )

            result = run_script("--plan-json", str(plan), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        blockers = report["results"][0]["blockers"]
        self.assertIn("structured_runner_command_shell_executable_blocked", blockers)
        self.assertIn("command_not_allowlisted_repo_script", blockers)
        self.assertEqual(report["results"][0]["eligibility"], "blocked_unsafe_or_unavailable_command")

    def test_structured_runner_command_rejects_non_string_argv_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            write_json(
                plan,
                plan_payload(
                    extra_action={
                        "runner_command": {
                            "argv": ["scripts/report_obelisk_sdk_status.py", "--compact", {"shell": "no"}],
                        },
                        "writes_under_evidence_dir": False,
                    },
                ),
            )

            result = run_script("--plan-json", str(plan), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["eligible_count"], 0)
        self.assertIn("structured_runner_command_non_string_arg_blocked", report["results"][0]["blockers"])

    def test_structured_checker_runner_command_is_offline_dry_run_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            manifest = root / "run" / "approved-bundle" / "approved-runtime-principal-lifecycle-evidence.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text("{}", encoding="utf-8")
            write_json(
                plan,
                plan_payload(
                    extra_action={
                        "id": "status_checker_approved_runtime_principal_lifecycle_evidence",
                        "action": "run_approved_runtime_evidence_checker_on_copied_manifest",
                        "action_kind": "checker",
                        "artifact": "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
                        "items": ["approved-bundle/approved-runtime-principal-lifecycle-evidence.json"],
                        "command_status": "NOT EXECUTED",
                        "command_text_not_executed": (
                            "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py "
                            f"{manifest} --json"
                        ),
                        "runner_command_available": True,
                        "runner_command": {
                            "argv": [
                                "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
                                str(manifest),
                                "--json",
                            ],
                            "execution_mode": "no_shell_offline_helper",
                        },
                        "command_path_binding": command_path_binding(
                            manifest.parents[1],
                            inputs=[
                                bound_artifact(
                                    manifest,
                                    role="input",
                                    relative_path=(
                                        "approved-bundle/"
                                        "approved-runtime-principal-lifecycle-evidence.json"
                                    ),
                                    argv_position=1,
                                )
                            ],
                        ),
                        "command_path_hash_bound": True,
                        "machine_executable": True,
                        "writes_under_evidence_dir": False,
                        "exact_copied_lifecycle_event_triplet_required_before_actionable": True,
                        "exact_copied_lifecycle_event_triplet_matched": True,
                    },
                ),
            )

            result = run_script("--plan-json", str(plan), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["eligible_count"], 1)
        action = report["results"][0]
        self.assertEqual(action["eligibility"], "eligible_offline_helper")
        self.assertEqual(
            action["argv"],
            [
                "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
                str(manifest),
                "--json",
            ],
        )
        self.assertEqual(action["blockers"], [])
        self.assertFalse(action["executed"])
        self.assertFalse(action["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(
            report["checker_required_post_window_replay"][
                "approved_evidence_bundle_checker_accepted_by_runner"
            ]
        )

    def test_output_flag_without_value_is_not_runner_eligible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            write_json(
                plan,
                plan_payload(
                    command="scripts/report_obelisk_sdk_status.py --json-output",
                    extra_action={"writes_under_evidence_dir": False},
                ),
            )

            result = run_script("--plan-json", str(plan), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["eligible_count"], 0)
        self.assertIn("--json-output:missing_value", report["results"][0]["blockers"])

    def test_post_window_preflight_shell_helper_is_not_offline_runner_eligible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            copied_log = root / "Obelisk.log"
            manifest = root / "window-manifest.env"
            copied_log.write_text("copied log\n", encoding="utf-8")
            manifest.write_text("run_id=20260606T100000Z-player-principal-lifecycle\n", encoding="utf-8")
            write_json(
                plan,
                plan_payload(
                    command=(
                        "scripts/check_player_principal_lifecycle_preflight.sh "
                        "--instance arkserver3 --map Genesis2 --mode stable "
                        "--expected-binary-sha256 "
                        "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                        "--run-id 20260606T100000Z-player-principal-lifecycle "
                        f"--window-manifest {manifest} --copied-log {copied_log} "
                        f"--evidence-dir {root} --json"
                    ),
                    extra_action={
                        "id": "closure_missing_preflight_post_json",
                        "action": "capture_post_window_stable_preflight_json",
                        "artifact": "preflight-post.json",
                    },
                ),
            )

            result = run_script(
                "--plan-json",
                str(plan),
                "--allow-evidence-dir-writes",
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "preflight_server_posture_check_not_started_by_runner",
            report["results"][0]["blockers"],
        )
        self.assertEqual(report["results"][0]["eligibility"], "blocked_live_or_server_action")

    def test_offline_bundle_helper_is_eligible_when_copied_inputs_exist_and_writes_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            copied_log = root / "Obelisk.log"
            manifest = root / "window-manifest.env"
            output_dir = root / "approved-bundle"
            copied_log.write_text("copied log\n", encoding="utf-8")
            manifest.write_text("run_id=20260606T100000Z-player-principal-lifecycle\n", encoding="utf-8")
            write_json(
                plan,
                plan_payload(
                    command=(
                        "scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py "
                        f"--copied-log {copied_log} "
                        f"--window-manifest {manifest} "
                        f"--output-dir {output_dir} "
                        "--obelisk-commit 0123456789abcdef0123456789abcdef01234567 "
                        "--reviewed-by runner-test --review-note consume-only"
                    ),
                    extra_action={
                        "id": "closure_missing_approved_bundle",
                        "action": "build_approved_runtime_principal_lifecycle_evidence_bundle",
                        "artifact": "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
                        "blocked_until": ["window-manifest.env"],
                        "command_path_binding": command_path_binding(
                            root,
                            inputs=[
                                bound_artifact(
                                    copied_log,
                                    role="input",
                                    relative_path="Obelisk.log",
                                    argv_flags=["--copied-log"],
                                ),
                                bound_artifact(
                                    manifest,
                                    role="input",
                                    relative_path="window-manifest.env",
                                    argv_flags=["--window-manifest"],
                                ),
                            ],
                            outputs=[
                                bound_artifact(
                                    output_dir,
                                    role="output_dir",
                                    relative_path="approved-bundle",
                                    argv_flags=["--output-dir"],
                                    must_exist=False,
                                )
                            ],
                        ),
                        "command_path_hash_bound": True,
                    },
                ),
            )

            result = run_script(
                "--plan-json",
                str(plan),
                "--allow-evidence-dir-writes",
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["eligible_count"], 1)
        self.assertEqual(report["first_eligible_action_id"], "closure_missing_approved_bundle")
        self.assertEqual(report["results"][0]["eligibility"], "eligible_offline_helper")
        self.assertEqual(report["results"][0]["blockers"], [])

    def test_bound_bundle_helper_fails_closed_when_copied_log_hash_drifts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            copied_log = root / "Obelisk.log"
            manifest = root / "window-manifest.env"
            output_dir = root / "approved-bundle"
            copied_log.write_text("copied log\n", encoding="utf-8")
            manifest.write_text("run_id=20260606T100000Z-player-principal-lifecycle\n", encoding="utf-8")
            binding = command_path_binding(
                root,
                inputs=[
                    bound_artifact(
                        copied_log,
                        role="input",
                        relative_path="Obelisk.log",
                        argv_flags=["--copied-log"],
                    ),
                    bound_artifact(
                        manifest,
                        role="input",
                        relative_path="window-manifest.env",
                        argv_flags=["--window-manifest"],
                    ),
                ],
                outputs=[
                    bound_artifact(
                        output_dir,
                        role="output_dir",
                        relative_path="approved-bundle",
                        argv_flags=["--output-dir"],
                        must_exist=False,
                    )
                ],
            )
            write_json(
                plan,
                plan_payload(
                    command=(
                        "scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py "
                        f"--copied-log {copied_log} "
                        f"--window-manifest {manifest} "
                        f"--output-dir {output_dir} "
                        "--obelisk-commit 0123456789abcdef0123456789abcdef01234567 "
                        "--reviewed-by runner-test --review-note consume-only"
                    ),
                    extra_action={
                        "id": "closure_missing_approved_bundle",
                        "action": "build_approved_runtime_principal_lifecycle_evidence_bundle",
                        "artifact": "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
                        "command_path_binding": binding,
                        "command_path_hash_bound": True,
                    },
                ),
            )
            copied_log.write_text("drifted copied log\n", encoding="utf-8")

            result = run_script(
                "--plan-json",
                str(plan),
                "--allow-evidence-dir-writes",
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        action = report["results"][0]
        self.assertEqual(report["eligible_count"], 0)
        self.assertTrue(
            any(
                blocker.startswith("command_path_binding_sha256_mismatch:Obelisk.log")
                for blocker in action["blockers"]
            )
        )
        self.assertEqual(action["eligibility"], "blocked_unsafe_or_unavailable_command")
        self.assertFalse(action["counts_as_approved_runtime_evidence"])

    def test_execute_requires_declared_dry_run_report_for_dry_run_first_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            dry_run_report = root / "post-window-next-actions.dry-run.json"
            write_json(
                plan,
                plan_payload(
                    command="scripts/report_obelisk_sdk_status.py --compact",
                    extra_action={
                        "id": "closure_missing_approved_bundle",
                        "action": "build_approved_runtime_principal_lifecycle_evidence_bundle",
                        "artifact": "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
                        "writes_under_evidence_dir": False,
                        "dry_run_first_required": True,
                        "dry_run_must_complete_before_execute": True,
                        "dry_run_report_path": str(dry_run_report),
                        "required_dry_run_artifacts": [str(dry_run_report)],
                    },
                ),
            )

            dry_run = run_script("--plan-json", str(plan), "--json")
            dry_run_payload = json.loads(dry_run.stdout)
            blocked = run_script("--plan-json", str(plan), "--execute", "--json")
            blocked_payload = json.loads(blocked.stdout)
            dry_run_report.write_text('{"schema":"runner-dry-run-fixture"}\n', encoding="utf-8")
            executed = run_script("--plan-json", str(plan), "--execute", "--json")
            executed_payload = json.loads(executed.stdout)

        self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
        self.assertEqual(dry_run_payload["eligible_count"], 1)
        self.assertEqual(dry_run_payload["results"][0]["blockers"], [])
        self.assertNotEqual(blocked.returncode, 0)
        self.assertEqual(blocked_payload["executed_count"], 0)
        self.assertIn(
            f"dry_run_first_required_artifact_missing:{dry_run_report}",
            blocked_payload["results"][0]["blockers"],
        )
        self.assertEqual(blocked_payload["results"][0]["dry_run_missing_artifacts"], [str(dry_run_report)])
        self.assertEqual(
            blocked_payload["results"][0]["eligibility"],
            "blocked_missing_inputs_or_artifacts",
        )
        self.assertEqual(executed.returncode, 0, executed.stderr)
        self.assertEqual(executed_payload["executed_count"], 1)
        self.assertEqual(executed_payload["results"][0]["status"], "executed_success")
        self.assertFalse(executed_payload["results"][0]["counts_as_approved_runtime_evidence"])

    def test_action_level_evidence_write_requires_explicit_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            write_json(
                plan,
                plan_payload(
                    command="scripts/report_obelisk_sdk_status.py --compact",
                    extra_action={
                        "evidence_dir": str(root),
                        "writes_under_evidence_dir": True,
                    },
                ),
            )

            blocked = run_script("--plan-json", str(plan), "--json")
            blocked_report = json.loads(blocked.stdout)
            allowed = run_script(
                "--plan-json",
                str(plan),
                "--allow-evidence-dir-writes",
                "--json",
            )
            allowed_report = json.loads(allowed.stdout)

        self.assertEqual(blocked.returncode, 0, blocked.stderr)
        self.assertIn(
            f"evidence_dir_write_requires_explicit_flag:{root}",
            blocked_report["results"][0]["blockers"],
        )
        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        self.assertEqual(allowed_report["eligible_count"], 1)

    def test_lifecycle_role_blocked_until_is_delegated_to_action_helper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            write_json(
                plan,
                plan_payload(
                    command="scripts/report_obelisk_sdk_status.py --compact",
                    extra_action={
                        "evidence_dir": str(root),
                        "writes_under_evidence_dir": False,
                        "blocked_until": [
                            "lifecycle-role/session_start",
                            "lifecycle-role/session_start_rejected",
                            "lifecycle-role/session_end",
                        ],
                    },
                ),
            )

            result = run_script("--plan-json", str(plan), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["eligible_count"], 1)
        self.assertEqual(report["results"][0]["blocked_until_missing"], [])

    def test_exact_triplet_blocker_blocks_evidence_bundle_helper_even_when_inputs_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            copied_log = root / "Obelisk.log"
            manifest = root / "window-manifest.env"
            output_dir = root / "approved-bundle"
            copied_log.write_text("copied log\n", encoding="utf-8")
            manifest.write_text("run_id=20260606T100000Z-player-principal-lifecycle\n", encoding="utf-8")
            write_json(
                plan,
                plan_payload(
                    command=(
                        "scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py "
                        f"--copied-log {copied_log} "
                        f"--window-manifest {manifest} "
                        f"--output-dir {output_dir} "
                        "--obelisk-commit 0123456789abcdef0123456789abcdef01234567 "
                        "--reviewed-by runner-test --review-note consume-only"
                    ),
                    extra_action={
                        "id": "closure_missing_approved_bundle",
                        "action": "build_approved_runtime_principal_lifecycle_evidence_bundle",
                        "artifact": "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
                        "command_path_binding": command_path_binding(
                            root,
                            inputs=[
                                bound_artifact(
                                    copied_log,
                                    role="input",
                                    relative_path="Obelisk.log",
                                    argv_flags=["--copied-log"],
                                ),
                                bound_artifact(
                                    manifest,
                                    role="input",
                                    relative_path="window-manifest.env",
                                    argv_flags=["--window-manifest"],
                                ),
                            ],
                            outputs=[
                                bound_artifact(
                                    output_dir,
                                    role="output_dir",
                                    relative_path="approved-bundle",
                                    argv_flags=["--output-dir"],
                                    must_exist=False,
                                )
                            ],
                        ),
                        "command_path_hash_bound": True,
                        "exact_copied_lifecycle_event_triplet_required_before_actionable": True,
                        "missing_copied_lifecycle_event_triplet_labels": [
                            "CheckJoinInProgress(1,0)",
                        ],
                        "writes_under_evidence_dir": True,
                    },
                ),
            )

            result = run_script(
                "--plan-json",
                str(plan),
                "--allow-evidence-dir-writes",
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        blockers = report["results"][0]["blockers"]
        self.assertIn(
            "exact_copied_lifecycle_event_triplet_missing:CheckJoinInProgress(1,0)",
            blockers,
        )
        self.assertEqual(report["eligible_count"], 0)
        self.assertEqual(report["results"][0]["eligibility"], "blocked_missing_inputs_or_artifacts")
        self.assertFalse(report["results"][0]["eligible_for_execution"])
        self.assertFalse(report["results"][0]["counts_as_approved_runtime_evidence"])

    def test_stale_passive_complete_role_triplet_checker_command_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            source_dir = "/tmp/live-validation-logs/20260607T071833Z-postpatch-ragnarok-theisland-monitor"
            manifest = f"{source_dir}/approved-bundle/approved-runtime-principal-lifecycle-evidence.json"
            write_json(
                plan,
                plan_payload(
                    command=(
                        "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py "
                        f"{manifest} --json"
                    ),
                    extra_action={
                        "id": "stale_passive_complete_triplet_checker",
                        "action": "run_approved_runtime_evidence_checker_on_copied_manifest",
                        "action_kind": "stale_passive_complete_role_triplet_non_evidence",
                        "artifact": "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
                        "items": [
                            "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
                        ],
                        "source_evidence_dir": source_dir,
                        "source_root_role": "post_reboot_passive_monitor_root",
                        "source_looks_like_passive_monitor_root": True,
                        "source_root_stale": True,
                        "source_root_valid_for_closure": False,
                        "passive_monitor_root_accepted_as_closure_evidence_dir": False,
                        "stale_or_passive_complete_role_triplet_non_evidence": True,
                        "exact_copied_lifecycle_event_triplet_required_before_actionable": True,
                        "exact_copied_lifecycle_event_triplet_matched": True,
                        "exact_copied_lifecycle_event_triplet_complete": True,
                        "writes_under_evidence_dir": False,
                        "authorized_by_this_report": False,
                        "counts_as_approved_runtime_evidence": False,
                    },
                ),
            )

            result = run_script("--plan-json", str(plan), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["eligible_count"], 0)
        action = report["results"][0]
        self.assertFalse(action["eligible_for_execution"])
        self.assertIn(
            "stale_passive_complete_role_triplet_non_evidence_not_runner",
            action["blockers"],
        )
        self.assertIn(
            "source_root_source_only_non_evidence_not_runner_action",
            action["blockers"],
        )
        self.assertTrue(action["stale_or_passive_complete_role_triplet_non_evidence"])
        self.assertEqual(
            action["source_root_boundary"]["classification"],
            "invalid_passive_monitor_root_source_only_non_evidence",
        )
        self.assertFalse(action["source_root_authorizes_runner"])
        self.assertFalse(action["counts_as_approved_runtime_evidence"])
        self.assertEqual(
            report["checker_required_post_window_replay"][
                "checker_actions_executed_by_runner_count"
            ],
            0,
        )
        self.assertFalse(report["approved_runtime_evidence"])

    def test_expired_runtime_window_non_evidence_is_not_runner_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            write_json(
                plan,
                plan_payload(extra_action=runtime_window_lifecycle_action(expired=True)),
            )

            result = run_script("--plan-json", str(plan), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["eligible_count"], 0)
        action = report["results"][0]
        self.assertIn(
            "expired_runtime_window_non_evidence_requires_manual_close_not_runner",
            action["blockers"],
        )
        self.assertTrue(action["expired_runtime_window_non_evidence"])
        self.assertTrue(action["prepare_fresh_player_backed_window_required"])
        self.assertTrue(action["copy_bundle_commands_suppressed_until_exact_triplet"])
        self.assertIn(
            "offline_parallel_evidence_lanes_are_planning_only_not_runner",
            action["blockers"],
        )
        self.assertTrue(action["offline_parallel_evidence_lanes_present"])
        self.assertEqual(
            action["offline_parallel_evidence_lanes"]["runtime_window_state"],
            "expired_non_evidence",
        )
        self.assertEqual(action["eligibility"], "blocked_unsafe_or_unavailable_command")
        boundary = report["runtime_window_lifecycle"]
        self.assertEqual(
            boundary["classification"],
            "expired_non_evidence_windows_blocked_prepare_fresh_player_backed_window",
        )
        self.assertEqual(
            boundary["expired_non_evidence_action_ids"],
            ["close_expired_player_principal_lifecycle_window_as_non_evidence"],
        )
        self.assertFalse(boundary["runner_copies_source_log"])
        self.assertFalse(boundary["runner_builds_bundle"])
        self.assertFalse(boundary["runner_runs_checker"])
        offline_lanes = report["offline_parallel_evidence_lanes"]
        self.assertTrue(offline_lanes["present"])
        self.assertEqual(
            offline_lanes["classification"],
            "parallel_offline_lanes_blocked_as_planning_metadata",
        )
        self.assertFalse(offline_lanes["runner_executes_parallel_lanes"])
        self.assertFalse(offline_lanes["lanes_count_as_approved_runtime_evidence"])
        self.assertEqual(offline_lanes["lane_count"], 4)
        self.assertEqual(offline_lanes["expected_lane_count"], 4)
        self.assertEqual(offline_lanes["missing_expected_lane_ids"], [])
        self.assertEqual(offline_lanes["unexpected_lane_ids"], [])
        self.assertEqual(offline_lanes["lane_misconfiguration_paths"], [])
        self.assertIn("post_runtime_identity_public_contract_gate", offline_lanes["lane_ids"])
        self.assertIn("post_identity_p0_chain_certificates", offline_lanes["lane_ids"])
        self.assertFalse(report["approved_runtime_evidence"])

    def test_active_runtime_window_waiting_is_not_closure_or_runner_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            write_json(
                plan,
                plan_payload(extra_action=runtime_window_lifecycle_action(expired=False)),
            )

            result = run_script("--plan-json", str(plan), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        action = report["results"][0]
        self.assertIn(
            "active_runtime_window_waiting_for_exact_triplet_not_runner",
            action["blockers"],
        )
        self.assertTrue(action["active_runtime_window_waiting_for_exact_triplet"])
        self.assertTrue(action["active_window_not_closure_ready"])
        self.assertFalse(action["prepare_fresh_player_backed_window_required"])
        self.assertIn(
            "offline_parallel_evidence_lanes_are_planning_only_not_runner",
            action["blockers"],
        )
        self.assertTrue(action["offline_parallel_evidence_lanes_present"])
        boundary = report["runtime_window_lifecycle"]
        self.assertEqual(boundary["classification"], "active_windows_waiting_not_runner_actions")
        self.assertEqual(
            boundary["active_waiting_action_ids"],
            ["wait_for_active_player_principal_lifecycle_window_exact_triplet_or_end"],
        )
        self.assertTrue(boundary["active_windows_remain_waiting"])
        self.assertFalse(boundary["fresh_player_backed_window_required"])
        self.assertTrue(report["offline_parallel_evidence_lanes"]["present"])
        self.assertFalse(
            report["offline_parallel_evidence_lanes"][
                "lanes_authorize_runtime_capture"
            ]
        )
        self.assertEqual(report["offline_parallel_evidence_lanes"]["lane_count"], 4)
        self.assertEqual(
            report["offline_parallel_evidence_lanes"]["missing_expected_lane_ids"],
            [],
        )
        self.assertEqual(
            report["offline_parallel_evidence_lanes"]["lane_misconfiguration_paths"],
            [],
        )
        self.assertEqual(report["eligible_count"], 0)
        self.assertFalse(report["approved_runtime_evidence"])

    def test_runner_reports_offline_parallel_lane_contract_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            action = runtime_window_lifecycle_action(expired=False)
            action["offline_parallel_evidence_lanes"]["runner_must_not_execute_lanes"] = False
            action["offline_parallel_evidence_lanes"]["lanes"][0][
                "runner_must_not_execute_lane"
            ] = False
            write_json(plan, plan_payload(extra_action=action))

            result = run_script("--plan-json", str(plan), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        action_result = report["results"][0]
        self.assertIn(
            "offline_parallel_evidence_lanes_misconfigured_not_runner",
            action_result["blockers"],
        )
        self.assertIn(
            "$.offline_parallel_evidence_lanes.runner_must_not_execute_lanes",
            action_result["offline_parallel_evidence_lanes_misconfiguration_paths"],
        )
        self.assertIn(
            "$.offline_parallel_evidence_lanes.lanes[0].runner_must_not_execute_lane",
            action_result["offline_parallel_evidence_lanes_misconfiguration_paths"],
        )
        self.assertIn(
            "$.offline_parallel_evidence_lanes.lanes[0].runner_must_not_execute_lane",
            report["offline_parallel_evidence_lanes"]["lane_misconfiguration_paths"],
        )
        self.assertEqual(report["offline_parallel_evidence_lanes"]["lane_count"], 4)
        self.assertFalse(report["offline_parallel_evidence_lanes"]["runner_executes_parallel_lanes"])
        self.assertEqual(report["eligible_count"], 0)
        self.assertFalse(report["approved_runtime_evidence"])

    def test_runner_preserves_exact_triplet_bundle_route_and_blocks_partial_live_like_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            route = exact_triplet_bundle_route_payload()
            write_json(
                plan,
                plan_payload(
                    extra_action={
                        "id": "wait_for_active_player_principal_lifecycle_window_exact_triplet_or_end",
                        "action": "wait_for_active_player_principal_lifecycle_window_exact_triplet_or_end",
                        "action_kind": "active_runtime_window_waiting_for_exact_triplet",
                        "items": ["session_start", "session_end"],
                        "role": "session_start",
                        "exact_triplet_bundle_route": route,
                        "next_action_target": "exact_copied_lifecycle_triplet_bundle",
                        "first_missing_runtime_evidence_path": "copied-lifecycle-triplet/HandleNewPlayer(1,1)",
                        "fastest_missing_role_artifact_path": route["fastest_missing_role_artifact_path"],
                        "runner_command_available": False,
                        "writes_under_evidence_dir": False,
                        "authorized_by_this_report": False,
                        "counts_as_approved_runtime_evidence": False,
                        "partial_lifecycle_material_counts_as_approved_runtime_evidence": False,
                        "copied_log_presence_counts_as_approved_runtime_evidence": False,
                        "direct_discord_send_counts_as_approved_runtime_evidence": False,
                        "active_notice_state_counts_as_approved_runtime_evidence": False,
                        "diagnostic_samples_count_as_approved_runtime_evidence": False,
                    },
                ),
            )

            result = run_script("--plan-json", str(plan), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        action = report["results"][0]
        self.assertIn(
            "active_runtime_window_waiting_for_exact_triplet_not_runner",
            action["blockers"],
        )
        self.assertEqual(action["next_action_target"], "exact_copied_lifecycle_triplet_bundle")
        self.assertEqual(
            action["first_missing_runtime_evidence_path"],
            "copied-lifecycle-triplet/HandleNewPlayer(1,1)",
        )
        self.assertEqual(
            action["exact_triplet_bundle_route"]["accepted_lifecycle_event_roles"],
            ["session_start_rejected"],
        )
        self.assertFalse(action["partial_lifecycle_material_counts_as_approved_runtime_evidence"])
        self.assertFalse(action["copied_log_presence_counts_as_approved_runtime_evidence"])
        self.assertFalse(action["direct_discord_send_counts_as_approved_runtime_evidence"])
        self.assertFalse(action["active_notice_state_counts_as_approved_runtime_evidence"])
        self.assertFalse(action["diagnostic_samples_count_as_approved_runtime_evidence"])
        summary = report["exact_triplet_bundle_runner_summary"]
        self.assertTrue(summary["present"])
        self.assertEqual(summary["first_missing_role"], "session_start")
        self.assertEqual(
            summary["first_missing_runtime_evidence_path"],
            "copied-lifecycle-triplet/HandleNewPlayer(1,1)",
        )
        self.assertFalse(summary["runner_accepts_partial_lifecycle_material_as_evidence"])
        self.assertFalse(summary["runner_accepts_copied_log_presence_as_evidence"])
        self.assertFalse(summary["runner_accepts_direct_discord_send_as_evidence"])
        self.assertFalse(summary["runner_accepts_active_notice_state_as_evidence"])
        self.assertFalse(summary["runner_accepts_diagnostic_samples_as_evidence"])
        self.assertFalse(summary["helper_command_authorized_by_runner"])
        self.assertEqual(report["eligible_count"], 0)
        self.assertFalse(report["approved_runtime_evidence"])


if __name__ == "__main__":
    unittest.main()
