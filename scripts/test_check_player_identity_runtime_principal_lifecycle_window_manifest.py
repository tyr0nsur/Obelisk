#!/usr/bin/env python3
"""Tests for check_player_identity_runtime_principal_lifecycle_window_manifest.py."""

from __future__ import annotations

import json
import hashlib
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT = SCRIPT_DIR / "check_player_identity_runtime_principal_lifecycle_window_manifest.py"

sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("check_player_identity_runtime_principal_lifecycle_window_manifest", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
CHECKER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CHECKER
SPEC.loader.exec_module(CHECKER)
from prepare_player_principal_lifecycle_window_request import (  # noqa: E402
    EXPECTED_SERVER_BINARY_PATH,
    FORBIDDEN_MARKERS,
    NON_CLAIMS,
    WINDOW_MARKERS,
    env_lines,
    markdown_request,
    operator_live_ops_brief,
    operator_approval_receipt_payload,
    post_window_replay_contract,
)
RUN_ID = "20260601T120000Z-player-principal-lifecycle"
COPIED_LOG_TEXT = "copied player principal lifecycle observer log\n"
GOOD_SHA = hashlib.sha256(COPIED_LOG_TEXT.encode("utf-8")).hexdigest()
TEST_COMMIT = "1234567890abcdef1234567890abcdef12345678"
ARK_SHA = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"


def future_window_fields() -> dict[str, str]:
    start = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0)
    capture_start = start + timedelta(minutes=1)
    capture_end = start + timedelta(minutes=8)
    rollback_end = start + timedelta(minutes=10)
    run_id = start.strftime("%Y%m%dT%H%M%SZ") + "-player-principal-lifecycle"
    payload = {
        "run_id": run_id,
        "approved_window_start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "approved_window_end_utc": rollback_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "actual_capture_start_utc": capture_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "actual_capture_end_utc": capture_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rollback_start_utc": capture_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rollback_end_utc": rollback_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return payload


def rewrite_lines_for_window(lines: list[str], fields: dict[str, str]) -> list[str]:
    rewritten = []
    for line in lines:
        if "=" not in line:
            rewritten.append(line)
            continue
        key, value = line.split("=", 1)
        if key in fields:
            value = fields[key]
        value = value.replace(RUN_ID, fields["run_id"])
        rewritten.append(f"{key}={value}")
    return rewritten


def manifest_lines(**overrides: str | None) -> list[str]:
    fields = {
        "run_id": RUN_ID,
        "obelisk_commit": TEST_COMMIT,
        "target": "arkserver2/TheIsland",
        "approval": "current-turn operator-approved runtime window, not standing approval",
        "approved_window_start_utc": "2026-06-01T12:00:00Z",
        "approved_window_end_utc": "2026-06-01T12:10:00Z",
        "actual_capture_start_utc": "2026-06-01T12:01:00Z",
        "actual_capture_end_utc": "2026-06-01T12:09:00Z",
        "copied_log_path": f"live-validation-logs/{RUN_ID}/Obelisk.log",
        "copied_log_sha256": GOOD_SHA,
        "request_pack_path": "window-request.json",
        "request_pack_sha256": "0" * 64,
        "observer_env_path": "observer-window.env",
        "observer_env_sha256": "0" * 64,
        "operator_approval_receipt_path": "operator-approval-receipt.json",
        "operator_approval_receipt_sha256": "0" * 64,
        "preflight_pre_path": "preflight-pre.json",
        "preflight_pre_sha256": "0" * 64,
        "preflight_post_path": "preflight-post.json",
        "preflight_post_sha256": "0" * 64,
        "pre_posture": "stable",
        "post_posture": "stable",
        "pre_check": "passed",
        "post_check": "passed",
        "rollback_start_utc": "2026-06-01T12:09:00Z",
        "rollback_end_utc": "2026-06-01T12:10:00Z",
        "rollback_completed": "true",
        "rollback_delta": "removed_observer_env_and_markers_preserved_disable_plugins",
        "observer_env_survived": "false",
        "observer_marker_survived": "false",
        "sibling_marker_entries": "absent",
        "sibling_observer_env": "absent",
        "user_policy": "no_regular_users",
        "notice_sent": "not_applicable",
        "log_budget": "10",
        "plugins_disabled": "true",
        "scanner_disabled": "true",
        "dispatch_limit": "0",
        "wrapper_profile": "observer-debug",
        "observer_exclusivity": "player_principal_lifecycle_only",
        "debug_escape_markers": "absent",
        "callback_escape_markers": "absent",
        "native_exec_disabled": "true",
        "ptrace_disabled": "true",
        "single_module_summary": "player_principal_lifecycle",
        "delivery_claim": "none",
        "principal_claim": "none",
    }
    for key, value in overrides.items():
        if value is None:
            fields.pop(key, None)
        else:
            fields[key] = value
    return [f"{key}={value}" for key, value in fields.items()]


def request_pack_payload(fields: dict[str, str], base: Path) -> dict:
    target = fields.get("target", "arkserver2/TheIsland").split("/", 1)
    copied_log_path = Path(fields["copied_log_path"])
    if not copied_log_path.is_absolute():
        copied_log_path = base / copied_log_path
    window_manifest_path = base / "window-manifest.env"
    payload = {
        "schema": "obelisk.player-principal-lifecycle-window-request.v1",
        "status": "candidate_only_request_pack",
        "approval_required": "current-turn operator-approved runtime window, not standing approval",
        "target": {"instance": target[0], "map": target[1]},
        "run_id": fields["run_id"],
        "ark_binary_sha256": ARK_SHA,
        "server_binary_path": EXPECTED_SERVER_BINARY_PATH,
        "obelisk_commit": fields.get("obelisk_commit", "missing-obelisk-commit"),
        "approved_window": {
            "start_utc": fields["approved_window_start_utc"],
            "end_utc": fields["approved_window_end_utc"],
        },
        "restart_expectation": "restart",
        "final_posture": "stable",
        "user_policy": fields.get("user_policy", "no_regular_users"),
        "notice_path": "not_applicable",
        "copied_evidence_dir": str(copied_log_path.parent),
        "copied_log_path": str(copied_log_path),
        "window_manifest_path": str(window_manifest_path),
        "observer_env_file": "observer-window.env",
        "marker_set": WINDOW_MARKERS,
        "forbidden_markers": FORBIDDEN_MARKERS,
        "rollback": {
            "owner": "operator",
            "delta": "remove observer env and markers, preserve stable enable-process-event-hook and disable-plugins",
        },
        "non_claims": NON_CLAIMS,
    }
    args = type(
        "Args",
        (),
        {
            "instance": target[0],
            "map_name": target[1],
            "binary_sha256": ARK_SHA,
        },
    )()
    payload["operator_live_ops_brief"] = operator_live_ops_brief(payload, env_lines(args))
    payload["post_window_replay_contract"] = post_window_replay_contract(payload)
    return payload


def preflight_payload(
    *,
    mode: str,
    instance: str,
    run_id: str = RUN_ID,
    map_name: str = "TheIsland",
    window_manifest_path: Path | None = None,
    copied_log_path: Path | None = None,
    env_file: Path | None = None,
    env_sha256: str | None = None,
    checked_at_utc: str = "2026-06-01T12:00:00Z",
) -> dict:
    if window_manifest_path is None:
        window_manifest_path = Path("/servidor/ark/workspace-offline/live-validation-logs") / run_id / "window-manifest.env"
    if copied_log_path is None:
        copied_log_path = Path("/servidor/ark/workspace-offline/live-validation-logs") / run_id / "Obelisk.log"
    return {
        "schema": "obelisk.player-principal-lifecycle-preflight.v1",
        "ready": True,
        "mode": mode,
        "run_id": run_id,
        "instance": instance,
        "map": map_name,
        "target": {"instance": instance, "map": map_name},
        "window_manifest_path": str(window_manifest_path),
        "copied_log_path": str(copied_log_path),
        "copied_evidence_dir": str(copied_log_path.parent),
        "server_binary": {
            "path": "/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer",
            "sha256": ARK_SHA,
        },
        "obelisk_root": "/servidor/ark/obelisk",
        "installed_wrapper": {
            "path": "/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ObeliskRun.sh",
            "sha256": "1" * 64,
        },
        "env_file": None if env_file is None else {"path": str(env_file), "sha256": env_sha256},
        "marker_dir": f"/servidor/ark/obelisk/state/instances/{instance}",
        "offline_only": False,
        "allow_stopped": True,
        "checked_at_utc": checked_at_utc,
        "posture_check": "accepted",
        "non_claim": "preflight only; not runtime approval and not permission to touch servers",
    }


def write_sidecars(base: Path, fields: dict[str, str]) -> dict[str, str]:
    observer_env_path = Path(fields["observer_env_path"])
    if not observer_env_path.is_absolute():
        observer_env_path = base / observer_env_path
    observer_env_text = "\n".join(
        [
            "OBELISK_INSTANCE_ID=arkserver2",
            "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1",
            "OBELISK_DISABLE_PLUGINS=1",
            "OBELISK_WRAPPER_PROFILE=observer-debug",
            "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1",
            f"OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256={ARK_SHA}",
            "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10",
            "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0",
            "OBELISK_PE_TRACE_LIMIT=0",
        ]
    ) + "\n"
    observer_env_sha256 = hashlib.sha256(observer_env_text.encode("utf-8")).hexdigest()
    copied_log_path = Path(fields["copied_log_path"])
    if not copied_log_path.is_absolute():
        copied_log_path = base / copied_log_path
    window_manifest_path = base / "window-manifest.env"
    request_pack_path = Path(fields["request_pack_path"])
    if not request_pack_path.is_absolute():
        request_pack_path = base / request_pack_path
    operator_request_path = request_pack_path.parent / "operator-approval-request.md"
    receipt_path = Path(fields.get("operator_approval_receipt_path", "operator-approval-receipt.json"))
    if not receipt_path.is_absolute():
        receipt_path = base / receipt_path
    request_payload = request_pack_payload(fields, base)
    contents = {
        "request_pack": json.dumps(request_payload, sort_keys=True) + "\n",
        "operator_request": markdown_request(
            request_payload,
            observer_env_text.splitlines(),
        ),
        "observer_env": observer_env_text,
        "preflight_pre": json.dumps(
            preflight_payload(
                mode="observer-window",
                instance="arkserver2",
                run_id=fields["run_id"],
                map_name=fields.get("map") or fields.get("map_name") or fields.get("target", "arkserver2/TheIsland").split("/", 1)[1],
                window_manifest_path=window_manifest_path,
                copied_log_path=copied_log_path,
                env_file=observer_env_path,
                env_sha256=observer_env_sha256,
                checked_at_utc=fields["approved_window_start_utc"],
            ),
            sort_keys=True,
        )
        + "\n",
        "preflight_post": json.dumps(
            preflight_payload(
                mode="stable",
                instance="arkserver2",
                run_id=fields["run_id"],
                map_name=fields.get("map") or fields.get("map_name") or fields.get("target", "arkserver2/TheIsland").split("/", 1)[1],
                window_manifest_path=window_manifest_path,
                copied_log_path=copied_log_path,
                checked_at_utc=fields["rollback_end_utc"],
            ),
            sort_keys=True,
        )
        + "\n",
    }
    key_map = {
        "request_pack": ("request_pack_path", "request_pack_sha256"),
        "operator_request": ("operator_request_path", "operator_request_sha256"),
        "observer_env": ("observer_env_path", "observer_env_sha256"),
        "preflight_pre": ("preflight_pre_path", "preflight_pre_sha256"),
        "preflight_post": ("preflight_post_path", "preflight_post_sha256"),
    }
    updated = dict(fields)
    updated["operator_request_path"] = str(operator_request_path)
    for content_key, (path_key, sha_key) in key_map.items():
        if path_key not in updated:
            continue
        path = Path(updated[path_key])
        if not path.is_absolute():
            path = base / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents[content_key], encoding="utf-8")
        updated[sha_key] = hashlib.sha256(path.read_bytes()).hexdigest()
    if "operator_approval_receipt_path" in updated:
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt = operator_approval_receipt_payload(
            request_payload,
            request_json_path=request_pack_path,
            request_md_path=operator_request_path,
            env_path=observer_env_path,
            operator_approved=True,
            operator_reference="test-current-turn-approval",
            approved_at_utc=fields["approved_window_start_utc"],
        )
        receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
        updated["operator_approval_receipt_path"] = str(receipt_path)
        updated["operator_approval_receipt_sha256"] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    updated.pop("operator_request_path", None)
    updated.pop("operator_request_sha256", None)
    return updated


class WindowManifestCheckerTests(unittest.TestCase):
    def test_post_window_replay_expiry_exception_is_exact(self) -> None:
        self.assertTrue(CHECKER.request_check_failed_only_because_window_expired(["approved_window_expired"]))
        self.assertFalse(CHECKER.request_check_failed_only_because_window_expired([]))
        self.assertFalse(
            CHECKER.request_check_failed_only_because_window_expired(
                ["approved_window_expired", "approved_window_expired"]
            )
        )
        self.assertFalse(
            CHECKER.request_check_failed_only_because_window_expired(
                ["approved_window_expired", "operator_markdown_drift"]
            )
        )
        self.assertFalse(CHECKER.request_check_failed_only_because_window_expired("approved_window_expired"))

    def run_checker(
        self,
        lines: list[str],
        *,
        check: bool = True,
        create_copied_log: bool = True,
        copied_log_text: str = COPIED_LOG_TEXT,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "window-manifest.env"
            fields = dict(line.split("=", 1) for line in lines if "=" in line)
            fields = write_sidecars(path.parent, fields)
            path.write_text("\n".join(f"{key}={value}" for key, value in fields.items()) + "\n", encoding="utf-8")
            copied_log = fields.get("copied_log_path")
            if create_copied_log and copied_log:
                copied_log_path = Path(copied_log)
                if not copied_log_path.is_absolute():
                    copied_log_path = path.parent / copied_log_path
                    copied_log_path.parent.mkdir(parents=True, exist_ok=True)
                    copied_log_path.write_text(copied_log_text, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(SCRIPT), str(path), "--json"],
                check=check,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

    def run_checker_in_approved_workspace(
        self,
        lines: list[str],
        *,
        check: bool = True,
        create_copied_log: bool = True,
        copied_log_text: str = COPIED_LOG_TEXT,
        sidecar_mutator=None,
    ) -> subprocess.CompletedProcess[str]:
        workspace = Path("/servidor/ark/workspace-offline")
        if not workspace.is_dir() or not os.access(workspace, os.W_OK):
            self.skipTest("/servidor/ark/workspace-offline is not writable in this environment")
        with tempfile.TemporaryDirectory(prefix="obelisk-test-player-principal-", dir=workspace) as tmp:
            root = Path(tmp)
            window_fields = future_window_fields()
            run_id = window_fields["run_id"]
            exact_dir = root / "live-validation-logs" / run_id
            exact_log = exact_dir / "Obelisk.log"
            exact_manifest = exact_dir / "window-manifest.env"
            exact_dir.mkdir(parents=True, exist_ok=True)
            rewritten_lines = []
            for line in rewrite_lines_for_window(lines, window_fields):
                if line == f"copied_log_path=live-validation-logs/{run_id}/Obelisk.log":
                    rewritten_lines.append(f"copied_log_path={exact_log}")
                else:
                    rewritten_lines.append(line)
            path = exact_manifest
            fields = dict(line.split("=", 1) for line in rewritten_lines if "=" in line)
            fields = write_sidecars(path.parent, fields)
            if sidecar_mutator is not None:
                sidecar_mutator(path.parent, fields)
            path.write_text("\n".join(f"{key}={value}" for key, value in fields.items()) + "\n", encoding="utf-8")
            copied_log = fields.get("copied_log_path")
            if create_copied_log and copied_log:
                copied_log_path = Path(copied_log)
                if not copied_log_path.is_absolute():
                    copied_log_path = path.parent / copied_log_path
                copied_log_path.parent.mkdir(parents=True, exist_ok=True)
                copied_log_path.write_text(copied_log_text, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(SCRIPT), str(path), "--json"],
                check=check,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, "OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"},
            )

    def mutate_preflight_checked_at(
        self,
        path_key: str,
        sha_key: str,
        checked_at_utc: str,
    ):
        def mutate(root: Path, fields: dict[str, str]) -> None:
            preflight_path = Path(fields[path_key])
            if not preflight_path.is_absolute():
                preflight_path = root / preflight_path
            payload = json.loads(preflight_path.read_text(encoding="utf-8"))
            payload["checked_at_utc"] = checked_at_utc
            preflight_path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
            fields[sha_key] = hashlib.sha256(preflight_path.read_bytes()).hexdigest()

        return mutate

    def test_accepts_approved_workspace_window_manifest_without_promoting_identity(self) -> None:
        result = self.run_checker_in_approved_workspace(manifest_lines())
        report = json.loads(result.stdout)

        self.assertTrue(report["ready"])
        self.assertTrue(report["operational_window_manifest_ready"])
        self.assertEqual(report["obelisk_commit"], TEST_COMMIT)
        self.assertEqual(report["copied_log"]["path_status"], "approved_offline_workspace")
        self.assertTrue(Path(report["copied_log"]["path"]).is_absolute())
        self.assertEqual(report["target"], {"instance": "arkserver2", "map": "TheIsland"})
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["remaining_blockers"], [])
        self.assertEqual(report["next_blocker"], "approved_runtime_observer_log_summary_and_manifest_missing")

    def test_rejects_operator_approval_receipt_completion_metadata_drift(self) -> None:
        def mutate(root: Path, fields: dict[str, str]) -> None:
            receipt_path = Path(fields["operator_approval_receipt_path"])
            if not receipt_path.is_absolute():
                receipt_path = root / receipt_path
            payload = json.loads(receipt_path.read_text(encoding="utf-8"))
            payload["operator_completion"]["approved_by_role"] = ""
            payload["operator_completion"]["approval_source"] = "standing_approval"
            receipt_path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
            fields["operator_approval_receipt_sha256"] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()

        result = self.run_checker_in_approved_workspace(
            manifest_lines(),
            check=False,
            sidecar_mutator=mutate,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operator_approval_receipt_approved_by_role_invalid", report["blockers"])
        self.assertIn("operator_approval_receipt_approval_source_mismatch", report["blockers"])
        self.assertFalse(report["ready"])

    def test_rejects_operator_approval_receipt_bound_request_pack_drift(self) -> None:
        def mutate(root: Path, fields: dict[str, str]) -> None:
            receipt_path = Path(fields["operator_approval_receipt_path"])
            if not receipt_path.is_absolute():
                receipt_path = root / receipt_path
            payload = json.loads(receipt_path.read_text(encoding="utf-8"))
            payload["bound_request_pack"]["restart_expectation"] = "stop-after-window"
            payload["bound_request_pack"]["final_posture"] = "stopped"
            payload["bound_request_pack"]["user_policy"] = "operator_approved_beta_users"
            payload["bound_request_pack"]["notice_path"] = "changed-notice"
            payload["bound_request_pack"]["rollback"]["delta"] = "changed"
            receipt_path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
            fields["operator_approval_receipt_sha256"] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()

        result = self.run_checker_in_approved_workspace(
            manifest_lines(),
            check=False,
            sidecar_mutator=mutate,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        for reason in (
            "operator_approval_receipt_restart_expectation_mismatch",
            "operator_approval_receipt_final_posture_mismatch",
            "operator_approval_receipt_user_policy_mismatch",
            "operator_approval_receipt_notice_path_mismatch",
            "operator_approval_receipt_rollback_mismatch",
        ):
            self.assertIn(reason, report["blockers"])
        self.assertFalse(report["ready"])

    def test_rejects_preflight_pre_checked_at_before_approved_window(self) -> None:
        result = self.run_checker_in_approved_workspace(
            manifest_lines(),
            check=False,
            sidecar_mutator=self.mutate_preflight_checked_at(
                "preflight_pre_path",
                "preflight_pre_sha256",
                "2026-01-01T12:00:00Z",
            ),
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("preflight_pre_path_checked_at_before_approved_window", report["blockers"])

    def test_rejects_preflight_pre_checked_at_after_capture_start(self) -> None:
        def mutate(root: Path, fields: dict[str, str]) -> None:
            self.mutate_preflight_checked_at(
                "preflight_pre_path",
                "preflight_pre_sha256",
                fields["actual_capture_end_utc"],
            )(root, fields)

        result = self.run_checker_in_approved_workspace(
            manifest_lines(),
            check=False,
            sidecar_mutator=mutate,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("preflight_pre_path_checked_at_after_capture_start", report["blockers"])

    def test_rejects_preflight_post_checked_at_before_capture_end(self) -> None:
        def mutate(root: Path, fields: dict[str, str]) -> None:
            self.mutate_preflight_checked_at(
                "preflight_post_path",
                "preflight_post_sha256",
                fields["actual_capture_start_utc"],
            )(root, fields)

        result = self.run_checker_in_approved_workspace(
            manifest_lines(),
            check=False,
            sidecar_mutator=mutate,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("preflight_post_path_checked_at_before_capture_end", report["blockers"])

    def test_rejects_preflight_post_checked_at_after_rollback_end(self) -> None:
        result = self.run_checker_in_approved_workspace(
            manifest_lines(),
            check=False,
            sidecar_mutator=self.mutate_preflight_checked_at(
                "preflight_post_path",
                "preflight_post_sha256",
                "2099-01-01T12:00:00Z",
            ),
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("preflight_post_path_checked_at_after_rollback_end", report["blockers"])

    def test_rejects_swapped_preflight_checked_at_order(self) -> None:
        def mutate(root: Path, fields: dict[str, str]) -> None:
            self.mutate_preflight_checked_at(
                "preflight_pre_path",
                "preflight_pre_sha256",
                fields["actual_capture_end_utc"],
            )(root, fields)
            self.mutate_preflight_checked_at(
                "preflight_post_path",
                "preflight_post_sha256",
                fields["actual_capture_start_utc"],
            )(root, fields)

        result = self.run_checker_in_approved_workspace(
            manifest_lines(),
            check=False,
            sidecar_mutator=mutate,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("preflight_checked_at_order_invalid", report["blockers"])

    def test_emit_template_from_copied_log_fills_path_sha_and_run_id(self) -> None:
        workspace = Path("/servidor/ark/workspace-offline")
        if not workspace.is_dir() or not os.access(workspace, os.W_OK):
            self.skipTest("/servidor/ark/workspace-offline is not writable in this environment")
        with tempfile.TemporaryDirectory(dir=workspace) as tmp:
            root = Path(tmp)
            copied_log = root / "live-validation-logs" / RUN_ID / "Obelisk.log"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text(COPIED_LOG_TEXT, encoding="utf-8")
            template = copied_log.parent / "window-manifest.env"

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--emit-template",
                    str(template),
                    "--copied-log",
                    str(copied_log),
                ],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual(result.stdout, "")
            fields = dict(
                line.split("=", 1)
                for line in template.read_text(encoding="utf-8").splitlines()
                if line and not line.startswith("#")
            )
            self.assertEqual(fields["run_id"], RUN_ID)
            self.assertEqual(fields["copied_log_path"], str(copied_log.resolve()))
            self.assertEqual(fields["copied_log_sha256"], GOOD_SHA)

    def test_emit_template_from_copied_log_rejects_protected_live_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            template = Path(temp_dir) / "window-manifest.env"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--emit-template",
                    str(template),
                    "--copied-log",
                    "/servidor/ark/obelisk/logs/arkserver2/Obelisk.log",
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--copied-log must not read from protected server root", result.stderr)

    def test_copied_log_option_requires_emit_template(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--copied-log",
                "/servidor/ark/workspace-offline/live-validation-logs/"
                f"{RUN_ID}/Obelisk.log",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--copied-log is only valid with --emit-template", result.stderr)

    def test_validate_preflight_content_requires_reviewed_binary_sha(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "window-manifest.env"
            observer_env = root / "observer-window.env"
            observer_env.write_text("OBELISK_INSTANCE_ID=arkserver2\n", encoding="utf-8")
            observer_env_sha256 = hashlib.sha256(observer_env.read_bytes()).hexdigest()
            copied_log = root / "Obelisk.log"
            preflight_path = root / "preflight-pre.json"
            preflight_path.write_text(
                json.dumps(
                    preflight_payload(
                        mode="observer-window",
                        instance="arkserver2",
                        window_manifest_path=manifest_path,
                        copied_log_path=copied_log,
                        env_file=observer_env,
                        env_sha256=observer_env_sha256,
                    ),
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            fields = {
                "run_id": RUN_ID,
                "copied_log_path": str(copied_log),
                "preflight_pre_path": str(preflight_path),
                "observer_env_path": str(observer_env),
                "observer_env_sha256": observer_env_sha256,
            }
            blockers: list[dict[str, object]] = []
            original_server_root = CHECKER.SERVER_ROOT
            original_approved_roots = CHECKER.APPROVED_OFFLINE_WORKSPACE_ROOTS
            try:
                CHECKER.SERVER_ROOT = root / "protected"
                CHECKER.APPROVED_OFFLINE_WORKSPACE_ROOTS = (root,)
                CHECKER.validate_preflight_content(
                    fields,
                    manifest_path,
                    blockers,
                    path_key="preflight_pre_path",
                    expected_mode="observer-window",
                    target=CHECKER.Target(instance="arkserver2", map_name="TheIsland"),
                )
            finally:
                CHECKER.SERVER_ROOT = original_server_root
                CHECKER.APPROVED_OFFLINE_WORKSPACE_ROOTS = original_approved_roots

        self.assertEqual([], blockers)

    def test_validate_preflight_content_rejects_text_or_wrong_binary_sha(self) -> None:
        for content, expected_reason in (
            (
                "player_principal_lifecycle_preflight=ok mode=observer-window instance=arkserver2\n",
                "preflight_pre_path_json_invalid",
            ),
            (None, "preflight_pre_path_binary_sha256_mismatch"),
        ):
            with self.subTest(expected_reason=expected_reason):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    manifest_path = root / "window-manifest.env"
                    observer_env = root / "observer-window.env"
                    observer_env.write_text("OBELISK_INSTANCE_ID=arkserver2\n", encoding="utf-8")
                    observer_env_sha256 = hashlib.sha256(observer_env.read_bytes()).hexdigest()
                    copied_log = root / "Obelisk.log"
                    preflight_path = root / "preflight-pre.json"
                    if content is None:
                        wrong_sha_payload = preflight_payload(
                            mode="observer-window",
                            instance="arkserver2",
                            window_manifest_path=manifest_path,
                            copied_log_path=copied_log,
                            env_file=observer_env,
                            env_sha256=observer_env_sha256,
                        )
                        wrong_sha_payload["server_binary"]["sha256"] = "0" * 64
                        content = json.dumps(wrong_sha_payload, sort_keys=True) + "\n"
                    preflight_path.write_text(content, encoding="utf-8")
                    fields = {
                        "run_id": RUN_ID,
                        "copied_log_path": str(copied_log),
                        "preflight_pre_path": str(preflight_path),
                        "observer_env_path": str(observer_env),
                        "observer_env_sha256": observer_env_sha256,
                    }
                    blockers: list[dict[str, object]] = []
                    original_server_root = CHECKER.SERVER_ROOT
                    original_approved_roots = CHECKER.APPROVED_OFFLINE_WORKSPACE_ROOTS
                    try:
                        CHECKER.SERVER_ROOT = root / "protected"
                        CHECKER.APPROVED_OFFLINE_WORKSPACE_ROOTS = (root,)
                        CHECKER.validate_preflight_content(
                            fields,
                            manifest_path,
                            blockers,
                            path_key="preflight_pre_path",
                            expected_mode="observer-window",
                            target=CHECKER.Target(instance="arkserver2", map_name="TheIsland"),
                        )
                    finally:
                        CHECKER.SERVER_ROOT = original_server_root
                        CHECKER.APPROVED_OFFLINE_WORKSPACE_ROOTS = original_approved_roots

                self.assertIn(expected_reason, [item["reason"] for item in blockers])

    def test_validate_preflight_content_rejects_observer_env_path_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "window-manifest.env"
            observer_env = root / "observer-window.env"
            observer_env.write_text("OBELISK_INSTANCE_ID=arkserver2\n", encoding="utf-8")
            observer_env_sha256 = hashlib.sha256(observer_env.read_bytes()).hexdigest()
            copied_log = root / "Obelisk.log"
            preflight_path = root / "preflight-pre.json"
            preflight_path.write_text(
                json.dumps(
                    preflight_payload(
                        mode="observer-window",
                        instance="arkserver2",
                        window_manifest_path=manifest_path,
                        copied_log_path=copied_log,
                        env_file=root / "stale-observer-window.env",
                        env_sha256=observer_env_sha256,
                    ),
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            fields = {
                "run_id": RUN_ID,
                "copied_log_path": str(copied_log),
                "preflight_pre_path": str(preflight_path),
                "observer_env_path": str(observer_env),
                "observer_env_sha256": observer_env_sha256,
            }
            blockers: list[dict[str, object]] = []
            original_server_root = CHECKER.SERVER_ROOT
            original_approved_roots = CHECKER.APPROVED_OFFLINE_WORKSPACE_ROOTS
            try:
                CHECKER.SERVER_ROOT = root / "protected"
                CHECKER.APPROVED_OFFLINE_WORKSPACE_ROOTS = (root,)
                CHECKER.validate_preflight_content(
                    fields,
                    manifest_path,
                    blockers,
                    path_key="preflight_pre_path",
                    expected_mode="observer-window",
                    target=CHECKER.Target(instance="arkserver2", map_name="TheIsland"),
                )
            finally:
                CHECKER.SERVER_ROOT = original_server_root
                CHECKER.APPROVED_OFFLINE_WORKSPACE_ROOTS = original_approved_roots

        self.assertIn("preflight_pre_path_env_file_path_mismatch", [item["reason"] for item in blockers])

    def test_validate_request_pack_rejects_manifest_path_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_dir = root / "approved" / "live-validation-logs" / RUN_ID
            manifest_dir.mkdir(parents=True)
            copied_log = manifest_dir / "Obelisk.log"
            copied_log.write_text(COPIED_LOG_TEXT, encoding="utf-8")
            manifest_path = manifest_dir / "window-manifest.env"
            request_pack = manifest_dir / "window-request.json"
            payload = {
                "schema": "obelisk.player-principal-lifecycle-window-request.v1",
                "run_id": RUN_ID,
                "target": {"instance": "arkserver2", "map": "TheIsland"},
                "approved_window": {
                    "start_utc": "2026-06-01T12:00:00Z",
                    "end_utc": "2026-06-01T12:10:00Z",
                },
                "copied_evidence_dir": str(manifest_dir / "stale"),
                "copied_log_path": str(manifest_dir / "stale" / "Obelisk.log"),
                "window_manifest_path": str(manifest_dir / "stale" / "window-manifest.env"),
            }
            request_pack.write_text(json.dumps(payload), encoding="utf-8")
            fields = {
                "run_id": RUN_ID,
                "target": "arkserver2/TheIsland",
                "approved_window_start_utc": "2026-06-01T12:00:00Z",
                "approved_window_end_utc": "2026-06-01T12:10:00Z",
                "copied_log_path": str(copied_log),
                "request_pack_path": str(request_pack),
            }
            blockers: list[dict[str, object]] = []
            original_server_root = CHECKER.SERVER_ROOT
            original_approved_roots = CHECKER.APPROVED_OFFLINE_WORKSPACE_ROOTS
            try:
                CHECKER.SERVER_ROOT = root / "protected"
                CHECKER.APPROVED_OFFLINE_WORKSPACE_ROOTS = (root / "approved",)
                CHECKER.validate_request_pack(fields, manifest_path, blockers)
            finally:
                CHECKER.SERVER_ROOT = original_server_root
                CHECKER.APPROVED_OFFLINE_WORKSPACE_ROOTS = original_approved_roots

        reasons = [item["reason"] for item in blockers]
        self.assertIn("request_pack_copied_log_path_manifest_mismatch", reasons)
        self.assertIn("request_pack_copied_evidence_dir_manifest_mismatch", reasons)
        self.assertIn("request_pack_window_manifest_path_manifest_mismatch", reasons)

    def test_accepts_legacy_users_policy_alias_and_split_target_fields(self) -> None:
        lines = manifest_lines(target=None, instance="arkserver2", map="TheIsland", user_policy=None)
        lines.append("users_policy=no_regular_users")
        result = self.run_checker_in_approved_workspace(lines)
        report = json.loads(result.stdout)

        self.assertTrue(report["ready"])
        self.assertEqual(report["user_policy"], "no_regular_users")
        self.assertEqual(report["target"], {"instance": "arkserver2", "map": "TheIsland"})

    def test_rejects_generic_unprotected_offline_window_manifest(self) -> None:
        result = self.run_checker(manifest_lines(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("copied_log_path_not_under_approved_offline_workspace", report["blockers"])
        self.assertEqual(report["copied_log"]["path_status"], "unprotected_offline")
        self.assertFalse(report["ready"])

    def test_rejects_copied_log_path_under_live_server_root(self) -> None:
        result = self.run_checker(
            manifest_lines(copied_log_path="/servidor/ark/Obelisk.log"),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("copied_log_path_under_protected_server_root", report["blockers"])
        self.assertEqual(report["next_blocker"], "window_manifest_not_accepted")
        self.assertFalse(report["ready"])

    def test_validate_request_pack_does_not_read_protected_request_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protected = root / "protected"
            approved = root / "approved"
            protected.mkdir()
            approved.mkdir()
            request_pack = protected / "window-request.json"
            request_pack.write_text("{not json", encoding="utf-8")
            manifest_path = approved / "window-manifest.env"
            fields = {"request_pack_path": str(request_pack)}
            blockers: list[dict[str, object]] = [
                {
                    "reason": "request_pack_path_under_protected_server_root",
                    "label": "request_pack_path",
                }
            ]

            original_server_root = CHECKER.SERVER_ROOT
            original_approved_roots = CHECKER.APPROVED_OFFLINE_WORKSPACE_ROOTS
            try:
                CHECKER.SERVER_ROOT = protected
                CHECKER.APPROVED_OFFLINE_WORKSPACE_ROOTS = (approved,)
                CHECKER.validate_request_pack(fields, manifest_path, blockers)
            finally:
                CHECKER.SERVER_ROOT = original_server_root
                CHECKER.APPROVED_OFFLINE_WORKSPACE_ROOTS = original_approved_roots

        reasons = [item["reason"] for item in blockers]
        self.assertIn("request_pack_path_under_protected_server_root", reasons)
        self.assertNotIn("request_pack_json_invalid", reasons)
        self.assertNotIn("request_pack_schema_mismatch", reasons)

    def test_rejects_missing_copied_log_and_placeholder_sha(self) -> None:
        result = self.run_checker(
            manifest_lines(copied_log_sha256="0" * 64),
            check=False,
            create_copied_log=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("copied_log_file_missing", report["blockers"])
        self.assertIn("copied_log_sha256_placeholder", report["blockers"])
        self.assertFalse(report["ready"])

    def test_rejects_copied_log_sha_mismatch(self) -> None:
        result = self.run_checker(
            manifest_lines(copied_log_sha256=GOOD_SHA),
            check=False,
            copied_log_text="different copied log\n",
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("copied_log_sha256_mismatch", report["blockers"])
        self.assertFalse(report["ready"])

    def test_rejects_copied_log_path_that_does_not_include_run_id(self) -> None:
        result = self.run_checker(
            manifest_lines(copied_log_path="wrong-run/Obelisk.log"),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("copied_log_path_run_id_mismatch", report["blockers"])
        self.assertFalse(report["ready"])

    def test_rejects_copied_log_path_outside_live_validation_run_shape(self) -> None:
        result = self.run_checker(
            manifest_lines(copied_log_path=f"{RUN_ID}/Obelisk.log"),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("copied_log_path_not_live_validation_run_log", report["blockers"])
        self.assertFalse(report["ready"])

    def test_rejects_approved_workspace_nested_live_validation_alias(self) -> None:
        workspace = Path("/servidor/ark/workspace-offline")
        if not workspace.is_dir() or not os.access(workspace, os.W_OK):
            self.skipTest("/servidor/ark/workspace-offline is not writable in this environment")
        with tempfile.TemporaryDirectory(dir=workspace) as tmp:
            root = Path(tmp)
            alias_log = root / "tmp" / "live-validation-logs" / RUN_ID / "Obelisk.log"
            alias_log.parent.mkdir(parents=True, exist_ok=True)
            alias_log.write_text(COPIED_LOG_TEXT, encoding="utf-8")
            exact_manifest = root / "live-validation-logs" / RUN_ID / "window-manifest.env"
            exact_manifest.parent.mkdir(parents=True, exist_ok=True)
            exact_manifest.write_text(
                "\n".join(manifest_lines(copied_log_path=str(alias_log))) + "\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(exact_manifest), "--json"],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, "OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"},
            )

        report = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("copied_log_path_not_exact_approved_run_log", report["blockers"])
        self.assertFalse(report["ready"])

    def test_rejects_unexpected_identity_or_ue_internal_fields(self) -> None:
        lines = manifest_lines()
        lines.extend(
            [
                "steamid=76561198000000000",
                "raw_params=0x1234",
                "uobject_address=0x5678",
                "unexpected_safe_key=value",
            ]
        )
        result = self.run_checker(lines, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected_field", report["blockers"])
        self.assertIn("forbidden_identity_or_ue_field", report["blockers"])
        self.assertFalse(report["ready"])

    def test_rejects_identity_or_ue_internal_values_in_allowed_fields(self) -> None:
        result = self.run_checker(
            manifest_lines(rollback_delta="removed_observer_env_after_steamid_redaction"),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden_identity_or_ue_value", report["blockers"])
        self.assertFalse(report["ready"])

    def test_rejects_extended_private_identity_terms_from_current_notes(self) -> None:
        result = self.run_checker(
            manifest_lines(rollback_delta="removed_observer_env_after_permission_state_and_identity_hash_redaction"),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden_identity_or_ue_value", report["blockers"])
        self.assertFalse(report["ready"])

    def test_rejects_public_capability_or_readiness_terms_in_allowed_values(self) -> None:
        result = self.run_checker(
            manifest_lines(rollback_delta="removed_observer_env_after_public_sdk_ready_and_command_reply_support"),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden_public_capability_or_readiness_value", report["blockers"])
        self.assertFalse(report["ready"])

    def test_rejects_noncanonical_rollback_delta(self) -> None:
        result = self.run_checker(
            manifest_lines(rollback_delta="removed_observer_markers_only"),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("rollback_delta_mismatch", report["blockers"])
        self.assertFalse(report["ready"])

    def test_rejects_claims_dispatch_and_budget_that_would_enable_delivery(self) -> None:
        result = self.run_checker(
            manifest_lines(
                log_budget="5",
                dispatch_limit="1",
                delivery_claim="plugin_delivery",
                principal_claim="principal_promoted",
            ),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("log_budget_not_exact_first_window_limit", report["blockers"])
        self.assertIn("dispatch_limit_not_zero", report["blockers"])
        self.assertIn("delivery_claim_not_none", report["blockers"])
        self.assertIn("principal_claim_not_none", report["blockers"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_missing_or_unsafe_obelisk_commit(self) -> None:
        missing = self.run_checker(manifest_lines(obelisk_commit=None), check=False)
        missing_report = json.loads(missing.stdout)
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("required_field_missing", missing_report["blockers"])

        unsafe = self.run_checker(manifest_lines(obelisk_commit="../main"), check=False)
        unsafe_report = json.loads(unsafe.stdout)
        self.assertNotEqual(unsafe.returncode, 0)
        self.assertIn("obelisk_commit_invalid", unsafe_report["blockers"])

        placeholder = self.run_checker(manifest_lines(obelisk_commit="test-commit"), check=False)
        placeholder_report = json.loads(placeholder.stdout)
        self.assertNotEqual(placeholder.returncode, 0)
        self.assertIn("obelisk_commit_invalid", placeholder_report["blockers"])

    def test_rejects_non_exclusive_observer_window_escape_gates(self) -> None:
        result = self.run_checker(
            manifest_lines(
                wrapper_profile="stable",
                observer_exclusivity="chat_and_player_principal",
                sibling_marker_entries=(
                    "enable-chat-events,enable-reflection-scanner,"
                    "enable-native-exec-probes,allow-ptrace,enable-debug-control,"
                    "allow-plugin-callbacks,symlink:enable-structure-reflection,malformed-entry"
                ),
                sibling_observer_env=(
                    "OBELISK_ENABLE_CHAT_EVENTS=1,OBELISK_ENABLE_REFLECTION_SCANNER=1,"
                    "OBELISK_ENABLE_NATIVE_EXEC_PROBES=1,OBELISK_DEBUG_ALLOW_PTRACE=1,"
                    "OBELISK_ENABLE_DEBUG_CONTROL=1,OBELISK_ALLOW_PLUGIN_CALLBACKS=1"
                ),
                debug_escape_markers="present",
                callback_escape_markers="present",
                native_exec_disabled="false",
                ptrace_disabled="false",
                single_module_summary="all_observers",
            ),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("wrapper_profile_not_observer_debug", report["blockers"])
        self.assertIn("observer_exclusivity_not_player_principal_lifecycle_only", report["blockers"])
        self.assertIn("sibling_marker_entries_not_absent", report["blockers"])
        self.assertIn("sibling_observer_env_not_absent", report["blockers"])
        self.assertIn("debug_escape_markers_not_absent", report["blockers"])
        self.assertIn("callback_escape_markers_not_absent", report["blockers"])
        self.assertIn("native_exec_disabled_not_true", report["blockers"])
        self.assertIn("ptrace_disabled_not_true", report["blockers"])
        self.assertIn("single_module_summary_not_player_principal_lifecycle", report["blockers"])

    def test_rejects_missing_explicit_no_sibling_marker_and_env_assertions(self) -> None:
        result = self.run_checker(
            manifest_lines(sibling_marker_entries=None, sibling_observer_env=None),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required_field_missing", report["blockers"])
        missing_labels = {
            detail["label"]
            for detail in report["blocker_details"]
            if detail["reason"] == "required_field_missing"
        }
        self.assertIn("sibling_marker_entries", missing_labels)
        self.assertIn("sibling_observer_env", missing_labels)
        self.assertIn("sibling_marker_entries_not_absent", report["blockers"])
        self.assertIn("sibling_observer_env_not_absent", report["blockers"])
        self.assertFalse(report["ready"])

    def test_rejects_request_pack_observer_env_drift(self) -> None:
        workspace = Path("/servidor/ark/workspace-offline")
        if not workspace.is_dir() or not os.access(workspace, os.W_OK):
            self.skipTest("/servidor/ark/workspace-offline is not writable in this environment")
        with tempfile.TemporaryDirectory(prefix="obelisk-test-player-principal-", dir=workspace) as tmp:
            root = Path(tmp)
            exact_dir = root / "live-validation-logs" / RUN_ID
            exact_log = exact_dir / "Obelisk.log"
            exact_manifest = exact_dir / "window-manifest.env"
            exact_dir.mkdir(parents=True, exist_ok=True)
            lines = []
            for line in manifest_lines():
                if line == f"copied_log_path=live-validation-logs/{RUN_ID}/Obelisk.log":
                    lines.append(f"copied_log_path={exact_log}")
                else:
                    lines.append(line)
            fields = dict(line.split("=", 1) for line in lines if "=" in line)
            fields = write_sidecars(exact_manifest.parent, fields)
            observer_env = Path(fields["observer_env_path"])
            if not observer_env.is_absolute():
                observer_env = exact_manifest.parent / observer_env
            observer_env.write_text(
                observer_env.read_text(encoding="utf-8").replace(
                    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10",
                    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=9",
                ),
                encoding="utf-8",
            )
            fields["observer_env_sha256"] = hashlib.sha256(observer_env.read_bytes()).hexdigest()
            exact_manifest.write_text(
                "\n".join(f"{key}={value}" for key, value in fields.items()) + "\n",
                encoding="utf-8",
            )
            exact_log.write_text(COPIED_LOG_TEXT, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(exact_manifest), "--json"],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, "OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"},
            )

        report = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_pack_window_request_check_failed", report["blockers"])
        self.assertFalse(report["ready"])

    def test_rejects_request_pack_operator_markdown_drift(self) -> None:
        def mutate(root: Path, fields: dict[str, str]) -> None:
            request_pack = Path(fields["request_pack_path"])
            if not request_pack.is_absolute():
                request_pack = root / request_pack
            operator_request = request_pack.parent / "operator-approval-request.md"
            operator_request.write_text(
                operator_request.read_text(encoding="utf-8").replace("dispatch limit=0", "dispatch limit=1"),
                encoding="utf-8",
            )

        result = self.run_checker_in_approved_workspace(
            manifest_lines(),
            check=False,
            sidecar_mutator=mutate,
        )
        report = json.loads(result.stdout)
        details = [
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "request_pack_window_request_check_failed"
        ]

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_pack_window_request_check_failed", report["blockers"])
        self.assertTrue(details)
        self.assertIn("operator_request_markdown_mismatch", details[0]["request_check_blockers"])
        self.assertFalse(report["ready"])

    def test_rejects_request_pack_post_window_replay_contract_sidecar_drift(self) -> None:
        def mutate(root: Path, fields: dict[str, str]) -> None:
            request_pack = Path(fields["request_pack_path"])
            if not request_pack.is_absolute():
                request_pack = root / request_pack
            payload = json.loads(request_pack.read_text(encoding="utf-8"))
            payload["post_window_replay_contract"]["sidecars"]["preflight_pre_path"] = "/tmp/preflight-pre.json"
            request_pack.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
            fields["request_pack_sha256"] = hashlib.sha256(request_pack.read_bytes()).hexdigest()
            observer_env = Path(fields["observer_env_path"])
            if not observer_env.is_absolute():
                observer_env = root / observer_env
            operator_request = request_pack.parent / "operator-approval-request.md"
            operator_request.write_text(
                markdown_request(payload, observer_env.read_text(encoding="utf-8").splitlines()),
                encoding="utf-8",
            )

        result = self.run_checker_in_approved_workspace(
            manifest_lines(),
            check=False,
            sidecar_mutator=mutate,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_pack_post_window_replay_contract_mismatch", report["blockers"])
        self.assertFalse(report["ready"])

    def test_rejects_request_pack_post_window_replay_contract_missing_receipt_sidecar(self) -> None:
        def mutate(root: Path, fields: dict[str, str]) -> None:
            request_pack = Path(fields["request_pack_path"])
            if not request_pack.is_absolute():
                request_pack = root / request_pack
            payload = json.loads(request_pack.read_text(encoding="utf-8"))
            payload["post_window_replay_contract"]["sidecars"].pop("operator_approval_receipt_path")
            request_pack.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
            fields["request_pack_sha256"] = hashlib.sha256(request_pack.read_bytes()).hexdigest()

        result = self.run_checker_in_approved_workspace(
            manifest_lines(),
            check=False,
            sidecar_mutator=mutate,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_pack_post_window_replay_contract_mismatch", report["blockers"])
        self.assertFalse(report["ready"])

    def test_rejects_request_pack_post_window_replay_contract_receipt_sidecar_drift(self) -> None:
        def mutate(root: Path, fields: dict[str, str]) -> None:
            request_pack = Path(fields["request_pack_path"])
            if not request_pack.is_absolute():
                request_pack = root / request_pack
            payload = json.loads(request_pack.read_text(encoding="utf-8"))
            payload["post_window_replay_contract"]["sidecars"][
                "operator_approval_receipt_path"
            ] = "/tmp/operator-approval-receipt.json"
            request_pack.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
            fields["request_pack_sha256"] = hashlib.sha256(request_pack.read_bytes()).hexdigest()
            observer_env = Path(fields["observer_env_path"])
            if not observer_env.is_absolute():
                observer_env = root / observer_env
            operator_request = request_pack.parent / "operator-approval-request.md"
            operator_request.write_text(
                markdown_request(payload, observer_env.read_text(encoding="utf-8").splitlines()),
                encoding="utf-8",
            )

        result = self.run_checker_in_approved_workspace(
            manifest_lines(),
            check=False,
            sidecar_mutator=mutate,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_pack_post_window_replay_contract_mismatch", report["blockers"])
        self.assertFalse(report["ready"])

    def test_rejects_request_pack_post_window_replay_contract_check_drift(self) -> None:
        def mutate(root: Path, fields: dict[str, str]) -> None:
            request_pack = Path(fields["request_pack_path"])
            if not request_pack.is_absolute():
                request_pack = root / request_pack
            payload = json.loads(request_pack.read_text(encoding="utf-8"))
            payload["post_window_replay_contract"]["checks"]["window_manifest_replay"] = [
                "scripts/check_player_identity_runtime_principal_lifecycle_window_manifest.py",
                "--json",
                str(root / "window-manifest.env"),
            ]
            request_pack.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
            fields["request_pack_sha256"] = hashlib.sha256(request_pack.read_bytes()).hexdigest()
            observer_env = Path(fields["observer_env_path"])
            if not observer_env.is_absolute():
                observer_env = root / observer_env
            operator_request = request_pack.parent / "operator-approval-request.md"
            operator_request.write_text(
                markdown_request(payload, observer_env.read_text(encoding="utf-8").splitlines()),
                encoding="utf-8",
            )

        result = self.run_checker_in_approved_workspace(
            manifest_lines(),
            check=False,
            sidecar_mutator=mutate,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_pack_post_window_replay_contract_check_mismatch", report["blockers"])
        self.assertFalse(report["ready"])

    def test_rejects_request_pack_obelisk_commit_mismatch(self) -> None:
        workspace = Path("/servidor/ark/workspace-offline")
        if not workspace.is_dir() or not os.access(workspace, os.W_OK):
            self.skipTest("/servidor/ark/workspace-offline is not writable in this environment")
        with tempfile.TemporaryDirectory(prefix="obelisk-test-player-principal-", dir=workspace) as tmp:
            root = Path(tmp)
            exact_dir = root / "live-validation-logs" / RUN_ID
            exact_log = exact_dir / "Obelisk.log"
            exact_manifest = exact_dir / "window-manifest.env"
            exact_dir.mkdir(parents=True, exist_ok=True)
            lines = []
            for line in manifest_lines():
                if line == f"copied_log_path=live-validation-logs/{RUN_ID}/Obelisk.log":
                    lines.append(f"copied_log_path={exact_log}")
                else:
                    lines.append(line)
            fields = dict(line.split("=", 1) for line in lines if "=" in line)
            fields = write_sidecars(exact_manifest.parent, fields)
            request_pack = Path(fields["request_pack_path"])
            if not request_pack.is_absolute():
                request_pack = exact_manifest.parent / request_pack
            payload = json.loads(request_pack.read_text(encoding="utf-8"))
            payload["obelisk_commit"] = "abcdef1234567890abcdef1234567890abcdef12"
            request_pack.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
            fields["request_pack_sha256"] = hashlib.sha256(request_pack.read_bytes()).hexdigest()
            exact_manifest.write_text(
                "\n".join(f"{key}={value}" for key, value in fields.items()) + "\n",
                encoding="utf-8",
            )
            exact_log.write_text(COPIED_LOG_TEXT, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(exact_manifest), "--json"],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, "OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"},
            )

        report = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_pack_obelisk_commit_mismatch", report["blockers"])
        self.assertFalse(report["ready"])

    def test_rejects_preflight_sidecar_content_drift_even_with_matching_sha(self) -> None:
        workspace = Path("/servidor/ark/workspace-offline")
        if not workspace.is_dir() or not os.access(workspace, os.W_OK):
            self.skipTest("/servidor/ark/workspace-offline is not writable in this environment")
        with tempfile.TemporaryDirectory(prefix="obelisk-test-player-principal-", dir=workspace) as tmp:
            root = Path(tmp)
            exact_dir = root / "live-validation-logs" / RUN_ID
            exact_log = exact_dir / "Obelisk.log"
            exact_manifest = exact_dir / "window-manifest.env"
            exact_dir.mkdir(parents=True, exist_ok=True)
            lines = []
            for line in manifest_lines():
                if line == f"copied_log_path=live-validation-logs/{RUN_ID}/Obelisk.log":
                    lines.append(f"copied_log_path={exact_log}")
                else:
                    lines.append(line)
            fields = dict(line.split("=", 1) for line in lines if "=" in line)
            fields = write_sidecars(exact_manifest.parent, fields)
            preflight_pre = Path(fields["preflight_pre_path"])
            if not preflight_pre.is_absolute():
                preflight_pre = exact_manifest.parent / preflight_pre
            preflight_pre.write_text(
                "player_principal_lifecycle_preflight=ok mode=observer-window instance=other\n",
                encoding="utf-8",
            )
            fields["preflight_pre_sha256"] = hashlib.sha256(preflight_pre.read_bytes()).hexdigest()
            exact_manifest.write_text(
                "\n".join(f"{key}={value}" for key, value in fields.items()) + "\n",
                encoding="utf-8",
            )
            exact_log.write_text(COPIED_LOG_TEXT, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(exact_manifest), "--json"],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, "OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"},
            )

        report = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("preflight_pre_path_json_invalid", report["blockers"])
        self.assertFalse(report["ready"])

    def test_rejects_preflight_sidecar_anchor_drift_even_with_matching_sha(self) -> None:
        workspace = Path("/servidor/ark/workspace-offline")
        if not workspace.is_dir() or not os.access(workspace, os.W_OK):
            self.skipTest("/servidor/ark/workspace-offline is not writable in this environment")
        cases = (
            ("run_id", "20260601T121111Z-player-principal-lifecycle", "preflight_pre_path_run_id_mismatch"),
            ("map", "Ragnarok", "preflight_pre_path_map_mismatch"),
            ("target.map", "Ragnarok", "preflight_pre_path_target_map_mismatch"),
            ("window_manifest_path", "stale/window-manifest.env", "preflight_pre_path_window_manifest_path_mismatch"),
            ("copied_log_path", "stale/Obelisk.log", "preflight_pre_path_copied_log_path_mismatch"),
            ("copied_evidence_dir", "stale", "preflight_pre_path_copied_evidence_dir_mismatch"),
            ("checked_at_utc", "not-utc", "preflight_pre_path_checked_at_utc_invalid"),
        )
        for key, value, reason in cases:
            with self.subTest(reason=reason):
                with tempfile.TemporaryDirectory(prefix="obelisk-test-player-principal-", dir=workspace) as tmp:
                    root = Path(tmp)
                    exact_dir = root / "live-validation-logs" / RUN_ID
                    exact_log = exact_dir / "Obelisk.log"
                    exact_manifest = exact_dir / "window-manifest.env"
                    exact_dir.mkdir(parents=True, exist_ok=True)
                    lines = []
                    for line in manifest_lines():
                        if line == f"copied_log_path=live-validation-logs/{RUN_ID}/Obelisk.log":
                            lines.append(f"copied_log_path={exact_log}")
                        else:
                            lines.append(line)
                    fields = dict(line.split("=", 1) for line in lines if "=" in line)
                    fields = write_sidecars(exact_manifest.parent, fields)
                    preflight_pre = Path(fields["preflight_pre_path"])
                    if not preflight_pre.is_absolute():
                        preflight_pre = exact_manifest.parent / preflight_pre
                    payload = json.loads(preflight_pre.read_text(encoding="utf-8"))
                    if key == "target.map":
                        payload["target"]["map"] = value
                    else:
                        payload[key] = value
                    preflight_pre.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
                    fields["preflight_pre_sha256"] = hashlib.sha256(preflight_pre.read_bytes()).hexdigest()
                    exact_manifest.write_text(
                        "\n".join(f"{field_key}={field_value}" for field_key, field_value in fields.items()) + "\n",
                        encoding="utf-8",
                    )
                    exact_log.write_text(COPIED_LOG_TEXT, encoding="utf-8")
                    result = subprocess.run(
                        [sys.executable, str(SCRIPT), str(exact_manifest), "--json"],
                        check=False,
                        text=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        env={**os.environ, "OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"},
                    )

                report = json.loads(result.stdout)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(reason, report["blockers"])
                self.assertFalse(report["ready"])

    def test_rejects_capture_outside_approved_window_and_bad_rollback_order(self) -> None:
        result = self.run_checker(
            manifest_lines(
                approved_window_start_utc="2026-06-01T12:00:00Z",
                approved_window_end_utc="2026-06-01T12:10:00Z",
                actual_capture_start_utc="2026-06-01T11:59:00Z",
                actual_capture_end_utc="2026-06-01T12:11:00Z",
                rollback_start_utc="2026-06-01T12:09:00Z",
                rollback_end_utc="2026-06-01T12:08:00Z",
            ),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("actual_capture_starts_before_approved_window", report["blockers"])
        self.assertIn("actual_capture_ends_after_approved_window", report["blockers"])
        self.assertIn("rollback_starts_before_capture_end", report["blockers"])
        self.assertIn("rollback_window_not_forward", report["blockers"])

    def test_rejects_unstable_posture_and_incomplete_rollback(self) -> None:
        result = self.run_checker(
            manifest_lines(
                post_posture="observer-window",
                post_check="failed",
                rollback_completed="false",
                observer_marker_survived="true",
                plugins_disabled="false",
                scanner_disabled="false",
            ),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("post_posture_not_stable", report["blockers"])
        self.assertIn("post_check_not_passed", report["blockers"])
        self.assertIn("rollback_completed_not_true", report["blockers"])
        self.assertIn("observer_marker_survived_not_false", report["blockers"])
        self.assertIn("plugins_disabled_not_true", report["blockers"])
        self.assertIn("scanner_disabled_not_true", report["blockers"])

    def test_beta_user_policy_requires_notice_sent(self) -> None:
        result = self.run_checker(
            manifest_lines(user_policy="operator_approved_beta_users", notice_sent="false"),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("beta_user_policy_requires_notice_sent", report["blockers"])

    def test_rejects_unknown_user_policy(self) -> None:
        result = self.run_checker(manifest_lines(user_policy="unknown"), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("user_policy_not_accepted", report["blockers"])

    def test_emits_parseable_but_not_ready_window_manifest_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "window-template.env"
            emit = subprocess.run(
                [sys.executable, str(SCRIPT), "--emit-template", str(path)],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(emit.returncode, 0, emit.stderr)

            validate = subprocess.run(
                [sys.executable, str(SCRIPT), str(path), "--json"],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.assertNotEqual(validate.returncode, 0)
        report = json.loads(validate.stdout)
        self.assertFalse(report["ready"])
        self.assertEqual(report["target"], {"instance": "arkserver2", "map": "TheIsland"})
        self.assertFalse(report["promotion_ready"])
        self.assertIn("copied_log_file_missing", report["blockers"])
        self.assertIn("copied_log_sha256_placeholder", report["blockers"])


if __name__ == "__main__":
    unittest.main()
