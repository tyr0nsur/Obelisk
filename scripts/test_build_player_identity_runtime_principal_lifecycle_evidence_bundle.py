#!/usr/bin/env python3
"""Tests for build_player_identity_runtime_principal_lifecycle_evidence_bundle.py."""

from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import check_player_identity_first_evidence_readiness as first_evidence_checker
import build_player_identity_runtime_principal_lifecycle_evidence_bundle as bundle_builder
from prepare_player_principal_lifecycle_window_request import (
    APPROVAL_TEXT,
    EXPECTED_BINARY_SHA256,
    EXPECTED_SERVER_BINARY_PATH,
    FORBIDDEN_MARKERS,
    NON_CLAIMS,
    WINDOW_MARKERS,
    env_lines,
    operator_live_ops_brief,
)

BUNDLE = SCRIPT_DIR / "build_player_identity_runtime_principal_lifecycle_evidence_bundle.py"
SHA = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
WINDOW_START = (datetime.now(timezone.utc) + timedelta(hours=1)).replace(microsecond=0)
RUN_ID = WINDOW_START.strftime("%Y%m%dT%H%M%SZ") + "-player-principal-lifecycle"
OFFLINE_WORKSPACE = Path("/servidor/ark/workspace-offline")
TEST_COMMIT = "1234567890abcdef1234567890abcdef12345678"
OTHER_TEST_COMMIT = "abcdef1234567890abcdef1234567890abcdef12"


def future_window() -> dict[str, str]:
    start = WINDOW_START
    actual_start = start + timedelta(minutes=1)
    actual_end = start + timedelta(minutes=9)
    end = start + timedelta(minutes=10)
    return {
        "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "actual_start": actual_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "actual_end": actual_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def runtime_log_lines() -> list[str]:
    return [
        "[info]  Obelisk Runtime Loaded Native (LD_PRELOAD)",
        "[info] ProcessEvent vtable-derived pattern candidates found: 1",
        "[info] ProcessEvent candidate[0] = 0x1d34e20",
        "[info] Found ProcessEvent at address: 0x1d34e20",
        "[info] ProcessEvent absolute x64 hook installed successfully. patch_size=18 trampoline=0x767c6aaa4000",
        "[info] ReflectionScanner disabled. Set OBELISK_ENABLE_REFLECTION_SCANNER=1 to run the experimental scanner.",
        "[warning] Plugin loading disabled by OBELISK_DISABLE_PLUGINS=1.",
        f"[info] PlayerPrincipalLifecycleObserver enabled binary_sha256={SHA} "
        "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
        "delivery_claim=none principal_claim=none.",
        "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start "
        "target=ShooterGameMode.HandleNewPlayer post_original=true "
        "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
        "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
        "principal_action=candidate_created principal_id_logged=false "
        "principal_generation_logged=false delivery_claim=none.",
        "[info] PlayerPrincipalLifecycleObserver event sequence=2 role=session_start_rejected "
        "target=ShooterGameMode.HandleNewPlayer post_original=true "
        "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=0,1 "
        "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
        "principal_action=none principal_id_logged=false principal_generation_logged=false "
        "delivery_claim=none.",
        "[info] PlayerPrincipalLifecycleObserver event sequence=3 role=session_end "
        "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
        "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
        "principal_action=candidate_invalidated principal_id_logged=false "
        "principal_generation_logged=false delivery_claim=none.",
    ]


def copied_log_path(root: Path) -> Path:
    return root / "live-validation-logs" / RUN_ID / "Obelisk.log"


def write_sidecar(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preflight_payload(
    *,
    mode: str,
    instance: str,
    env_file: Path | None = None,
    env_sha256: str | None = None,
) -> str:
    payload = {
        "schema": "obelisk.player-principal-lifecycle-preflight.v1",
        "ready": True,
        "mode": mode,
        "instance": instance,
        "map": None,
        "server_binary": {
            "path": "/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer",
            "sha256": SHA,
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
        "posture_check": "accepted",
        "non_claim": "preflight only; not runtime approval and not permission to touch servers",
    }
    return json.dumps(payload, sort_keys=True) + "\n"


class BuildRuntimePrincipalLifecycleEvidenceBundleTests(unittest.TestCase):
    def temp_offline_workspace(self) -> tempfile.TemporaryDirectory[str]:
        if not OFFLINE_WORKSPACE.is_dir():
            self.skipTest(f"approved offline workspace missing: {OFFLINE_WORKSPACE}")
        return tempfile.TemporaryDirectory(prefix="obelisk-test-player-principal-", dir=OFFLINE_WORKSPACE)

    def write_window_manifest(self, temp_dir: Path, copied_log: Path) -> Path:
        manifest = temp_dir / "live-validation-logs" / RUN_ID / "window-manifest.env"
        copied_log_sha256 = (
            hashlib.sha256(copied_log.read_bytes()).hexdigest()
            if copied_log.is_file()
            else "0000000000000000000000000000000000000000000000000000000000000000"
        )
        sidecar_dir = temp_dir / "player-principal-preflight" / RUN_ID
        request_pack = sidecar_dir / "window-request.json"
        observer_env = sidecar_dir / "observer-window.env"
        preflight_pre = manifest.parent / "preflight-pre.json"
        preflight_post = manifest.parent / "preflight-post.json"
        window = future_window()
        request_args = type(
            "Args",
            (),
            {
                "instance": "arkserver2",
                "map_name": "TheIsland",
                "binary_sha256": EXPECTED_BINARY_SHA256,
            },
        )()
        observer_env_sha256 = write_sidecar(
            observer_env,
            "\n".join(env_lines(request_args))
            + "\n",
        )
        request_payload = {
            "schema": "obelisk.player-principal-lifecycle-window-request.v1",
            "run_id": RUN_ID,
            "status": "candidate_only_request_pack",
            "approval_required": APPROVAL_TEXT,
            "ark_binary_sha256": EXPECTED_BINARY_SHA256,
            "server_binary_path": EXPECTED_SERVER_BINARY_PATH,
            "obelisk_commit": TEST_COMMIT,
            "target": {"instance": "arkserver2", "map": "TheIsland"},
            "approved_window": {
                "start_utc": window["start"],
                "end_utc": window["end"],
            },
            "restart_expectation": "restart",
            "final_posture": "stable",
            "user_policy": "no_regular_users",
            "notice_path": "not_applicable",
            "copied_evidence_dir": str(copied_log.parent),
            "copied_log_path": str(copied_log),
            "window_manifest_path": str(manifest),
            "observer_env_file": "observer-window.env",
            "marker_set": WINDOW_MARKERS,
            "forbidden_markers": FORBIDDEN_MARKERS,
            "rollback": {
                "owner": "operator",
                "delta": "remove observer env and markers, preserve stable enable-process-event-hook and disable-plugins",
            },
            "non_claims": NON_CLAIMS,
        }
        request_payload["operator_live_ops_brief"] = operator_live_ops_brief(
            request_payload,
            env_lines(request_args),
        )
        request_pack_sha256 = write_sidecar(
            request_pack,
            json.dumps(request_payload, sort_keys=True) + "\n",
        )
        preflight_pre_sha256 = write_sidecar(
            preflight_pre,
            preflight_payload(
                mode="observer-window",
                instance="arkserver2",
                env_file=observer_env,
                env_sha256=observer_env_sha256,
            ),
        )
        preflight_post_sha256 = write_sidecar(
            preflight_post,
            preflight_payload(mode="stable", instance="arkserver2"),
        )
        manifest.write_text(
            "\n".join(
                [
                    f"run_id={RUN_ID}",
                    f"obelisk_commit={TEST_COMMIT}",
                    "target=arkserver2/TheIsland",
                    "approval=current-turn operator-approved runtime window, not standing approval",
                    f"approved_window_start_utc={window['start']}",
                    f"approved_window_end_utc={window['end']}",
                    f"actual_capture_start_utc={window['actual_start']}",
                    f"actual_capture_end_utc={window['actual_end']}",
                    f"copied_log_path={copied_log}",
                    f"copied_log_sha256={copied_log_sha256}",
                    f"request_pack_path={request_pack}",
                    f"request_pack_sha256={request_pack_sha256}",
                    f"observer_env_path={observer_env}",
                    f"observer_env_sha256={observer_env_sha256}",
                    f"preflight_pre_path={preflight_pre}",
                    f"preflight_pre_sha256={preflight_pre_sha256}",
                    f"preflight_post_path={preflight_post}",
                    f"preflight_post_sha256={preflight_post_sha256}",
                    "pre_posture=stable",
                    "post_posture=stable",
                    "pre_check=passed",
                    "post_check=passed",
                    f"rollback_start_utc={window['actual_end']}",
                    f"rollback_end_utc={window['end']}",
                    "rollback_completed=true",
                    "rollback_delta=removed_observer_env_and_markers_preserved_disable_plugins",
                    "observer_env_survived=false",
                    "observer_marker_survived=false",
                    "user_policy=no_regular_users",
                    "notice_sent=not_applicable",
                    "log_budget=10",
                    "plugins_disabled=true",
                    "scanner_disabled=true",
                    "dispatch_limit=0",
                    "wrapper_profile=observer-debug",
                    "observer_exclusivity=player_principal_lifecycle_only",
                    "sibling_marker_entries=absent",
                    "sibling_observer_env=absent",
                    "debug_escape_markers=absent",
                    "callback_escape_markers=absent",
                    "native_exec_disabled=true",
                    "ptrace_disabled=true",
                    "single_module_summary=player_principal_lifecycle",
                    "delivery_claim=none",
                    "principal_claim=none",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return manifest

    def write_relative_window_manifest(self, temp_dir: Path, copied_log: Path) -> Path:
        manifest = self.write_window_manifest(temp_dir, copied_log)
        manifest.write_text(
            manifest.read_text(encoding="utf-8").replace(
                f"copied_log_path={copied_log}",
                f"copied_log_path={copied_log.relative_to(manifest.parent)}",
            ),
            encoding="utf-8",
        )
        return manifest

    def run_bundle(
        self,
        copied_log: Path,
        output_dir: Path,
        *,
        window_manifest: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if window_manifest is None:
            window_manifest = self.write_window_manifest(output_dir.parent, copied_log)
        env = os.environ.copy()
        env["OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES"] = "1"
        return subprocess.run(
            [
                sys.executable,
                str(BUNDLE),
                "--copied-log",
                str(copied_log),
                "--window-manifest",
                str(window_manifest),
                "--output-dir",
                str(output_dir),
                "--obelisk-commit",
                TEST_COMMIT,
                "--reviewed-by",
                "runtime-reviewer",
                "--review-note",
                "bounded redacted lifecycle observer summary accepted for consume-only review",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

    def run_preflight(self, evidence_dir: Path) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES"] = "1"
        return subprocess.run(
            [
                sys.executable,
                str(BUNDLE),
                "--preflight-only",
                "--evidence-dir",
                str(evidence_dir),
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

    def test_preflight_rejects_malformed_request_pack_sidecars_without_building(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            evidence_dir = temp_dir / "live-validation-logs" / RUN_ID
            sidecar_dir = evidence_dir / "sidecars" / RUN_ID
            sidecar_dir.mkdir(parents=True)
            (sidecar_dir / "window-request.json").write_text("{}", encoding="utf-8")
            (sidecar_dir / "observer-window.env").write_text("OBELISK_INSTANCE_ID=arkserver2\n", encoding="utf-8")
            (sidecar_dir / "preflight-pre.txt").write_text("preflight=ok\n", encoding="utf-8")
            (sidecar_dir / "preflight-post.txt").write_text("preflight=ok\n", encoding="utf-8")

            result = self.run_preflight(evidence_dir)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(
            report["schema"],
            "obelisk.players-identity-runtime-principal-lifecycle-evidence-bundle-preflight.v1",
        )
        self.assertFalse(report["ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertFalse(report["request_pack_ready"])
        self.assertFalse(report["request_pack_is_runtime_evidence"])
        self.assertFalse(report["approved_runtime_manifest_present"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertEqual(report["next_blocker"], "copied_log_and_window_manifest_required")
        self.assertEqual(
            [artifact["artifact"] for artifact in report["next_required_artifacts"]],
            [
                "copied_obelisk_log",
                "checked_window_manifest_env",
                "approved_runtime_principal_lifecycle_evidence_manifest",
            ],
        )
        self.assertEqual(
            [artifact["present"] for artifact in report["next_required_artifacts"]],
            [False, False, False],
        )
        self.assertIn("request_pack_check_failed", report["blockers"])
        self.assertIn("copied_log_missing", report["blockers"])
        self.assertIn("window_manifest_missing", report["blockers"])
        self.assertIn("approved_runtime_manifest_missing", report["blockers"])

    def test_preflight_accepts_builder_inputs_before_approved_manifest(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            self.write_window_manifest(temp_dir, copied_log)

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertTrue(report["ready"])
        self.assertTrue(report["bundle_inputs_ready"])
        self.assertFalse(report["request_pack_is_runtime_evidence"])
        self.assertFalse(report["approved_runtime_manifest_present"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertEqual(report["next_blocker"], "run_offline_evidence_bundle_builder")
        self.assertEqual(
            [artifact["present"] for artifact in report["next_required_artifacts"]],
            [True, True, False],
        )
        self.assertTrue(report["next_required_artifacts"][2]["satisfies_approved_runtime_evidence"])
        self.assertNotIn("copied_log_missing", report["blockers"])
        self.assertNotIn("window_manifest_missing", report["blockers"])
        self.assertIn(
            "ready means the offline bundle builder has the copied inputs it needs; it does not mean approved runtime evidence already exists",
            report["non_claims"],
        )

    def test_preflight_rejects_bad_request_pack_even_with_log_and_manifest_inputs(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            manifest = self.write_window_manifest(temp_dir, copied_log)
            fields = dict(
                line.split("=", 1)
                for line in manifest.read_text(encoding="utf-8").splitlines()
                if line and not line.startswith("#")
            )
            request_pack = Path(fields["request_pack_path"])
            request_pack.write_text("{}", encoding="utf-8")
            fields["request_pack_sha256"] = hashlib.sha256(request_pack.read_bytes()).hexdigest()
            manifest.write_text(
                "\n".join(f"{key}={value}" for key, value in fields.items()) + "\n",
                encoding="utf-8",
            )

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertTrue(report["bundle_inputs_ready"])
        self.assertFalse(report["request_pack_ready"])
        self.assertIn("request_pack_check_failed", report["blockers"])
        self.assertIn("window_manifest_check_failed", report["blockers"])

    def test_builds_complete_consume_only_bundle(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")

            result = self.run_bundle(copied_log, output_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["status"], "accepted")
            self.assertEqual(report["summary_modules"], ["player_principal_lifecycle"])
            self.assertFalse(report["promotion_ready"])
            self.assertFalse(report["public_sdk_ready"])
            self.assertFalse(report["runtime_ready"])
            self.assertEqual(
                report["negative_readiness_checks"],
                {
                    "promote_ready": False,
                    "public_readiness_ready": False,
                    "runtime_readiness_ready": False,
                },
            )
            self.assertEqual(report["consume_gate_status"], "accepted")
            self.assertTrue((output_dir / "runtime-observer-summary.json").is_file())
            self.assertTrue((output_dir / "player-principal-lifecycle-window-manifest.check.json").is_file())
            self.assertTrue((output_dir / "approved-runtime-principal-lifecycle-evidence.json").is_file())
            self.assertTrue((output_dir / "approved-runtime-principal-lifecycle-evidence.check.json").is_file())
            self.assertTrue((output_dir / "approved-runtime-principal-lifecycle-evidence.promote-check.json").is_file())
            self.assertTrue((output_dir / "approved-runtime-principal-lifecycle-evidence.public-readiness-check.json").is_file())
            self.assertTrue((output_dir / "approved-runtime-principal-lifecycle-evidence.runtime-readiness-check.json").is_file())
            self.assertTrue((output_dir / "approved-runtime-principal-lifecycle-evidence.consume-gate.json").is_file())
            self.assertTrue((output_dir / "evidence-bundle-report.json").is_file())
            for output_name, output in report["outputs"].items():
                output_path = Path(output["path"])
                self.assertTrue(output_path.is_file(), output_name)
                self.assertEqual(output["sha256"], hashlib.sha256(output_path.read_bytes()).hexdigest())
            identity = report["bundle_report_identity"]
            self.assertEqual(
                identity["artifact_kind"],
                "obelisk.players-identity-runtime-principal-lifecycle-evidence-bundle.v1",
            )
            self.assertEqual(
                identity["capture_id"],
                RUN_ID,
            )
            self.assertTrue(report["operational_window"]["manifest_ready"])
            self.assertEqual(report["operational_window"]["obelisk_commit"], TEST_COMMIT)

    def test_rejects_placeholder_cli_obelisk_commit(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            result = self.run_bundle(copied_log, output_dir)
            command = result.args
            command[command.index("--obelisk-commit") + 1] = "test-commit"
            placeholder = subprocess.run(
                command,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, "OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"},
            )

        self.assertNotEqual(placeholder.returncode, 0)
        self.assertIn("--obelisk-commit must be a reviewed 40-character lowercase Git SHA", placeholder.stderr)

    def test_builds_bundle_with_relative_window_manifest_log_path(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_relative_window_manifest(temp_dir, copied_log)

            result = self.run_bundle(copied_log, output_dir, window_manifest=window_manifest)

            self.assertEqual(result.returncode, 0, result.stderr)
            window_check = json.loads(
                (output_dir / "player-principal-lifecycle-window-manifest.check.json").read_text(encoding="utf-8")
            )
            self.assertEqual(window_check["copied_log"]["path"], str(copied_log.resolve()))

    def test_generated_bundle_manifest_clears_first_evidence_runtime_blocker_only(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")

            result = self.run_bundle(copied_log, output_dir)
            self.assertEqual(result.returncode, 0, result.stderr)

            old_env = os.environ.get("OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES")
            os.environ["OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES"] = "1"
            try:
                diagnosis = first_evidence_checker.approved_runtime_principal_lifecycle_evidence_manifest_diagnosis(
                    output_dir / "approved-runtime-principal-lifecycle-evidence.json"
                )
            finally:
                if old_env is None:
                    os.environ.pop("OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES", None)
                else:
                    os.environ["OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES"] = old_env
            if not (
                first_evidence_checker.APPROVED_CANDIDATE_ROOT_FALLBACK.is_dir()
                and first_evidence_checker.APPROVED_LIFECYCLE_ANCHOR_CANDIDATES_FALLBACK.is_file()
                and first_evidence_checker.APPROVED_PRINCIPAL_INVALIDATION_POLICY_FALLBACK.is_file()
            ):
                self.skipTest("approved workspace first-evidence fallbacks are not available")
            preflight = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "check_player_identity_first_evidence_readiness.py"),
                    "--json",
                    "--approved-runtime-principal-lifecycle-evidence-manifest",
                    str(output_dir / "approved-runtime-principal-lifecycle-evidence.json"),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, "OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"},
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
            ["observer_enable", "session_start_anchor", "session_start_rejected_anchor", "session_end_anchor"],
        )
        self.assertEqual(
            diagnosis["consumer_cases"],
            ["malformed_or_unsupported_evidence", "stale_after_logout"],
        )
        report = json.loads(preflight.stdout)
        approved = report["first_evidence"]["approved_runtime_principal_lifecycle_evidence_manifest"]
        self.assertTrue(approved["ready"])
        self.assertTrue(approved["approved_runtime_evidence_present"])
        self.assertTrue(approved["runtime_evidence_ready"])
        self.assertEqual(approved["remaining_blockers"], [])
        self.assertNotIn("approved_runtime_evidence_missing", report["blockers"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_fails_closed_for_live_server_log_path(self) -> None:
        with self.temp_offline_workspace() as temp:
            result = self.run_bundle(
                Path("/servidor/ark/obelisk/logs/arkserver2/Obelisk.log"),
                Path(temp) / "bundle",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--copied-log must be an offline copy, not a live server path", result.stderr)

    def test_rejects_live_copied_log_before_analysis_even_with_offline_manifest(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)
            output_dir = temp_dir / "bundle"

            result = self.run_bundle(
                Path("/servidor/ark/obelisk/logs/arkserver2/Obelisk.log"),
                output_dir,
                window_manifest=window_manifest,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--copied-log must be an offline copy, not a live server path", result.stderr)
            self.assertFalse((output_dir / "runtime-observer-summary.json").exists())

    def test_rejects_protected_output_dir_before_writing(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)

            result = self.run_bundle(
                copied_log,
                Path("/servidor/ark/obelisk/player-principal-bundle"),
                window_manifest=window_manifest,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--output-dir must not write under protected server root", result.stderr)
            self.assertFalse((temp_dir / "runtime-observer-summary.json").exists())

    def test_rejects_symlinked_output_dir_before_writing(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)
            target = temp_dir / "real-output-root"
            target.mkdir()
            link = temp_dir / "linked-output-root"
            link.symlink_to(target, target_is_directory=True)

            result = self.run_bundle(copied_log, link / "bundle", window_manifest=window_manifest)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--output-dir must not be a symlink", result.stderr)
            self.assertFalse((target / "bundle" / "runtime-observer-summary.json").exists())

    def test_fails_closed_for_events_before_safe_gate(self) -> None:
        lines = runtime_log_lines()
        lines.insert(
            7,
            "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start "
            "target=ShooterGameMode.HandleNewPlayer post_original=true "
            "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
            "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
            "principal_action=candidate_created principal_id_logged=false "
            "principal_generation_logged=false delivery_claim=none.",
        )
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(lines) + "\n", encoding="utf-8")

            result = self.run_bundle(copied_log, output_dir)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("analyze_runtime_observer_log failed", result.stderr)
            self.assertIn("player_principal_event_before_safe_gate", result.stderr)

    def test_fails_closed_when_window_manifest_sha_does_not_match_log(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)
            text = window_manifest.read_text(encoding="utf-8")
            window_manifest.write_text(
                text.replace(
                    f"copied_log_sha256={hashlib.sha256(copied_log.read_bytes()).hexdigest()}",
                    "copied_log_sha256=0000000000000000000000000000000000000000000000000000000000000000",
                ),
                encoding="utf-8",
            )

            result = self.run_bundle(copied_log, output_dir, window_manifest=window_manifest)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("check player principal lifecycle window manifest failed", result.stderr)
            self.assertIn("copied_log_sha256_mismatch", result.stderr)

    def test_fails_closed_when_window_manifest_commit_does_not_match_summary(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)
            text = window_manifest.read_text(encoding="utf-8")
            window_manifest.write_text(
                text.replace(f"obelisk_commit={TEST_COMMIT}", f"obelisk_commit={OTHER_TEST_COMMIT}"),
                encoding="utf-8",
            )

            result = self.run_bundle(copied_log, output_dir, window_manifest=window_manifest)

            self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_pack_obelisk_commit_mismatch", result.stderr)

    def test_fails_closed_when_runtime_gate_limit_does_not_match_first_window_budget(self) -> None:
        lines = [
            line.replace("limit=10 dispatch_limit=0", "limit=9 dispatch_limit=0")
            for line in runtime_log_lines()
        ]
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(lines) + "\n", encoding="utf-8")

            result = self.run_bundle(copied_log, output_dir)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "runtime observer summary gate limit does not match exact first-window log budget",
                result.stderr,
            )

    def test_fails_closed_when_copied_log_does_not_confirm_plugins_disabled(self) -> None:
        lines = [
            line for line in runtime_log_lines()
            if "Plugin loading disabled by OBELISK_DISABLE_PLUGINS=1" not in line
        ]
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(lines) + "\n", encoding="utf-8")

            result = self.run_bundle(copied_log, output_dir)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "runtime observer summary plugins_disabled does not match approved copied-log posture",
                result.stderr,
            )
            self.assertFalse((output_dir / "approved-runtime-principal-lifecycle-evidence.json").exists())

    def test_fails_closed_when_copied_log_does_not_confirm_scanner_disabled(self) -> None:
        lines = [
            line for line in runtime_log_lines()
            if "ReflectionScanner disabled" not in line
        ]
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(lines) + "\n", encoding="utf-8")

            result = self.run_bundle(copied_log, output_dir)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "runtime observer summary reflection_scanner_disabled does not match approved copied-log posture",
                result.stderr,
            )
            self.assertFalse((output_dir / "approved-runtime-principal-lifecycle-evidence.json").exists())

    def test_rejects_negative_readiness_report_that_overclaims_public_sdk(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            bundle_builder.require_negative_readiness_report(
                {
                    "ready": False,
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                    "promotion_ready": False,
                    "public_sdk_ready": True,
                    "runtime_ready": False,
                    "blockers": ["public_readiness_blocked_until_identity_public_contract_gate"],
                    "next_blocker": "identity_public_contract_gate_missing",
                },
                "public-readiness approved runtime principal lifecycle evidence check",
                "public_readiness_blocked_until_identity_public_contract_gate",
            )

        self.assertIn("overclaims public_sdk_ready", str(raised.exception))

    def test_rejects_negative_readiness_report_with_wrong_blocker(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            bundle_builder.require_negative_readiness_report(
                {
                    "ready": False,
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                    "promotion_ready": False,
                    "public_sdk_ready": False,
                    "runtime_ready": False,
                    "blockers": ["approved_runtime_evidence_not_accepted"],
                    "next_blocker": "approved_runtime_evidence_not_accepted",
                },
                "promote approved runtime principal lifecycle evidence check",
                "promote_blocked_until_identity_public_contract_gate",
            )

        self.assertIn("failed for an unexpected blocker", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
