#!/usr/bin/env python3
"""Tests for build_player_identity_runtime_principal_lifecycle_evidence_bundle.py."""

from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
BUNDLE = SCRIPT_DIR / "build_player_identity_runtime_principal_lifecycle_evidence_bundle.py"
SHA = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
RUN_ID = "20260601T120000Z-player-principal-lifecycle"


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
    return root / RUN_ID / "Obelisk.log"


class BuildRuntimePrincipalLifecycleEvidenceBundleTests(unittest.TestCase):
    def write_window_manifest(self, temp_dir: Path, copied_log: Path) -> Path:
        manifest = temp_dir / "window.env"
        copied_log_sha256 = (
            hashlib.sha256(copied_log.read_bytes()).hexdigest()
            if copied_log.is_file()
            else "0000000000000000000000000000000000000000000000000000000000000000"
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

    def run_bundle(
        self,
        copied_log: Path,
        output_dir: Path,
        *,
        window_manifest: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if window_manifest is None:
            window_manifest = self.write_window_manifest(output_dir.parent, copied_log)
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
        )

    def test_builds_complete_consume_only_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
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

    def test_fails_closed_for_live_server_log_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_bundle(
                Path("/servidor/ark/obelisk/logs/arkserver2/Obelisk.log"),
                Path(temp) / "bundle",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("check player principal lifecycle window manifest failed", result.stderr)

    def test_rejects_protected_output_dir_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
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
        with tempfile.TemporaryDirectory() as temp:
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
        with tempfile.TemporaryDirectory() as temp:
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
        with tempfile.TemporaryDirectory() as temp:
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
        with tempfile.TemporaryDirectory() as temp:
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
        with tempfile.TemporaryDirectory() as temp:
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


if __name__ == "__main__":
    unittest.main()
