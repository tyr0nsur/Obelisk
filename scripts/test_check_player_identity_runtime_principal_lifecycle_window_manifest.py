#!/usr/bin/env python3
"""Tests for check_player_identity_runtime_principal_lifecycle_window_manifest.py."""

from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT = SCRIPT_DIR / "check_player_identity_runtime_principal_lifecycle_window_manifest.py"
RUN_ID = "20260601T120000Z-player-principal-lifecycle"
COPIED_LOG_TEXT = "copied player principal lifecycle observer log\n"
GOOD_SHA = hashlib.sha256(COPIED_LOG_TEXT.encode("utf-8")).hexdigest()


def manifest_lines(**overrides: str | None) -> list[str]:
    fields = {
        "run_id": RUN_ID,
        "obelisk_commit": "test-commit",
        "target": "arkserver2/TheIsland",
        "approval": "current-turn operator-approved runtime window, not standing approval",
        "approved_window_start_utc": "2026-06-01T12:00:00Z",
        "approved_window_end_utc": "2026-06-01T12:10:00Z",
        "actual_capture_start_utc": "2026-06-01T12:01:00Z",
        "actual_capture_end_utc": "2026-06-01T12:09:00Z",
        "copied_log_path": f"live-validation-logs/{RUN_ID}/Obelisk.log",
        "copied_log_sha256": GOOD_SHA,
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


class WindowManifestCheckerTests(unittest.TestCase):
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
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            fields = dict(line.split("=", 1) for line in lines if "=" in line)
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
    ) -> subprocess.CompletedProcess[str]:
        workspace = Path("/servidor/ark/workspace-offline")
        if not workspace.is_dir() or not os.access(workspace, os.W_OK):
            self.skipTest("/servidor/ark/workspace-offline is not writable in this environment")
        with tempfile.TemporaryDirectory(dir=workspace) as tmp:
            path = Path(tmp) / "window-manifest.env"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            fields = dict(line.split("=", 1) for line in lines if "=" in line)
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

    def test_accepts_approved_workspace_window_manifest_without_promoting_identity(self) -> None:
        result = self.run_checker_in_approved_workspace(manifest_lines())
        report = json.loads(result.stdout)

        self.assertTrue(report["ready"])
        self.assertTrue(report["operational_window_manifest_ready"])
        self.assertEqual(report["obelisk_commit"], "test-commit")
        self.assertEqual(report["copied_log"]["path_status"], "approved_offline_workspace")
        self.assertEqual(report["target"], {"instance": "arkserver2", "map": "TheIsland"})
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["remaining_blockers"], [])
        self.assertEqual(report["next_blocker"], "approved_runtime_observer_log_summary_and_manifest_missing")

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

    def test_rejects_non_exclusive_observer_window_escape_gates(self) -> None:
        result = self.run_checker(
            manifest_lines(
                wrapper_profile="stable",
                observer_exclusivity="chat_and_player_principal",
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
        self.assertIn("debug_escape_markers_not_absent", report["blockers"])
        self.assertIn("callback_escape_markers_not_absent", report["blockers"])
        self.assertIn("native_exec_disabled_not_true", report["blockers"])
        self.assertIn("ptrace_disabled_not_true", report["blockers"])
        self.assertIn("single_module_summary_not_player_principal_lifecycle", report["blockers"])

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
