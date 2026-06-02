#!/usr/bin/env python3
"""Tests for prepare_player_principal_lifecycle_window_request.py."""

from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT = SCRIPT_DIR / "prepare_player_principal_lifecycle_window_request.py"
SHA = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
TEST_COMMIT = "1234567890abcdef1234567890abcdef12345678"


def future_window() -> tuple[str, str, str]:
    start = (datetime.now(timezone.utc) + timedelta(hours=1)).replace(microsecond=0)
    end = start + timedelta(minutes=10)
    return (
        start.strftime("%Y%m%dT%H%M%SZ") + "-player-principal-lifecycle",
        start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        end.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def base_args(output_dir: Path) -> list[str]:
    run_id, start, end = future_window()
    return [
        sys.executable,
        str(SCRIPT),
        "--instance",
        "arkserver2",
        "--map",
        "TheIsland",
        "--run-id",
        run_id,
        "--obelisk-commit",
        TEST_COMMIT,
        "--approved-window-start-utc",
        start,
        "--approved-window-end-utc",
        end,
        "--binary-sha256",
        SHA,
        "--restart-expectation",
        "restart",
        "--final-posture",
        "stable",
        "--user-policy",
        "no_regular_users",
        "--rollback-owner",
        "operator",
        "--output-dir",
        str(output_dir),
        "--json",
    ]


class PreparePlayerPrincipalLifecycleWindowRequestTests(unittest.TestCase):
    def test_prepares_secret_free_request_pack_without_authorizing_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            result = subprocess.run(
                base_args(output_dir),
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            report = json.loads(result.stdout)
            request = json.loads((output_dir / "window-request.json").read_text(encoding="utf-8"))
            env = (output_dir / "observer-window.env").read_text(encoding="utf-8").splitlines()
            markdown = (output_dir / "operator-approval-request.md").read_text(encoding="utf-8")
            receipt_template = json.loads(
                (output_dir / "operator-approval-receipt.template.json").read_text(encoding="utf-8")
            )
            output_sha256 = {
                filename: hashlib.sha256((output_dir / filename).read_bytes()).hexdigest()
                for filename in (
                    "observer-window.env",
                    "window-request.json",
                    "operator-approval-request.md",
                    "operator-approval-receipt.template.json",
                )
            }

        self.assertEqual(report["status"], "prepared")
        self.assertEqual(report["target"], {"instance": "arkserver2", "map": "TheIsland"})
        self.assertIn("no server operation", report["non_claim"])
        self.assertTrue(report["planning_only"])
        self.assertFalse(report["server_operations_authorized"])
        self.assertFalse(report["runtime_work_authorized"])
        self.assertFalse(report["publication_authorized"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["v1_completion_ready"])
        for name, filename in (
            ("observer_env", "observer-window.env"),
            ("request_json", "window-request.json"),
            ("operator_request", "operator-approval-request.md"),
            ("operator_approval_receipt_template", "operator-approval-receipt.template.json"),
        ):
            self.assertEqual(report["outputs"][name]["path"], str(output_dir / filename))
            self.assertEqual(
                report["outputs"][name]["sha256"],
                output_sha256[filename],
            )
        self.assertFalse((output_dir / "operator-approval-receipt.json").exists())
        self.assertEqual(
            receipt_template["schema"],
            "obelisk.player-principal-lifecycle-operator-approval-receipt.v1",
        )
        self.assertEqual(receipt_template["status"], "generated_template")
        self.assertFalse(receipt_template["receipt_completed"])
        self.assertFalse(receipt_template["operator_current_turn_approval_recorded"])
        self.assertFalse(receipt_template["approval_scope"]["standing_approval"])
        self.assertFalse(receipt_template["approval_scope"]["reusable"])
        for value in receipt_template["non_authorization_flags"].values():
            self.assertFalse(value)
        self.assertEqual(request["schema"], "obelisk.player-principal-lifecycle-window-request.v1")
        self.assertEqual(request["status"], "candidate_only_request_pack")
        self.assertEqual(request["approval_required"], "current-turn operator-approved runtime window, not standing approval")
        self.assertEqual(request["copied_log_path"], f"/servidor/ark/workspace-offline/live-validation-logs/{request['run_id']}/Obelisk.log")
        replay_contract = request["post_window_replay_contract"]
        self.assertTrue(replay_contract["required"])
        self.assertTrue(replay_contract["offline_only"])
        self.assertEqual(
            replay_contract["sidecars"]["request_pack_path"],
            f"/servidor/ark/workspace-offline/live-validation-logs/{request['run_id']}/window-request.json",
        )
        self.assertEqual(
            replay_contract["sidecars"]["preflight_pre_path"],
            f"/servidor/ark/workspace-offline/live-validation-logs/{request['run_id']}/preflight-pre.json",
        )
        self.assertEqual(
            replay_contract["sidecars"]["operator_approval_receipt_path"],
            f"/servidor/ark/workspace-offline/live-validation-logs/{request['run_id']}/operator-approval-receipt.json",
        )
        self.assertIn("--post-window-replay", replay_contract["checks"]["window_manifest_replay"])
        self.assertIn("does not authorize runtime work", replay_contract["non_authorization"])
        self.assertIn("enable-player-principal-lifecycle-observer", request["marker_set"])
        self.assertIn("enable-reflection-scanner", request["forbidden_markers"])
        self.assertIn("does not claim stable principal identity", request["non_claims"])
        self.assertEqual(
            request["operator_live_ops_brief"]["post_run_stable_posture"]["verification_commands"],
            [
                [
                    "scripts/check_player_principal_lifecycle_preflight.sh",
                    "--instance",
                    "arkserver2",
                    "--map",
                    "TheIsland",
                    "--mode",
                    "stable",
                    "--expected-binary-sha256",
                    SHA,
                ],
                [
                    "scripts/check_obelisk_server_posture.sh",
                    "--expect-stable",
                    "--map",
                    "TheIsland",
                    "--instance",
                    "arkserver2",
                ],
            ],
        )
        self.assertEqual(
            env,
            [
                "OBELISK_INSTANCE_ID=arkserver2",
                "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1",
                "OBELISK_DISABLE_PLUGINS=1",
                "OBELISK_WRAPPER_PROFILE=observer-debug",
                "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1",
                f"OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256={SHA}",
                "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10",
                "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0",
                "OBELISK_PE_TRACE_LIMIT=0",
            ],
        )
        self.assertIn("This is a request pack only. It does not authorize server operations.", markdown)
        self.assertIn("dispatch limit=0", markdown)
        self.assertIn("log limit=10", markdown)
        self.assertIn("Post-window replay contract:", markdown)
        self.assertIn("preflight_pre_path=/servidor/ark/workspace-offline/live-validation-logs/", markdown)
        self.assertIn("operator_approval_receipt_path=/servidor/ark/workspace-offline/live-validation-logs/", markdown)
        self.assertIn("completed operator-approval-receipt.json", markdown)
        self.assertIn("--post-window-replay", markdown)
        self.assertIn(
            "scripts/check_player_principal_lifecycle_preflight.sh --instance arkserver2 --map TheIsland "
            f"--mode stable --expected-binary-sha256 {SHA}",
            markdown,
        )
        self.assertIn(
            "scripts/check_obelisk_server_posture.sh --expect-stable --map TheIsland --instance arkserver2",
            markdown,
        )

    def test_beta_user_policy_requires_notice_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = base_args(Path(tmp) / "request")
            args[args.index("--user-policy") + 1] = "operator_approved_beta_users"
            result = subprocess.run(args, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--notice-path must name the approved notice path", result.stderr)

    def test_rejects_bad_run_id_and_window_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad_run = base_args(Path(tmp) / "bad-run")
            bad_run[bad_run.index("--run-id") + 1] = "latest"
            bad_run_result = subprocess.run(bad_run, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            bad_window = base_args(Path(tmp) / "bad-window")
            start = datetime.now(timezone.utc) + timedelta(hours=1)
            bad_window[bad_window.index("--run-id") + 1] = (
                start.strftime("%Y%m%dT%H%M%SZ") + "-player-principal-lifecycle"
            )
            bad_window[bad_window.index("--approved-window-start-utc") + 1] = start.strftime("%Y-%m-%dT%H:%M:%SZ")
            bad_window[bad_window.index("--approved-window-end-utc") + 1] = (
                start - timedelta(minutes=1)
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
            bad_window_result = subprocess.run(bad_window, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.assertNotEqual(bad_run_result.returncode, 0)
        self.assertIn("--run-id must match", bad_run_result.stderr)
        self.assertNotEqual(bad_window_result.returncode, 0)
        self.assertIn("must be before", bad_window_result.stderr)

    def test_rejects_expired_approved_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = base_args(Path(tmp) / "request")
            args[args.index("--run-id") + 1] = "20260101T120000Z-player-principal-lifecycle"
            args[args.index("--approved-window-start-utc") + 1] = "2026-01-01T12:00:00Z"
            args[args.index("--approved-window-end-utc") + 1] = "2026-01-01T12:10:00Z"
            result = subprocess.run(args, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be in the future", result.stderr)

    def test_rejects_already_started_approved_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = base_args(Path(tmp) / "request")
            start = (datetime.now(timezone.utc) - timedelta(seconds=60)).replace(microsecond=0)
            end = (datetime.now(timezone.utc) + timedelta(minutes=5)).replace(microsecond=0)
            args[args.index("--run-id") + 1] = start.strftime("%Y%m%dT%H%M%SZ") + "-player-principal-lifecycle"
            args[args.index("--approved-window-start-utc") + 1] = start.strftime("%Y-%m-%dT%H:%M:%SZ")
            args[args.index("--approved-window-end-utc") + 1] = end.strftime("%Y-%m-%dT%H:%M:%SZ")
            result = subprocess.run(args, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--approved-window-start-utc must be in the future", result.stderr)

    def test_rejects_run_id_window_start_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = base_args(Path(tmp) / "request")
            args[args.index("--run-id") + 1] = "20260601T120001Z-player-principal-lifecycle"
            result = subprocess.run(args, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must match --approved-window-start-utc exactly", result.stderr)

    def test_rejects_approved_window_longer_than_first_window_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = base_args(Path(tmp) / "request")
            start = datetime.strptime(
                args[args.index("--approved-window-start-utc") + 1],
                "%Y-%m-%dT%H:%M:%SZ",
            ).replace(tzinfo=timezone.utc)
            args[args.index("--approved-window-end-utc") + 1] = (
                start + timedelta(minutes=11)
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
            result = subprocess.run(args, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duration must not exceed 10 minutes", result.stderr)

    def test_rejects_restart_final_posture_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stop_with_stable = base_args(Path(tmp) / "stop-stable")
            stop_with_stable[stop_with_stable.index("--restart-expectation") + 1] = "stop-after-window"
            stop_with_stable_result = subprocess.run(
                stop_with_stable,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            restart_with_stopped = base_args(Path(tmp) / "restart-stopped")
            restart_with_stopped[restart_with_stopped.index("--final-posture") + 1] = "stopped"
            restart_with_stopped_result = subprocess.run(
                restart_with_stopped,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.assertNotEqual(stop_with_stable_result.returncode, 0)
        self.assertIn("stop-after-window requires --final-posture stopped", stop_with_stable_result.stderr)
        self.assertNotEqual(restart_with_stopped_result.returncode, 0)
        self.assertIn("none/start/restart requires --final-posture stable", restart_with_stopped_result.stderr)

    def test_stopped_final_posture_emits_allow_stopped_post_run_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            args = base_args(output_dir)
            args[args.index("--restart-expectation") + 1] = "stop-after-window"
            args[args.index("--final-posture") + 1] = "stopped"
            subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            request = json.loads((output_dir / "window-request.json").read_text(encoding="utf-8"))

        self.assertEqual(
            request["operator_live_ops_brief"]["post_run_stable_posture"]["verification_commands"],
            [
                [
                    "scripts/check_player_principal_lifecycle_preflight.sh",
                    "--instance",
                    "arkserver2",
                    "--map",
                    "TheIsland",
                    "--mode",
                    "stable",
                    "--expected-binary-sha256",
                    SHA,
                    "--allow-stopped",
                ],
            ],
        )

    def test_rejects_wrong_binary_sha_and_live_output_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wrong_sha = base_args(Path(tmp) / "wrong-sha")
            wrong_sha[wrong_sha.index("--binary-sha256") + 1] = "0" * 64
            wrong_sha_result = subprocess.run(wrong_sha, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.assertNotEqual(wrong_sha_result.returncode, 0)
        self.assertIn("must match reviewed ARK SHA256", wrong_sha_result.stderr)

        live_output = base_args(Path("/servidor/ark/obelisk/request-pack"))
        live_output_result = subprocess.run(live_output, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertNotEqual(live_output_result.returncode, 0)
        self.assertIn("must not write under protected server root", live_output_result.stderr)

    def test_rejects_placeholder_obelisk_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = base_args(Path(tmp) / "request")
            args[args.index("--obelisk-commit") + 1] = "test-commit"
            result = subprocess.run(args, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--obelisk-commit must be a reviewed 40-character lowercase Git SHA", result.stderr)


if __name__ == "__main__":
    unittest.main()
