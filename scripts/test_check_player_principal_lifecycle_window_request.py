#!/usr/bin/env python3
"""Tests for check_player_principal_lifecycle_window_request.py."""

from __future__ import annotations

import json
import importlib.util
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

sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("check_player_principal_lifecycle_window_request", CHECK)
assert SPEC is not None and SPEC.loader is not None
REQUEST_CHECKER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = REQUEST_CHECKER
SPEC.loader.exec_module(REQUEST_CHECKER)


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
    def run_checker(
        self,
        output_dir: Path,
        *,
        check: bool = True,
        extra_args: list[str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [
                sys.executable,
                str(CHECK),
                str(output_dir / "window-request.json"),
                "--env-file",
                str(output_dir / "observer-window.env"),
                *(extra_args or []),
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
            request = json.loads((output_dir / "window-request.json").read_text(encoding="utf-8"))

        self.assertTrue(report["ready"])
        self.assertTrue(report["request_pack_ready"])
        self.assertTrue(report["planning_only"])
        self.assertFalse(report["server_operations_authorized"])
        self.assertFalse(report["runtime_work_authorized"])
        self.assertFalse(report["publication_authorized"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["v1_completion_ready"])
        self.assertEqual(report["next_blocker"], "operator_current_turn_runtime_window_approval_required")
        self.assertTrue(report["operator_request_verified"])
        self.assertEqual(report["target"], {"instance": "arkserver2", "map": "TheIsland"})
        self.assertIn("does not authorize server operations", report["non_claims"][1])
        brief = request["operator_live_ops_brief"]
        self.assertEqual({"instance": "arkserver2", "map": "TheIsland"}, brief["target"])
        self.assertEqual(SHA, brief["server_binary"]["sha256"])
        self.assertEqual("player_principal_lifecycle_only", brief["feature_gates"]["observer"])
        self.assertEqual(0, brief["feature_gates"]["dispatch_limit"])
        self.assertEqual(10, brief["feature_gates"]["log_limit"])
        self.assertEqual("stable", brief["post_run_stable_posture"]["expected"])
        self.assertEqual(
            request["post_window_replay_contract"]["sidecars"]["operator_approval_receipt_path"],
            brief["evidence_capture"]["operator_approval_receipt_path"],
        )
        self.assertEqual("completed_operator_receipt", brief["evidence_capture"]["operator_approval_receipt_required"])
        self.assertEqual(
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
            brief["post_run_stable_posture"]["verification_commands"],
        )

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
        self.assertIn("operator_live_ops_brief_mismatch", report["blockers"])

    def test_rejects_operator_live_ops_brief_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["operator_live_ops_brief"]["feature_gates"]["dispatch_limit"] = 1
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operator_live_ops_brief_mismatch", report["blockers"])

    def test_rejects_operator_request_markdown_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            markdown_path = output_dir / "operator-approval-request.md"
            markdown_path.write_text(
                markdown_path.read_text(encoding="utf-8").replace("dispatch limit=0", "dispatch limit=1"),
                encoding="utf-8",
            )
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_request_verified"])
        self.assertIn("operator_request_markdown_mismatch", report["blockers"])

    def test_rejects_missing_post_window_replay_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request.pop("post_window_replay_contract")
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_missing_required", report["blockers"])

    def test_rejects_post_window_replay_contract_path_outside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["post_window_replay_contract"]["sidecars"]["observer_env_path"] = "/tmp/observer-window.env"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            (output_dir / "operator-approval-request.md").write_text(
                REQUEST_CHECKER.markdown_request(
                    request,
                    (output_dir / "observer-window.env").read_text(encoding="utf-8").splitlines(),
                ),
                encoding="utf-8",
            )
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("post_window_replay_contract_mismatch", report["blockers"])
        self.assertIn("post_window_replay_contract_observer_env_path_not_approved_offline_workspace", report["blockers"])

    def test_rejects_post_window_replay_contract_receipt_path_outside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["post_window_replay_contract"]["sidecars"][
                "operator_approval_receipt_path"
            ] = "/tmp/operator-approval-receipt.json"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            (output_dir / "operator-approval-request.md").write_text(
                REQUEST_CHECKER.markdown_request(
                    request,
                    (output_dir / "observer-window.env").read_text(encoding="utf-8").splitlines(),
                ),
                encoding="utf-8",
            )
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("post_window_replay_contract_mismatch", report["blockers"])
        self.assertIn(
            "post_window_replay_contract_operator_approval_receipt_path_not_approved_offline_workspace",
            report["blockers"],
        )

    def test_post_window_replay_tolerates_expired_window_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            old_run_id = request["run_id"]
            request = json.loads(json.dumps(request).replace(old_run_id, "20260101T000000Z-player-principal-lifecycle"))
            request["approved_window"]["start_utc"] = "2026-01-01T00:00:00Z"
            request["approved_window"]["end_utc"] = "2026-01-01T00:10:00Z"
            request["run_id"] = "20260101T000000Z-player-principal-lifecycle"
            request["operator_live_ops_brief"]["start_restart_stop_window"]["start_utc"] = "2026-01-01T00:00:00Z"
            request["operator_live_ops_brief"]["start_restart_stop_window"]["end_utc"] = "2026-01-01T00:10:00Z"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            (output_dir / "observer-window.env").write_text(
                "\n".join(REQUEST_CHECKER.env_lines(REQUEST_CHECKER.args_for_env(request))) + "\n",
                encoding="utf-8",
            )
            (output_dir / "operator-approval-request.md").write_text(
                REQUEST_CHECKER.markdown_request(
                    request,
                    (output_dir / "observer-window.env").read_text(encoding="utf-8").splitlines(),
                ),
                encoding="utf-8",
            )
            result = self.run_checker(output_dir, extra_args=["--post-window-replay"])
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["ready"])
        self.assertTrue(report["post_window_replay"])
        self.assertTrue(report["post_window_replay_expiry_tolerated"])
        self.assertEqual([], report["blockers"])

    def test_post_window_replay_rejects_expired_window_plus_markdown_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            old_run_id = request["run_id"]
            request = json.loads(json.dumps(request).replace(old_run_id, "20260101T000000Z-player-principal-lifecycle"))
            request["approved_window"]["start_utc"] = "2026-01-01T00:00:00Z"
            request["approved_window"]["end_utc"] = "2026-01-01T00:10:00Z"
            request["run_id"] = "20260101T000000Z-player-principal-lifecycle"
            request["operator_live_ops_brief"]["start_restart_stop_window"]["start_utc"] = "2026-01-01T00:00:00Z"
            request["operator_live_ops_brief"]["start_restart_stop_window"]["end_utc"] = "2026-01-01T00:10:00Z"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            (output_dir / "observer-window.env").write_text(
                "\n".join(REQUEST_CHECKER.env_lines(REQUEST_CHECKER.args_for_env(request))) + "\n",
                encoding="utf-8",
            )
            markdown_path = output_dir / "operator-approval-request.md"
            markdown_path.write_text(
                REQUEST_CHECKER.markdown_request(
                    request,
                    (output_dir / "observer-window.env").read_text(encoding="utf-8").splitlines(),
                ).replace("dispatch limit=0", "dispatch limit=1"),
                encoding="utf-8",
            )
            result = self.run_checker(output_dir, check=False, extra_args=["--post-window-replay"])
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["ready"])
        self.assertFalse(report["post_window_replay_expiry_tolerated"])
        self.assertIn("approved_window_expired", report["blockers"])
        self.assertIn("operator_request_markdown_mismatch", report["blockers"])

    def test_rejects_missing_operator_request_markdown_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            (output_dir / "operator-approval-request.md").unlink()
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_request_verified"])
        self.assertIn("operator_request_unreadable", report["blockers"])

    def test_rejects_env_file_from_different_request_pack_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            other_output_dir = Path(tmp) / "other-request"
            prepare_pack(output_dir)
            prepare_pack(other_output_dir)
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--env-file", str(other_output_dir / "observer-window.env")],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("env_file_not_sibling_of_request_json", report["blockers"])

    def test_rejects_operator_request_from_different_request_pack_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            other_output_dir = Path(tmp) / "other-request"
            prepare_pack(output_dir)
            other_output_dir.mkdir()
            (other_output_dir / "operator-approval-request.md").write_text(
                (output_dir / "operator-approval-request.md").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--operator-request", str(other_output_dir / "operator-approval-request.md")],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_request_verified"])
        self.assertIn("operator_request_not_sibling_of_request_json", report["blockers"])

    def test_rejects_already_started_approved_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            start = (datetime.now(timezone.utc) - timedelta(seconds=60)).replace(microsecond=0)
            end = (datetime.now(timezone.utc) + timedelta(minutes=5)).replace(microsecond=0)
            request["run_id"] = start.strftime("%Y%m%dT%H%M%SZ") + "-player-principal-lifecycle"
            request["approved_window"]["start_utc"] = start.strftime("%Y-%m-%dT%H:%M:%SZ")
            request["approved_window"]["end_utc"] = end.strftime("%Y-%m-%dT%H:%M:%SZ")
            request_path.write_text(json.dumps(request), encoding="utf-8")
            markdown_path = output_dir / "operator-approval-request.md"
            markdown_path.write_text(
                REQUEST_CHECKER.markdown_request(
                    request,
                    (output_dir / "observer-window.env").read_text(encoding="utf-8").splitlines(),
                ),
                encoding="utf-8",
            )
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("approved_window_already_started", report["blockers"])
        self.assertNotIn("approved_window_expired", report["blockers"])

    def test_rejects_post_run_verification_command_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["operator_live_ops_brief"]["post_run_stable_posture"]["verification_commands"][0][2] = "arkserver3"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operator_live_ops_brief_mismatch", report["blockers"])

    def test_rejects_restart_final_posture_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["restart_expectation"] = "stop-after-window"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("restart_expectation_final_posture_mismatch", report["blockers"])

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

    def test_rejects_approved_window_duration_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            start = datetime.strptime(
                request["approved_window"]["start_utc"],
                "%Y-%m-%dT%H:%M:%SZ",
            ).replace(tzinfo=timezone.utc)
            request["approved_window"]["end_utc"] = (start + timedelta(minutes=11)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("approved_window_duration_too_long", report["blockers"])
        self.assertEqual(report["next_blocker"], "request_pack_not_accepted")

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

    def test_accepts_negated_private_or_ue_boundary_text(self) -> None:
        blockers: list[dict[str, object]] = []
        REQUEST_CHECKER.validate_secret_free(
            {
                "privacy_boundary": [
                    "must not expose raw_params",
                    "do not log player_id",
                    "does not capture player_id",
                    "does not collect player_id",
                    "does not record raw_params",
                    "never report ue_pointer values",
                    "forbidden: raw_params",
                    "without fname_index output",
                ]
            },
            blockers,
        )

        self.assertEqual([], blockers)

    def test_rejects_unnegated_private_or_ue_boundary_text(self) -> None:
        blockers: list[dict[str, object]] = []
        REQUEST_CHECKER.validate_secret_free(
            {
                "privacy_boundary": [
                    "logs raw_params",
                    "captures player_id",
                ]
            },
            blockers,
        )

        self.assertEqual(["forbidden_private_or_ue_value", "forbidden_private_or_ue_value"], [
            item["reason"] for item in blockers
        ])

    def test_rejects_mixed_negated_and_unnegated_private_or_ue_text(self) -> None:
        blockers: list[dict[str, object]] = []
        REQUEST_CHECKER.validate_secret_free(
            {"privacy_boundary": "must not expose raw_params; captures player_id"},
            blockers,
        )

        self.assertEqual(["forbidden_private_or_ue_value"], [item["reason"] for item in blockers])

    def test_rejects_mixed_negation_with_but_then_private_or_ue_text(self) -> None:
        for text in (
            "must not expose raw_params but captures player_id",
            "does not record raw_params then captures player_id",
        ):
            with self.subTest(text=text):
                blockers: list[dict[str, object]] = []
                REQUEST_CHECKER.validate_secret_free({"privacy_boundary": text}, blockers)

                self.assertEqual(["forbidden_private_or_ue_value"], [item["reason"] for item in blockers])

    def test_rejects_mixed_negation_with_but_runtime_readiness_claim(self) -> None:
        self.assertTrue(
            REQUEST_CHECKER.contains_unnegated_positive_capability_claim(
                "does not authorize runtime readiness but runtime ready"
            )
        )

    def test_accepts_negated_runtime_readiness_suffix_claims(self) -> None:
        for text in ("runtime readiness remains blocked", "runtime ready remains blocked"):
            with self.subTest(text=text):
                self.assertFalse(REQUEST_CHECKER.contains_unnegated_positive_capability_claim(text))

    def test_rejects_blocked_prefix_as_private_or_ue_negation(self) -> None:
        blockers: list[dict[str, object]] = []
        REQUEST_CHECKER.validate_secret_free(
            {"privacy_boundary": "blocked player_id raw_params"},
            blockers,
        )

        self.assertEqual(["forbidden_private_or_ue_value"], [item["reason"] for item in blockers])

    def test_rejects_blocked_prefix_as_runtime_readiness_negation_in_request_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["user_policy"] = "operator_approved_beta_users"
            request["notice_path"] = "blocked runtime readiness enabled"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
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
