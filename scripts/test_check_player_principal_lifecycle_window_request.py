#!/usr/bin/env python3
"""Tests for check_player_principal_lifecycle_window_request.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PREPARE = SCRIPT_DIR / "prepare_player_principal_lifecycle_window_request.py"
CHECK = SCRIPT_DIR / "check_player_principal_lifecycle_window_request.py"
SHA = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
TEST_COMMIT = "1234567890abcdef1234567890abcdef12345678"


def prepare_args(output_dir: Path) -> list[str]:
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    end = start + timedelta(minutes=10)
    run_id = start.strftime("%Y%m%dT%H%M%SZ") + "-player-principal-lifecycle"
    return [
        sys.executable,
        str(PREPARE),
        "--instance",
        "arkserver2",
        "--map",
        "TheIsland",
        "--run-id",
        run_id,
        "--obelisk-commit",
        TEST_COMMIT,
        "--approved-window-start-utc",
        start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "--approved-window-end-utc",
        end.strftime("%Y-%m-%dT%H:%M:%SZ"),
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


def prepare_pack(output_dir: Path) -> None:
    subprocess.run(
        prepare_args(output_dir),
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class CheckPlayerPrincipalLifecycleWindowRequestTests(unittest.TestCase):
    def run_checker(self, output_dir: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [
                sys.executable,
                str(CHECK),
                str(output_dir / "window-request.json"),
                "--env-file",
                str(output_dir / "observer-window.env"),
                "--json",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if check and result.returncode != 0:
            self.fail(f"checker failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def test_accepts_prepared_request_pack_without_authorizing_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            result = self.run_checker(output_dir)
            report = json.loads(result.stdout)

        self.assertTrue(report["ready"])
        self.assertTrue(report["request_pack_ready"])
        self.assertEqual(report["next_blocker"], "operator_current_turn_runtime_window_approval_required")
        self.assertEqual(report["target"], {"instance": "arkserver2", "map": "TheIsland"})
        self.assertIn("does not authorize server operations", report["non_claims"][1])

    def test_rejects_env_snapshot_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            env_path = output_dir / "observer-window.env"
            env_path.write_text(
                env_path.read_text(encoding="utf-8").replace(
                    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0",
                    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=1",
                ),
                encoding="utf-8",
            )
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("observer_env_snapshot_mismatch", report["blockers"])
        self.assertIn("observer_env_required_key_missing_or_mismatch", report["blockers"])

    def test_rejects_nested_live_validation_alias_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["copied_log_path"] = (
                "/servidor/ark/workspace-offline/tmp/live-validation-logs/"
                f"{request['run_id']}/Obelisk.log"
            )
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("copied_log_path_not_exact_expected_path", report["blockers"])

    def test_rejects_run_id_window_start_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            start = datetime.strptime(
                request["approved_window"]["start_utc"],
                "%Y-%m-%dT%H:%M:%SZ",
            ).replace(tzinfo=timezone.utc)
            request["approved_window"]["start_utc"] = (start + timedelta(minutes=1)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("run_id_window_start_mismatch", report["blockers"])

    def test_rejects_expired_approved_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["approved_window"]["start_utc"] = "2026-01-01T12:00:00Z"
            request["approved_window"]["end_utc"] = "2026-01-01T12:10:00Z"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("approved_window_expired", report["blockers"])

    def test_rejects_beta_policy_without_notice_and_public_readiness_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["user_policy"] = "operator_approved_beta_users"
            request["notice_path"] = "not_applicable"
            request["approval_required"] = "does not authorize server operations; public SDK ready"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("beta_user_policy_requires_notice_path", report["blockers"])
        self.assertIn("approval_required_mismatch", report["blockers"])
        self.assertIn("forbidden_public_capability_or_readiness_claim", report["blockers"])

    def test_rejects_live_server_request_path(self) -> None:
        live_result = subprocess.run(
            [
                sys.executable,
                str(CHECK),
                "/servidor/ark/obelisk/window-request.json",
                "--env-file",
                "/servidor/ark/obelisk/observer-window.env",
                "--json",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertNotEqual(live_result.returncode, 0)
        self.assertIn("must not read from protected server root", live_result.stderr)

    def test_rejects_placeholder_obelisk_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["obelisk_commit"] = "reviewed-obelisk-commit"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("obelisk_commit_invalid", report["blockers"])


if __name__ == "__main__":
    unittest.main()
