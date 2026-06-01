#!/usr/bin/env python3
"""Tests for build_player_identity_runtime_principal_lifecycle_evidence_bundle.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
BUNDLE = SCRIPT_DIR / "build_player_identity_runtime_principal_lifecycle_evidence_bundle.py"
SHA = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"


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


class BuildRuntimePrincipalLifecycleEvidenceBundleTests(unittest.TestCase):
    def run_bundle(self, copied_log: Path, output_dir: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(BUNDLE),
                "--copied-log",
                str(copied_log),
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
            copied_log = temp_dir / "Obelisk.log"
            output_dir = temp_dir / "bundle"
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
            self.assertTrue((output_dir / "approved-runtime-principal-lifecycle-evidence.json").is_file())
            self.assertTrue((output_dir / "approved-runtime-principal-lifecycle-evidence.check.json").is_file())
            self.assertTrue((output_dir / "approved-runtime-principal-lifecycle-evidence.promote-check.json").is_file())
            self.assertTrue((output_dir / "approved-runtime-principal-lifecycle-evidence.public-readiness-check.json").is_file())
            self.assertTrue((output_dir / "approved-runtime-principal-lifecycle-evidence.runtime-readiness-check.json").is_file())
            self.assertTrue((output_dir / "approved-runtime-principal-lifecycle-evidence.consume-gate.json").is_file())
            self.assertTrue((output_dir / "evidence-bundle-report.json").is_file())

    def test_fails_closed_for_live_server_log_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_bundle(
                Path("/servidor/ark/obelisk/logs/arkserver2/Obelisk.log"),
                Path(temp) / "bundle",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("analyze_runtime_observer_log failed", result.stderr)

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
            copied_log = temp_dir / "Obelisk.log"
            output_dir = temp_dir / "bundle"
            copied_log.write_text("\n".join(lines) + "\n", encoding="utf-8")

            result = self.run_bundle(copied_log, output_dir)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("analyze_runtime_observer_log failed", result.stderr)
            self.assertIn("player_principal_event_before_safe_gate", result.stderr)


if __name__ == "__main__":
    unittest.main()
