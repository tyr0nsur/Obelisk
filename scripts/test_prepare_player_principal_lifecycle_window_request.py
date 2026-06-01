#!/usr/bin/env python3
"""Tests for prepare_player_principal_lifecycle_window_request.py."""

from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT = SCRIPT_DIR / "prepare_player_principal_lifecycle_window_request.py"
SHA = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
TEST_COMMIT = "1234567890abcdef1234567890abcdef12345678"


def base_args(output_dir: Path) -> list[str]:
    return [
        sys.executable,
        str(SCRIPT),
        "--instance",
        "arkserver2",
        "--map",
        "TheIsland",
        "--run-id",
        "20260601T120000Z-player-principal-lifecycle",
        "--obelisk-commit",
        TEST_COMMIT,
        "--approved-window-start-utc",
        "2026-06-01T12:00:00Z",
        "--approved-window-end-utc",
        "2026-06-01T12:10:00Z",
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
            output_sha256 = {
                filename: hashlib.sha256((output_dir / filename).read_bytes()).hexdigest()
                for filename in (
                    "observer-window.env",
                    "window-request.json",
                    "operator-approval-request.md",
                )
            }

        self.assertEqual(report["status"], "prepared")
        self.assertEqual(report["target"], {"instance": "arkserver2", "map": "TheIsland"})
        self.assertIn("no server operation", report["non_claim"])
        for name, filename in (
            ("observer_env", "observer-window.env"),
            ("request_json", "window-request.json"),
            ("operator_request", "operator-approval-request.md"),
        ):
            self.assertEqual(report["outputs"][name]["path"], str(output_dir / filename))
            self.assertEqual(
                report["outputs"][name]["sha256"],
                output_sha256[filename],
            )
        self.assertEqual(request["schema"], "obelisk.player-principal-lifecycle-window-request.v1")
        self.assertEqual(request["status"], "candidate_only_request_pack")
        self.assertEqual(request["approval_required"], "current-turn operator-approved runtime window, not standing approval")
        self.assertEqual(
            request["copied_log_path"],
            "/servidor/ark/workspace-offline/live-validation-logs/20260601T120000Z-player-principal-lifecycle/Obelisk.log",
        )
        self.assertIn("enable-player-principal-lifecycle-observer", request["marker_set"])
        self.assertIn("enable-reflection-scanner", request["forbidden_markers"])
        self.assertIn("does not claim stable principal identity", request["non_claims"])
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
            bad_window[bad_window.index("--approved-window-start-utc") + 1] = "2026-06-01T12:10:00Z"
            bad_window[bad_window.index("--approved-window-end-utc") + 1] = "2026-06-01T12:00:00Z"
            bad_window_result = subprocess.run(bad_window, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.assertNotEqual(bad_run_result.returncode, 0)
        self.assertIn("--run-id must match", bad_run_result.stderr)
        self.assertNotEqual(bad_window_result.returncode, 0)
        self.assertIn("must be before", bad_window_result.stderr)

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
