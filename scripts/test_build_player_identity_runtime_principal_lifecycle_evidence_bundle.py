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
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import check_player_identity_first_evidence_readiness as first_evidence_checker
import build_player_identity_runtime_principal_lifecycle_evidence_bundle as bundle_builder

BUNDLE = SCRIPT_DIR / "build_player_identity_runtime_principal_lifecycle_evidence_bundle.py"
SHA = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
RUN_ID = "20260601T120000Z-player-principal-lifecycle"
OFFLINE_WORKSPACE = Path("/servidor/ark/workspace-offline")


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
        preflight_pre = manifest.parent / "preflight-pre.txt"
        preflight_post = manifest.parent / "preflight-post.txt"
        request_pack_sha256 = write_sidecar(
            request_pack,
            json.dumps(
                {
                    "schema": "obelisk.player-principal-lifecycle-window-request.v1",
                    "run_id": RUN_ID,
                    "status": "candidate_only_request_pack",
                    "obelisk_commit": "test-commit",
                    "target": {"instance": "arkserver2", "map": "TheIsland"},
                    "approved_window": {
                        "start_utc": "2026-06-01T12:00:00Z",
                        "end_utc": "2026-06-01T12:10:00Z",
                    },
                    "observer_env_file": "observer-window.env",
                },
                sort_keys=True,
            )
            + "\n",
        )
        observer_env_sha256 = write_sidecar(
            observer_env,
            "\n".join(
                [
                    "OBELISK_WRAPPER_PROFILE=observer-debug",
                    "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1",
                    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0",
                    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10",
                ]
            )
            + "\n",
        )
        preflight_pre_sha256 = write_sidecar(
            preflight_pre,
            "player_principal_lifecycle_preflight=ok mode=observer-window instance=arkserver2\n",
        )
        preflight_post_sha256 = write_sidecar(
            preflight_post,
            "player_principal_lifecycle_preflight=ok mode=stable instance=arkserver2\n",
        )
        manifest.write_text(
            "\n".join(
                [
                    f"run_id={RUN_ID}",
                    "obelisk_commit=test-commit",
                    "target=arkserver2/TheIsland",
                    "approval=current-turn operator-approved runtime window, not standing approval",
                    "approved_window_start_utc=2026-06-01T12:00:00Z",
                    "approved_window_end_utc=2026-06-01T12:10:00Z",
                    "actual_capture_start_utc=2026-06-01T12:01:00Z",
                    "actual_capture_end_utc=2026-06-01T12:09:00Z",
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
                    "rollback_start_utc=2026-06-01T12:09:00Z",
                    "rollback_end_utc=2026-06-01T12:10:00Z",
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
                "test-commit",
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
            self.assertTrue(report["operational_window"]["manifest_ready"])
            self.assertEqual(report["operational_window"]["obelisk_commit"], "test-commit")

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

            diagnosis = first_evidence_checker.approved_runtime_principal_lifecycle_evidence_manifest_diagnosis(
                output_dir / "approved-runtime-principal-lifecycle-evidence.json"
            )
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
                text.replace("obelisk_commit=test-commit", "obelisk_commit=other-commit"),
                encoding="utf-8",
            )

            result = self.run_bundle(copied_log, output_dir, window_manifest=window_manifest)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("window manifest obelisk_commit does not match runtime observer summary", result.stderr)

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
