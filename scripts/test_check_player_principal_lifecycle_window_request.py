#!/usr/bin/env python3
"""Tests for check_player_principal_lifecycle_window_request.py."""

from __future__ import annotations

import json
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PREPARE = SCRIPT_DIR / "prepare_player_principal_lifecycle_window_request.py"
CHECK = SCRIPT_DIR / "check_player_principal_lifecycle_window_request.py"
TEST_COMMIT = "1" * 40
_FAKE_GIT_DIR = tempfile.TemporaryDirectory()
_FAKE_GIT = Path(_FAKE_GIT_DIR.name) / "git"
_FAKE_GIT.write_text(
    f"""#!/bin/sh
if [ "$1" = "rev-parse" ]; then
  printf '%s\\n' "{TEST_COMMIT}"
  exit 0
fi
if [ "$1" = "cat-file" ] && [ "$2" = "-e" ]; then
  commit="$3"
  commit="${{commit%%^*}}"
  if [ "$commit" = "{TEST_COMMIT}" ]; then
    exit 0
  fi
fi
exit 1
""",
    encoding="utf-8",
)
_FAKE_GIT.chmod(0o755)
_FAKE_GIT_ENV = {
    **os.environ,
    "PATH": f"{_FAKE_GIT_DIR.name}{os.pathsep}{os.environ['PATH']}",
}

sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("check_player_principal_lifecycle_window_request", CHECK)
assert SPEC is not None and SPEC.loader is not None
REQUEST_CHECKER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = REQUEST_CHECKER
SPEC.loader.exec_module(REQUEST_CHECKER)
from prepare_player_principal_lifecycle_window_request import (  # noqa: E402
    AUTHORIZATION_FLAGS,
    EXPECTED_BINARY_SHA256,
    operator_approval_receipt_payload,
)


SHA = EXPECTED_BINARY_SHA256


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
        env=_FAKE_GIT_ENV,
    )


def add_seconds(timestamp: str, seconds: int) -> str:
    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(timezone.utc)
    return (dt + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_completed_receipt(
    output_dir: Path,
    receipt_path: Path | None = None,
    *,
    approved_at_utc: str | None = None,
) -> Path:
    request_path = output_dir / "window-request.json"
    env_path = output_dir / "observer-window.env"
    operator_request_path = output_dir / "operator-approval-request.md"
    request = json.loads(request_path.read_text(encoding="utf-8"))
    approval_time = approved_at_utc or add_seconds(request["prepared_at_utc"], 1)
    receipt = operator_approval_receipt_payload(
        request,
        request_json_path=request_path,
        request_md_path=operator_request_path,
        env_path=env_path,
        operator_approved=True,
        operator_reference="operator",
        approved_at_utc=approval_time,
    )
    path = receipt_path or (output_dir / "operator-approval-receipt.json")
    path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
    return path


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
            env=_FAKE_GIT_ENV,
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
        self.assertFalse(report["stable_claim_allowed"])
        self.assertFalse(report["request_pack_counts_as_approved_runtime_evidence"])
        self.assertEqual(report["next_blocker"], "operator_current_turn_runtime_window_approval_required")
        self.assertRegex(request["prepared_at_utc"], r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
        self.assertLess(request["prepared_at_utc"], request["approved_window"]["start_utc"])
        self.assertEqual(AUTHORIZATION_FLAGS, request["authorization_flags"])
        self.assertTrue(report["operator_request_verified"])
        self.assertFalse(report["operator_approval_receipt_verified"])
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
        self.assertEqual(
            request["post_window_replay_contract"]["sidecars"]["request_pack_path"],
            brief["evidence_capture"]["request_pack_path"],
        )
        self.assertEqual(
            request["post_window_replay_contract"]["sidecars"]["observer_env_path"],
            brief["evidence_capture"]["observer_env_path"],
        )
        self.assertEqual(
            request["post_window_replay_contract"]["sidecars"]["operator_approval_request_path"],
            brief["evidence_capture"]["operator_approval_request_path"],
        )
        self.assertEqual(
            request["post_window_replay_contract"]["sidecars"]["preflight_pre_path"],
            brief["evidence_capture"]["preflight_pre_path"],
        )
        self.assertEqual(
            request["post_window_replay_contract"]["sidecars"]["preflight_post_path"],
            brief["evidence_capture"]["preflight_post_path"],
        )
        self.assertEqual(request["run_id"], brief["artifact_binding"]["run_id"])
        self.assertEqual(
            request["post_window_replay_contract"]["sidecars"]["window_manifest_path"],
            brief["artifact_binding"]["required_sidecars"]["window_manifest_env"],
        )
        self.assertEqual(
            request["post_window_replay_contract"]["sidecars"]["operator_approval_request_path"],
            brief["artifact_binding"]["required_sidecars"]["operator_approval_request_md"],
        )
        self.assertEqual(
            request["post_window_replay_contract"]["sidecars"]["copied_log_path"],
            brief["artifact_binding"]["required_sidecars"]["copied_obelisk_log"],
        )
        self.assertEqual("exact_run_id_window_artifacts_only", brief["artifact_binding"]["binding_claim"])
        self.assertEqual("completed_operator_receipt", brief["evidence_capture"]["operator_approval_receipt_required"])
        self.assertIn("does not authorize server operations, marker/env changes", brief["non_authorization"])
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

    def test_rejects_authorization_flags_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["authorization_flags"]["runtime_work_authorized"] = True
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("authorization_flags_mismatch", report["blockers"])
        self.assertIn("authorization_flag_runtime_work_authorized_not_false", report["blockers"])

    def test_rejects_operator_live_ops_brief_artifact_binding_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["operator_live_ops_brief"]["artifact_binding"]["required_sidecars"][
                "preflight_post_json"
            ] = "/servidor/ark/workspace-offline/live-validation-logs/other/preflight-post.json"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operator_live_ops_brief_artifact_binding_mismatch", report["blockers"])
        self.assertIn("operator_live_ops_brief_mismatch", report["blockers"])

    def test_rejects_operator_live_ops_brief_template_receipt_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["operator_live_ops_brief"]["evidence_capture"][
                "operator_approval_receipt_required"
            ] = "generated_template"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operator_live_ops_brief_receipt_required_not_completed_receipt", report["blockers"])
        self.assertIn("operator_live_ops_brief_mismatch", report["blockers"])

    def test_rejects_operator_live_ops_brief_runtime_authorization_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["operator_live_ops_brief"]["non_authorization"] = "brief says runtime work authorized"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operator_live_ops_brief_non_authorization_mismatch", report["blockers"])
        self.assertIn("forbidden_public_capability_or_readiness_claim", report["blockers"])

    def test_rejects_request_pack_approved_runtime_evidence_text_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["operator_live_ops_brief"]["non_authorization"] = (
                "request pack counts as approved runtime evidence"
            )
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operator_live_ops_brief_non_authorization_mismatch", report["blockers"])
        self.assertIn("forbidden_public_capability_or_readiness_claim", report["blockers"])

    def test_rejects_request_pack_missing_prepared_at_utc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request.pop("prepared_at_utc")
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_missing_required", report["blockers"])
        self.assertIn("prepared_at_utc_not_string", report["blockers"])

    def test_rejects_request_pack_prepared_too_far_before_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            start = datetime.fromisoformat(
                request["approved_window"]["start_utc"].replace("Z", "+00:00")
            ).astimezone(timezone.utc)
            request["prepared_at_utc"] = (start - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
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
        self.assertIn("prepared_at_utc_too_far_before_approved_window", report["blockers"])
        self.assertFalse(report["runtime_work_authorized"])

    def test_rejects_request_pack_prepared_in_future(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            start = datetime.fromisoformat(
                request["approved_window"]["start_utc"].replace("Z", "+00:00")
            ).astimezone(timezone.utc)
            request["prepared_at_utc"] = (start - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
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
        self.assertIn("prepared_at_utc_in_future", report["blockers"])

    def test_rejects_receipt_approved_before_request_prepared(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            receipt_path = write_completed_receipt(output_dir, approved_at_utc="2026-06-01T00:00:00Z")
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertIn("operator_approval_receipt_approved_before_request_prepared", report["blockers"])

    def test_rejects_receipt_approved_at_request_prepared(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request = json.loads((output_dir / "window-request.json").read_text(encoding="utf-8"))
            receipt_path = write_completed_receipt(
                output_dir,
                approved_at_utc=request["prepared_at_utc"],
            )
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertIn("operator_approval_receipt_approved_before_request_prepared", report["blockers"])

    def test_rejects_receipt_approved_at_or_after_window_start(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request = json.loads((output_dir / "window-request.json").read_text(encoding="utf-8"))
            receipt_path = write_completed_receipt(
                output_dir,
                approved_at_utc=request["approved_window"]["start_utc"],
            )
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertIn("operator_approval_receipt_approved_at_or_after_window_start", report["blockers"])

    def test_rejects_receipt_approved_too_far_before_window_start(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request = json.loads((output_dir / "window-request.json").read_text(encoding="utf-8"))
            start = datetime.fromisoformat(
                request["approved_window"]["start_utc"].replace("Z", "+00:00")
            ).astimezone(timezone.utc)
            receipt_path = write_completed_receipt(
                output_dir,
                approved_at_utc=(start - timedelta(minutes=11)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertIn("operator_approval_receipt_approved_too_far_before_window_start", report["blockers"])

    def test_rejects_receipt_approved_in_future(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request = json.loads((output_dir / "window-request.json").read_text(encoding="utf-8"))
            start = datetime.fromisoformat(
                request["approved_window"]["start_utc"].replace("Z", "+00:00")
            ).astimezone(timezone.utc)
            receipt_path = write_completed_receipt(
                output_dir,
                approved_at_utc=(start - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertIn("operator_approval_receipt_approved_in_future", report["blockers"])

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
        self.assertIn("post_window_replay_contract_observer_env_path_not_exact_expected_path", report["blockers"])

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
        self.assertIn(
            "post_window_replay_contract_operator_approval_receipt_path_not_exact_expected_path",
            report["blockers"],
        )

    def test_rejects_post_window_replay_contract_sidecar_in_wrong_run_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["post_window_replay_contract"]["sidecars"]["preflight_post_path"] = (
                "/servidor/ark/workspace-offline/live-validation-logs/"
                f"{request['run_id']}-other/preflight-post.json"
            )
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
            "post_window_replay_contract_preflight_post_path_not_exact_expected_path",
            report["blockers"],
        )

    def test_rejects_post_window_replay_contract_missing_bound_operator_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["post_window_replay_contract"]["sidecars"].pop("operator_approval_request_path")
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("post_window_replay_contract_sidecars_missing_required", report["blockers"])
        self.assertIn("post_window_replay_contract_mismatch", report["blockers"])
        self.assertIn("operator_request_markdown_projection_failed", report["blockers"])

    def test_post_window_replay_rejects_window_not_completed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            receipt_path = write_completed_receipt(output_dir)
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["ready"])
        self.assertIn("post_window_replay_window_not_completed", report["blockers"])

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
            request["prepared_at_utc"] = "2025-12-31T23:55:00Z"
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
            receipt_path = write_completed_receipt(output_dir, approved_at_utc="2025-12-31T23:56:00Z")
            result = self.run_checker(
                output_dir,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["ready"])
        self.assertTrue(report["post_window_replay"])
        self.assertTrue(report["post_window_replay_expiry_tolerated"])
        self.assertTrue(report["operator_approval_receipt_verified"])
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
            request["prepared_at_utc"] = "2025-12-31T23:55:00Z"
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
            receipt_path = write_completed_receipt(output_dir, approved_at_utc="2025-12-31T23:56:00Z")
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["ready"])
        self.assertFalse(report["post_window_replay_expiry_tolerated"])
        self.assertIn("approved_window_expired", report["blockers"])
        self.assertIn("operator_request_markdown_mismatch", report["blockers"])

    def test_post_window_replay_requires_completed_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            result = self.run_checker(output_dir, check=False, extra_args=["--post-window-replay"])
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertIn("operator_approval_receipt_required_for_post_window_replay", report["blockers"])

    def test_post_window_replay_rejects_generated_receipt_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            receipt_path = output_dir / "operator-approval-receipt.json"
            receipt_path.write_text(
                (output_dir / "operator-approval-receipt.template.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertIn("operator_approval_receipt_generated_template_not_completed_receipt", report["blockers"])
        self.assertIn("operator_approval_receipt_status_not_completed", report["blockers"])

    def test_rejects_operator_approval_receipt_runtime_readiness_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            receipt_path = write_completed_receipt(output_dir)
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["operator_completion"]["approved_by_role"] = "operator runtime ready"
            receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertIn(
            "operator_approval_receipt_forbidden_public_capability_or_readiness_claim",
            report["blockers"],
        )

    def test_rejects_operator_approval_receipt_server_restart_authorization_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            receipt_path = write_completed_receipt(output_dir)
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["operator_completion"]["approved_by_role"] = "operator server restart authorized"
            receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertIn(
            "operator_approval_receipt_forbidden_public_capability_or_readiness_claim",
            report["blockers"],
        )

    def test_rejects_operator_approval_receipt_complete_sdk_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            receipt_path = write_completed_receipt(output_dir)
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["operator_completion"]["approved_by_role"] = "operator complete SDK claim"
            receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertIn(
            "operator_approval_receipt_forbidden_public_capability_or_readiness_claim",
            report["blockers"],
        )

    def test_rejects_operator_approval_receipt_approved_runtime_evidence_text_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            receipt_path = write_completed_receipt(output_dir)
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["operator_completion"]["approved_by_role"] = (
                "completed receipt counts as approved runtime evidence"
            )
            receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertIn(
            "operator_approval_receipt_forbidden_public_capability_or_readiness_claim",
            report["blockers"],
        )

    def test_nested_receipt_shape_blocker_clears_receipt_verified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            receipt_path = write_completed_receipt(output_dir)
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["approval_scope"]["unexpected_runtime_authorization_note"] = False
            receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertIn("operator_approval_receipt_scope_unexpected_keys", report["blockers"])

    def test_rejects_completed_receipt_without_post_window_replay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            receipt_path = write_completed_receipt(output_dir)
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["ready"])
        self.assertFalse(report["post_window_replay"])
        self.assertFalse(report["post_window_replay_expiry_tolerated"])
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertIn("operator_approval_receipt_requires_post_window_replay", report["blockers"])

    def test_rejects_receipt_replay_across_request_pack_bindings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            other_dir = Path(tmp) / "other-request"
            other_dir.mkdir()
            prepare_pack(output_dir)
            receipt_path = write_completed_receipt(output_dir)
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["bound_request_pack"]["run_id"] = "20260101T000000Z-player-principal-lifecycle"
            receipt["bound_request_pack"]["final_posture"] = "stopped"
            receipt["bound_artifacts"]["observer_window_env"]["sha256"] = "0" * 64
            receipt["bound_artifacts"]["operator_approval_request_md"]["sha256"] = "0" * 64
            receipt["request_pack_digest"]["sha256"] = "0" * 64
            replayed_receipt_path = other_dir / "operator-approval-receipt.json"
            replayed_receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--operator-approval-receipt", str(replayed_receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_approval_receipt_verified"])
        for reason in (
            "operator_approval_receipt_not_sibling_of_request_json",
            "operator_approval_receipt_run_id_mismatch",
            "operator_approval_receipt_final_posture_mismatch",
            "operator_approval_receipt_observer_window_env_artifact_mismatch",
            "operator_approval_receipt_operator_approval_request_md_artifact_mismatch",
            "operator_approval_receipt_digest_mismatch",
        ):
            self.assertIn(reason, report["blockers"])

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
        details = {
            item["reason"]: item
            for item in report["blocker_details"]
            if item["reason"] == "approved_window_already_started"
        }
        self.assertEqual("already_started", details["approved_window_already_started"]["stale_condition"])

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
        details = {
            item["reason"]: item
            for item in report["blocker_details"]
            if item["reason"] == "approved_window_expired"
        }
        self.assertEqual("expired", details["approved_window_expired"]["stale_condition"])

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

    def test_rejects_runtime_evidence_claim_source_aliases(self) -> None:
        for text in (
            "window request counts as approved runtime evidence",
            "operator approval request proves approved runtime evidence",
            "observer window env is approved runtime evidence",
            "source marker counts as approved runtime evidence",
        ):
            with self.subTest(text=text):
                self.assertTrue(REQUEST_CHECKER.contains_unnegated_positive_capability_claim(text))

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

    def test_rejects_nonexistent_forty_hex_obelisk_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["obelisk_commit"] = "a" * 40
            request_path.write_text(json.dumps(request), encoding="utf-8")

            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("obelisk_commit_invalid", report["blockers"])


if __name__ == "__main__":
    unittest.main()
